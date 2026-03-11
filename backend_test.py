#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Bible Buddy - 5 New Features
Testing against production URL: https://voice-chat-kids.preview.emergentagent.com/api

Features to Test:
1. Challenge Stats in Parent Dashboard
2. COPPA-Compliant Consent 
3. Refactored Routes (all still working)
4. Family Leaderboard
5. Resend Domain Verification
"""

import aiohttp
import asyncio
import json
import sys
from datetime import datetime

# Base URL for testing
BASE_URL = "https://voice-chat-kids.preview.emergentagent.com/api"

class BibleBuddyTester:
    def __init__(self):
        self.session = None
        self.test_results = []
        self.auth_token = None
        self.alice_child_id = None
        self.bob_child_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    def log_test(self, test_name: str, success: bool, details: str = "", response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   → {details}")
        if response_data and not success:
            print(f"   → Response: {response_data}")
        print()
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    async def make_request(self, method: str, endpoint: str, data=None, auth_required=True):
        """Make HTTP request with error handling"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if auth_required and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        try:
            if method == "GET":
                resp = await self.session.get(url, headers=headers)
            elif method == "POST":
                resp = await self.session.post(url, headers=headers, json=data)
            elif method == "PATCH":
                resp = await self.session.patch(url, headers=headers, json=data)
                
            response_data = None
            try:
                response_data = await resp.json()
            except:
                response_data = {"text": await resp.text()}
                
            return resp.status, response_data
            
        except Exception as e:
            return 500, {"error": str(e)}
            
    async def setup_test_user(self):
        """Setup - Create test user with multiple children"""
        print("🔧 SETUP: Creating test user with multiple children")
        
        # Step 1: Register user
        register_data = {
            "email": "full_test@test.com",
            "password": "test123",
            "name": "Full Tester"
        }
        
        status, response = await self.make_request("POST", "/auth/register", register_data, auth_required=False)
        
        if status == 200:
            self.auth_token = response.get("token")
            self.log_test("Register test user", True, f"Token: {self.auth_token[:20]}...")
        else:
            # Try login in case user already exists
            login_data = {"email": "full_test@test.com", "password": "test123"}
            status, response = await self.make_request("POST", "/auth/login", login_data, auth_required=False)
            if status == 200:
                self.auth_token = response.get("token")
                self.log_test("Login existing test user", True, f"Token: {self.auth_token[:20]}...")
            else:
                self.log_test("Register/Login test user", False, f"Status: {status}", response)
                return False
                
        # Step 2: Create Alice (7-9 age tier)
        alice_data = {"name": "Alice", "age_tier": "7-9"}
        status, response = await self.make_request("POST", "/children", alice_data)
        
        if status == 200:
            self.alice_child_id = response.get("child_id")
            self.log_test("Create Alice child", True, f"Child ID: {self.alice_child_id}")
        else:
            self.log_test("Create Alice child", False, f"Status: {status}", response)
            return False
            
        # Step 3: Create Bob (10-12 age tier)  
        bob_data = {"name": "Bob", "age_tier": "10-12"}
        status, response = await self.make_request("POST", "/children", bob_data)
        
        if status == 200:
            self.bob_child_id = response.get("child_id")
            self.log_test("Create Bob child", True, f"Child ID: {self.bob_child_id}")
            return True
        else:
            self.log_test("Create Bob child", False, f"Status: {status}", response)
            return False
            
    async def test_feature_1_challenge_stats(self):
        """Feature 1: Challenge Stats in Parent Dashboard"""
        print("\n🎯 FEATURE 1: Challenge Stats in Parent Dashboard")
        
        # Step 4: Submit a challenge for Alice
        # First get a verse challenge
        status, challenge_response = await self.make_request("GET", "/verse-challenge?age_tier=7-9&difficulty=easy", auth_required=False)
        
        if status != 200:
            self.log_test("Get verse challenge for Alice", False, f"Status: {status}", challenge_response)
            return False
            
        self.log_test("Get verse challenge for Alice", True, f"Reference: {challenge_response.get('reference')}")
        
        # Determine correct answers by comparing display_text with full_verse
        display_text = challenge_response.get("display_text", "")
        full_verse = challenge_response.get("full_verse", "")
        blank_count = challenge_response.get("blank_count", 0)
        
        # Extract answers from blanks (simple approach - find words that were replaced with ____) 
        display_words = display_text.split()
        full_words = full_verse.split()
        correct_answers = []
        
        for i, (display_word, full_word) in enumerate(zip(display_words, full_words)):
            if "____" in display_word:
                # Extract the clean word (removing punctuation)
                clean_word = full_word.strip(".,;:!?'\"—").lower()
                correct_answers.append(clean_word)
                
        if len(correct_answers) == 0:
            # Fallback: just use some words from the verse
            correct_answers = [w.strip(".,;:!?'\"—").lower() for w in full_words[:blank_count] if len(w.strip(".,;:!?'\"—")) >= 4]
            
        submission_data = {
            "child_id": self.alice_child_id,
            "answers": correct_answers,
            "difficulty": "easy"
        }
        
        # Step 5: Submit challenge answers
        status, submit_response = await self.make_request("POST", "/verse-challenge/submit", submission_data, auth_required=False)
        
        if status == 200:
            score = submit_response.get("score", 0)
            self.log_test("Submit challenge for Alice", True, f"Score: {score}%")
        else:
            self.log_test("Submit challenge for Alice", False, f"Status: {status}", submit_response)
            
        # Step 6: Get challenge stats for Alice
        status, stats_response = await self.make_request("GET", f"/verse-challenge/stats/{self.alice_child_id}", auth_required=False)
        
        if status == 200:
            total_played = stats_response.get("total_played", 0)
            avg_score = stats_response.get("average_score", 0)
            self.log_test("Get Alice challenge stats", True, f"Total played: {total_played}, Avg score: {avg_score}")
        else:
            self.log_test("Get Alice challenge stats", False, f"Status: {status}", stats_response)
            
        # Step 7: Get dashboard stats for Alice
        status, dashboard_response = await self.make_request("GET", f"/dashboard/stats/{self.alice_child_id}")
        
        if status == 200:
            conversations = dashboard_response.get("total_conversations", 0)
            messages = dashboard_response.get("total_messages", 0)
            self.log_test("Get Alice dashboard stats", True, f"Conversations: {conversations}, Messages: {messages}")
            return True
        else:
            self.log_test("Get Alice dashboard stats", False, f"Status: {status}", dashboard_response)
            return False
            
    async def test_feature_2_coppa_consent(self):
        """Feature 2: COPPA-Compliant Consent"""
        print("\n🔒 FEATURE 2: COPPA-Compliant Consent")
        
        # Step 8: Get COPPA policy
        status, policy_response = await self.make_request("GET", "/coppa-policy", auth_required=False)
        
        if status == 200:
            required_fields = ["data_collected", "data_usage", "data_not_collected", "retention", "parent_rights"]
            has_all_fields = all(field in policy_response for field in required_fields)
            self.log_test("Get COPPA policy", has_all_fields, f"Has all required fields: {has_all_fields}")
        else:
            self.log_test("Get COPPA policy", False, f"Status: {status}", policy_response)
            
        # Step 9: Give consent for Alice (correct name)
        alice_consent_data = {"child_name_confirmation": "Alice"}
        status, consent_response = await self.make_request("POST", f"/children/{self.alice_child_id}/consent", alice_consent_data)
        
        if status == 200:
            self.log_test("Give consent for Alice (correct name)", True, "Consent recorded")
        else:
            self.log_test("Give consent for Alice (correct name)", False, f"Status: {status}", consent_response)
            
        # Step 10: Try wrong name (should fail)
        wrong_consent_data = {"child_name_confirmation": "WrongName"}
        status, wrong_response = await self.make_request("POST", f"/children/{self.alice_child_id}/consent", wrong_consent_data)
        
        if status == 400:
            self.log_test("Give consent with wrong name (should fail)", True, "Correctly rejected wrong name")
        else:
            self.log_test("Give consent with wrong name (should fail)", False, f"Status: {status} (expected 400)", wrong_response)
            
        # Step 11: Give consent for Bob (correct name)
        bob_consent_data = {"child_name_confirmation": "Bob"}
        status, bob_consent_response = await self.make_request("POST", f"/children/{self.bob_child_id}/consent", bob_consent_data)
        
        if status == 200:
            self.log_test("Give consent for Bob (correct name)", True, "Consent recorded")
        else:
            self.log_test("Give consent for Bob (correct name)", False, f"Status: {status}", bob_consent_response)
            
        # Step 12: Verify consent recorded for Alice
        status, alice_profile = await self.make_request("GET", f"/children/{self.alice_child_id}")
        
        if status == 200:
            consent_given = alice_profile.get("parental_consent_given", False)
            consent_timestamp = alice_profile.get("consent_timestamp")
            consent_method = alice_profile.get("consent_method")
            
            if consent_given and consent_timestamp and consent_method:
                self.log_test("Verify Alice consent recorded", True, f"Consent: {consent_given}, Method: {consent_method}")
                return True
            else:
                self.log_test("Verify Alice consent recorded", False, f"Missing consent fields: {alice_profile}")
        else:
            self.log_test("Verify Alice consent recorded", False, f"Status: {status}", alice_profile)
            
        return False
        
    async def test_feature_3_refactored_routes(self):
        """Feature 3: Refactored Routes (all still working)"""  
        print("\n🔄 FEATURE 3: Refactored Routes (ensuring all still work)")
        
        routes_to_test = [
            ("POST", "/auth/login", {"email": "full_test@test.com", "password": "test123"}, False),
            ("GET", "/auth/me", None, True),
            ("GET", "/knowledge-base", None, False),
            ("GET", "/teachers", None, False),
            ("GET", "/verse-of-the-day?age_tier=7-9", None, False),
            ("GET", "/verse-challenge?age_tier=10-12", None, False),
            ("GET", f"/dashboard/conversations/{self.alice_child_id}", None, True),
            ("GET", "/voices", None, False),
        ]
        
        all_passed = True
        
        for method, endpoint, data, auth_required in routes_to_test:
            status, response = await self.make_request(method, endpoint, data, auth_required)
            
            success = status == 200
            if success:
                # Additional checks for specific endpoints
                if "knowledge-base" in endpoint:
                    success = "questions" in response and "total" in response
                elif "teachers" in endpoint:
                    success = "teachers" in response and len(response.get("teachers", [])) > 0
                elif "verse-of-the-day" in endpoint:
                    success = "verse" in response and "reference" in response
                elif "voices" in endpoint:
                    success = "voices" in response and len(response.get("voices", [])) >= 10
                elif "auth/me" in endpoint:
                    success = "user_id" in response and "email" in response
                    
            self.log_test(f"Route: {method} {endpoint}", success, f"Status: {status}")
            
            if not success:
                all_passed = False
                
        # Test chat endpoint
        chat_data = {
            "child_id": self.alice_child_id,
            "message": "Who is God?",
            "age_tier": "7-9"
        }
        status, chat_response = await self.make_request("POST", "/chat", chat_data, auth_required=False)
        
        if status == 200 and "session_id" in chat_response and "response" in chat_response:
            self.log_test("POST /chat endpoint", True, f"Status: {status}")
        else:
            self.log_test("POST /chat endpoint", False, f"Status: {status}", chat_response)
            all_passed = False
            
        return all_passed
        
    async def test_feature_4_family_leaderboard(self):
        """Feature 4: Family Leaderboard"""
        print("\n🏆 FEATURE 4: Family Leaderboard")
        
        # Step 21: Submit challenges for Bob too
        # Get verse challenge for Bob's age tier
        status, bob_challenge = await self.make_request("GET", "/verse-challenge?age_tier=10-12&difficulty=easy", auth_required=False)
        
        if status != 200:
            self.log_test("Get verse challenge for Bob", False, f"Status: {status}", bob_challenge)
            return False
            
        # Extract correct answers for Bob's challenge
        display_text = bob_challenge.get("display_text", "")
        full_verse = bob_challenge.get("full_verse", "")
        blank_count = bob_challenge.get("blank_count", 0)
        
        display_words = display_text.split()
        full_words = full_verse.split()
        bob_answers = []
        
        for i, (display_word, full_word) in enumerate(zip(display_words, full_words)):
            if "____" in display_word:
                clean_word = full_word.strip(".,;:!?'\"—").lower()
                bob_answers.append(clean_word)
                
        if len(bob_answers) == 0:
            bob_answers = [w.strip(".,;:!?'\"—").lower() for w in full_words[:blank_count] if len(w.strip(".,;:!?'\"—")) >= 4]
            
        bob_submission = {
            "child_id": self.bob_child_id,
            "answers": bob_answers,
            "difficulty": "easy"
        }
        
        status, bob_submit_response = await self.make_request("POST", "/verse-challenge/submit", bob_submission, auth_required=False)
        
        if status == 200:
            bob_score = bob_submit_response.get("score", 0)
            self.log_test("Submit challenge for Bob", True, f"Score: {bob_score}%")
        else:
            self.log_test("Submit challenge for Bob", False, f"Status: {status}", bob_submit_response)
            
        # Step 22: Get family leaderboard
        status, leaderboard_response = await self.make_request("GET", "/leaderboard")
        
        if status == 200:
            leaderboard = leaderboard_response.get("leaderboard", [])
            family_stats = leaderboard_response.get("family_stats", {})
            
            # Validate leaderboard structure
            has_valid_structure = True
            required_leaderboard_fields = ["rank", "name", "age_tier", "challenge_stats", "chat_stats"]
            required_family_fields = ["total_children", "total_challenges_completed", "family_average_score"]
            
            if len(leaderboard) >= 2:  # Should have Alice and Bob
                for entry in leaderboard:
                    if not all(field in entry for field in required_leaderboard_fields):
                        has_valid_structure = False
                        break
                        
                    # Check challenge_stats structure
                    challenge_stats = entry.get("challenge_stats", {})
                    if not all(field in challenge_stats for field in ["total_played", "average_score", "current_streak"]):
                        has_valid_structure = False
                        break
                        
                    # Check chat_stats structure  
                    chat_stats = entry.get("chat_stats", {})
                    if not all(field in chat_stats for field in ["total_conversations", "total_messages"]):
                        has_valid_structure = False
                        break
                        
                # Check family_stats structure
                if not all(field in family_stats for field in required_family_fields):
                    has_valid_structure = False
                    
                if has_valid_structure:
                    total_children = family_stats.get("total_children", 0)
                    total_challenges = family_stats.get("total_challenges_completed", 0)
                    self.log_test("Get family leaderboard", True, 
                                f"Children: {total_children}, Total challenges: {total_challenges}, Entries: {len(leaderboard)}")
                    return True
                else:
                    self.log_test("Get family leaderboard", False, "Invalid leaderboard structure", leaderboard_response)
            else:
                self.log_test("Get family leaderboard", False, f"Expected 2+ children, got {len(leaderboard)}", leaderboard_response)
        else:
            self.log_test("Get family leaderboard", False, f"Status: {status}", leaderboard_response)
            
        return False
        
    async def test_feature_5_resend_domain_verification(self):
        """Feature 5: Resend Domain Verification"""
        print("\n📧 FEATURE 5: Resend Domain Verification")
        
        # Step 23: Get domain status
        status, domain_response = await self.make_request("GET", "/email/domain-status")
        
        if status == 200:
            current_sender = domain_response.get("current_sender")
            is_verified = domain_response.get("is_verified")
            using_default = domain_response.get("using_default")
            
            required_fields = ["current_sender", "is_verified", "using_default"]
            has_required = all(field in domain_response for field in required_fields)
            
            if has_required:
                details = f"Sender: {current_sender}, Verified: {is_verified}, Using default: {using_default}"
                
                # If using default, should have setup instructions
                if using_default:
                    setup_instructions = domain_response.get("setup_instructions", {})
                    required_dns_records = domain_response.get("setup_instructions", {}).get("required_dns_records", [])
                    
                    if setup_instructions and required_dns_records:
                        self.log_test("Get domain status with setup instructions", True, 
                                    f"{details}, Has setup instructions: {len(setup_instructions)} fields")
                        return True
                    else:
                        self.log_test("Get domain status", False, "Missing setup instructions for default domain")
                else:
                    self.log_test("Get domain status (custom domain)", True, details)
                    return True
            else:
                self.log_test("Get domain status", False, f"Missing required fields: {domain_response}")
        else:
            self.log_test("Get domain status", False, f"Status: {status}", domain_response)
            
        return False
        
    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print("="*60)
        
        # Group by feature
        features = {
            "Setup": [],
            "Feature 1 - Challenge Stats": [],
            "Feature 2 - COPPA Consent": [],
            "Feature 3 - Refactored Routes": [],
            "Feature 4 - Family Leaderboard": [],
            "Feature 5 - Domain Verification": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if any(x in test_name.lower() for x in ["register", "login", "create alice", "create bob"]):
                features["Setup"].append(result)
            elif any(x in test_name.lower() for x in ["challenge", "stats", "dashboard"]) and "family" not in test_name.lower():
                features["Feature 1 - Challenge Stats"].append(result)
            elif any(x in test_name.lower() for x in ["coppa", "consent"]):
                features["Feature 2 - COPPA Consent"].append(result)
            elif "route" in test_name.lower():
                features["Feature 3 - Refactored Routes"].append(result)
            elif any(x in test_name.lower() for x in ["leaderboard", "family"]):
                features["Feature 4 - Family Leaderboard"].append(result)
            elif any(x in test_name.lower() for x in ["domain", "email"]):
                features["Feature 5 - Domain Verification"].append(result)
                
        for feature, results in features.items():
            if results:
                feature_passed = sum(1 for r in results if r["success"])
                feature_total = len(results)
                status_emoji = "✅" if feature_passed == feature_total else "⚠️" if feature_passed > 0 else "❌"
                print(f"\n{status_emoji} {feature}: {feature_passed}/{feature_total}")
                
        print(f"\nOverall Status: {'✅ ALL FEATURES WORKING' if passed == total else '⚠️ SOME ISSUES FOUND' if passed > total*0.8 else '❌ MAJOR ISSUES'}")
        
        return passed == total


async def main():
    """Run comprehensive backend testing"""
    print("🎯 Bible Buddy - Comprehensive Backend Testing")
    print("Testing 5 New Features against Production API")
    print(f"Base URL: {BASE_URL}")
    print("="*60)
    
    async with BibleBuddyTester() as tester:
        # Setup phase
        if not await tester.setup_test_user():
            print("❌ Setup failed - cannot continue with feature testing")
            return False
            
        # Test each feature
        feature_1_ok = await tester.test_feature_1_challenge_stats()
        feature_2_ok = await tester.test_feature_2_coppa_consent()
        feature_3_ok = await tester.test_feature_3_refactored_routes()
        feature_4_ok = await tester.test_feature_4_family_leaderboard()
        feature_5_ok = await tester.test_feature_5_resend_domain_verification()
        
        # Print results
        success = tester.print_summary()
        
        return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)