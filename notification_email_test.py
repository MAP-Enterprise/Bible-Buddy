#!/usr/bin/env python3
"""
Bible Buddy Notification & Email API Testing Suite
Comprehensive test for notification and email endpoints as specified in review request
"""

import requests
import json
import sys
from typing import Dict, Any
import time
import uuid

# Backend URL from environment
BACKEND_URL = "https://bible-buddy-auth.preview.emergentagent.com/api"

class NotificationEmailTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = BACKEND_URL
        self.test_results = []
        self.failed_tests = []
        self.token = None
        self.child_id = None
        
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
    
    def setup_test_user(self):
        """Step 1: Register a new parent and create a child"""
        print("\n=== STEP 1: SETUP - REGISTER & CREATE CHILD ===")
        
        timestamp = int(time.time())
        email = f"notiftest_{timestamp}@test.com"
        
        try:
            # Register parent
            register_payload = {
                "email": email,
                "password": "TestPass123!",
                "name": "Notif Test Parent"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", 
                                       json=register_payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.log_test("User Registration", True, 
                            f"Registered user: {email}, token starts with: {self.token[:5]}...")
            else:
                self.log_test("User Registration", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Create child
            if self.token:
                child_payload = {
                    "name": "TestKid",
                    "age_tier": "7-9"
                }
                
                headers = {"Authorization": f"Bearer {self.token}"}
                response = self.session.post(f"{self.base_url}/children", 
                                           json=child_payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self.child_id = data.get("child_id")
                    self.log_test("Child Creation", True, 
                                f"Created child: {child_payload['name']}, ID: {self.child_id}")
                    return True
                else:
                    self.log_test("Child Creation", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            self.log_test("Setup", False, f"Exception: {str(e)}")
            return False
    
    def test_notification_settings_get_defaults(self):
        """Step 2: GET notification settings defaults"""
        print("\n=== STEP 2: NOTIFICATION SETTINGS - GET DEFAULTS ===")
        
        if not self.token:
            self.log_test("Get Defaults", False, "No authentication token")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/notifications/settings", 
                                      headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected defaults
                expected_defaults = {
                    "notify_on_session_start": True,
                    "notify_on_every_message": False,
                    "email_weekly_summary": True
                }
                
                all_correct = True
                for key, expected_value in expected_defaults.items():
                    actual_value = data.get(key)
                    if actual_value != expected_value:
                        self.log_test(f"Default {key}", False, 
                                    f"Expected {expected_value}, got {actual_value}")
                        all_correct = False
                
                if all_correct:
                    self.log_test("Notification Settings Defaults", True, 
                                f"All defaults correct: {data}")
                    
                # Check that push_tokens_count is present
                if "push_tokens_count" in data:
                    self.log_test("Push Tokens Count Field", True, 
                                f"push_tokens_count: {data['push_tokens_count']}")
                else:
                    self.log_test("Push Tokens Count Field", False, "Missing push_tokens_count field")
                    
            else:
                self.log_test("Get Notification Settings", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get Notification Settings", False, f"Exception: {str(e)}")
    
    def test_notification_settings_update(self):
        """Step 3: UPDATE notification settings"""
        print("\n=== STEP 3: NOTIFICATION SETTINGS - UPDATE ===")
        
        if not self.token:
            self.log_test("Update Settings", False, "No authentication token")
            return
        
        try:
            update_payload = {
                "notify_on_every_message": True,
                "notify_on_session_start": False
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.put(f"{self.base_url}/notifications/settings", 
                                      json=update_payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test("Update Notification Settings", True, 
                                f"Settings updated successfully: {data}")
                else:
                    self.log_test("Update Notification Settings", False, 
                                f"Unexpected response: {data}")
            else:
                self.log_test("Update Notification Settings", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Update Notification Settings", False, f"Exception: {str(e)}")
    
    def test_notification_settings_verify_update(self):
        """Step 4: Verify notification settings update"""
        print("\n=== STEP 4: NOTIFICATION SETTINGS - VERIFY UPDATE ===")
        
        if not self.token:
            self.log_test("Verify Update", False, "No authentication token")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/notifications/settings", 
                                      headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that our updates were applied
                expected_values = {
                    "notify_on_session_start": False,
                    "notify_on_every_message": True
                }
                
                all_correct = True
                for key, expected_value in expected_values.items():
                    actual_value = data.get(key)
                    if actual_value != expected_value:
                        self.log_test(f"Verify {key}", False, 
                                    f"Expected {expected_value}, got {actual_value}")
                        all_correct = False
                
                if all_correct:
                    self.log_test("Verify Settings Update", True, 
                                f"All updates applied correctly: {data}")
                    
            else:
                self.log_test("Verify Settings Update", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Verify Settings Update", False, f"Exception: {str(e)}")
    
    def test_register_push_token(self):
        """Step 5: Register push notification token"""
        print("\n=== STEP 5: REGISTER PUSH TOKEN ===")
        
        if not self.token:
            self.log_test("Register Push Token", False, "No authentication token")
            return
        
        try:
            token_payload = {
                "token": "ExponentPushToken[testxyz123]",
                "device_id": "test_device",
                "platform": "web"
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.post(f"{self.base_url}/notifications/register-token", 
                                       json=token_payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test("Register Push Token", True, 
                                f"Push token registered: {data}")
                else:
                    self.log_test("Register Push Token", False, 
                                f"Unexpected response: {data}")
            else:
                self.log_test("Register Push Token", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Register Push Token", False, f"Exception: {str(e)}")
    
    def test_verify_push_token_registered(self):
        """Step 6: Verify push token was registered"""
        print("\n=== STEP 6: VERIFY PUSH TOKEN REGISTERED ===")
        
        if not self.token:
            self.log_test("Verify Push Token", False, "No authentication token")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/notifications/settings", 
                                      headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                push_tokens_count = data.get("push_tokens_count", 0)
                
                if push_tokens_count == 1:
                    self.log_test("Verify Push Token Count", True, 
                                f"Push token count is 1 as expected")
                else:
                    self.log_test("Verify Push Token Count", False, 
                                f"Expected push_tokens_count: 1, got: {push_tokens_count}")
                    
            else:
                self.log_test("Verify Push Token", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Verify Push Token", False, f"Exception: {str(e)}")
    
    def test_chat_triggers_notification(self):
        """Step 7: Send chat message (triggers notification)"""
        print("\n=== STEP 7: CHAT - SEND MESSAGE (TRIGGERS NOTIFICATION) ===")
        
        if not self.child_id:
            self.log_test("Chat Trigger", False, "No child ID available")
            return
        
        try:
            chat_payload = {
                "session_id": None,
                "child_id": self.child_id,
                "message": "Who is Jesus?",
                "age_tier": "7-9",
                "include_audio": False
            }
            
            response = self.session.post(f"{self.base_url}/chat", 
                                       json=chat_payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that we got a proper chat response
                if data.get("response") and data.get("session_id"):
                    self.log_test("Chat Message (Notification Trigger)", True, 
                                f"Chat successful, response length: {len(data['response'])} chars")
                else:
                    self.log_test("Chat Message (Notification Trigger)", False, 
                                f"Incomplete chat response: {data}")
                    
            else:
                self.log_test("Chat Message (Notification Trigger)", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Chat Message (Notification Trigger)", False, f"Exception: {str(e)}")
    
    def test_email_preview_weekly_summary(self):
        """Step 8: Preview weekly summary email"""
        print("\n=== STEP 8: EMAIL - PREVIEW WEEKLY SUMMARY ===")
        
        if not self.token:
            self.log_test("Email Preview", False, "No authentication token")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/email/preview-weekly-summary", 
                                      headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                
                # Check that it's HTML and contains expected content
                if "text/html" in response.headers.get("content-type", "").lower() or content.strip().startswith("<!DOCTYPE html"):
                    # Check for key elements in the email
                    required_elements = ["Bible Buddy", "Weekly Summary"]
                    missing_elements = [elem for elem in required_elements if elem not in content]
                    
                    if not missing_elements:
                        self.log_test("Email Preview Content", True, 
                                    f"HTML email contains required elements. Length: {len(content)} chars")
                    else:
                        self.log_test("Email Preview Content", False, 
                                    f"Missing elements: {missing_elements}")
                else:
                    self.log_test("Email Preview Format", False, 
                                "Response is not HTML format")
                    
            else:
                self.log_test("Email Preview", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Email Preview", False, f"Exception: {str(e)}")
    
    def test_notification_settings_disable_email(self):
        """Step 9: Disable email weekly summary"""
        print("\n=== STEP 9: NOTIFICATION SETTINGS - DISABLE EMAIL ===")
        
        if not self.token:
            self.log_test("Disable Email", False, "No authentication token")
            return
        
        try:
            update_payload = {
                "email_weekly_summary": False
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.put(f"{self.base_url}/notifications/settings", 
                                      json=update_payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test("Disable Email Summary", True, 
                                f"Email summary disabled: {data}")
                else:
                    self.log_test("Disable Email Summary", False, 
                                f"Unexpected response: {data}")
            else:
                self.log_test("Disable Email Summary", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Disable Email Summary", False, f"Exception: {str(e)}")
    
    def test_unauthenticated_access(self):
        """Step 10: Test unauthenticated access"""
        print("\n=== STEP 10: AUTH - UNAUTHENTICATED ACCESS ===")
        
        try:
            # Test notifications settings without token
            response1 = self.session.get(f"{self.base_url}/notifications/settings", timeout=10)
            
            if response1.status_code == 401:
                self.log_test("Notifications - Unauthenticated", True, 
                            "Correctly returned 401 for notifications/settings")
            else:
                self.log_test("Notifications - Unauthenticated", False, 
                            f"Expected 401, got {response1.status_code}")
            
            # Test email send without token
            response2 = self.session.post(f"{self.base_url}/email/send-weekly-summary", timeout=10)
            
            if response2.status_code == 401:
                self.log_test("Email - Unauthenticated", True, 
                            "Correctly returned 401 for email/send-weekly-summary")
            else:
                self.log_test("Email - Unauthenticated", False, 
                            f"Expected 401, got {response2.status_code}")
                
        except Exception as e:
            self.log_test("Unauthenticated Access", False, f"Exception: {str(e)}")
    
    def run_full_test_flow(self):
        """Run the complete 10-step notification and email test flow"""
        print("🚀 Starting Bible Buddy Notification & Email API Testing...")
        print(f"Backend URL: {self.base_url}")
        
        # Run all steps in sequence
        if self.setup_test_user():
            self.test_notification_settings_get_defaults()
            self.test_notification_settings_update()
            self.test_notification_settings_verify_update()
            self.test_register_push_token()
            self.test_verify_push_token_registered()
            self.test_chat_triggers_notification()
            self.test_email_preview_weekly_summary()
            self.test_notification_settings_disable_email()
        else:
            print("❌ Setup failed, skipping remaining tests")
        
        # Always test unauthenticated access
        self.test_unauthenticated_access()
        
        # Summary
        print("\n" + "="*60)
        print("📊 NOTIFICATION & EMAIL TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return passed_tests, failed_tests

if __name__ == "__main__":
    tester = NotificationEmailTester()
    passed, failed = tester.run_full_test_flow()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)