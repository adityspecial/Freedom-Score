from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import openai
import json

# Google Auth imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import jwt


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI setup
openai_api_key = os.environ.get('OPENAI_API_KEY')
if not openai_api_key:
    logging.warning("OPENAI_API_KEY not found in environment variables")
else:
    openai.api_key = openai_api_key

# Google OAuth setup
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'openid', 'email', 'profile']

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class CalendarAnalysisRequest(BaseModel):
    calendar_data: str
    time_period: Optional[str] = "this week"

class GoogleAuthRequest(BaseModel):
    token: str

class CalendarAnalysisResponse(BaseModel):
    independence_percentage: int
    witty_message: str
    detailed_analysis: str
    meeting_stats: dict
    recommendations: List[str]

class UserToken(BaseModel):
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    user_email: str
    user_name: str

# Helper functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, GOOGLE_CLIENT_ID, algorithms=['RS256'], options={"verify_signature": False})
        user_email = payload.get('email')
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # Get user from database
        user = await db.users.find_one({"user_email": user_email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")

def get_calendar_service(access_token: str):
    """Create Google Calendar service with access token"""
    credentials = Credentials(token=access_token)
    return build('calendar', 'v3', credentials=credentials)

def format_calendar_events(events: List[Dict]) -> str:
    """Format Google Calendar events into readable text for AI analysis"""
    if not events:
        return "No meetings found in the specified time period."
    
    formatted_events = []
    for event in events:
        summary = event.get('summary', 'No title')
        
        # Handle different date/time formats
        start = event.get('start', {})
        end = event.get('end', {})
        
        if 'dateTime' in start:
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            
            # Format times nicely
            start_str = start_time.strftime('%I:%M %p')
            end_str = end_time.strftime('%I:%M %p')
            date_str = start_time.strftime('%Y-%m-%d')
            
            formatted_events.append(f"{date_str} {start_str} - {end_str}: {summary}")
        elif 'date' in start:
            # All-day events
            formatted_events.append(f"{start['date']}: {summary} (All day)")
    
    return "\n".join(formatted_events)

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Meeting Oppression Calculator API with Google Calendar"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.post("/auth/google")
async def auth_google(request: GoogleAuthRequest):
    """Handle Google OAuth token from frontend"""
    try:
        # Decode the Google JWT token
        payload = jwt.decode(request.token, options={"verify_signature": False})
        
        user_email = payload.get('email')
        user_name = payload.get('name')
        user_id = payload.get('sub')
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        
        # For this demo, we'll create a simple JWT token
        # In production, you'd want proper JWT signing
        user_token = {
            "user_id": user_id,
            "user_email": user_email,
            "user_name": user_name,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        # Store user in database
        await db.users.update_one(
            {"user_email": user_email},
            {"$set": {
                "user_id": user_id,
                "user_email": user_email,
                "user_name": user_name,
                "last_login": datetime.utcnow()
            }},
            upsert=True
        )
        
        # Create a simple token (in production, use proper JWT signing)
        token = jwt.encode(user_token, "secret", algorithm="HS256")
        
        return {
            "access_token": token,
            "user": {
                "email": user_email,
                "name": user_name,
                "id": user_id
            }
        }
        
    except Exception as e:
        logging.error(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@api_router.get("/auth/google-calendar")
async def auth_google_calendar():
    """Initiate Google Calendar OAuth flow"""
    try:
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES
        )
        
        # Set redirect URI
        flow.redirect_uri = "https://33ce9b05-4933-4296-b96d-89a98e35c3ef.preview.emergentagent.com/api/auth/callback"
        
        # Generate OAuth URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return {"authorization_url": authorization_url, "state": state}
        
    except Exception as e:
        logging.error(f"OAuth flow error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create OAuth flow")

@api_router.get("/auth/callback")
async def auth_callback(code: str, state: str = None):
    """Handle OAuth callback"""
    try:
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES
        )
        
        flow.redirect_uri = "https://33ce9b05-4933-4296-b96d-89a98e35c3ef.preview.emergentagent.com/api/auth/callback"
        
        # Exchange code for token
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        user_email = user_info.get('email')
        user_name = user_info.get('name')
        user_id = user_info.get('id')
        
        # Store credentials in database
        await db.user_tokens.update_one(
            {"user_email": user_email},
            {"$set": {
                "user_id": user_id,
                "user_email": user_email,
                "user_name": user_name,
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_expiry": credentials.expiry,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )
        
        # Redirect to frontend with success
        return RedirectResponse(url="https://33ce9b05-4933-4296-b96d-89a98e35c3ef.preview.emergentagent.com/?auth=success")
        
    except Exception as e:
        logging.error(f"OAuth callback error: {str(e)}")
        return RedirectResponse(url="https://33ce9b05-4933-4296-b96d-89a98e35c3ef.preview.emergentagent.com/?auth=error")

@api_router.get("/calendar/events")
async def get_calendar_events(
    time_period: str = "this_week",
    user: dict = Depends(get_current_user)
):
    """Fetch calendar events for the authenticated user"""
    try:
        # Get user's stored credentials
        user_tokens = await db.user_tokens.find_one({"user_email": user["user_email"]})
        if not user_tokens or not user_tokens.get("access_token"):
            raise HTTPException(status_code=401, detail="Calendar access not authorized")
        
        # Calculate time range
        now = datetime.utcnow()
        if time_period == "today":
            time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
            time_max = time_min + timedelta(days=1)
        elif time_period == "this_week":
            days_since_monday = now.weekday()
            time_min = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            time_max = time_min + timedelta(days=7)
        elif time_period == "this_month":
            time_min = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = time_min.replace(month=time_min.month + 1) if time_min.month < 12 else time_min.replace(year=time_min.year + 1, month=1)
            time_max = next_month
        else:  # recent_days (last 7 days)
            time_min = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            time_max = now
        
        # Get calendar service
        service = get_calendar_service(user_tokens["access_token"])
        
        # Fetch events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return {
            "events": events,
            "count": len(events),
            "time_period": time_period,
            "time_range": {
                "start": time_min.isoformat(),
                "end": time_max.isoformat()
            }
        }
        
    except Exception as e:
        logging.error(f"Error fetching calendar events: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch calendar events")

@api_router.post("/analyze-calendar-auto", response_model=CalendarAnalysisResponse)
async def analyze_calendar_auto(
    time_period: str = "this_week",
    user: dict = Depends(get_current_user)
):
    """Automatically analyze user's calendar using Google Calendar API"""
    try:
        # Get user's calendar events
        events_data = await get_calendar_events(time_period, user)
        events = events_data["events"]
        
        # Format events for AI analysis
        calendar_data = format_calendar_events(events)
        
        if not calendar_data or calendar_data == "No meetings found in the specified time period.":
            return CalendarAnalysisResponse(
                independence_percentage=95,
                witty_message="You're 95% independent! Either you're living the dream or your calendar is broken. I'm betting on the dream.",
                detailed_analysis="Your calendar is remarkably free of meetings. You're either incredibly efficient at avoiding unnecessary meetings, or you've achieved the mythical state of 'meeting-free existence.' Either way, congratulations on reclaiming your time!",
                meeting_stats={
                    "total_meetings": 0,
                    "total_hours": 0,
                    "avg_meeting_length": 0,
                    "longest_meeting_free_block": "Your entire schedule"
                },
                recommendations=[
                    "Keep doing whatever you're doing!",
                    "Share your meeting avoidance secrets with colleagues",
                    "Use this free time for focused deep work",
                    "Consider if you're missing important collaborations"
                ]
            )
        
        # Analyze with AI
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        # Create the AI prompt for analyzing meeting oppression
        prompt = f"""
        You are a witty AI assistant that analyzes people's meeting schedules to calculate their "meeting oppression" level.

        Calendar Data for {time_period}:
        {calendar_data}

        Please analyze this calendar data and provide:
        1. An "independence percentage" (0-100%) - higher means less oppressed by meetings
        2. A witty, sarcastic message about their meeting situation (like "You're 38% independent. Take back your damn day.")
        3. Detailed analysis of their meeting patterns
        4. Basic meeting statistics (total meetings, hours in meetings, etc.)
        5. 3-5 actionable recommendations to reduce meeting oppression

        Consider factors like:
        - Meeting frequency and density
        - Back-to-back meetings
        - Meeting length and types
        - Time blocks for focused work
        - Meeting-free periods

        Respond in JSON format:
        {{
            "independence_percentage": <number>,
            "witty_message": "<sarcastic/witty message>",
            "detailed_analysis": "<2-3 paragraph analysis>",
            "meeting_stats": {{
                "total_meetings": <number>,
                "total_hours": <number>,
                "avg_meeting_length": <number>,
                "longest_meeting_free_block": "<description>"
            }},
            "recommendations": ["<recommendation 1>", "<recommendation 2>", ...]
        }}
        """

        # Call OpenAI API
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a witty meeting oppression calculator that helps people realize how much their calendar controls their life."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )

        # Parse the AI response
        ai_response = response.choices[0].message.content
        
        # Try to extract JSON from the response
        try:
            # Find JSON in the response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            json_str = ai_response[start_idx:end_idx]
            result = json.loads(json_str)
        except:
            # Fallback if JSON parsing fails
            result = {
                "independence_percentage": 50,
                "witty_message": "Your calendar is a hot mess, but at least you're consistently chaotic.",
                "detailed_analysis": "Your meeting schedule suggests you're stuck in corporate purgatory. Time to rebel.",
                "meeting_stats": {
                    "total_meetings": len(events),
                    "total_hours": "Too many",
                    "avg_meeting_length": "Eternal",
                    "longest_meeting_free_block": "Probably lunch"
                },
                "recommendations": [
                    "Block calendar time for actual work",
                    "Question every recurring meeting",
                    "Learn to say 'Could this be an email?'"
                ]
            }

        return CalendarAnalysisResponse(**result)

    except Exception as e:
        logging.error(f"Error analyzing calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@api_router.post("/analyze-calendar", response_model=CalendarAnalysisResponse)
async def analyze_calendar(request: CalendarAnalysisRequest):
    """Manual calendar analysis (legacy endpoint)"""
    try:
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        # Create the AI prompt for analyzing meeting oppression
        prompt = f"""
        You are a witty AI assistant that analyzes people's meeting schedules to calculate their "meeting oppression" level.

        Calendar Data for {request.time_period}:
        {request.calendar_data}

        Please analyze this calendar data and provide:
        1. An "independence percentage" (0-100%) - higher means less oppressed by meetings
        2. A witty, sarcastic message about their meeting situation (like "You're 38% independent. Take back your damn day.")
        3. Detailed analysis of their meeting patterns
        4. Basic meeting statistics (total meetings, hours in meetings, etc.)
        5. 3-5 actionable recommendations to reduce meeting oppression

        Consider factors like:
        - Meeting frequency and density
        - Back-to-back meetings
        - Meeting length and types
        - Time blocks for focused work
        - Meeting-free periods

        Respond in JSON format:
        {{
            "independence_percentage": <number>,
            "witty_message": "<sarcastic/witty message>",
            "detailed_analysis": "<2-3 paragraph analysis>",
            "meeting_stats": {{
                "total_meetings": <number>,
                "total_hours": <number>,
                "avg_meeting_length": <number>,
                "longest_meeting_free_block": "<description>"
            }},
            "recommendations": ["<recommendation 1>", "<recommendation 2>", ...]
        }}
        """

        # Call OpenAI API
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a witty meeting oppression calculator that helps people realize how much their calendar controls their life."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )

        # Parse the AI response
        ai_response = response.choices[0].message.content
        
        # Try to extract JSON from the response
        try:
            # Find JSON in the response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            json_str = ai_response[start_idx:end_idx]
            result = json.loads(json_str)
        except:
            # Fallback if JSON parsing fails
            result = {
                "independence_percentage": 50,
                "witty_message": "Your calendar is a hot mess, but at least you're consistently chaotic.",
                "detailed_analysis": "Your meeting schedule suggests you're stuck in corporate purgatory. Time to rebel.",
                "meeting_stats": {
                    "total_meetings": "Unknown",
                    "total_hours": "Too many",
                    "avg_meeting_length": "Eternal",
                    "longest_meeting_free_block": "Probably lunch"
                },
                "recommendations": [
                    "Block calendar time for actual work",
                    "Question every recurring meeting",
                    "Learn to say 'Could this be an email?'"
                ]
            }

        return CalendarAnalysisResponse(**result)

    except Exception as e:
        logging.error(f"Error analyzing calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()