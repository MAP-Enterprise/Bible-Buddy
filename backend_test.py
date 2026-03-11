#!/usr/bin/env python3
"""
Bible Story of the Week - Backend API Testing

This script tests the Bible Story of the Week feature for the Bible Buddy app
as specified in the review request.

Test Requirements:
1. Test `/api/story-of-the-week` endpoint
2. Test caching behavior
3. Test other existing endpoints for regression
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Backend URL from frontend environment configuration
BACKEND_URL = "https://bible-buddy-19.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"

class BibleStoryTester:
    def __init__(self):
        self.session = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, success: bool, message: str, details: dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    async def test_story_endpoint_with_age_tiers(self):
        """Test 1: /api/story-of-the-week endpoint with different age tiers"""
        print("\n🧪 Testing /api/story-of-the-week endpoint...")
        
        age_tiers = ["7-9", "4-6", "13-18", None]  # None tests default
        required_fields = ["week_key", "week_number", "title", "reference", "characters", 
                          "theme", "icon", "colors", "summary", "narrative", 
                          "discussion_questions", "age_tier"]
        
        for i, age_tier in enumerate(age_tiers):
            test_name = f"story_endpoint_age_tier_{age_tier or 'default'}"
            
            try:
                url = f"{API_BASE_URL}/story-of-the-week"
                if age_tier:
                    url += f"?age_tier={age_tier}"
                
                async with self.session.get(url) as response:
                    if response.status != 200:
                        self.log_test(test_name, False, 
                                    f"Expected 200, got {response.status}", 
                                    {"status_code": response.status})
                        continue
                    
                    data = await response.json()
                    
                    # Verify all required fields are present
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        self.log_test(test_name, False, 
                                    f"Missing fields: {missing_fields}", 
                                    {"missing_fields": missing_fields})
                        continue
                    
                    # Verify specific field types and constraints
                    issues = []
                    
                    # Verify narrative is a non-empty string
                    if not isinstance(data.get("narrative"), str) or len(data["narrative"].strip()) == 0:
                        issues.append("narrative is not a non-empty string")
                    
                    # Verify discussion_questions is a list with exactly 3 items
                    discussion_questions = data.get("discussion_questions", [])
                    if not isinstance(discussion_questions, list) or len(discussion_questions) != 3:
                        issues.append(f"discussion_questions must be list with 3 items, got {len(discussion_questions)} items")
                    
                    # Verify characters is a non-empty list
                    characters = data.get("characters", [])
                    if not isinstance(characters, list) or len(characters) == 0:
                        issues.append("characters must be non-empty list")
                    
                    # Verify colors is a list with 2 color strings
                    colors = data.get("colors", [])
                    if not isinstance(colors, list) or len(colors) != 2:
                        issues.append(f"colors must be list with 2 items, got {len(colors)} items")
                    
                    # Verify week_number is an integer between 1-52
                    week_number = data.get("week_number")
                    if not isinstance(week_number, int) or not (1 <= week_number <= 52):
                        issues.append(f"week_number must be integer 1-52, got {week_number}")
                    
                    # Verify age_tier
                    expected_age_tier = age_tier or "7-9"  # Default should be 7-9
                    if data.get("age_tier") != expected_age_tier:
                        issues.append(f"age_tier mismatch: expected {expected_age_tier}, got {data.get('age_tier')}")
                    
                    if issues:
                        self.log_test(test_name, False, 
                                    f"Field validation issues: {'; '.join(issues)}", 
                                    {"issues": issues, "response": data})
                    else:
                        # Success - store data for caching test
                        if i == 0:  # First test (age_tier=7-9)
                            self.first_response = data
                        
                        self.log_test(test_name, True, 
                                    f"All fields valid for age tier {expected_age_tier}", 
                                    {
                                        "week_number": data["week_number"],
                                        "title": data["title"],
                                        "narrative_length": len(data["narrative"]),
                                        "discussion_questions_count": len(discussion_questions),
                                        "characters_count": len(characters)
                                    })
                        
                        # Verify age-appropriate differences
                        if age_tier == "4-6":
                            # Should have simpler narrative for younger children
                            pass  # This is subjective, but we can check it exists
                        elif age_tier == "13-18":
                            # Should have more sophisticated narrative for teens
                            pass  # This is subjective, but we can check it exists
                            
            except Exception as e:
                self.log_test(test_name, False, f"Exception: {str(e)}", {"error": str(e)})
    
    async def test_caching_behavior(self):
        """Test 2: Verify caching behavior"""
        print("\n🧪 Testing caching behavior...")
        
        try:
            # Make first request and record timing
            start_time = time.time()
            async with self.session.get(f"{API_BASE_URL}/story-of-the-week?age_tier=7-9") as response1:
                first_duration = time.time() - start_time
                if response1.status != 200:
                    self.log_test("caching_first_request", False, 
                                f"First request failed with status {response1.status}")
                    return
                
                first_data = await response1.json()
            
            # Make second request immediately and record timing
            start_time = time.time()
            async with self.session.get(f"{API_BASE_URL}/story-of-the-week?age_tier=7-9") as response2:
                second_duration = time.time() - start_time
                if response2.status != 200:
                    self.log_test("caching_second_request", False, 
                                f"Second request failed with status {response2.status}")
                    return
                
                second_data = await response2.json()
            
            # Verify same week_key and narrative (should be identical from cache)
            week_key_match = first_data.get("week_key") == second_data.get("week_key")
            narrative_match = first_data.get("narrative") == second_data.get("narrative")
            
            if not week_key_match:
                self.log_test("caching_verification", False, 
                            "week_key mismatch between requests", 
                            {
                                "first_week_key": first_data.get("week_key"),
                                "second_week_key": second_data.get("week_key")
                            })
                return
            
            if not narrative_match:
                self.log_test("caching_verification", False, 
                            "narrative mismatch between requests (not cached)", 
                            {
                                "first_narrative_length": len(first_data.get("narrative", "")),
                                "second_narrative_length": len(second_data.get("narrative", ""))
                            })
                return
            
            # Second request should be faster (cached)
            # Note: This might not always be true due to network variability, but we can log it
            self.log_test("caching_verification", True, 
                        "Caching verified - identical responses", 
                        {
                            "week_key": first_data.get("week_key"),
                            "first_request_time": f"{first_duration:.3f}s",
                            "second_request_time": f"{second_duration:.3f}s",
                            "cached_faster": second_duration < first_duration
                        })
                        
        except Exception as e:
            self.log_test("caching_verification", False, f"Exception: {str(e)}", {"error": str(e)})
    
    async def test_health_endpoint(self):
        """Test 3: /api/health endpoint still works"""
        print("\n🧪 Testing /api/health endpoint...")
        
        try:
            async with self.session.get(f"{API_BASE_URL}/health") as response:
                if response.status != 200:
                    self.log_test("health_endpoint", False, 
                                f"Expected 200, got {response.status}")
                    return
                
                data = await response.json()
                required_fields = ["status", "llm_configured", "tts_configured", "stt_configured", "knowledge_base_size"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("health_endpoint", False, 
                                f"Missing fields: {missing_fields}", 
                                {"response": data})
                else:
                    self.log_test("health_endpoint", True, 
                                "Health endpoint working correctly", 
                                {"response": data})
                    
        except Exception as e:
            self.log_test("health_endpoint", False, f"Exception: {str(e)}", {"error": str(e)})
    
    async def test_regression_endpoints(self):
        """Test 4: Other existing endpoints still work (regression)"""
        print("\n🧪 Testing existing endpoints for regression...")
        
        endpoints_to_test = [
            ("verse_of_the_day", "/verse-of-the-day?age_tier=7-9"),
            ("verse_challenge", "/verse-challenge?age_tier=7-9"),
            ("voices", "/voices"),
        ]
        
        for test_name, endpoint in endpoints_to_test:
            try:
                async with self.session.get(f"{API_BASE_URL}{endpoint}") as response:
                    if response.status != 200:
                        self.log_test(f"regression_{test_name}", False, 
                                    f"Expected 200, got {response.status}")
                        continue
                    
                    data = await response.json()
                    
                    # Basic validation that we got some data
                    if not data or not isinstance(data, dict):
                        self.log_test(f"regression_{test_name}", False, 
                                    "Empty or invalid response data")
                        continue
                    
                    # Endpoint-specific validation
                    if test_name == "verse_of_the_day":
                        required = ["date", "verse", "reference", "theme", "explanation"]
                        missing = [f for f in required if f not in data]
                        if missing:
                            self.log_test(f"regression_{test_name}", False, 
                                        f"Missing fields: {missing}")
                            continue
                    
                    elif test_name == "verse_challenge":
                        required = ["date", "reference", "theme", "difficulty", "display_text", "blank_count"]
                        missing = [f for f in required if f not in data]
                        if missing:
                            self.log_test(f"regression_{test_name}", False, 
                                        f"Missing fields: {missing}")
                            continue
                    
                    elif test_name == "voices":
                        if "voices" not in data or not isinstance(data["voices"], list):
                            self.log_test(f"regression_{test_name}", False, 
                                        "Invalid voices response structure")
                            continue
                    
                    self.log_test(f"regression_{test_name}", True, 
                                f"Endpoint working correctly", 
                                {"endpoint": endpoint})
                    
            except Exception as e:
                self.log_test(f"regression_{test_name}", False, 
                            f"Exception: {str(e)}", {"error": str(e)})
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Bible Story of the Week Backend API Testing")
        print(f"📍 Testing against: {API_BASE_URL}")
        print("=" * 70)
        
        await self.test_story_endpoint_with_age_tiers()
        await self.test_caching_behavior()
        await self.test_health_endpoint()
        await self.test_regression_endpoints()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
        
        print("\n📝 Detailed Results:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")
        
        return passed_tests, failed_tests

async def main():
    """Main test execution"""
    try:
        async with BibleStoryTester() as tester:
            passed, failed = await tester.run_all_tests()
            
            print(f"\n🏁 Testing Complete: {passed} passed, {failed} failed")
            return failed == 0
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)