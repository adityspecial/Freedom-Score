from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import openai


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

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


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

class CalendarAnalysisResponse(BaseModel):
    independence_percentage: int
    witty_message: str
    detailed_analysis: str
    meeting_stats: dict
    recommendations: List[str]

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Meeting Oppression Calculator API"}

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

@api_router.post("/analyze-calendar", response_model=CalendarAnalysisResponse)
async def analyze_calendar(request: CalendarAnalysisRequest):
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
        import json
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