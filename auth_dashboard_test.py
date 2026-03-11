#!/usr/bin/env python3
"""
Bible Buddy Auth and Dashboard API Testing Suite
Tests the exact 13-step flow requested in the review request
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
import time

# Backend URL from review request
BACKEND_URL = "https://bible-buddy-19.preview.emergentagent.com/api"

class AuthDashboardTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = BACKEND_URL
        self.test_results = []
        self.failed_tests = []
        self.token = None
        self.user_id = None
        self.child_id = None
        self.session_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = "", response: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response": response
        }
        self.test_results.append(result)
        if not success:
            self.failed_tests.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {details}")
        
    def test_step_1_register(self):
        """Step 1: Auth - Register"""
        print("\n=== 1. Auth - Register ===")
        
        try:
            payload = {
                "email": "testflow@parent.com",
                "password": "TestPass123!",
                "name": "Flow Test Parent"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", 
                                      json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["user_id", "name", "email", "token"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Register - Required Fields", False, 
                                f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check token format
                token = data.get("token")
                if token and token.startswith("st_"):
                    self.log_test("Register - Token Format", True, 
                                f"Token starts with 'st_': {token[:20]}...")
                    self.token = token
                    self.user_id = data.get("user_id")
                else:
                    self.log_test("Register - Token Format", False, 
                                f"Token should start with 'st_', got: {token}")
                    return False
                
                # Check password_hash NOT returned
                if "password_hash" not in data:
                    self.log_test("Register - Security", True, 
                                "password_hash correctly NOT returned")
                else:
                    self.log_test("Register - Security", False, 
                                "password_hash leaked in response!")
                    return False
                
                self.log_test("Register - Success", True, 
                            f"User registered: {data['name']} ({data['email']})")
                return True
                
            else:
                self.log_test("Register", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Register", False, f"Exception: {str(e)}")
            return False
    
    def test_step_2_duplicate_register(self):
        """Step 2: Auth - Duplicate Register (should return 400)"""
        print("\n=== 2. Auth - Duplicate Register ===")
        
        try:
            payload = {
                "email": "testflow@parent.com",
                "password": "TestPass123!",
                "name": "Flow Test Parent"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", 
                                      json=payload, timeout=15)
            
            if response.status_code == 400:
                self.log_test("Duplicate Register", True, 
                            "Correctly rejected duplicate email with 400")
                return True
            else:
                self.log_test("Duplicate Register", False, 
                            f"Expected 400, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Duplicate Register", False, f"Exception: {str(e)}")
            return False
    
    def test_step_3_login(self):
        """Step 3: Auth - Login"""
        print("\n=== 3. Auth - Login ===")
        
        try:
            payload = {
                "email": "testflow@parent.com",
                "password": "TestPass123!"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", 
                                      json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if "token" in data:
                    new_token = data["token"]
                    self.log_test("Login - Success", True, 
                                f"Login successful, token: {new_token[:20]}...")
                    # Update token for subsequent requests
                    self.token = new_token
                    return True
                else:
                    self.log_test("Login - Token Missing", False, 
                                "Login response missing token")
                    return False
            else:
                self.log_test("Login", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Login", False, f"Exception: {str(e)}")
            return False
    
    def test_step_4_auth_me_with_token(self):
        """Step 4: Auth - Me (with Bearer token)"""
        print("\n=== 4. Auth - Me (with Bearer token) ===")
        
        if not self.token:
            self.log_test("Auth Me - Token Missing", False, "No token from previous steps")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/auth/me", 
                                      headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check password_hash NOT returned
                if "password_hash" not in data:
                    self.log_test("Auth Me - Security", True, 
                                "password_hash correctly NOT returned")
                else:
                    self.log_test("Auth Me - Security", False, 
                                "password_hash leaked in /me response!")
                    return False
                
                # Check user data present
                if "user_id" in data and "name" in data and "email" in data:
                    self.log_test("Auth Me - Success", True, 
                                f"User data: {data['name']} ({data['email']})")
                    return True
                else:
                    self.log_test("Auth Me - Data Missing", False, 
                                "Missing user_id, name, or email in response")
                    return False
            else:
                self.log_test("Auth Me", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Auth Me", False, f"Exception: {str(e)}")
            return False
    
    def test_step_5_auth_me_without_token(self):
        """Step 5: Auth - Me (without token, should return 401)"""
        print("\n=== 5. Auth - Me (without token) ===")
        
        try:
            response = self.session.get(f"{self.base_url}/auth/me", timeout=15)
            
            if response.status_code == 401:
                self.log_test("Auth Me No Token", True, 
                            "Correctly returned 401 for unauthenticated request")
                return True
            else:
                self.log_test("Auth Me No Token", False, 
                            f"Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Auth Me No Token", False, f"Exception: {str(e)}")
            return False
    
    def test_step_6_create_child(self):
        """Step 6: Children - Create Child"""
        print("\n=== 6. Children - Create Child ===")
        
        if not self.token:
            self.log_test("Create Child - Token Missing", False, "No token from previous steps")
            return False
        
        try:
            payload = {
                "name": "TestChild",
                "age_tier": "7-9"
            }
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = self.session.post(f"{self.base_url}/children", 
                                      json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                if "child_id" in data and "parent_id" in data:
                    self.child_id = data["child_id"]
                    
                    # Check parent_id matches user_id
                    if data["parent_id"] == self.user_id:
                        self.log_test("Create Child - Success", True, 
                                    f"Child created: {data['name']} (ID: {self.child_id})")
                        return True
                    else:
                        self.log_test("Create Child - Parent ID Mismatch", False, 
                                    f"Parent ID {data['parent_id']} doesn't match user ID {self.user_id}")
                        return False
                else:
                    self.log_test("Create Child - Missing Fields", False, 
                                "Response missing child_id or parent_id")
                    return False
            else:
                self.log_test("Create Child", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Create Child", False, f"Exception: {str(e)}")
            return False
    
    def test_step_7_create_second_child(self):
        """Step 7: Children - Create Second Child"""
        print("\n=== 7. Children - Create Second Child ===")
        
        if not self.token:
            self.log_test("Create Second Child - Token Missing", False, "No token from previous steps")
            return False
        
        try:
            payload = {
                "name": "SecondChild",
                "age_tier": "4-6"
            }
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = self.session.post(f"{self.base_url}/children", 
                                      json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Second Child - Success", True, 
                            f"Second child created: {data['name']}")
                return True
            else:
                self.log_test("Create Second Child", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Create Second Child", False, f"Exception: {str(e)}")
            return False
    
    def test_step_8_list_children(self):
        """Step 8: Children - List Children (should return 2)"""
        print("\n=== 8. Children - List Children ===")
        
        if not self.token:
            self.log_test("List Children - Token Missing", False, "No token from previous steps")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/children", 
                                      headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if "children" in data:
                    children = data["children"]
                    
                    if len(children) == 2:
                        self.log_test("List Children - Count", True, 
                                    f"Found 2 children: {[c['name'] for c in children]}")
                        return True
                    else:
                        self.log_test("List Children - Count", False, 
                                    f"Expected 2 children, got {len(children)}")
                        return False
                else:
                    self.log_test("List Children - Structure", False, 
                                "Response missing 'children' field")
                    return False
            else:
                self.log_test("List Children", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("List Children", False, f"Exception: {str(e)}")
            return False
    
    def test_step_9_chat_message(self):
        """Step 9: Chat - Send message"""
        print("\n=== 9. Chat - Send message ===")
        
        if not self.child_id:
            self.log_test("Chat Message - Child Missing", False, "No child_id from previous steps")
            return False
        
        try:
            payload = {
                "session_id": None,
                "child_id": self.child_id,
                "message": "Who is Jesus?",
                "age_tier": "7-9",
                "include_audio": True
            }
            
            response = self.session.post(f"{self.base_url}/chat", 
                                      json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["session_id", "response", "from_knowledge_base"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Chat Message - Missing Fields", False, 
                                f"Missing fields: {missing_fields}")
                    return False
                
                self.session_id = data.get("session_id")
                from_kb = data.get("from_knowledge_base", False)
                
                self.log_test("Chat Message - Success", True, 
                            f"Response received, session_id: {self.session_id}, from_knowledge_base: {from_kb}")
                return True
            else:
                self.log_test("Chat Message", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Chat Message", False, f"Exception: {str(e)}")
            return False
    
    def test_step_10_dashboard_stats(self):
        """Step 10: Dashboard - Stats"""
        print("\n=== 10. Dashboard - Stats ===")
        
        if not self.token or not self.child_id:
            self.log_test("Dashboard Stats - Missing Data", False, "No token or child_id from previous steps")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/dashboard/stats/{self.child_id}", 
                                      headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check total_conversations >= 1 (from our chat message)
                conversations = data.get("total_conversations", 0)
                
                if conversations >= 1:
                    self.log_test("Dashboard Stats - Conversations", True, 
                                f"Total conversations: {conversations} (expected >= 1)")
                else:
                    self.log_test("Dashboard Stats - Conversations", False, 
                                f"Expected >= 1 conversations, got {conversations}")
                    return False
                
                self.log_test("Dashboard Stats - Success", True, 
                            f"Stats: {conversations} conversations, {data.get('total_messages', 0)} messages")
                return True
            else:
                self.log_test("Dashboard Stats", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard Stats", False, f"Exception: {str(e)}")
            return False
    
    def test_step_11_dashboard_conversations(self):
        """Step 11: Dashboard - Conversations"""
        print("\n=== 11. Dashboard - Conversations ===")
        
        if not self.token or not self.child_id:
            self.log_test("Dashboard Conversations - Missing Data", False, "No token or child_id from previous steps")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/dashboard/conversations/{self.child_id}", 
                                      headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if "conversations" in data:
                    conversations = data["conversations"]
                    
                    if len(conversations) > 0:
                        # Check if conversations have messages
                        has_messages = any("messages" in conv for conv in conversations)
                        
                        if has_messages:
                            self.log_test("Dashboard Conversations - Success", True, 
                                        f"Found {len(conversations)} conversations with messages")
                            return True
                        else:
                            self.log_test("Dashboard Conversations - No Messages", False, 
                                        "Conversations found but no messages field")
                            return False
                    else:
                        self.log_test("Dashboard Conversations - Empty", False, 
                                    "No conversations found (expected at least 1)")
                        return False
                else:
                    self.log_test("Dashboard Conversations - Structure", False, 
                                "Response missing 'conversations' field")
                    return False
            else:
                self.log_test("Dashboard Conversations", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard Conversations", False, f"Exception: {str(e)}")
            return False
    
    def test_step_12_logout(self):
        """Step 12: Auth - Logout"""
        print("\n=== 12. Auth - Logout ===")
        
        if not self.token:
            self.log_test("Logout - Token Missing", False, "No token from previous steps")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.post(f"{self.base_url}/auth/logout", 
                                       headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Logout - Success", True, 
                            f"Logout successful: {data.get('message', 'No message')}")
                return True
            else:
                self.log_test("Logout", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Logout", False, f"Exception: {str(e)}")
            return False
    
    def test_step_13_auth_me_after_logout(self):
        """Step 13: Auth - Me after logout (should return 401)"""
        print("\n=== 13. Auth - Me after logout ===")
        
        if not self.token:
            self.log_test("Auth Me After Logout - Token Missing", False, "No token from previous steps")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/auth/me", 
                                      headers=headers, timeout=15)
            
            if response.status_code == 401:
                self.log_test("Auth Me After Logout", True, 
                            "Correctly returned 401 for invalidated token")
                return True
            else:
                self.log_test("Auth Me After Logout", False, 
                            f"Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Auth Me After Logout", False, f"Exception: {str(e)}")
            return False
    
    def run_auth_dashboard_flow(self):
        """Run the complete 13-step auth and dashboard flow"""
        print("🎯 Bible Buddy Auth and Dashboard API Testing")
        print(f"Backend URL: {self.base_url}")
        print("="*70)
        
        # Run all 13 steps in sequence
        steps = [
            ("Step 1", self.test_step_1_register),
            ("Step 2", self.test_step_2_duplicate_register),  
            ("Step 3", self.test_step_3_login),
            ("Step 4", self.test_step_4_auth_me_with_token),
            ("Step 5", self.test_step_5_auth_me_without_token),
            ("Step 6", self.test_step_6_create_child),
            ("Step 7", self.test_step_7_create_second_child),
            ("Step 8", self.test_step_8_list_children),
            ("Step 9", self.test_step_9_chat_message),
            ("Step 10", self.test_step_10_dashboard_stats),
            ("Step 11", self.test_step_11_dashboard_conversations),
            ("Step 12", self.test_step_12_logout),
            ("Step 13", self.test_step_13_auth_me_after_logout),
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            try:
                success = step_func()
                if success:
                    success_count += 1
            except Exception as e:
                self.log_test(step_name, False, f"Unexpected exception: {str(e)}")
        
        # Summary
        print("\n" + "="*70)
        print("📊 AUTH & DASHBOARD FLOW TEST SUMMARY")
        print("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        # Show flow completion
        print(f"\n🔄 Flow Completion: {success_count}/13 steps completed successfully")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  - {test['test']}: {test['details']}")
                
        return passed_tests, failed_tests, success_count

if __name__ == "__main__":
    tester = AuthDashboardTester()
    passed, failed, flow_steps = tester.run_auth_dashboard_flow()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)