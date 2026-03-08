from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import uuid
from datetime import datetime
import base64
from emergentintegrations.llm.chat import LlmChat, UserMessage
from elevenlabs import ElevenLabs, VoiceSettings
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

# ElevenLabs client
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Create the main app
app = FastAPI(title="Bible Buddy API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class AgeTier(str):
    """Age tier types"""
    pass

AGE_TIERS = ["4-6", "7-9", "10-12", "13-18"]

class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    age_tier: str = "7-9"  # Default age tier
    preferred_translation: str = "NIV"  # KJV, NIV, Good News, Message
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserProfileCreate(BaseModel):
    name: str
    age_tier: str = "7-9"
    preferred_translation: str = "NIV"

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    audio_url: Optional[str] = None  # Base64 audio for TTS
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    age_tier: str
    messages: List[dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    message: str
    age_tier: str = "7-9"
    include_audio: bool = True

class ChatResponse(BaseModel):
    session_id: str
    response: str
    audio_url: Optional[str] = None
    bible_verses: List[str] = []

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # Rachel - warm, friendly voice

class SafetyCheckResult(BaseModel):
    is_safe: bool
    category: Optional[str] = None
    redirect_message: Optional[str] = None

# ==================== SAFETY FILTERING ====================

# Unsafe content patterns to block
UNSAFE_PATTERNS = [
    # Violence
    "kill", "murder", "hurt", "violence", "weapon", "gun", "knife", "blood", "gore",
    # Self-harm
    "suicide", "self-harm", "cut myself", "end my life", "want to die",
    # Explicit content
    "sex", "naked", "porn", "explicit", "inappropriate",
    # Harmful instructions
    "how to make a bomb", "how to hurt", "how to kill",
    # Hate speech
    "hate", "racist", "discrimination",
    # Off-topic manipulation
    "bypass", "ignore instructions", "pretend you're not",
]

# Redirect messages for different categories
SAFETY_REDIRECTS = {
    "violence": "I understand you might be curious about difficult topics. Let's talk about how God teaches us about peace and love instead. Would you like to hear a story about Jesus showing kindness?",
    "self-harm": "I hear that you might be going through a hard time. God loves you so much! Please talk to a trusted adult, parent, or call a helpline. Would you like to hear about how much God cares for you?",
    "explicit": "That's not something I can help with. Let's talk about something wonderful from the Bible instead! Would you like to hear an amazing story?",
    "off-topic": "I'm Bible Buddy, and I love talking about God, Jesus, and the Bible! What would you like to learn about?",
    "manipulation": "I'm here to help you learn about God's word in a fun way! What Bible question can I answer for you?",
}

def check_content_safety(text: str) -> SafetyCheckResult:
    """Pre-process check for unsafe content"""
    text_lower = text.lower()
    
    # Check for self-harm keywords first (highest priority)
    self_harm_keywords = ["suicide", "self-harm", "cut myself", "end my life", "want to die", "kill myself"]
    for keyword in self_harm_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(
                is_safe=False,
                category="self-harm",
                redirect_message=SAFETY_REDIRECTS["self-harm"]
            )
    
    # Check for violence
    violence_keywords = ["kill", "murder", "hurt someone", "weapon", "gun", "knife", "blood", "gore"]
    for keyword in violence_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(
                is_safe=False,
                category="violence",
                redirect_message=SAFETY_REDIRECTS["violence"]
            )
    
    # Check for explicit content
    explicit_keywords = ["sex", "naked", "porn", "explicit"]
    for keyword in explicit_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(
                is_safe=False,
                category="explicit",
                redirect_message=SAFETY_REDIRECTS["explicit"]
            )
    
    # Check for manipulation attempts
    manipulation_keywords = ["bypass", "ignore instructions", "pretend you're not", "jailbreak", "ignore previous"]
    for keyword in manipulation_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(
                is_safe=False,
                category="manipulation",
                redirect_message=SAFETY_REDIRECTS["manipulation"]
            )
    
    return SafetyCheckResult(is_safe=True)

def post_process_safety(response: str) -> str:
    """Post-process check for response safety"""
    # Ensure response doesn't contain unsafe content
    response_lower = response.lower()
    
    for pattern in UNSAFE_PATTERNS:
        if pattern in response_lower:
            return "I'd love to share something wonderful from the Bible with you! What would you like to learn about?"
    
    return response

# ==================== AGE-TIER PROMPTS ====================

def get_age_tier_system_prompt(age_tier: str, preferred_translation: str = "NIV") -> str:
    """Get age-appropriate system prompt"""
    
    base_guidelines = f"""
You are Bible Buddy, a warm, friendly, and loving guide who helps children learn about God, Jesus, and the Bible.

CORE PRINCIPLES:
1. Always ground your answers in Scripture - cite verses from {preferred_translation} translation when relevant
2. Be age-appropriate in vocabulary and explanation depth
3. Never be preachy or judgmental - be encouraging and loving
4. Show empathy and understanding
5. Keep children safe - never discuss inappropriate topics
6. If asked something outside of Bible/faith topics, gently redirect to spiritual discussions
7. Use multiple Bible translations when helpful: KJV, NIV, Good News, Message Translation

SAFETY RULES (CRITICAL):
- Never provide harmful information
- Always redirect sensitive topics to trusted adults
- Maintain a positive, encouraging tone
- If unsure about appropriateness, err on the side of caution
"""

    age_prompts = {
        "4-6": f"""{base_guidelines}

AGE GROUP: 4-6 years old (Preschool/Kindergarten)

COMMUNICATION STYLE:
- Use very simple words (1-2 syllable words preferred)
- Short sentences (5-8 words max)
- Be playful and fun - use expressions like "Wow!", "That's so cool!"
- Use lots of comparisons to things kids know (toys, animals, family)
- Tell stories like they're adventures
- Be extra warm and encouraging
- Use repetition to help them remember

EXPLANATION DEPTH:
- Focus on one simple idea at a time
- Use concrete examples they can see and touch
- Relate everything to love, kindness, and family
- Keep Bible verses very short (just a few words)

SCRIPTURE STYLE:
- Paraphrase verses in super simple language
- Focus on the feeling/message, not exact words
- Example: "God loves you SO much!" instead of quoting John 3:16 directly

EXAMPLE RESPONSE for "Who made the world?":
"Guess what? God made EVERYTHING! 🌟 He made the fluffy clouds, the sparkly stars, the cute puppies, and even YOU! The Bible says God looked at everything He made and said 'This is GOOD!' God is so amazing and He loves you so, so much!"
""",

        "7-9": f"""{base_guidelines}

AGE GROUP: 7-9 years old (Early Elementary)

COMMUNICATION STYLE:
- Use clear, simple language but can include some bigger words with explanation
- Sentences can be longer (8-12 words)
- Be enthusiastic and encouraging
- Use stories and examples from everyday life
- Can introduce simple Bible characters and their adventures
- Ask engaging questions to keep them thinking

EXPLANATION DEPTH:
- Can explain simple concepts with a bit more detail
- Connect Bible stories to their daily lives
- Introduce cause and effect in stories
- Can discuss feelings and choices

SCRIPTURE STYLE:
- Can quote short verses directly
- Always explain what the verse means in simple words
- Reference the book name: "The Bible says in {preferred_translation}..."

EXAMPLE RESPONSE for "Why did Jesus die?":
"That's such an important question! Jesus loved everyone SO much - even you and me! He died on the cross to take away the bad things (sins) that separate us from God. It's like if you broke your mom's favorite vase, and your big brother said 'I'll take the punishment for you.' That's what Jesus did for us! And guess what? He came back to life! The Bible says 'God so loved the world that He gave His one and only Son' (John 3:16). Isn't that amazing love?"
""",

        "10-12": f"""{base_guidelines}

AGE GROUP: 10-12 years old (Upper Elementary/Pre-teen)

COMMUNICATION STYLE:
- Use age-appropriate vocabulary - can introduce theological terms with explanation
- Longer, more complex sentences are okay
- Be thoughtful and engaging
- Encourage questions and deeper thinking
- Can discuss more complex emotions and situations
- Be relatable - understand their world

EXPLANATION DEPTH:
- Can explore concepts in more depth
- Discuss context and background of Bible stories
- Connect faith to real-life challenges they face
- Can introduce different perspectives respectfully

SCRIPTURE STYLE:
- Quote verses more fully with reference
- Can compare different translations
- Encourage them to look up verses themselves
- Discuss what verses mean in context

EXAMPLE RESPONSE for "Why does God let bad things happen?":
"That's one of the deepest questions people ask, and it shows you're really thinking! The Bible doesn't give us one simple answer, but here's what we do know: God gave people free will - the ability to make choices. Sometimes people make bad choices that hurt others. Also, we live in a world that's not perfect because of sin.

But here's the amazing part - God promises to be WITH us through hard times. Romans 8:28 says 'God works all things together for good for those who love Him.' This doesn't mean bad things are good, but that God can bring something good out of them.

Jesus himself suffered, so He understands our pain. And one day, God promises to make everything right. What made you think about this question?"
""",

        "13-18": f"""{base_guidelines}

AGE GROUP: 13-18 years old (Teenager)

COMMUNICATION STYLE:
- Speak to them as a mature friend, not talking down
- Can use complex vocabulary and theological terms
- Be authentic and honest - teens detect fake quickly
- Acknowledge when questions are hard or when there are different views
- Respect their intelligence and ability to think critically
- Be relevant to their real struggles

EXPLANATION DEPTH:
- Dive deep into theological concepts
- Discuss historical and cultural context
- Present multiple interpretations fairly when relevant
- Connect faith to real issues they face (identity, relationships, future)
- Encourage critical thinking while grounding in Scripture

SCRIPTURE STYLE:
- Quote verses fully with context
- Discuss original language meanings when helpful
- Compare translations: KJV, NIV, Good News, Message
- Encourage personal Bible study

EXAMPLE RESPONSE for "How do I know God is real?":
"This is probably one of the most honest and important questions you can ask. Let me share a few perspectives:

**Philosophical**: Many thinkers point to the 'fine-tuning' of the universe - the precise conditions needed for life suggest design rather than chance. Also, where does our sense of morality come from?

**Historical**: The resurrection of Jesus is one of the best-documented events in ancient history. Even skeptical historians acknowledge something happened that transformed fearful disciples into bold witnesses.

**Personal**: Millions of people throughout history describe encountering God in prayer, through Scripture, and in their lives. Romans 1:20 says 'Since the creation of the world God's invisible qualities have been clearly seen.'

**Honest acknowledgment**: Faith involves trust in what we can't fully prove. Hebrews 11:1 calls faith 'confidence in what we hope for and assurance about what we do not see.'

Doubt isn't the opposite of faith - it's often part of the journey. What specifically makes you wonder about this?"
"""
    }
    
    return age_prompts.get(age_tier, age_prompts["7-9"])

# ==================== API ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {"message": "Welcome to Bible Buddy API!", "status": "online"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_configured": bool(EMERGENT_LLM_KEY),
        "tts_configured": bool(ELEVENLABS_API_KEY)
    }

# User Profile Endpoints
@api_router.post("/users", response_model=UserProfile)
async def create_user(user: UserProfileCreate):
    """Create a new user profile"""
    user_obj = UserProfile(**user.dict())
    await db.users.insert_one(user_obj.dict())
    return user_obj

@api_router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str):
    """Get user profile by ID"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(**user)

@api_router.put("/users/{user_id}", response_model=UserProfile)
async def update_user(user_id: str, updates: UserProfileCreate):
    """Update user profile"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": updates.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    user = await db.users.find_one({"id": user_id})
    return UserProfile(**user)

# Chat Session Endpoints
@api_router.post("/sessions", response_model=ChatSession)
async def create_session(user_id: str, age_tier: str = "7-9"):
    """Create a new chat session"""
    session = ChatSession(user_id=user_id, age_tier=age_tier)
    await db.sessions.insert_one(session.dict())
    return session

@api_router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(session_id: str):
    """Get chat session with message history"""
    session = await db.sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatSession(**session)

@api_router.get("/users/{user_id}/sessions", response_model=List[ChatSession])
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    sessions = await db.sessions.find({"user_id": user_id}).to_list(100)
    return [ChatSession(**s) for s in sessions]

# Main Chat Endpoint
@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with safety filtering and age-appropriate responses"""
    
    # Step 1: Pre-process safety check
    safety_check = check_content_safety(request.message)
    if not safety_check.is_safe:
        # Log blocked content
        await db.safety_logs.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": request.user_id,
            "message": request.message,
            "category": safety_check.category,
            "timestamp": datetime.utcnow()
        })
        
        # Generate audio for redirect message if requested
        audio_url = None
        if request.include_audio and eleven_client:
            try:
                audio_url = await generate_tts_audio(safety_check.redirect_message)
            except Exception as e:
                logger.error(f"TTS error: {e}")
        
        return ChatResponse(
            session_id=request.session_id or str(uuid.uuid4()),
            response=safety_check.redirect_message,
            audio_url=audio_url,
            bible_verses=[]
        )
    
    # Step 2: Get or create session
    session_id = request.session_id
    if session_id:
        session = await db.sessions.find_one({"id": session_id})
        if not session:
            session = ChatSession(id=session_id, user_id=request.user_id, age_tier=request.age_tier)
            await db.sessions.insert_one(session.dict())
    else:
        session = ChatSession(user_id=request.user_id, age_tier=request.age_tier)
        session_id = session.id
        await db.sessions.insert_one(session.dict())
    
    # Step 3: Get user preferences
    user = await db.users.find_one({"id": request.user_id})
    preferred_translation = user.get("preferred_translation", "NIV") if user else "NIV"
    
    # Step 4: Build conversation history
    session_data = await db.sessions.find_one({"id": session_id})
    messages_history = session_data.get("messages", []) if session_data else []
    
    # Step 5: Generate response using LLM
    try:
        system_prompt = get_age_tier_system_prompt(request.age_tier, preferred_translation)
        
        chat_client = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        # Add conversation history for context
        context = ""
        if messages_history:
            recent_messages = messages_history[-6:]  # Last 3 exchanges
            for msg in recent_messages:
                role = "Child" if msg.get("role") == "user" else "Bible Buddy"
                context += f"{role}: {msg.get('content', '')}\n"
        
        # Create the message with context
        full_message = f"{context}\nChild: {request.message}" if context else request.message
        
        user_message = UserMessage(text=full_message)
        response_text = await chat_client.send_message(user_message)
        
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        response_text = "I'm having a little trouble right now. Can you ask me again? I love talking about the Bible with you!"
    
    # Step 6: Post-process safety check
    response_text = post_process_safety(response_text)
    
    # Step 7: Extract Bible verses from response
    bible_verses = extract_bible_verses(response_text)
    
    # Step 8: Generate TTS audio if requested
    audio_url = None
    if request.include_audio and eleven_client:
        try:
            audio_url = await generate_tts_audio(response_text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    # Step 9: Save messages to session
    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat()
    }
    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": response_text,
        "audio_url": audio_url,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await db.sessions.update_one(
        {"id": session_id},
        {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        audio_url=audio_url,
        bible_verses=bible_verses
    )

# Text-to-Speech Endpoint
@api_router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Generate speech from text using ElevenLabs"""
    if not eleven_client:
        raise HTTPException(status_code=503, detail="TTS service not configured")
    
    try:
        audio_url = await generate_tts_audio(request.text, request.voice_id)
        return {"audio_url": audio_url}
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_tts_audio(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL") -> str:
    """Generate TTS audio and return as base64"""
    if not eleven_client:
        return None
    
    try:
        # Use a child-friendly voice with warm settings
        voice_settings = VoiceSettings(
            stability=0.7,
            similarity_boost=0.75,
            style=0.5,
            use_speaker_boost=True
        )
        
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=voice_settings
        )
        
        # Collect audio data
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk
        
        # Convert to base64
        audio_b64 = base64.b64encode(audio_data).decode()
        return f"data:audio/mpeg;base64,{audio_b64}"
        
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        return None

def extract_bible_verses(text: str) -> List[str]:
    """Extract Bible verse references from response text"""
    import re
    # Pattern to match common Bible verse formats
    patterns = [
        r'\b(\d?\s*[A-Za-z]+\s+\d+:\d+(?:-\d+)?)\b',  # John 3:16, 1 John 4:7-8
        r'\b([A-Za-z]+\s+\d+:\d+(?:-\d+)?)\b',  # Genesis 1:1
    ]
    
    verses = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        verses.extend(matches)
    
    return list(set(verses))  # Remove duplicates

# Safety Check Endpoint (for testing)
@api_router.post("/safety/check")
async def check_safety(text: str):
    """Check if text is safe"""
    result = check_content_safety(text)
    return result.dict()

# Get Available Voices
@api_router.get("/voices")
async def get_voices():
    """Get available ElevenLabs voices"""
    if not eleven_client:
        return {"voices": [], "message": "TTS not configured"}
    
    try:
        voices_response = eleven_client.voices.get_all()
        voices = [
            {
                "voice_id": v.voice_id,
                "name": v.name,
                "category": getattr(v, 'category', 'custom')
            }
            for v in voices_response.voices[:10]  # Limit to 10 voices
        ]
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Voices error: {e}")
        return {"voices": [], "error": str(e)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
