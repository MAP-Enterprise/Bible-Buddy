#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Bible Buddy - Family Reading Night Reminder Feature
Testing against: https://bible-buddy-19.preview.emergentagent.com/api
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Base URL from frontend .env
BASE_URL = "https://bible-buddy-19.preview.emergentagent.com/api"

class ReadingNightTester:
    def __init__(self):
        self.session = None
        self.results = []
        self.auth_token = None
        
    async def create_session(self):
        """Create HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if details:
            print(f"  📝 {details}")
        self.results.append({"test": test_name, "success": success, "details": details})
    
    async def test_reading_night_preview(self):
        """Test 1: Reading Night Preview (public endpoint)"""
        try:
            url = f"{BASE_URL}/notifications/reading-night-preview"
            async with self.session.get(url) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Verify required fields are present and non-empty
                    required_fields = ["title", "reference", "theme", "summary", "icon", "colors", "week_number"]
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        self.log_result("Reading Night Preview", False, 
                                      f"Missing fields: {missing_fields}")
                        return
                    
                    # Verify field types and non-empty values
                    checks = [
                        (isinstance(data["title"], str) and len(data["title"]) > 0, "title should be non-empty string"),
                        (isinstance(data["reference"], str) and len(data["reference"]) > 0, "reference should be non-empty string"),
                        (isinstance(data["theme"], str) and len(data["theme"]) > 0, "theme should be non-empty string"),
                        (isinstance(data["summary"], str) and len(data["summary"]) > 0, "summary should be non-empty string"),
                        (isinstance(data["icon"], str) and len(data["icon"]) > 0, "icon should be non-empty string"),
                        (isinstance(data["colors"], list) and len(data["colors"]) == 2, "colors should be list of 2 strings"),
                        (isinstance(data["week_number"], int), "week_number should be integer"),
                        (all(isinstance(color, str) for color in data["colors"]), "all colors should be strings")
                    ]
                    
                    failed_checks = [msg for check, msg in checks if not check]
                    if failed_checks:
                        self.log_result("Reading Night Preview", False, 
                                      f"Field validation failed: {'; '.join(failed_checks)}")
                        return
                    
                    self.log_result("Reading Night Preview", True, 
                                  f"Title: {data['title']}, Reference: {data['reference']}, Theme: {data['theme']}, Week: {data['week_number']}")
                else:
                    self.log_result("Reading Night Preview", False, 
                                  f"HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Reading Night Preview", False, f"Exception: {str(e)}")
    
    async def test_reading_night_unauthenticated(self):
        """Test 2: Reading Night Settings - Unauthenticated Access"""
        try:
            # Test GET without auth
            get_url = f"{BASE_URL}/notifications/reading-night"
            async with self.session.get(get_url) as response:
                if response.status == 401:
                    get_result = True
                    get_details = "GET correctly returns 401"
                else:
                    get_result = False
                    get_details = f"GET expected 401, got {response.status}"
            
            # Test PUT without auth
            put_url = f"{BASE_URL}/notifications/reading-night"
            payload = {"enabled": True, "day": "friday", "hour": 19}
            async with self.session.put(put_url, json=payload) as response:
                if response.status == 401:
                    put_result = True
                    put_details = "PUT correctly returns 401"
                else:
                    put_result = False
                    put_details = f"PUT expected 401, got {response.status}"
            
            overall_success = get_result and put_result
            combined_details = f"{get_details}, {put_details}"
            
            self.log_result("Reading Night Settings - Unauthenticated", overall_success, combined_details)
                    
        except Exception as e:
            self.log_result("Reading Night Settings - Unauthenticated", False, f"Exception: {str(e)}")
    
    async def test_create_parent_account(self):
        """Test 3: Create a test parent account for authentication"""
        try:
            url = f"{BASE_URL}/auth/register"
            payload = {
                "name": "ReadingNightTester",
                "email": "readingnight@test.com",
                "password": "testpass123"
            }
            
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200 or response.status == 201:
                    if "token" in data:
                        self.auth_token = data["token"]
                        self.log_result("Create Parent Account", True, 
                                      f"Account created successfully, token received")
                    else:
                        self.log_result("Create Parent Account", False, 
                                      f"Account created but no token in response: {data}")
                else:
                    # Check if account already exists
                    if response.status == 400 and "already exists" in str(data).lower():
                        # Try to login instead
                        login_url = f"{BASE_URL}/auth/login"
                        login_payload = {"email": "readingnight@test.com", "password": "testpass123"}
                        async with self.session.post(login_url, json=login_payload) as login_response:
                            login_data = await login_response.json()
                            if login_response.status == 200 and "token" in login_data:
                                self.auth_token = login_data["token"]
                                self.log_result("Create Parent Account", True, 
                                              f"Account already exists, logged in successfully")
                            else:
                                self.log_result("Create Parent Account", False, 
                                              f"Login failed: HTTP {login_response.status}: {login_data}")
                    else:
                        self.log_result("Create Parent Account", False, 
                                      f"Signup failed: HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Create Parent Account", False, f"Exception: {str(e)}")
    
    async def test_reading_night_with_auth(self):
        """Test 4: Reading Night Settings - With Authentication"""
        if not self.auth_token:
            self.log_result("Reading Night Settings - With Auth", False, "No auth token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test GET with auth - should return default settings
            get_url = f"{BASE_URL}/notifications/reading-night"
            async with self.session.get(get_url, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    expected_defaults = {
                        "enabled": False,
                        "day": "friday", 
                        "hour": 19
                    }
                    
                    checks = [
                        (data.get("enabled") == expected_defaults["enabled"], f"enabled should be {expected_defaults['enabled']}"),
                        (data.get("day") == expected_defaults["day"], f"day should be {expected_defaults['day']}"),
                        (data.get("hour") == expected_defaults["hour"], f"hour should be {expected_defaults['hour']}")
                    ]
                    
                    failed_checks = [msg for check, msg in checks if not check]
                    if failed_checks:
                        get_success = False
                        get_details = f"Default values incorrect: {'; '.join(failed_checks)}"
                    else:
                        get_success = True
                        get_details = f"GET returns correct defaults: enabled={data['enabled']}, day={data['day']}, hour={data['hour']}"
                else:
                    get_success = False
                    get_details = f"GET failed: HTTP {response.status}: {data}"
            
            if not get_success:
                self.log_result("Reading Night Settings - With Auth", False, get_details)
                return
            
            # Test PUT with auth - update settings
            put_url = f"{BASE_URL}/notifications/reading-night"
            payload = {"enabled": True, "day": "saturday", "hour": 20}
            async with self.session.put(put_url, json=payload, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    if "saturday" in data.get("message", "").lower():
                        put_success = True
                        put_details = f"PUT successful: {data.get('message', 'Updated')}"
                    else:
                        put_success = False
                        put_details = f"PUT success but message doesn't mention Saturday: {data}"
                else:
                    put_success = False
                    put_details = f"PUT failed: HTTP {response.status}: {data}"
            
            if not put_success:
                self.log_result("Reading Night Settings - With Auth", False, f"{get_details}; {put_details}")
                return
            
            # Test GET again to verify changes
            async with self.session.get(get_url, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    expected_updated = {
                        "enabled": True,
                        "day": "saturday", 
                        "hour": 20
                    }
                    
                    checks = [
                        (data.get("enabled") == expected_updated["enabled"], f"enabled should be {expected_updated['enabled']}"),
                        (data.get("day") == expected_updated["day"], f"day should be {expected_updated['day']}"),
                        (data.get("hour") == expected_updated["hour"], f"hour should be {expected_updated['hour']}")
                    ]
                    
                    failed_checks = [msg for check, msg in checks if not check]
                    if failed_checks:
                        verify_success = False
                        verify_details = f"Updated values incorrect: {'; '.join(failed_checks)}"
                    else:
                        verify_success = True
                        verify_details = f"Settings updated correctly: enabled={data['enabled']}, day={data['day']}, hour={data['hour']}"
                else:
                    verify_success = False
                    verify_details = f"Verification GET failed: HTTP {response.status}: {data}"
            
            overall_success = get_success and put_success and verify_success
            combined_details = f"{get_details}; {put_details}; {verify_details}"
            
            self.log_result("Reading Night Settings - With Auth", overall_success, combined_details)
                    
        except Exception as e:
            self.log_result("Reading Night Settings - With Auth", False, f"Exception: {str(e)}")
    
    async def test_validation_tests(self):
        """Test 5: Validation Tests - Invalid Data"""
        if not self.auth_token:
            self.log_result("Validation Tests", False, "No auth token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            put_url = f"{BASE_URL}/notifications/reading-night"
            
            # Test invalid day
            invalid_day_payload = {"enabled": True, "day": "invalid_day", "hour": 19}
            async with self.session.put(put_url, json=invalid_day_payload, headers=headers) as response:
                data = await response.json()
                
                if response.status == 400:
                    invalid_day_success = True
                    invalid_day_details = "Invalid day correctly rejected with 400"
                else:
                    invalid_day_success = False
                    invalid_day_details = f"Invalid day expected 400, got {response.status}: {data}"
            
            # Test invalid hour
            invalid_hour_payload = {"enabled": True, "day": "friday", "hour": 25}
            async with self.session.put(put_url, json=invalid_hour_payload, headers=headers) as response:
                data = await response.json()
                
                if response.status == 400:
                    invalid_hour_success = True
                    invalid_hour_details = "Invalid hour correctly rejected with 400"
                else:
                    invalid_hour_success = False
                    invalid_hour_details = f"Invalid hour expected 400, got {response.status}: {data}"
            
            overall_success = invalid_day_success and invalid_hour_success
            combined_details = f"{invalid_day_details}; {invalid_hour_details}"
            
            self.log_result("Validation Tests", overall_success, combined_details)
                    
        except Exception as e:
            self.log_result("Validation Tests", False, f"Exception: {str(e)}")
    
    async def test_toggle_off(self):
        """Test 6: Toggle Off Reading Night"""
        if not self.auth_token:
            self.log_result("Toggle Off", False, "No auth token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Toggle off
            put_url = f"{BASE_URL}/notifications/reading-night"
            payload = {"enabled": False, "day": "saturday", "hour": 20}
            async with self.session.put(put_url, json=payload, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    toggle_success = True
                    toggle_details = f"Toggle off successful: {data.get('message', 'Updated')}"
                else:
                    toggle_success = False
                    toggle_details = f"Toggle off failed: HTTP {response.status}: {data}"
            
            if not toggle_success:
                self.log_result("Toggle Off", False, toggle_details)
                return
            
            # Verify enabled is false
            get_url = f"{BASE_URL}/notifications/reading-night"
            async with self.session.get(get_url, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    if data.get("enabled") == False:
                        verify_success = True
                        verify_details = "Verified enabled=false"
                    else:
                        verify_success = False
                        verify_details = f"Expected enabled=false, got enabled={data.get('enabled')}"
                else:
                    verify_success = False
                    verify_details = f"Verification failed: HTTP {response.status}: {data}"
            
            overall_success = toggle_success and verify_success
            combined_details = f"{toggle_details}; {verify_details}"
            
            self.log_result("Toggle Off", overall_success, combined_details)
                    
        except Exception as e:
            self.log_result("Toggle Off", False, f"Exception: {str(e)}")
    
    async def test_regression_tests(self):
        """Test 7: Regression Tests - Verify existing endpoints still work"""
        try:
            endpoints = [
                ("/story-of-the-week?age_tier=7-9", "Story of the Week"),
                ("/story-progress/test_child_123", "Story Progress"),
                ("/health", "Health Check")
            ]
            
            all_passed = True
            details = []
            
            for endpoint, name in endpoints:
                url = f"{BASE_URL}{endpoint}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        details.append(f"{name}: ✅")
                    else:
                        details.append(f"{name}: ❌ HTTP {response.status}")
                        all_passed = False
            
            self.log_result("Regression Tests", all_passed, "; ".join(details))
            
        except Exception as e:
            self.log_result("Regression Tests", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"🌙 FAMILY READING NIGHT REMINDER TEST SUMMARY")
        print(f"{'='*60}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print(f"\n🎉 CONCLUSION: {'ALL TESTS PASSED!' if failed_tests == 0 else f'{failed_tests} TESTS FAILED'}")
    
    async def run_all_tests(self):
        """Run all Family Reading Night Reminder tests"""
        print("🚀 Starting Family Reading Night Reminder Backend Tests")
        print(f"🌐 Testing against: {BASE_URL}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        await self.create_session()
        
        try:
            # Run tests in order
            await self.test_reading_night_preview()
            await self.test_reading_night_unauthenticated()
            await self.test_create_parent_account()
            await self.test_reading_night_with_auth()
            await self.test_validation_tests()
            await self.test_toggle_off()
            await self.test_regression_tests()
            
        finally:
            await self.close_session()
        
        self.print_summary()

async def main():
    """Main test execution"""
    tester = ReadingNightTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())