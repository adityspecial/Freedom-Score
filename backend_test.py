import requests
import json
import sys
from datetime import datetime

class MeetingOppressionAPITester:
    def __init__(self, base_url="https://33ce9b05-4933-4296-b96d-89a98e35c3ef.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
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
            expected_message = "Meeting Oppression Calculator API"
            if response.get("message") == expected_message:
                print(f"✅ Correct message: '{expected_message}'")
                return True
            else:
                print(f"❌ Incorrect message: Expected '{expected_message}', got '{response.get('message')}'")
                return False
        return False

    def test_analyze_calendar(self, calendar_data, time_period="this week"):
        """Test the analyze-calendar endpoint"""
        success, response = self.run_test(
            "Analyze Calendar",
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
    
    # Run tests
    root_test_passed = tester.test_root_endpoint()
    
    analyze_test_passed = tester.test_analyze_calendar(sample_calendar_data)
    
    # Test with different time periods
    time_periods = ["today", "this week", "this month", "recent days"]
    time_period_tests_passed = []
    
    for period in time_periods:
        print(f"\n🔍 Testing with time period: {period}")
        result = tester.test_analyze_calendar(sample_calendar_data, period)
        time_period_tests_passed.append(result)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Summary
    if root_test_passed and analyze_test_passed and all(time_period_tests_passed):
        print("\n✅ All API tests passed successfully!")
    else:
        print("\n❌ Some API tests failed. See details above.")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())