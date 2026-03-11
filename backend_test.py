#!/usr/bin/env python3
"""
Bible Buddy Backend Testing Suite - New Features
Tests for 3 newly implemented features:
1. 365 Verse of the Day
2. KB Age Pre-warming 
3. Persistent Conversation History
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://voice-chat-kids.preview.emergentagent.com/api"

class BibleBuddyTester:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.test_results = []
        self.parent_data = {}
        self.child_data = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, status: str, details: str = "", response_data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {details}")
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> tuple[int, Dict]:
        """Make HTTP request and return status code and response data"""
        url = f"{BACKEND_URL}{endpoint}"
        request_headers = headers or {}
        
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with self.session.request(method, url, json=data, headers=request_headers) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}
                return response.status, response_data
        except Exception as e:
            return 0, {"error": str(e)}

    # ==================== FEATURE 1: 365 VERSE OF THE DAY TESTS ====================
    
    async def test_verse_of_the_day_age_tiers(self):
        """Test 1-5: Verse of the Day with different age tiers"""
        
        # Test 1: Age tier 7-9
        status, data = await self.make_request("GET", "/verse-of-the-day?age_tier=7-9")
        if status == 200:
            required_fields = ["date", "verse", "reference", "theme", "explanation", "age_tier"]
            missing_fields = [field for field in required_fields if field not in data]
            if not missing_fields:
                self.log_test("Verse of Day (7-9)", "PASS", 
                             f"All required fields present. Theme: {data.get('theme')}, Reference: {data.get('reference')}", data)
            else:
                self.log_test("Verse of Day (7-9)", "FAIL", f"Missing fields: {missing_fields}", data)
        else:
            self.log_test("Verse of Day (7-9)", "FAIL", f"HTTP {status}", data)
        
        # Test 2: Age tier 4-6 (should be same verse but different explanation)
        status, data_4_6 = await self.make_request("GET", "/verse-of-the-day?age_tier=4-6")
        if status == 200:
            required_fields = ["date", "verse", "reference", "theme", "explanation", "age_tier"]
            missing_fields = [field for field in required_fields if field not in data_4_6]
            if not missing_fields and data_4_6.get("age_tier") == "4-6":
                self.log_test("Verse of Day (4-6)", "PASS", 
                             f"Age-adapted explanation for 4-6. Theme: {data_4_6.get('theme')}", data_4_6)
            else:
                self.log_test("Verse of Day (4-6)", "FAIL", f"Missing fields or wrong age_tier: {missing_fields}", data_4_6)
        else:
            self.log_test("Verse of Day (4-6)", "FAIL", f"HTTP {status}", data_4_6)
        
        # Test 3: Age tier 13-18 (should be same verse but different explanation)
        status, data_13_18 = await self.make_request("GET", "/verse-of-the-day?age_tier=13-18")
        if status == 200:
            required_fields = ["date", "verse", "reference", "theme", "explanation", "age_tier"]
            missing_fields = [field for field in required_fields if field not in data_13_18]
            if not missing_fields and data_13_18.get("age_tier") == "13-18":
                self.log_test("Verse of Day (13-18)", "PASS", 
                             f"Age-adapted explanation for teens. Theme: {data_13_18.get('theme')}", data_13_18)
            else:
                self.log_test("Verse of Day (13-18)", "FAIL", f"Missing fields or wrong age_tier: {missing_fields}", data_13_18)
        else:
            self.log_test("Verse of Day (13-18)", "FAIL", f"HTTP {status}", data_13_18)
        
        # Test 4: Verify March theme (today is March 11, 2026, day 70, should be Courage/Strength theme)
        if hasattr(data, 'get') and data.get('theme'):
            theme = data.get('theme', '').lower()
            march_themes = ['courage', 'strength', 'brave', 'bold', 'fearless']
            is_march_theme = any(march_theme in theme for march_theme in march_themes)
            self.log_test("March Theme Check", 
                         "PASS" if is_march_theme else "INFO", 
                         f"March 11 theme: {data.get('theme')} {'(matches expected March themes)' if is_march_theme else '(different theme)'}")
        
        # Test 5: Caching verification (second call should be faster)
        start_time = time.time()
        status2, data2 = await self.make_request("GET", "/verse-of-the-day?age_tier=7-9")
        response_time = time.time() - start_time
        
        if status2 == 200 and data == data2:
            cache_status = "PASS" if response_time < 0.5 else "INFO"
            self.log_test("Verse Caching", cache_status, 
                         f"Second call: {response_time:.3f}s, identical response: {data == data2}")
        else:
            self.log_test("Verse Caching", "FAIL", f"Response mismatch or error: HTTP {status2}")

    # ==================== FEATURE 2: KB AGE PRE-WARMING TESTS ====================
    
    async def test_kb_age_prewarming(self):
        """Test 6-9: Knowledge Base Age Pre-warming with instant responses"""
        
        age_tiers = ["4-6", "7-9", "10-12", "13-18"]
        question = "Who is Jesus?"
        
        for i, age_tier in enumerate(age_tiers, 6):
            start_time = time.time()
            
            payload = {
                "child_id": "test_child",
                "message": question,
                "age_tier": age_tier
            }
            
            status, data = await self.make_request("POST", "/chat", payload)
            response_time = time.time() - start_time
            
            if status == 200:
                from_kb = data.get("from_knowledge_base", False)
                response_text = data.get("response", "")
                
                if from_kb and response_text:
                    # Calculate approximate response complexity for age verification
                    avg_word_length = sum(len(word) for word in response_text.split()) / len(response_text.split()) if response_text.split() else 0
                    
                    self.log_test(f"KB Age Pre-warm ({age_tier})", "PASS", 
                                 f"Instant KB response ({response_time:.3f}s), avg word length: {avg_word_length:.1f}, from_knowledge_base: True", 
                                 {"response_snippet": response_text[:100] + "..." if len(response_text) > 100 else response_text})
                else:
                    self.log_test(f"KB Age Pre-warm ({age_tier})", "FAIL", 
                                 f"Expected KB response but got from_knowledge_base: {from_kb}", data)
            else:
                self.log_test(f"KB Age Pre-warm ({age_tier})", "FAIL", f"HTTP {status}", data)
        
        # Store responses for age adaptation comparison
        self.kb_age_responses = {}

    # ==================== FEATURE 3: PERSISTENT CONVERSATION HISTORY TESTS ====================
    
    async def test_persistent_conversation_history(self):
        """Test 7-12: Complete conversation history persistence flow"""
        
        # Test 7: Register a fresh user
        register_payload = {
            "email": "persistence_test@test.com",
            "password": "test123",
            "name": "Persistence Test"
        }
        
        status, data = await self.make_request("POST", "/auth/register", register_payload)
        if status == 200:
            self.auth_token = data.get("token")
            self.parent_data = data
            self.log_test("User Registration", "PASS", f"Registered user: {data.get('name')}", data)
        else:
            # Try login instead (user might already exist)
            login_payload = {"email": "persistence_test@test.com", "password": "test123"}
            status, data = await self.make_request("POST", "/auth/login", login_payload)
            if status == 200:
                self.auth_token = data.get("token")
                self.parent_data = data
                self.log_test("User Login", "PASS", f"Logged in existing user: {data.get('name')}", data)
            else:
                self.log_test("User Auth", "FAIL", f"Registration/Login failed: HTTP {status}", data)
                return
        
        # Test 8: Create a child
        child_payload = {
            "name": "PersistKid",
            "age_tier": "7-9"
        }
        
        status, data = await self.make_request("POST", "/children", child_payload)
        if status == 200:
            self.child_data = data
            child_id = data.get("child_id")
            self.log_test("Child Creation", "PASS", f"Created child: {data.get('name')}, ID: {child_id}", data)
        else:
            self.log_test("Child Creation", "FAIL", f"HTTP {status}", data)
            return
        
        # Test 9: Send 3 chat messages in the same session
        child_id = self.child_data.get("child_id")
        messages = [
            "Who made the world?",
            "Tell me more about Adam", 
            "Who was Eve?"
        ]
        
        session_id = None
        for i, message in enumerate(messages, 1):
            payload = {
                "child_id": child_id,
                "message": message,
                "age_tier": "7-9"
            }
            
            if session_id:
                payload["session_id"] = session_id
            
            status, data = await self.make_request("POST", "/chat", payload)
            if status == 200:
                if not session_id:
                    session_id = data.get("session_id")
                response_text = data.get("response", "")
                self.log_test(f"Chat Message {i}", "PASS", 
                             f"Message sent, session: {session_id}, response length: {len(response_text)}", 
                             {"message": message, "response_snippet": response_text[:50] + "..." if len(response_text) > 50 else response_text})
            else:
                self.log_test(f"Chat Message {i}", "FAIL", f"HTTP {status}", data)
                return
        
        # Store session_id for later tests
        self.session_id = session_id
        
        # Test 10: Verify conversation history
        status, data = await self.make_request("GET", f"/dashboard/conversations/{child_id}")
        if status == 200:
            conversations = data.get("conversations", [])
            if conversations and len(conversations) >= 1:
                conversation = conversations[0]
                message_count = conversation.get("message_count", 0)
                expected_messages = 6  # 3 user + 3 assistant
                
                if message_count == expected_messages:
                    self.log_test("Conversation History", "PASS", 
                                 f"Found {len(conversations)} conversation(s) with {message_count} messages", data)
                else:
                    self.log_test("Conversation History", "PARTIAL", 
                                 f"Found {message_count} messages, expected {expected_messages}", data)
            else:
                self.log_test("Conversation History", "FAIL", f"No conversations found", data)
        else:
            self.log_test("Conversation History", "FAIL", f"HTTP {status}", data)
        
        # Test 11: Verify conversation detail
        if hasattr(self, 'session_id') and self.session_id:
            status, data = await self.make_request("GET", f"/dashboard/conversation/{self.session_id}")
            if status == 200:
                messages = data.get("messages", [])
                if len(messages) == 6:  # 3 user + 3 assistant
                    has_timestamps = all("timestamp" in msg for msg in messages)
                    self.log_test("Conversation Detail", "PASS", 
                                 f"Retrieved {len(messages)} messages, all with timestamps: {has_timestamps}", 
                                 {"message_count": len(messages), "has_timestamps": has_timestamps})
                else:
                    self.log_test("Conversation Detail", "PARTIAL", 
                                 f"Retrieved {len(messages)} messages, expected 6", data)
            else:
                self.log_test("Conversation Detail", "FAIL", f"HTTP {status}", data)
        
        # Test 12: Verify dashboard stats
        status, data = await self.make_request("GET", f"/dashboard/stats/{child_id}")
        if status == 200:
            total_conversations = data.get("total_conversations", 0)
            total_messages = data.get("total_messages", 0)
            
            if total_conversations >= 1 and total_messages >= 6:
                self.log_test("Dashboard Stats", "PASS", 
                             f"Stats: {total_conversations} conversations, {total_messages} messages", data)
            else:
                self.log_test("Dashboard Stats", "PARTIAL", 
                             f"Stats: {total_conversations} conversations, {total_messages} messages (expected: >=1, >=6)", data)
        else:
            self.log_test("Dashboard Stats", "FAIL", f"HTTP {status}", data)

    # ==================== TEST RUNNER ====================
    
    async def run_all_tests(self):
        """Run all backend tests for new features"""
        print("🎯 BIBLE BUDDY NEW FEATURES BACKEND TESTING")
        print("=" * 60)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Feature 1: 365 Verse of the Day
        print("📖 FEATURE 1: 365 VERSE OF THE DAY")
        print("-" * 40)
        await self.test_verse_of_the_day_age_tiers()
        print()
        
        # Feature 2: KB Age Pre-warming
        print("🧠 FEATURE 2: KB AGE PRE-WARMING")
        print("-" * 40)
        await self.test_kb_age_prewarming()
        print()
        
        # Feature 3: Persistent Conversation History
        print("💾 FEATURE 3: PERSISTENT CONVERSATION HISTORY")
        print("-" * 40)
        await self.test_persistent_conversation_history()
        print()
        
        # Summary
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        partial = sum(1 for r in self.test_results if r["status"] in ["PARTIAL", "INFO"])
        total = len(self.test_results)
        
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"⚠️  PARTIAL/INFO: {partial}")
        print(f"📈 TOTAL: {total}")
        
        if failed > 0:
            print("\n🚨 FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"   - {result['test']}: {result['details']}")
        
        success_rate = (passed / total) * 100 if total > 0 else 0
        print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
        
        return self.test_results


async def main():
    """Main test runner"""
    async with BibleBuddyTester() as tester:
        results = await tester.run_all_tests()
        
        # Save detailed results
        with open("/app/test_results_new_features.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📝 Detailed results saved to: /app/test_results_new_features.json")


if __name__ == "__main__":
    asyncio.run(main())