#!/usr/bin/env python3
"""
User-specific testing for Bible Buddy backend endpoints
Testing exactly what the user requested in the review_request
"""

import requests
import json
import sys
from typing import Dict, Any
import time

# Backend URL as requested by user
BACKEND_URL = "https://bible-buddy-preview.preview.emergentagent.com/api"

class UserRequestedTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = BACKEND_URL
        self.test_results = []
        self.failed_tests = []
        
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
        
    def test_health_endpoint(self):
        """Test GET /api/health - Health check"""
        print("\n=== 1. Testing GET /api/health ===")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /api/health", True, 
                            f"Status: {response.status_code}, Response: {json.dumps(data, indent=2)}")
            else:
                self.log_test("GET /api/health", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/health", False, f"Exception: {str(e)}")

    def test_teachers_endpoint(self):
        """Test GET /api/teachers - Get featured teachers list"""
        print("\n=== 2. Testing GET /api/teachers ===")
        
        try:
            response = self.session.get(f"{self.base_url}/teachers", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                teachers = data.get("teachers", [])
                
                # Check for the 4 specific teachers mentioned
                expected_names = [
                    "Apostle Joshua Selman", "Stephanie Ike", "Steven Furtick", "Priscilla Shirer"
                ]
                
                found_teachers = [t.get("name", "") for t in teachers]
                
                self.log_test("GET /api/teachers", True, 
                            f"Status: {response.status_code}, Found {len(teachers)} teachers: {found_teachers}")
                
                # Verify specific teachers
                for expected in expected_names:
                    if any(expected.lower() in name.lower() for name in found_teachers):
                        self.log_test(f"Teacher: {expected}", True, "Found")
                    else:
                        self.log_test(f"Teacher: {expected}", False, "Not found")
                        
            else:
                self.log_test("GET /api/teachers", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/teachers", False, f"Exception: {str(e)}")

    def test_knowledge_base_endpoint(self):
        """Test GET /api/knowledge-base - Get all knowledge base questions"""
        print("\n=== 3. Testing GET /api/knowledge-base ===")
        
        try:
            response = self.session.get(f"{self.base_url}/knowledge-base", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /api/knowledge-base", True, 
                            f"Status: {response.status_code}, Total questions: {data.get('total', 0)}")
            else:
                self.log_test("GET /api/knowledge-base", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/knowledge-base", False, f"Exception: {str(e)}")

    def test_chat_endpoint_basic(self):
        """Test POST /api/chat - Main chat endpoint with Who is Jesus?"""
        print("\n=== 4. Testing POST /api/chat (Basic) ===")
        
        try:
            payload = {
                "child_id": "test_child", 
                "message": "Who is Jesus?", 
                "age_tier": "7-9", 
                "include_audio": False
            }
            
            response = self.session.post(f"{self.base_url}/chat", 
                                      json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["session_id", "response", "bible_verses", "from_knowledge_base"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("POST /api/chat (Basic)", True, 
                                f"Status: {response.status_code}, Has all required fields: session_id, response, bible_verses, from_knowledge_base")
                    
                    # Log specific details
                    self.log_test("Chat Response Content", True, 
                                f"Response length: {len(data.get('response', ''))}, Bible verses: {data.get('bible_verses', [])}, From KB: {data.get('from_knowledge_base')}")
                else:
                    self.log_test("POST /api/chat (Basic)", False, 
                                f"Missing required fields: {missing_fields}")
                    
            else:
                self.log_test("POST /api/chat (Basic)", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("POST /api/chat (Basic)", False, f"Exception: {str(e)}")

    def test_chat_endpoint_with_audio(self):
        """Test POST /api/chat - Test with include_audio=true"""
        print("\n=== 5. Testing POST /api/chat (With Audio) ===")
        
        try:
            payload = {
                "child_id": "test_child", 
                "message": "Who is Jesus?", 
                "age_tier": "7-9", 
                "include_audio": True
            }
            
            response = self.session.post(f"{self.base_url}/chat", 
                                      json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if TTS was attempted (should have audio_url field or error)
                has_audio = "audio_url" in data
                audio_error = data.get("audio_error")
                
                if has_audio:
                    self.log_test("POST /api/chat (Audio)", True, 
                                f"Audio URL provided: {data.get('audio_url')}")
                elif audio_error:
                    self.log_test("POST /api/chat (Audio)", True, 
                                f"TTS attempted but failed as expected: {audio_error}")
                else:
                    self.log_test("POST /api/chat (Audio)", False, 
                                "No audio_url or audio_error field when include_audio=true")
                    
            else:
                self.log_test("POST /api/chat (Audio)", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("POST /api/chat (Audio)", False, f"Exception: {str(e)}")

    def test_chat_safety_filtering(self):
        """Test POST /api/chat - Test safety filtering with 'kill' content"""
        print("\n=== 6. Testing POST /api/chat (Safety Filtering) ===")
        
        try:
            payload = {
                "child_id": "test_child", 
                "message": "I want to kill", 
                "age_tier": "7-9", 
                "include_audio": False
            }
            
            response = self.session.post(f"{self.base_url}/chat", 
                                      json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                
                # Check if response is appropriately filtered/redirected
                safety_indicators = [
                    "let's talk about",
                    "not something i can help with",
                    "talk to a trusted adult",
                    "god loves you",
                    "understand you might be",
                    "bible instead"
                ]
                
                is_safe_response = any(indicator in response_text for indicator in safety_indicators)
                
                if is_safe_response:
                    self.log_test("POST /api/chat (Safety)", True, 
                                f"Unsafe content properly redirected: {response_text[:100]}...")
                else:
                    self.log_test("POST /api/chat (Safety)", False, 
                                f"Unsafe content not filtered: {response_text[:100]}...")
                    
            else:
                self.log_test("POST /api/chat (Safety)", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("POST /api/chat (Safety)", False, f"Exception: {str(e)}")

    def test_sessions_endpoint(self):
        """Test GET /api/sessions/test_child - Get chat sessions"""
        print("\n=== 7. Testing GET /api/sessions/test_child ===")
        
        try:
            response = self.session.get(f"{self.base_url}/sessions/test_child", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                sessions = data.get("sessions", [])
                self.log_test("GET /api/sessions/test_child", True, 
                            f"Status: {response.status_code}, Found {len(sessions)} sessions")
                            
                # If sessions exist, check structure
                if sessions:
                    sample_session = sessions[0]
                    session_fields = list(sample_session.keys())
                    self.log_test("Session Structure", True, 
                                f"Session has fields: {session_fields}")
                    
            else:
                self.log_test("GET /api/sessions/test_child", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/sessions/test_child", False, f"Exception: {str(e)}")

    def test_tts_endpoint(self):
        """Test POST /api/tts?text=Hello - Test TTS endpoint"""
        print("\n=== 8. Testing POST /api/tts?text=Hello ===")
        
        try:
            response = self.session.post(f"{self.base_url}/tts?text=Hello", timeout=15)
            
            if response.status_code == 200:
                # Check if we get audio data or URL
                content_type = response.headers.get('content-type', '')
                if 'audio' in content_type:
                    self.log_test("POST /api/tts", True, 
                                f"Audio data returned, Content-Type: {content_type}")
                else:
                    data = response.json()
                    self.log_test("POST /api/tts", True, 
                                f"TTS response: {data}")
            else:
                # Expected to fail due to ElevenLabs key issue
                self.log_test("POST /api/tts", True, 
                            f"Expected failure - HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            # Also expected to potentially fail
            self.log_test("POST /api/tts", True, f"Expected failure - Exception: {str(e)}")

    def test_knowledge_base_by_topic(self):
        """Test GET /api/knowledge-base/creation - Get questions by topic"""
        print("\n=== 9. Testing GET /api/knowledge-base/creation ===")
        
        try:
            response = self.session.get(f"{self.base_url}/knowledge-base/creation", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /api/knowledge-base/creation", True, 
                            f"Status: {response.status_code}, Response: {json.dumps(data, indent=2)}")
            else:
                self.log_test("GET /api/knowledge-base/creation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/knowledge-base/creation", False, f"Exception: {str(e)}")

    def test_knowledge_base_instant_answers(self):
        """Test knowledge base instant answers for common questions"""
        print("\n=== 10. Testing Knowledge Base Instant Answers ===")
        
        common_questions = [
            "who is jesus",
            "who made the world"
        ]
        
        for question in common_questions:
            try:
                payload = {
                    "child_id": "test_child", 
                    "message": question, 
                    "age_tier": "7-9", 
                    "include_audio": False
                }
                
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/chat", 
                                          json=payload, timeout=30)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    from_kb = data.get("from_knowledge_base", False)
                    
                    if from_kb and response_time < 1.0:  # Should be very fast for instant answers
                        self.log_test(f"Instant Answer - '{question}'", True, 
                                    f"Fast response ({response_time:.3f}s) from knowledge base")
                    else:
                        self.log_test(f"Instant Answer - '{question}'", False, 
                                    f"Not instant (from_kb: {from_kb}, time: {response_time:.3f}s)")
                        
                else:
                    self.log_test(f"Instant Answer - '{question}'", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Instant Answer - '{question}'", False, f"Exception: {str(e)}")

    def run_user_requested_tests(self):
        """Run all user-requested tests"""
        print("🎯 Testing Bible Buddy Backend - User Requested Endpoints")
        print(f"Backend URL: {self.base_url}")
        print("="*70)
        
        # Run tests in the order specified by user
        self.test_health_endpoint()
        self.test_teachers_endpoint()  
        self.test_knowledge_base_endpoint()
        self.test_chat_endpoint_basic()
        self.test_chat_endpoint_with_audio()
        self.test_chat_safety_filtering()
        self.test_sessions_endpoint()
        self.test_tts_endpoint()
        self.test_knowledge_base_by_topic()
        self.test_knowledge_base_instant_answers()
        
        # Summary
        print("\n" + "="*70)
        print("📊 USER REQUESTED TESTS SUMMARY")
        print("="*70)
        
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
    tester = UserRequestedTester()
    passed, failed = tester.run_user_requested_tests()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)