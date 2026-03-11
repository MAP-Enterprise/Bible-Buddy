#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Bible Buddy - Story Progress Tracker Feature
Testing against: https://bible-buddy-19.preview.emergentagent.com/api
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Base URL from frontend .env
BASE_URL = "https://bible-buddy-19.preview.emergentagent.com/api"

class StoryProgressTester:
    def __init__(self):
        self.session = None
        self.results = []
        
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
    
    async def test_get_story_progress_empty_state(self):
        """Test 1: Get story progress for new child (empty state)"""
        try:
            url = f"{BASE_URL}/story-progress/new_child_999"
            async with self.session.get(url) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Verify expected empty state structure
                    expected_fields = ["total_read", "total_stories", "current_streak", "best_streak", 
                                     "badges_earned", "total_badges", "badges", "recent_reads", "read_week_keys"]
                    
                    missing_fields = [field for field in expected_fields if field not in data]
                    if missing_fields:
                        self.log_result("Get Story Progress (Empty State)", False, 
                                      f"Missing fields: {missing_fields}")
                        return
                    
                    # Verify empty state values
                    checks = [
                        (data["total_read"] == 0, "total_read should be 0"),
                        (data["total_stories"] == 52, "total_stories should be 52"),
                        (data["current_streak"] == 0, "current_streak should be 0"),
                        (data["best_streak"] == 0, "best_streak should be 0"),
                        (data["badges_earned"] == 0, "badges_earned should be 0"),
                        (data["total_badges"] == 12, "total_badges should be 12"),
                        (len(data["badges"]) == 12, "badges array should have 12 items"),
                        (all(not badge["earned"] for badge in data["badges"]), "all badges should be earned: false"),
                        (data["recent_reads"] == [], "recent_reads should be empty"),
                        (data["read_week_keys"] == [], "read_week_keys should be empty")
                    ]
                    
                    failed_checks = [msg for check, msg in checks if not check]
                    if failed_checks:
                        self.log_result("Get Story Progress (Empty State)", False, 
                                      f"Failed checks: {'; '.join(failed_checks)}")
                        return
                    
                    self.log_result("Get Story Progress (Empty State)", True, 
                                  f"All fields correct. Total stories: {data['total_stories']}, badges: {data['total_badges']}")
                else:
                    self.log_result("Get Story Progress (Empty State)", False, 
                                  f"HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Get Story Progress (Empty State)", False, f"Exception: {str(e)}")
    
    async def test_mark_story_read_first_time(self):
        """Test 2: Mark a story as read for the first time"""
        try:
            url = f"{BASE_URL}/story-progress/mark-read"
            payload = {
                "child_id": "test_progress_child",
                "week_key": "2026-W08",
                "story_title": "Creation",
                "story_reference": "Genesis 1-2"
            }
            
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Verify response structure and values
                    expected_fields = ["status", "total_read", "current_streak", "best_streak", 
                                     "new_badges", "total_badges"]
                    missing_fields = [field for field in expected_fields if field not in data]
                    if missing_fields:
                        self.log_result("Mark Story Read (First Time)", False, 
                                      f"Missing fields: {missing_fields}")
                        return
                    
                    checks = [
                        (data["status"] == "marked", "status should be 'marked'"),
                        (data["total_read"] == 1, "total_read should be 1"),
                        (data["total_badges"] >= 1, "total_badges should be at least 1"),
                        ("new_badges" in data, "new_badges field should be present")
                    ]
                    
                    failed_checks = [msg for check, msg in checks if not check]
                    if failed_checks:
                        self.log_result("Mark Story Read (First Time)", False, 
                                      f"Failed checks: {'; '.join(failed_checks)}")
                        return
                    
                    # Check if "First Story" badge was earned
                    first_story_earned = any(badge.get("name") == "First Story" for badge in data.get("new_badges", []))
                    if first_story_earned:
                        badge_detail = "First Story badge earned"
                    else:
                        badge_detail = f"New badges: {[b.get('name', 'unknown') for b in data.get('new_badges', [])]}"
                    
                    self.log_result("Mark Story Read (First Time)", True, 
                                  f"Status: {data['status']}, total_read: {data['total_read']}, {badge_detail}")
                else:
                    self.log_result("Mark Story Read (First Time)", False, 
                                  f"HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Mark Story Read (First Time)", False, f"Exception: {str(e)}")
    
    async def test_duplicate_read_prevention(self):
        """Test 3: Attempt to mark the same story as read again (should prevent duplicate)"""
        try:
            url = f"{BASE_URL}/story-progress/mark-read"
            payload = {
                "child_id": "test_progress_child",
                "week_key": "2026-W08",
                "story_title": "Creation",
                "story_reference": "Genesis 1-2"
            }
            
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200:
                    if data.get("status") == "already_read":
                        self.log_result("Duplicate Read Prevention", True, 
                                      f"Correctly prevented duplicate: {data.get('message', 'No message')}")
                    else:
                        self.log_result("Duplicate Read Prevention", False, 
                                      f"Expected 'already_read' status, got: {data.get('status')}")
                else:
                    self.log_result("Duplicate Read Prevention", False, 
                                  f"HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Duplicate Read Prevention", False, f"Exception: {str(e)}")
    
    async def test_mark_multiple_stories_and_verify_badges(self):
        """Test 4: Mark multiple stories and verify badge progression"""
        try:
            stories = [
                {
                    "child_id": "test_progress_child",
                    "week_key": "2026-W09",
                    "story_title": "Noah's Ark",
                    "story_reference": "Genesis 6-9"
                },
                {
                    "child_id": "test_progress_child",
                    "week_key": "2026-W10",
                    "story_title": "Abraham",
                    "story_reference": "Genesis 12"
                }
            ]
            
            url = f"{BASE_URL}/story-progress/mark-read"
            total_marked = 1  # Already marked 1 story in previous test
            
            for i, story in enumerate(stories, 1):
                async with self.session.post(url, json=story) as response:
                    data = await response.json()
                    
                    if response.status == 200 and data.get("status") == "marked":
                        total_marked += 1
                        print(f"  📖 Marked story {total_marked}: {story['story_title']}")
                    else:
                        self.log_result("Mark Multiple Stories", False, 
                                      f"Failed to mark story {i}: {data}")
                        return
            
            # After marking 3 stories total, check progress
            progress_url = f"{BASE_URL}/story-progress/test_progress_child"
            async with self.session.get(progress_url) as response:
                data = await response.json()
                
                if response.status == 200:
                    if data["total_read"] == 3:
                        # Check if "Getting Started" badge (3 stories) was earned
                        earned_badges = [badge["name"] for badge in data["badges"] if badge["earned"]]
                        getting_started_earned = "Getting Started" in earned_badges
                        
                        if getting_started_earned:
                            self.log_result("Mark Multiple Stories & Verify Badges", True, 
                                          f"Total read: {data['total_read']}, Getting Started badge earned. All earned badges: {earned_badges}")
                        else:
                            self.log_result("Mark Multiple Stories & Verify Badges", False, 
                                          f"Total read: {data['total_read']}, but Getting Started badge not earned. Earned badges: {earned_badges}")
                    else:
                        self.log_result("Mark Multiple Stories & Verify Badges", False, 
                                      f"Expected total_read=3, got {data['total_read']}")
                else:
                    self.log_result("Mark Multiple Stories & Verify Badges", False, 
                                  f"Failed to get progress: HTTP {response.status}")
                    
        except Exception as e:
            self.log_result("Mark Multiple Stories & Verify Badges", False, f"Exception: {str(e)}")
    
    async def test_streak_calculation(self):
        """Test 5: Verify streak calculation with consecutive weeks"""
        try:
            # Mark story for consecutive week W11 (following W08, W09, W10)
            url = f"{BASE_URL}/story-progress/mark-read"
            payload = {
                "child_id": "test_progress_child",
                "week_key": "2026-W11",
                "story_title": "Test Story",
                "story_reference": "Test"
            }
            
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200 and data.get("status") == "marked":
                    print(f"  📖 Marked consecutive story for W11")
                    
                    # Get progress to check streak
                    progress_url = f"{BASE_URL}/story-progress/test_progress_child"
                    async with self.session.get(progress_url) as response2:
                        progress_data = await response2.json()
                        
                        if response2.status == 200:
                            current_streak = progress_data.get("current_streak", 0)
                            best_streak = progress_data.get("best_streak", 0)
                            earned_badges = [badge["name"] for badge in progress_data["badges"] if badge["earned"]]
                            
                            # W08, W09, W10, W11 should be consecutive (depends on streak algorithm)
                            # Note: The algorithm considers consecutive weeks, so we should have a streak
                            if current_streak > 0:
                                # Check if "Week Warrior" badge (2+ streak) was earned
                                week_warrior_earned = "Week Warrior" in earned_badges
                                
                                self.log_result("Streak Calculation", True, 
                                              f"Current streak: {current_streak}, best: {best_streak}. Week Warrior earned: {week_warrior_earned}")
                            else:
                                self.log_result("Streak Calculation", False, 
                                              f"Expected streak > 0 for consecutive weeks W08-W11, got current_streak: {current_streak}")
                        else:
                            self.log_result("Streak Calculation", False, 
                                          f"Failed to get progress: HTTP {response2.status}")
                else:
                    self.log_result("Streak Calculation", False, 
                                  f"Failed to mark consecutive story: {data}")
                    
        except Exception as e:
            self.log_result("Streak Calculation", False, f"Exception: {str(e)}")
    
    async def test_get_full_progress(self):
        """Test 6: Get full progress after marking multiple stories"""
        try:
            url = f"{BASE_URL}/story-progress/test_progress_child"
            async with self.session.get(url) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Verify all expected fields are present
                    expected_fields = ["total_read", "total_stories", "current_streak", "best_streak", 
                                     "badges_earned", "total_badges", "badges", "recent_reads", "read_week_keys"]
                    missing_fields = [field for field in expected_fields if field not in data]
                    if missing_fields:
                        self.log_result("Get Full Progress", False, 
                                      f"Missing fields: {missing_fields}")
                        return
                    
                    # Verify expected values
                    checks = [
                        (data["total_read"] == 4, f"total_read should be 4, got {data['total_read']}"),
                        (len(data["recent_reads"]) == 4, f"recent_reads should have 4 items, got {len(data['recent_reads'])}"),
                        (len(data["read_week_keys"]) == 4, f"read_week_keys should have 4 entries, got {len(data['read_week_keys'])}"),
                        (data["total_stories"] == 52, "total_stories should be 52"),
                        (len(data["badges"]) == 12, "badges array should have 12 items"),
                        (data["badges_earned"] > 0, "should have earned some badges")
                    ]
                    
                    failed_checks = [msg for check, msg in checks if not check]
                    if failed_checks:
                        self.log_result("Get Full Progress", False, 
                                      f"Failed checks: {'; '.join(failed_checks)}")
                        return
                    
                    # Count earned badges
                    earned_badges = [badge["name"] for badge in data["badges"] if badge["earned"]]
                    week_keys = data["read_week_keys"]
                    
                    self.log_result("Get Full Progress", True, 
                                  f"Total read: {data['total_read']}, streak: {data['current_streak']}, " +
                                  f"earned badges: {len(earned_badges)} ({', '.join(earned_badges)}), " +
                                  f"week keys: {week_keys}")
                else:
                    self.log_result("Get Full Progress", False, 
                                  f"HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Get Full Progress", False, f"Exception: {str(e)}")
    
    async def test_regression_endpoints(self):
        """Test 7: Verify other endpoints still work (regression test)"""
        try:
            endpoints = [
                ("/story-of-the-week?age_tier=7-9", "Story of the Week"),
                ("/verse-of-the-day?age_tier=7-9", "Verse of the Day"),
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
    
    async def test_cleanup_verification(self):
        """Test 8: Verify test data state (no cleanup needed as per instructions)"""
        try:
            # This is just to verify the final state is consistent
            url = f"{BASE_URL}/story-progress/test_progress_child"
            async with self.session.get(url) as response:
                data = await response.json()
                
                if response.status == 200:
                    self.log_result("Cleanup Verification", True, 
                                  f"Final state consistent - test data preserved as intended. " +
                                  f"Child 'test_progress_child' has {data['total_read']} stories read.")
                else:
                    self.log_result("Cleanup Verification", False, 
                                  f"HTTP {response.status}: {data}")
                    
        except Exception as e:
            self.log_result("Cleanup Verification", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"🎯 STORY PROGRESS TRACKER TEST SUMMARY")
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
        """Run all Story Progress Tracker tests"""
        print("🚀 Starting Story Progress Tracker Backend Tests")
        print(f"🌐 Testing against: {BASE_URL}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        await self.create_session()
        
        try:
            # Run tests in order
            await self.test_get_story_progress_empty_state()
            await self.test_mark_story_read_first_time()
            await self.test_duplicate_read_prevention()
            await self.test_mark_multiple_stories_and_verify_badges()
            await self.test_streak_calculation()
            await self.test_get_full_progress()
            await self.test_regression_endpoints()
            await self.test_cleanup_verification()
            
        finally:
            await self.close_session()
        
        self.print_summary()

async def main():
    """Main test execution"""
    tester = StoryProgressTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())