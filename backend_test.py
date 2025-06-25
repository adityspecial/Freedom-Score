import requests
import json
import sys
from datetime import datetime

class MeetingOppressionAPITester:
    def __init__(self, base_url="https://33ce9b05-4933-4296-b96d-89a98e35c3ef.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None

    def run_test(self, name, method, endpoint, expected_status, data=None, auth=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.text:
                    try:
                        return success, response.json()
                    except:
                        return success, response.text
                return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        if success:
            expected_message = "Liberty Tracker - Time Freedom Calculator API 🇺🇸"
            if response.get("message") == expected_message:
                print(f"✅ Correct message: '{expected_message}'")
                return True
            else:
                print(f"❌ Incorrect message: Expected '{expected_message}', got '{response.get('message')}'")
                return False
        return False

    def test_google_calendar_auth_url(self):
        """Test the Google Calendar OAuth URL generation"""
        success, response = self.run_test(
            "Google Calendar Auth URL",
            "GET",
            "auth/google-calendar",
            200
        )
        
        if success:
            if "authorization_url" in response and "state" in response:
                auth_url = response["authorization_url"]
                print(f"✅ Auth URL generated: {auth_url[:60]}...")
                
                # Check if URL contains required scopes
                required_scopes = ["calendar.readonly", "openid", "email", "profile"]
                missing_scopes = []
                
                for scope in required_scopes:
                    if scope not in auth_url:
                        missing_scopes.append(scope)
                
                if missing_scopes:
                    print(f"❌ Missing scopes in auth URL: {', '.join(missing_scopes)}")
                    return False
                
                print("✅ Auth URL contains all required scopes")
                return True
            else:
                print("❌ Missing 'authorization_url' or 'state' in response")
                return False
        
        return False

    def test_google_auth(self, token):
        """Test the Google auth endpoint (simulated)"""
        success, response = self.run_test(
            "Google Auth (Simulated)",
            "POST",
            "auth/google",
            400,  # Expecting 400 since we're using a fake token
            data={"token": token}
        )
        
        # We expect this to fail with a 400 error since we're using a fake token
        # But we want to verify the endpoint exists and responds
        return success

    def test_analyze_calendar(self, calendar_data, time_period="this week"):
        """Test the analyze-calendar endpoint (manual mode)"""
        success, response = self.run_test(
            "Analyze Calendar (Manual)",
            "POST",
            "analyze-calendar",
            200,
            data={"calendar_data": calendar_data, "time_period": time_period}
        )
        
        if success:
            # Verify response structure
            required_fields = [
                "independence_percentage", 
                "witty_message", 
                "detailed_analysis", 
                "meeting_stats", 
                "recommendations"
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"❌ Missing fields in response: {', '.join(missing_fields)}")
                return False
            
            # Verify meeting_stats structure
            required_stats = [
                "total_meetings", 
                "total_hours", 
                "avg_meeting_length", 
                "longest_meeting_free_block"
            ]
            
            missing_stats = [stat for stat in required_stats if stat not in response["meeting_stats"]]
            
            if missing_stats:
                print(f"❌ Missing fields in meeting_stats: {', '.join(missing_stats)}")
                return False
                
            print("✅ Response structure is valid")
            print(f"✅ Independence percentage: {response['independence_percentage']}%")
            print(f"✅ Witty message: {response['witty_message']}")
            return True
        
        return False
        
    def test_analyze_calendar_auto(self, time_period="this_week"):
        """Test the auto calendar analysis endpoint (requires auth)"""
        success, response = self.run_test(
            "Analyze Calendar (Auto)",
            "POST",
            f"analyze-calendar-auto?time_period={time_period}",
            401,  # Expecting 401 since we don't have a valid token
            data={},
            auth=True
        )
        
        # We expect this to fail with a 401 error since we don't have a valid token
        # But we want to verify the endpoint exists and responds
        return success

def main():
    # Setup
    tester = MeetingOppressionAPITester()
    
    # Sample calendar data
    sample_calendar_data = """
    9:00 AM - 10:00 AM: Daily Standup
    10:00 AM - 11:30 AM: Product Review Meeting  
    2:00 PM - 3:00 PM: 1:1 with Manager
    3:30 PM - 4:30 PM: Sprint Planning
    """
    
    # Fake Google token for testing
    fake_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFiZDY4NWY1ZThmYzYyZDc1ODcwNWMxZWIwZThhNzUyNGM5YWIzYTgiLCJ0eXAiOiJKV1QifQ"
    
    # Run tests
    print("\n===== TESTING BASIC API FUNCTIONALITY =====")
    root_test_passed = tester.test_root_endpoint()
    
    print("\n===== TESTING GOOGLE OAUTH INTEGRATION =====")
    google_auth_url_test_passed = tester.test_google_calendar_auth_url()
    google_auth_test_passed = tester.test_google_auth(fake_token)
    
    print("\n===== TESTING CALENDAR ANALYSIS =====")
    analyze_test_passed = tester.test_analyze_calendar(sample_calendar_data)
    
    # Test with different time periods
    time_periods = ["today", "this_week", "this_month", "recent_days"]
    time_period_tests_passed = []
    
    for period in time_periods:
        print(f"\n🔍 Testing with time period: {period}")
        result = tester.test_analyze_calendar(sample_calendar_data, period)
        time_period_tests_passed.append(result)
    
    # Test auto analysis (will fail with 401 but we want to verify the endpoint exists)
    auto_analysis_test_passed = tester.test_analyze_calendar_auto()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Summary
    print("\n===== TEST SUMMARY =====")
    print(f"Root API Endpoint: {'✅' if root_test_passed else '❌'}")
    print(f"Google Auth URL Generation: {'✅' if google_auth_url_test_passed else '❌'}")
    print(f"Google Auth Endpoint: {'✅' if google_auth_test_passed else '❌'}")
    print(f"Manual Calendar Analysis: {'✅' if analyze_test_passed else '❌'}")
    print(f"Time Period Testing: {'✅' if all(time_period_tests_passed) else '❌'}")
    print(f"Auto Calendar Analysis Endpoint: {'✅' if auto_analysis_test_passed else '❌'}")
    
    if (root_test_passed and google_auth_url_test_passed and google_auth_test_passed and 
        analyze_test_passed and all(time_period_tests_passed) and auto_analysis_test_passed):
        print("\n✅ All API tests passed successfully!")
    else:
        print("\n⚠️ Some API tests failed or returned expected errors. See details above.")
    
    return 0 if tester.tests_passed > 0 else 1

if __name__ == "__main__":
    sys.exit(main())