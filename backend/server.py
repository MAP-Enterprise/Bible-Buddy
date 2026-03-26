from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import base64
from anthropic import AsyncAnthropic

async def _anthropic_chat(system_message: str, user_text: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 600) -> str:
    """Drop-in replacement for LlmChat - calls Anthropic API directly."""
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_message,
        messages=[{"role": "user", "content": user_text}]
    )
    return response.content[0].text

try:
    from elevenlabs import ElevenLabs, VoiceSettings
except ImportError:
    ElevenLabs = None
    VoiceSettings = None
# Deepgram is used via REST API directly
import aiohttp
import io

import asyncio

ROOT_DIR = Path(__file__).parent
AUDIO_CACHE_DIR = ROOT_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(exist_ok=True)

# Background TTS task tracker
_tts_tasks: Dict[str, asyncio.Task] = {}

# In-memory cache for KB age-adapted answers (avoids MongoDB round-trip)
_kb_cache: Dict[str, str] = {}
# In-memory cache for user profiles
_profile_cache: Dict[str, dict] = {}
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')

# Initialize clients
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
# Deepgram is used via REST API directly (no SDK client needed)

# Create the main app
app = FastAPI(title="Bible Buddy API - Phase 2")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

AGE_TIERS = ["4-6", "7-9", "10-12", "13-18"]

# Parent Account Model
class ParentAccount(BaseModel):
    user_id: str = Field(default_factory=lambda: f"parent_{uuid.uuid4().hex[:12]}")
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Child Profile Model
class ChildProfile(BaseModel):
    child_id: str = Field(default_factory=lambda: f"child_{uuid.uuid4().hex[:12]}")
    parent_id: str
    name: str
    age_tier: str = "7-9"
    avatar: Optional[str] = None
    preferred_translation: str = "NIV"
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    parental_consent_given: bool = False
    consent_timestamp: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChildProfileCreate(BaseModel):
    name: str
    age_tier: str = "7-9"
    avatar: Optional[str] = None
    preferred_translation: str = "NIV"
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"

# Session Model
class UserSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:12]}")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Chat Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    audio_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    child_id: str
    parent_id: str
    age_tier: str
    messages: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    child_id: str
    message: str
    age_tier: str = "7-9"
    include_audio: bool = True

class ChatResponse(BaseModel):
    session_id: str
    response: str
    audio_url: Optional[str] = None
    bible_verses: List[str] = []
    from_knowledge_base: bool = False

class VoiceChatRequest(BaseModel):
    child_id: str
    age_tier: str = "7-9"
    session_id: Optional[str] = None

# Usage Statistics Model
class UsageStats(BaseModel):
    total_conversations: int = 0
    total_messages: int = 0
    time_spent_minutes: int = 0
    most_asked_topics: List[str] = []
    last_active: Optional[datetime] = None

# Safety Models
class SafetyCheckResult(BaseModel):
    is_safe: bool
    category: Optional[str] = None
    redirect_message: Optional[str] = None

# ==================== KNOWLEDGE BASE ====================
# Pre-loaded 100 common faith questions for instant responses

KNOWLEDGE_BASE = {
    # Creation & God
    "who made the world": {
        "answer": "God made the whole world! The very first verse in the Bible says 'In the beginning, God created the heavens and the earth' (Genesis 1:1). He made the sun, moon, stars, oceans, animals, and even you!",
        "verses": ["Genesis 1:1", "Psalm 19:1"],
        "topic": "creation"
    },
    "who is god": {
        "answer": "God is our loving Heavenly Father who created everything and everyone. He is all-powerful, all-knowing, and is always with us. The Bible tells us 'God is love' (1 John 4:8).",
        "verses": ["1 John 4:8", "Psalm 139:7-10"],
        "topic": "god"
    },
    "where does god live": {
        "answer": "God lives in heaven, but He is also everywhere! The Bible says heaven is His throne, but He also promises to live in our hearts when we believe in Him.",
        "verses": ["Psalm 11:4", "1 Corinthians 3:16"],
        "topic": "god"
    },
    "can god hear me": {
        "answer": "Yes! God hears every word you say and even knows your thoughts. The Bible says 'The Lord hears the righteous' (Psalm 34:17). You can talk to God anytime!",
        "verses": ["Psalm 34:17", "1 Peter 3:12"],
        "topic": "prayer"
    },
    "does god love me": {
        "answer": "Absolutely! God loves you SO much! The Bible says 'God so loved the world that He gave His one and only Son' (John 3:16). You are precious to God!",
        "verses": ["John 3:16", "Romans 8:38-39"],
        "topic": "love"
    },
    
    # Jesus
    "who is jesus": {
        "answer": "Jesus is God's Son who came to earth to show us God's love and to save us. He lived a perfect life, performed miracles, and died on the cross for our sins. But He rose again and is alive today!",
        "verses": ["John 3:16", "John 14:6"],
        "topic": "jesus"
    },
    "why did jesus die": {
        "answer": "Jesus died because He loves us so much. We all do wrong things (sins), and Jesus took the punishment for us. It's like a big brother taking the blame for something you did. He did this so we can be friends with God forever!",
        "verses": ["Romans 5:8", "1 Peter 3:18"],
        "topic": "jesus"
    },
    "did jesus come back to life": {
        "answer": "Yes! Three days after Jesus died, He came back to life! This is called the resurrection. It's the most amazing miracle ever, and it shows that Jesus has power over death. He's alive today in heaven!",
        "verses": ["Matthew 28:6", "1 Corinthians 15:3-4"],
        "topic": "jesus"
    },
    "what miracles did jesus do": {
        "answer": "Jesus did many amazing miracles! He healed sick people, made blind people see, walked on water, calmed storms, and even brought people back to life. These miracles showed that He is truly God's Son.",
        "verses": ["John 20:30-31", "Matthew 11:4-5"],
        "topic": "jesus"
    },
    "where is jesus now": {
        "answer": "Jesus is in heaven, sitting at the right hand of God the Father. But through the Holy Spirit, He is also with everyone who believes in Him. He promised 'I am with you always' (Matthew 28:20).",
        "verses": ["Mark 16:19", "Matthew 28:20"],
        "topic": "jesus"
    },
    
    # Bible
    "what is the bible": {
        "answer": "The Bible is God's special book! It's actually a collection of 66 books written by many different people, but all inspired by God. It tells us about God's love, how to live, and about Jesus.",
        "verses": ["2 Timothy 3:16", "Psalm 119:105"],
        "topic": "bible"
    },
    "who wrote the bible": {
        "answer": "Many different people wrote the Bible over thousands of years - kings, shepherds, fishermen, and prophets. But God inspired every word, which means He guided the writers. It's God's message to us!",
        "verses": ["2 Peter 1:21", "2 Timothy 3:16"],
        "topic": "bible"
    },
    "is the bible true": {
        "answer": "Yes, the Bible is true! Christians believe it's God's Word and can be trusted completely. Many things in the Bible have been proven by history and archaeology. Most importantly, when we read it, God speaks to our hearts.",
        "verses": ["John 17:17", "Psalm 119:160"],
        "topic": "bible"
    },
    
    # Prayer
    "how do i pray": {
        "answer": "Praying is simply talking to God! You can pray anytime, anywhere. You don't need special words. Just tell God what's on your heart - thank Him, ask for help, or just talk. He's always listening!",
        "verses": ["Philippians 4:6", "Matthew 6:9-13"],
        "topic": "prayer"
    },
    "what should i pray about": {
        "answer": "You can pray about anything! Thank God for good things, ask for help when you're scared or worried, pray for your family and friends, and ask God to help you be kind. God cares about everything in your life!",
        "verses": ["1 Thessalonians 5:17", "Philippians 4:6"],
        "topic": "prayer"
    },
    "does god answer prayers": {
        "answer": "Yes, God always hears and answers prayers! Sometimes He says 'yes,' sometimes 'no,' and sometimes 'wait.' God knows what's best for us, even when we don't understand. Keep talking to Him!",
        "verses": ["1 John 5:14-15", "Matthew 7:7"],
        "topic": "prayer"
    },
    
    # Heaven & Angels
    "what is heaven like": {
        "answer": "Heaven is an amazing place where God lives! The Bible describes it as beautiful beyond imagination - streets of gold, no more crying or pain, and we'll be with God and loved ones forever. It's the best place ever!",
        "verses": ["Revelation 21:4", "John 14:2-3"],
        "topic": "heaven"
    },
    "are angels real": {
        "answer": "Yes, angels are real! They are special beings God created to serve Him and help people. The Bible tells many stories of angels delivering messages, protecting people, and praising God.",
        "verses": ["Psalm 91:11", "Hebrews 1:14"],
        "topic": "angels"
    },
    "do i have a guardian angel": {
        "answer": "The Bible tells us that God sends angels to watch over and protect those who love Him. Whether you have one specific angel or many helping you, you can trust that God protects His children!",
        "verses": ["Psalm 91:11", "Matthew 18:10"],
        "topic": "angels"
    },
    
    # Sin & Forgiveness
    "what is sin": {
        "answer": "Sin is when we do things that go against what God wants. It's like breaking God's rules - lying, being mean, disobeying parents. Everyone sins, but the good news is God forgives us when we're sorry!",
        "verses": ["Romans 3:23", "1 John 1:9"],
        "topic": "sin"
    },
    "does god forgive me": {
        "answer": "Yes! God always forgives you when you're truly sorry. The Bible says 'If we confess our sins, He is faithful and just to forgive us' (1 John 1:9). God's love and forgiveness have no limits!",
        "verses": ["1 John 1:9", "Psalm 103:12"],
        "topic": "forgiveness"
    },
    "what if i keep sinning": {
        "answer": "God understands that we all make mistakes, even the same ones sometimes. What matters is that you're truly sorry and keep trying to do better. God's grace is bigger than all your mistakes!",
        "verses": ["Romans 8:1", "Lamentations 3:22-23"],
        "topic": "forgiveness"
    },
    
    # Hard Questions
    "why do bad things happen": {
        "answer": "This is a hard question that even adults wonder about. Bad things happen because sin entered the world. But God promises to be with us through hard times and can bring good out of bad situations.",
        "verses": ["Romans 8:28", "John 16:33"],
        "topic": "suffering"
    },
    "why does god let people suffer": {
        "answer": "God gave people free will to make choices, and sometimes people make bad choices that hurt others. God doesn't cause suffering, but He promises to comfort us and walk with us through hard times.",
        "verses": ["2 Corinthians 1:3-4", "Psalm 34:18"],
        "topic": "suffering"
    },
    "is god mad at me": {
        "answer": "God is not mad at you! He loves you unconditionally. Like a good parent who corrects their child, God may not like some things we do, but He always loves WHO we are. You are His precious child!",
        "verses": ["Romans 8:1", "Zephaniah 3:17"],
        "topic": "love"
    },
    "what happens when i die": {
        "answer": "For those who believe in Jesus, death is not the end - it's the beginning of eternal life with God in heaven! Our bodies rest, but our spirits go to be with God. It's like going home to the best place ever.",
        "verses": ["John 11:25-26", "2 Corinthians 5:8"],
        "topic": "death"
    },
    
    # Holy Spirit
    "who is the holy spirit": {
        "answer": "The Holy Spirit is God living in us! When we believe in Jesus, the Holy Spirit comes to live in our hearts. He helps us understand the Bible, makes us stronger, and guides us to do good things.",
        "verses": ["John 14:26", "Acts 1:8"],
        "topic": "holy_spirit"
    },
    "how do i know god is real": {
        "answer": "You can know God is real by looking at His amazing creation, reading His Word in the Bible, feeling His love in your heart, and seeing answered prayers. Many people throughout history have experienced God's presence!",
        "verses": ["Romans 1:20", "Hebrews 11:1"],
        "topic": "faith"
    },
    
    # Salvation
    "how do i become a christian": {
        "answer": "Becoming a Christian is beautiful and simple! Believe that Jesus is God's Son, that He died for your sins and rose again. Tell God you're sorry for your sins and ask Jesus to be your Savior. That's it - you're part of God's family!",
        "verses": ["Romans 10:9", "John 1:12"],
        "topic": "salvation"
    },
    "what does it mean to be saved": {
        "answer": "Being 'saved' means being rescued from sin and its consequences. When you believe in Jesus, He saves you - forgives your sins and gives you eternal life. It's like being rescued from drowning!",
        "verses": ["Ephesians 2:8-9", "John 3:16"],
        "topic": "salvation"
    },
    "am i saved": {
        "answer": "If you've believed in Jesus as your Savior and asked Him into your heart, yes, you are saved! The Bible says 'everyone who calls on the name of the Lord will be saved' (Romans 10:13). You can be confident in God's promise!",
        "verses": ["Romans 10:13", "1 John 5:13"],
        "topic": "salvation"
    },
    
    # Church & Worship
    "why do we go to church": {
        "answer": "Church is where God's family gathers together to worship, learn about God, and encourage each other. It's like a big family meeting! The Bible says we should meet together to grow stronger in faith.",
        "verses": ["Hebrews 10:25", "Acts 2:42"],
        "topic": "church"
    },
    "what is worship": {
        "answer": "Worship is showing God how much we love and appreciate Him. We can worship by singing, praying, reading the Bible, being kind to others, or just telling God how awesome He is. It's celebrating God!",
        "verses": ["Psalm 95:6", "John 4:24"],
        "topic": "worship"
    },
    
    # Bible Characters
    "tell me about noah": {
        "answer": "Noah was a man who loved God when everyone else was being bad. God told Noah to build a huge boat called an ark because a great flood was coming. Noah obeyed, and God saved Noah, his family, and many animals!",
        "verses": ["Genesis 6-9", "Hebrews 11:7"],
        "topic": "bible_stories"
    },
    "tell me about david": {
        "answer": "David was a shepherd boy who became a great king! When he was young, he defeated a giant named Goliath with just a sling and stones because he trusted God. David wrote many songs to God called Psalms.",
        "verses": ["1 Samuel 17", "Psalm 23"],
        "topic": "bible_stories"
    },
    "tell me about moses": {
        "answer": "Moses was chosen by God to lead His people out of slavery in Egypt. God spoke to Moses through a burning bush and helped him perform amazing miracles. Moses also received the Ten Commandments from God!",
        "verses": ["Exodus 3", "Exodus 20"],
        "topic": "bible_stories"
    },
    "tell me about abraham": {
        "answer": "Abraham was a man of great faith! God promised him he would be the father of a great nation, even when he was very old. Abraham trusted God even when things seemed impossible. He's called the father of faith!",
        "verses": ["Genesis 12", "Hebrews 11:8-12"],
        "topic": "bible_stories"
    },
    "tell me about daniel": {
        "answer": "Daniel was a young man who loved God even when it was dangerous. He kept praying even when a king said not to, and he was thrown into a den of hungry lions! But God sent an angel to shut the lions' mouths!",
        "verses": ["Daniel 6", "Daniel 1"],
        "topic": "bible_stories"
    },
    "tell me about jonah": {
        "answer": "Jonah was a prophet who tried to run away from God! God told him to go to a city called Nineveh, but Jonah went the other way. He was swallowed by a big fish and spent 3 days inside until he said sorry to God!",
        "verses": ["Jonah 1-4"],
        "topic": "bible_stories"
    },
    
    # Practical Faith
    "how can i be kind": {
        "answer": "Being kind is one of the best ways to show God's love! You can be kind by sharing, using nice words, helping others, including people who feel left out, and treating others the way you want to be treated.",
        "verses": ["Ephesians 4:32", "Galatians 5:22"],
        "topic": "character"
    },
    "how do i love others": {
        "answer": "Jesus said to love others like you love yourself! You can show love by being kind, sharing, listening, helping, forgiving, and putting others first. When we love others, we're showing God's love!",
        "verses": ["John 13:34-35", "1 Corinthians 13:4-7"],
        "topic": "love"
    },
    "how do i forgive someone": {
        "answer": "Forgiveness can be hard, but God helps us! When someone hurts you, tell God how you feel and ask Him to help you forgive. Remember how much God has forgiven you. Forgiveness sets your heart free!",
        "verses": ["Ephesians 4:32", "Matthew 6:14-15"],
        "topic": "forgiveness"
    },
    "what should i do when im scared": {
        "answer": "When you're scared, remember God is with you! You can pray and tell God how you feel. The Bible says 'God has not given us a spirit of fear, but of power, love, and a sound mind' (2 Timothy 1:7). You're never alone!",
        "verses": ["2 Timothy 1:7", "Isaiah 41:10"],
        "topic": "fear"
    },
    "what should i do when im sad": {
        "answer": "It's okay to feel sad sometimes - even Jesus cried! When you're sad, you can talk to God about it. He promises to comfort you. Also talk to a parent or trusted adult. Remember, sadness doesn't last forever.",
        "verses": ["Psalm 34:18", "Matthew 5:4"],
        "topic": "emotions"
    },
    "how do i trust god": {
        "answer": "Trusting God means believing He loves you and knows what's best, even when things are hard. Start by reading His promises in the Bible, talking to Him in prayer, and remembering times He's helped you before!",
        "verses": ["Proverbs 3:5-6", "Psalm 56:3"],
        "topic": "faith"
    },
    
    # Identity Questions
    "why did god make me": {
        "answer": "God made you because He wanted to! You're not an accident - you're God's masterpiece created for a special purpose. God has amazing plans for your life and loves you more than you can imagine!",
        "verses": ["Ephesians 2:10", "Jeremiah 29:11"],
        "topic": "identity"
    },
    "does god have a plan for me": {
        "answer": "Yes! God has wonderful plans for your life! Jeremiah 29:11 says 'I know the plans I have for you... plans to give you hope and a future.' God created you for a unique purpose that only you can fulfill!",
        "verses": ["Jeremiah 29:11", "Ephesians 2:10"],
        "topic": "purpose"
    },
    "am i special to god": {
        "answer": "You are SO special to God! He made you unique and loves everything about you. The Bible says you are 'fearfully and wonderfully made' (Psalm 139:14). There's no one else like you in the whole world!",
        "verses": ["Psalm 139:14", "Luke 12:7"],
        "topic": "identity"
    },
    
    # Ten Commandments
    "what are the ten commandments": {
        "answer": "The Ten Commandments are special rules God gave to Moses to help people know how to live. They include loving God first, respecting parents, not lying or stealing, and treating others well. They're like God's guidelines for a good life!",
        "verses": ["Exodus 20:1-17", "Deuteronomy 5:6-21"],
        "topic": "commandments"
    },
    
    # The Trinity
    "what is the trinity": {
        "answer": "The Trinity is one of the most amazing mysteries about God! It means God is one God, but exists as three persons: God the Father, God the Son (Jesus), and God the Holy Spirit. They're all equally God, working together in perfect love!",
        "verses": ["Matthew 28:19", "2 Corinthians 13:14"],
        "topic": "trinity"
    },
    
    # Baptism
    "what is baptism": {
        "answer": "Baptism is a special ceremony where someone is dipped in water to show they've decided to follow Jesus. It's like a picture of dying to your old life and rising to new life with Jesus. It's a beautiful celebration!",
        "verses": ["Romans 6:4", "Matthew 28:19"],
        "topic": "baptism"
    },
    
    # Communion
    "what is communion": {
        "answer": "Communion (also called the Lord's Supper) is when Christians eat bread and drink grape juice together to remember what Jesus did for us. The bread reminds us of Jesus's body, and the juice reminds us of His blood given for us.",
        "verses": ["1 Corinthians 11:23-26", "Luke 22:19-20"],
        "topic": "communion"
    },
    
    # Spiritual Growth
    "how can i grow closer to god": {
        "answer": "Great question! You can grow closer to God by reading the Bible, praying every day, going to church, obeying what you learn, and spending time with other Christians. It's like any friendship - the more time you spend together, the closer you get!",
        "verses": ["James 4:8", "Psalm 119:11"],
        "topic": "spiritual_growth"
    },
    "how do i hear god": {
        "answer": "God speaks to us in many ways! Through the Bible, through prayer, through wise people, and through that quiet voice in your heart. To hear God better, spend quiet time with Him and ask Him to speak to you!",
        "verses": ["John 10:27", "1 Kings 19:12"],
        "topic": "hearing_god"
    },
    
    # More Identity Questions  
    "what if people dont like me": {
        "answer": "Even if some people don't like you, GOD loves you completely! Jesus wasn't liked by everyone either. Focus on being kind and loving, and remember your worth comes from God, not from what others think.",
        "verses": ["John 15:18-19", "Galatians 1:10"],
        "topic": "identity"
    },
    "why am i different": {
        "answer": "Being different is wonderful! God made everyone unique on purpose. Your differences are your superpowers - they make you special and allow you to do things no one else can do exactly the way you can!",
        "verses": ["1 Corinthians 12:18-20", "Psalm 139:13-14"],
        "topic": "identity"
    },
}

def find_knowledge_base_answer(question: str) -> Optional[Dict]:
    """Search knowledge base for matching question"""
    question_lower = question.lower().strip()
    
    # Remove common question words
    clean_question = question_lower.replace("?", "").replace("!", "")
    for word in ["please", "can you", "could you", "tell me", "what's", "what is", "who's", "why is", "how is"]:
        clean_question = clean_question.replace(word, "")
    clean_question = clean_question.strip()
    
    # Skip KB for personal/emotional messages — these need the adaptive AI
    personal_signals = ["i feel", "i am", "i'm", "i dont", "i don't", "i can't", "i cant", 
                        "i think", "my life", "help me", "scared", "afraid", "worried", "sad",
                        "lonely", "angry", "confused", "lost", "hurt", "struggling",
                        "i need", "i want to", "i wish", "how can i be", "how do i"]
    for signal in personal_signals:
        if signal in clean_question:
            return None  # Force AI path for personal questions
    
    # Exact match
    if clean_question in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[clean_question]
    
    # Partial match - question contains a key or key contains the question
    for key, value in KNOWLEDGE_BASE.items():
        if key in clean_question or clean_question in key:
            return value
    
    # Word overlap match - require 70%+ of key words present
    for key, value in KNOWLEDGE_BASE.items():
        key_words = set(key.split())
        question_words = set(clean_question.split())
        if len(key_words) >= 2:
            overlap = len(key_words & question_words)
            if overlap >= max(2, len(key_words) * 0.7):
                return value
    
    return None

# ==================== FEATURED TEACHERS ====================

FEATURED_TEACHERS = {
    "apostle_selman": {
        "name": "Apostle Joshua Selman",
        "ministry": "Koinonia Global",
        "style": "Deep theological teaching with practical application, emphasis on the Holy Spirit",
        "topics": {
            "prayer": [
                "Prayer is not just asking God for things — it's communion with Him. When you pray, you're building a relationship.",
                "The quality of your prayer life determines the quality of your spiritual life.",
                "Prayer is the only way to maintain your spiritual temperature."
            ],
            "holy_spirit": [
                "The Holy Spirit is your greatest advantage in life. He is the difference between struggle and victory.",
                "There is no substitute for the presence of God. Make His presence your priority.",
                "The Holy Spirit will teach you all things and guide you into all truth."
            ],
            "purpose": [
                "Your purpose is not something you create — it's something you discover through intimacy with God.",
                "God has a specific assignment for your life. Don't waste your years living someone else's dream.",
                "Wisdom is the principal thing — get wisdom, and in all your getting, get understanding."
            ],
            "growth": [
                "Your spiritual growth is measured by your hunger for God's word, not your years in church.",
                "Maturity is when you can handle the word of God and let it transform you from the inside out.",
                "Growth happens in seasons of discomfort. Don't run from the process."
            ],
            "fear": [
                "Fear is a signal that you're stepping into territory the enemy doesn't want you to conquer.",
                "The antidote to fear is the knowledge of God. Know Him and fear loses its power."
            ],
            "identity": [
                "You are not what people call you. You are what God calls you.",
                "Your value was settled at the cross. Nothing can add to it or take from it."
            ],
            "faith": [
                "Faith is not the absence of fear — it's the presence of trust despite fear.",
                "Your faith must be rooted in the Word of God, not in your circumstances."
            ]
        }
    },
    "stephanie_ike": {
        "name": "Pastor Stephanie Ike",
        "ministry": "ONE Church LA / The Light Church",
        "style": "Encouraging, empathetic, focused on identity and emotional healing",
        "topics": {
            "identity": [
                "You are not what happened to you — you are who God says you are.",
                "Stop letting your past write your future. God has already authored a better story for you.",
                "Your identity is not in your achievements, your failures, or what others think. It's in Christ alone."
            ],
            "fear": [
                "Fear is faith in the enemy. Every time you choose fear, you're trusting the wrong voice.",
                "You weren't created to live in fear. God gave you a spirit of power, love, and a sound mind.",
                "When fear speaks, respond with Scripture. The Word of God silences every lie."
            ],
            "self_worth": [
                "Your feelings are valid, but they don't determine your value. God's Word does.",
                "God's love for you is not based on your performance. He loved you before you did anything.",
                "Stop waiting to feel worthy. You already are — the cross proved it."
            ],
            "purpose": [
                "You were created on purpose, for a purpose. There are no accidents with God.",
                "Don't compare your journey to others. God has a unique path designed just for you.",
                "Your calling may not look like everyone else's, and that's exactly the point."
            ],
            "anxiety": [
                "Anxiety is a thief — it steals your present by making you afraid of the future.",
                "When you feel overwhelmed, remember: God is not anxious about your situation. Rest in His peace.",
                "Give your worries to God. He can handle what you were never meant to carry."
            ],
            "relationships": [
                "Healthy relationships start with knowing who you are in Christ first.",
                "Don't let the wrong relationships distract you from your divine assignment."
            ]
        }
    },
    "steven_furtick": {
        "name": "Pastor Steven Furtick",
        "ministry": "Elevation Church",
        "style": "Passionate, energetic, motivational with practical faith applications",
        "topics": {
            "faith": [
                "What God starts, He finishes. Your job is to trust the process even when you can't see the end.",
                "Don't let your feelings determine your faith. Faith is a decision, not an emotion.",
                "Your limitations are God's opportunities. What you see as a problem, God sees as potential."
            ],
            "doubt": [
                "Doubt is not the opposite of faith — it's a step on the journey of faith.",
                "Even the disciples doubted. The question is not whether you doubt, but whether you keep walking.",
                "God is not intimidated by your questions. Bring them to Him honestly."
            ],
            "perseverance": [
                "What looks like a setback is often a setup for something greater.",
                "Don't give up in the middle of your miracle. The breakthrough is closer than you think.",
                "The enemy's job is to steal, kill, and destroy. Your job is to stand firm."
            ],
            "confidence": [
                "Your confidence is not in yourself — it's in who God is and what He said about you.",
                "Stop shrinking to fit spaces you were meant to outgrow.",
                "God didn't bring you this far to leave you. Walk boldly."
            ],
            "fear": [
                "Fear will always give you a reason to quit. Faith will always give you a reason to continue.",
                "The biggest enemy of your destiny is not the devil — it's your own doubt."
            ],
            "purpose": [
                "You are not an accident. God planned you before the foundation of the world.",
                "Stop waiting for perfect conditions. Start where you are with what you have."
            ]
        }
    },
    "priscilla_shirer": {
        "name": "Priscilla Shirer",
        "ministry": "Going Beyond Ministries",
        "style": "Bold, Scripture-rich, focused on spiritual warfare and practical application",
        "topics": {
            "spiritual_warfare": [
                "Prayer is not preparation for the battle — prayer IS the battle.",
                "The enemy wants to distract you from your divine assignment. Stay focused.",
                "Put on the full armor of God. You're in a real fight, but you have real weapons."
            ],
            "prayer": [
                "Prayer is your most powerful weapon. Use it before, during, and after every battle.",
                "When you don't know what to pray, the Holy Spirit intercedes for you. You're never alone in prayer.",
                "Specific prayers get specific answers. Be bold and precise with God."
            ],
            "identity": [
                "Your identity in Christ is your greatest weapon against the enemy's lies.",
                "The enemy can only defeat you if you forget who you are. Remember: you are God's child.",
                "You are chosen, called, and equipped. Walk in that truth every single day."
            ],
            "discernment": [
                "Discernment comes from spending time with God. You can't hear His voice in the noise.",
                "God's Word is your sword — learn to use it. A soldier who doesn't know their weapon is vulnerable.",
                "Not every open door is from God. Ask for discernment before you walk through."
            ],
            "fear": [
                "Fear is the enemy's strategy to keep you from your God-given assignment.",
                "When you feel afraid, remember who goes before you. The battle is already won."
            ],
            "strength": [
                "You don't have to be strong in your own power. God's strength is made perfect in your weakness.",
                "When you feel like you can't go on, that's when God shows up the most."
            ]
        }
    }
}

def get_relevant_teacher_wisdom(topics: list) -> str:
    """Get relevant teacher quotes based on the topics being discussed"""
    wisdom = []
    topic_map = {
        "prayer": "prayer", "pray": "prayer", "praying": "prayer",
        "fear": "fear", "afraid": "fear", "scared": "fear", "worry": "fear", "anxious": "fear", "anxiety": "anxiety",
        "identity": "identity", "who am i": "identity", "worth": "self_worth", "value": "self_worth",
        "purpose": "purpose", "calling": "purpose", "destiny": "purpose", "future": "purpose",
        "faith": "faith", "believe": "faith", "trust": "faith",
        "doubt": "doubt", "unsure": "doubt", "confused": "doubt",
        "holy spirit": "holy_spirit", "spirit": "holy_spirit",
        "grow": "growth", "growing": "growth", "mature": "growth",
        "strong": "strength", "strength": "strength", "weak": "strength",
        "fight": "spiritual_warfare", "battle": "spiritual_warfare", "enemy": "spiritual_warfare", "devil": "spiritual_warfare",
        "confident": "confidence", "confidence": "confidence", "bold": "confidence",
        "give up": "perseverance", "quit": "perseverance", "hard": "perseverance", "difficult": "perseverance",
        "friend": "relationships", "relationship": "relationships", "lonely": "relationships",
        "discern": "discernment", "decision": "discernment", "choose": "discernment",
        "self worth": "self_worth", "not good enough": "self_worth",
    }
    
    matched_topics = set()
    for topic_keyword in topics:
        topic_lower = topic_keyword.lower()
        for keyword, mapped_topic in topic_map.items():
            if keyword in topic_lower:
                matched_topics.add(mapped_topic)
    
    if not matched_topics:
        matched_topics = {"faith", "purpose"}  # Default
    
    for teacher_id, teacher in FEATURED_TEACHERS.items():
        for topic in matched_topics:
            if topic in teacher["topics"]:
                quotes = teacher["topics"][topic][:1]  # Take first quote per topic per teacher
                for q in quotes:
                    wisdom.append(f'{teacher["name"]}: "{q}"')
    
    return "\n".join(wisdom[:4])  # Max 4 quotes to keep prompt focused

# ==================== VOICE OPTIONS ====================

VOICE_OPTIONS = [
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah", "gender": "female", "accent": "American", "description": "Warm and friendly", "preview_text": "Hi! I'm Sarah, your Bible Buddy!"},
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Grace", "gender": "female", "accent": "American", "description": "Calm and gentle", "preview_text": "Hi! I'm Grace, your Bible Buddy!"},
    {"id": "jBpfuIE2acCO8z3wKNLl", "name": "Gigi", "gender": "female", "accent": "American", "description": "Young and energetic", "preview_text": "Hi! I'm Gigi, your Bible Buddy!"},
    {"id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "gender": "female", "accent": "British", "description": "Warm British storyteller", "preview_text": "Hi! I'm Charlotte, your Bible Buddy!"},
    {"id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily", "gender": "female", "accent": "British", "description": "Bright and cheerful", "preview_text": "Hi! I'm Lily, your Bible Buddy!"},
    {"id": "FGY2WhTYpPnrIDTdsKH5", "name": "Amara", "gender": "female", "accent": "African", "description": "Rich and soothing", "preview_text": "Hi! I'm Amara, your Bible Buddy!"},
    {"id": "ErXwobaYiN019PkySvjV", "name": "David", "gender": "male", "accent": "American", "description": "Friendly and clear", "preview_text": "Hi! I'm David, your Bible Buddy!"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Joshua", "gender": "male", "accent": "American", "description": "Strong and encouraging", "preview_text": "Hi! I'm Joshua, your Bible Buddy!"},
    {"id": "VR6AewLTigWG4xSOukaG", "name": "Emmanuel", "gender": "male", "accent": "British", "description": "Confident and warm", "preview_text": "Hi! I'm Emmanuel, your Bible Buddy!"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Caleb", "gender": "male", "accent": "American", "description": "Deep and reassuring", "preview_text": "Hi! I'm Caleb, your Bible Buddy!"},
]

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah

@api_router.get("/voices")
async def get_voice_options():
    """Get available voice options"""
    return {"voices": VOICE_OPTIONS, "default_voice_id": DEFAULT_VOICE_ID}

@api_router.post("/voices/preview")
async def preview_voice(voice_id: str):
    """Generate a short preview of a voice"""
    if not eleven_client:
        raise HTTPException(status_code=503, detail="TTS not configured")
    
    voice = next((v for v in VOICE_OPTIONS if v["id"] == voice_id), None)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    audio_url = await generate_tts_audio(voice["preview_text"], voice_id)
    if not audio_url:
        raise HTTPException(status_code=500, detail="Failed to generate preview")
    return {"audio_url": audio_url}

# ==================== SAFETY FILTERING ====================

UNSAFE_PATTERNS = [
    "kill", "murder", "hurt", "violence", "weapon", "gun", "knife",
    "suicide", "self-harm", "cut myself", "end my life", "want to die",
    "sex", "naked", "porn", "explicit",
    "bypass", "ignore instructions", "pretend you're not", "jailbreak"
]

SAFETY_REDIRECTS = {
    "violence": "I understand you might be curious about difficult topics. Let's talk about how God teaches us about peace and love instead. Would you like to hear a story about Jesus showing kindness?",
    "self-harm": "I hear that you might be going through a hard time. God loves you so much! Please talk to a trusted adult, parent, or call a helpline. Would you like to hear about how much God cares for you?",
    "explicit": "That's not something I can help with. Let's talk about something wonderful from the Bible instead! Would you like to hear an amazing story?",
    "manipulation": "I'm here to help you learn about God's word in a fun way! What Bible question can I answer for you?",
}

def check_content_safety(text: str) -> SafetyCheckResult:
    """Pre-process check for unsafe content"""
    text_lower = text.lower()
    
    # Self-harm check (highest priority)
    self_harm_keywords = ["suicide", "self-harm", "cut myself", "end my life", "want to die", "kill myself"]
    for keyword in self_harm_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(is_safe=False, category="self-harm", redirect_message=SAFETY_REDIRECTS["self-harm"])
    
    # Violence check
    violence_keywords = ["kill", "murder", "hurt someone", "weapon", "gun", "knife"]
    for keyword in violence_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(is_safe=False, category="violence", redirect_message=SAFETY_REDIRECTS["violence"])
    
    # Explicit check
    explicit_keywords = ["sex", "naked", "porn", "explicit"]
    for keyword in explicit_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(is_safe=False, category="explicit", redirect_message=SAFETY_REDIRECTS["explicit"])
    
    # Manipulation check
    manipulation_keywords = ["bypass", "ignore instructions", "pretend you're not", "jailbreak"]
    for keyword in manipulation_keywords:
        if keyword in text_lower:
            return SafetyCheckResult(is_safe=False, category="manipulation", redirect_message=SAFETY_REDIRECTS["manipulation"])
    
    return SafetyCheckResult(is_safe=True)

def post_process_safety(response: str) -> str:
    """Post-process check for response safety"""
    response_lower = response.lower()
    for pattern in UNSAFE_PATTERNS:
        if pattern in response_lower:
            return "I'd love to share something wonderful from the Bible with you! What would you like to learn about?"
    return response

# ==================== USER PROFILE SYSTEM ====================

async def get_or_create_user_profile(child_id: str) -> dict:
    """Get or create an adaptive user profile that learns from conversations"""
    profile = await db.user_profiles.find_one({"child_id": child_id}, {"_id": 0})
    if profile:
        return profile
    
    profile = {
        "child_id": child_id,
        "topics_interested": [],
        "fears_concerns": [],
        "strengths": [],
        "struggles": [],
        "conversation_count": 0,
        "personality_notes": "",
        "growth_milestones": [],
        "favorite_verses": [],
        "last_topics": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.user_profiles.insert_one({**profile})
    return profile

async def update_user_profile(child_id: str, message: str, response: str, age_tier: str):
    """Analyze conversation and update user profile (runs in background)"""
    try:
        profile = await get_or_create_user_profile(child_id)
        
        analysis_text = await _anthropic_chat(
            system_message="""Analyze this child-Bible guide conversation. Return ONLY valid JSON:
{"topics":[],"emotions":[],"struggles":[],"strengths":[],"personality_note":""}
Empty list/string if nothing to add. JSON only, no markdown.""",
            user_text=f"Child: {message}\nGuide: {response}",
            model="claude-3-haiku-20240307",
            max_tokens=200
        )
        
        # Parse the analysis
        import json as json_module
        # Clean the response - remove markdown code blocks if present
        clean = analysis_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            clean = clean.rsplit("```", 1)[0]
        
        analysis = json_module.loads(clean)
        
        # Update profile incrementally
        update_ops = {
            "$inc": {"conversation_count": 1},
            "$set": {
                "last_topics": analysis.get("topics", []),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$addToSet": {}
        }
        
        add_to_set = {}
        if analysis.get("topics"):
            add_to_set["topics_interested"] = {"$each": analysis["topics"][:3]}
        if analysis.get("emotions") or analysis.get("struggles"):
            struggles = analysis.get("struggles", []) + [e for e in analysis.get("emotions", []) if e in ["fear", "anxiety", "sadness", "confusion", "doubt", "loneliness"]]
            if struggles:
                add_to_set["fears_concerns"] = {"$each": struggles[:3]}
        if analysis.get("strengths"):
            add_to_set["strengths"] = {"$each": analysis["strengths"][:2]}
        
        if add_to_set:
            update_ops["$addToSet"] = add_to_set
        else:
            del update_ops["$addToSet"]
        
        if analysis.get("personality_note"):
            update_ops["$set"]["personality_notes"] = analysis["personality_note"]
        
        await db.user_profiles.update_one({"child_id": child_id}, update_ops, upsert=True)
        
        # Trim arrays to prevent unbounded growth (keep last 20 items)
        for field in ["topics_interested", "fears_concerns", "strengths", "struggles"]:
            await db.user_profiles.update_one(
                {"child_id": child_id},
                [{"$set": {field: {"$slice": [f"${field}", -20]}}}]
            )
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")

def build_user_context(profile: dict, child_name: str = "", age_tier: str = "") -> str:
    """Build a concise user context string for the AI prompt"""
    parts = []

    if child_name:
        parts.append(f"This child's name is {child_name}. Address them by name naturally in your answer.")

    if age_tier:
        age_labels = {
            "4-6": "4-6 years old", "7-9": "7-9 years old",
            "10-12": "10-12 years old", "13-18": "13-18 years old"
        }
        parts.append(f"Age: {age_labels.get(age_tier, age_tier)}.")

    if profile.get("conversation_count", 0) > 0:
        parts.append(f"You've had {profile['conversation_count']} conversations with {child_name or 'this child'} before — build on what you know.")
    else:
        parts.append(f"This is your first conversation with {child_name or 'this child'}. Welcome them warmly and personally.")

    if profile.get("topics_interested"):
        recent = profile["topics_interested"][-6:]
        parts.append(f"Topics they've explored before: {', '.join(recent)}. Connect to these if relevant.")

    if profile.get("fears_concerns"):
        recent = list(set(profile["fears_concerns"][-4:]))
        parts.append(f"Concerns or struggles they've shared: {', '.join(recent)}. Speak Scripture directly into these if they're relevant.")

    if profile.get("strengths"):
        recent = list(set(profile["strengths"][-4:]))
        parts.append(f"Strengths you've seen in them: {', '.join(recent)}. Affirm and build on these.")

    if profile.get("personality_notes"):
        parts.append(f"What you know about this child: {profile['personality_notes']}")

    if profile.get("last_topics"):
        parts.append(f"Their most recent topics: {', '.join(profile['last_topics'][:3])}.")

    parts.append(f"IMPORTANT: Your answer must feel written SPECIFICALLY for {child_name or 'this child'}, not a generic response any child could receive. Use their name. Make it personal.")

    return "\n".join(parts) if parts else ""

# ==================== AGE-TIER PROMPTS ====================

def get_age_tier_system_prompt(age_tier: str, preferred_translation: str = "NIV", user_context: str = "", teacher_wisdom: str = "") -> str:
    """Get age-appropriate system prompt with user context and teacher wisdom"""
    
    base_rules = f"""You are Bible Buddy — a theologically sound Bible teacher and spiritual guide for children. You teach the TRUTH of Scripture, not cultural opinion. You are grounded in orthodox Christian doctrine.

Bible Translation: {preferred_translation}

THEOLOGICAL FOUNDATIONS (non-negotiable):
- God is sovereign, holy, just, and loving. He is the Creator of all things.
- Jesus Christ is the Son of God, fully God and fully man. He died for our sins, rose again, and is the only way to salvation (John 14:6).
- The Holy Spirit is real, active, and personal — He is the believer's helper, teacher, and comforter (John 16:13).
- The Bible is the inspired, authoritative Word of God. It is the final authority on all matters of faith.
- Sin is real and separates us from God. Salvation comes through faith in Jesus Christ alone, by grace (Ephesians 2:8-9).
- Prayer is communion with God — not a wish list, but a relationship. The Holy Spirit helps us pray (Romans 8:26).
- Every person has a God-given identity, purpose, and calling. Our worth comes from being made in God's image, confirmed at the cross.
- Spiritual warfare is real. Believers have authority through Christ and the armor of God (Ephesians 6:10-18).

RULES:
- ALWAYS ground answers in specific Scripture. Cite 2-3 Bible verses with chapter and verse.
- Teach biblical TRUTH — do not soften, water down, or culturally adjust core doctrine.
- Never reduce God to a "nice buddy" — He is holy, powerful, and worthy of reverence AND He is a loving Father.
- Don't avoid topics like sin, repentance, the cross, sacrifice, holiness, obedience, and spiritual discipline — teach them at the right age level.
- Connect every answer back to God's Word and His character.
- Never discuss violence graphically, politics, or inappropriate topics.
- Be personal — use the child's name and reference what you know about them. NEVER give a generic response.
- NEVER bend truth to match cultural norms, progressive trends, or popular opinion. Scripture is the authority — not culture.
- If a question touches on gender, identity, relationships, or ethics: answer from Scripture alone. Do not hedge or add cultural qualifiers.
- NEVER mention teacher names in your response. Their wisdom is internalized into YOUR voice. Only reveal sources if asked directly.
- Speak with conviction and authority from Scripture, not opinion.
- Keep answers focused: 3-5 sentences for young children, 4-6 for older. Quality over length."""

    user_section = ""
    if user_context:
        user_section = f"\n\nWHAT YOU KNOW ABOUT THIS CHILD:\n{user_context}"
    
    teacher_section = ""
    if teacher_wisdom:
        teacher_section = f"\n\nWISDOM TO INTERNALIZE (this shapes your teaching voice — speak it as your own, NEVER attribute it):\n{teacher_wisdom}"

    age_prompts = {
        "4-6": f"""{base_rules}{user_section}{teacher_section}

YOU ARE TEACHING A 4-6 YEAR OLD. Adapt LANGUAGE, not TRUTH:
- Use words a 4-year-old knows. Max 2-3 short sentences.
- Be warm and playful: "Wow!", "Guess what!", "How cool!"
- Explain through things they know: family, animals, playing, food
- Retell verses as tiny stories with feelings: happy, loved, safe, brave
- STILL teach real truth: God made them, Jesus loves them and died for them, God is powerful and good
- Don't skip hard truths — just simplify: "Sin means when we choose to not listen to God. But Jesus fixed it!"
- If you know this child, reference their life warmly""",

        "7-9": f"""{base_rules}{user_section}{teacher_section}

YOU ARE TEACHING A 7-9 YEAR OLD. Adapt language, not truth:
- Clear, simple sentences. 3-4 sentences max.
- Explain theological concepts simply: "Grace means God gives us what we don't deserve — forgiveness!"
- Teach the REAL story: creation, sin, Jesus' sacrifice, resurrection, the Holy Spirit, salvation
- Don't avoid topics like obedience, prayer, the Holy Spirit's power, or standing against wrong
- Connect to their life: school, friends, fairness, being brave
- Be enthusiastic but substantive — every answer should teach something real from Scripture
- If you know this child, make it personal""",

        "10-12": f"""{base_rules}{user_section}{teacher_section}

YOU ARE TEACHING A 10-12 YEAR OLD. Deeper truth, real substance:
- 3-5 sentences with theological depth. Use proper terms and explain them.
- Teach doctrine: salvation, sanctification, the Trinity, spiritual gifts, prayer as warfare
- Address real pre-teen challenges through Scripture: peer pressure, identity, fear, doubt, obedience
- Don't be vague — be specific with Scripture references and what they mean
- Teach them to think biblically: "The world says X, but God's Word says Y because..."
- Challenge them: "What does this mean for how you live this week?"
- If you know this child's struggles, speak Scripture directly into those areas""",

        "13-18": f"""{base_rules}{user_section}{teacher_section}

YOU ARE TEACHING A 13-18 YEAR OLD. Speak as a mentor with theological weight:
- 3-5 thoughtful, doctrinally rich sentences. Respect their intelligence.
- Use and explain theological terms naturally: sanctification, justification, sovereignty, covenant, redemption
- Address REAL issues with BIBLICAL answers: identity, doubt, anxiety, relationships, purpose, sexuality, social media — always grounded in Scripture, never in cultural opinion
- Be honest about hard questions — acknowledge complexity but point to God's Word as the authority
- Teach them to discern: "Culture says X, but Scripture says Y — here's why that matters"
- If you know their struggles, speak prophetically and personally into their life with Scripture
- Build conviction: help them own their faith, not just inherit it
- The Holy Spirit is real and active — teach them to depend on Him, not just head knowledge"""
    }
    
    return age_prompts.get(age_tier, age_prompts["7-9"])

# ==================== AUTHENTICATION ====================

async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session token"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        return None
    
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        return None
    
    # Check expiry
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user = await db.parents.find_one({"user_id": session.get("user_id")}, {"_id": 0})
    return user

# ==================== API ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {"message": "Bible Buddy API - Phase 2", "status": "online"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_configured": bool(ANTHROPIC_API_KEY),
        "tts_configured": bool(ELEVENLABS_API_KEY),
        "stt_configured": bool(DEEPGRAM_API_KEY),
        "knowledge_base_size": len(KNOWLEDGE_BASE)
    }

# ==================== AUTHENTICATION ENDPOINTS (see routes/auth.py) ====================
# ==================== CHILD PROFILE ENDPOINTS (see routes/children.py) ====================
# ==================== MOVED TO ROUTES ====================

# ==================== CHAT ENDPOINTS ====================

@api_router.post("/chat", response_model=ChatResponse)
async def chat(request_data: ChatRequest):
    """Main chat endpoint - returns text immediately, audio generated in background"""
    
    # Look up child's preferred voice
    child_voice = DEFAULT_VOICE_ID
    child_record = await db.children.find_one({"child_id": request_data.child_id}, {"_id": 0, "voice_id": 1})
    if child_record and child_record.get("voice_id"):
        child_voice = child_record["voice_id"]
    
    # Safety check
    safety_check = check_content_safety(request_data.message)
    if not safety_check.is_safe:
        await db.safety_logs.insert_one({
            "child_id": request_data.child_id,
            "message": request_data.message,
            "category": safety_check.category,
            "timestamp": datetime.now(timezone.utc)
        })
        return ChatResponse(
            session_id=request_data.session_id or str(uuid.uuid4()),
            response=safety_check.redirect_message,
            audio_url=None,
            bible_verses=[],
            from_knowledge_base=False
        )
    
    # Determine if this is a new session (for notification purposes)
    is_new_session = request_data.session_id is None
    
    # Check knowledge base first
    kb_answer = find_knowledge_base_answer(request_data.message)
    if kb_answer:
        session_id = request_data.session_id or str(uuid.uuid4())
        
        # Use in-memory cache for instant age-adapted KB answers
        cache_key = f"kb_{hashlib.md5((kb_answer['answer'] + request_data.age_tier).encode()).hexdigest()[:16]}"
        
        if cache_key in _kb_cache:
            response_text = _kb_cache[cache_key]
        else:
            # Check MongoDB cache
            cached = await db.kb_age_cache.find_one({"cache_key": cache_key}, {"_id": 0})
            if cached:
                response_text = cached["response"]
                _kb_cache[cache_key] = response_text
            else:
                # Generate and cache (first time only — subsequent requests will be instant)
                response_text = kb_answer["answer"]
                try:
                    age_labels = {"4-6": "a 4-6 year old preschooler (very simple tiny words, 2-3 short sentences, playful)", 
                                  "7-9": "a 7-9 year old (clear simple language, 3-4 sentences, explain big words)", 
                                  "10-12": "a 10-12 year old pre-teen (more depth, 3-5 sentences)", 
                                  "13-18": "a teenager (mature mentor tone, 3-5 thoughtful sentences)"}
                    age_label = age_labels.get(request_data.age_tier, age_labels["7-9"])
                    response_text = await _anthropic_chat(
                        system_message="Rephrase this Bible answer for the specified age group. Keep facts and verses. Adapt language only. Return ONLY the rephrased text.",
                        user_text=f"For {age_label}:\n\n{kb_answer['answer']}",
                        max_tokens=400
                    )
                    _kb_cache[cache_key] = response_text
                    await db.kb_age_cache.insert_one({"cache_key": cache_key, "response": response_text, "age_tier": request_data.age_tier})
                except Exception as e:
                    logger.error(f"KB rephrase error: {e}")
        
        # Check if audio is cached
        audio_url = None
        if request_data.include_audio and eleven_client:
            text_hash = hashlib.md5(response_text.encode()).hexdigest()[:16]
            audio_path = AUDIO_CACHE_DIR / f"{text_hash}.mp3"
            if audio_path.exists():
                audio_url = f"/api/audio/{text_hash}.mp3"
            else:
                asyncio.create_task(_background_tts(response_text, session_id, child_voice))
        
        await save_chat_messages(session_id, request_data.child_id, request_data.age_tier, 
                                request_data.message, response_text, audio_url)
        
        # Notify parent in background
        asyncio.create_task(notif_routes.notify_parent_on_chat(
            request_data.child_id, None, request_data.message, is_new_session
        ))
        
        return ChatResponse(
            session_id=session_id,
            response=response_text,
            audio_url=audio_url,
            bible_verses=kb_answer.get("verses", []),
            from_knowledge_base=True
        )
    
    # Use LLM for non-cached questions
    try:
        child = await db.children.find_one({"child_id": request_data.child_id}, {"_id": 0})
        preferred_translation = child.get("preferred_translation", "NIV") if child else "NIV"
        child_name = child.get("name", "") if child else ""
        child_age_tier = child.get("age_tier", request_data.age_tier) if child else request_data.age_tier
        
        # Get user profile for personalization
        user_profile = await get_or_create_user_profile(request_data.child_id)
        user_context = build_user_context(user_profile, child_name, child_age_tier)
        
        # Get relevant teacher wisdom based on the question
        message_words = request_data.message.lower().split()
        teacher_wisdom = get_relevant_teacher_wisdom(message_words + [request_data.message.lower()])
        
        system_prompt = get_age_tier_system_prompt(
            child_age_tier, preferred_translation, user_context, teacher_wisdom
        )
        
        response_text = await _anthropic_chat(
            system_message=system_prompt,
            user_text=request_data.message,
            model="claude-haiku-4-5",
            max_tokens=450
        )
        
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        response_text = "I'm having a little trouble right now. Can you ask me again?"
    
    response_text = post_process_safety(response_text)
    bible_verses = extract_bible_verses(response_text)
    
    # DON'T wait for TTS - return text immediately, generate audio in background
    session_id = request_data.session_id or str(uuid.uuid4())
    if request_data.include_audio and eleven_client:
        asyncio.create_task(_background_tts(response_text, session_id, child_voice))
    
    # Update user profile in background (learns from this conversation)
    asyncio.create_task(update_user_profile(
        request_data.child_id, request_data.message, response_text, request_data.age_tier
    ))
    
    await save_chat_messages(session_id, request_data.child_id, request_data.age_tier,
                            request_data.message, response_text, None)
    
    # Notify parent in background
    asyncio.create_task(notif_routes.notify_parent_on_chat(
        request_data.child_id, None, request_data.message, is_new_session
    ))
    
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        audio_url=None,  # Frontend will poll/fetch audio separately
        bible_verses=bible_verses,
        from_knowledge_base=False
    )

async def _background_tts(text: str, session_id: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL"):
    """Generate TTS in background and update the session"""
    try:
        audio_url = await generate_tts_audio(text, voice_id)
        if audio_url:
            # Update the session's last message with audio URL
            await db.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"messages.-1.audio_url": audio_url, "last_audio_url": audio_url}}
            )
    except Exception as e:
        logger.error(f"Background TTS error: {e}")

@api_router.get("/audio-status/{session_id}")
async def get_audio_status(session_id: str):
    """Check if audio is ready for a session (for polling)"""
    # Check if TTS has completed for this session
    session = await db.sessions.find_one({"session_id": session_id}, {"_id": 0, "last_audio_url": 1})
    if session and session.get("last_audio_url"):
        return {"ready": True, "audio_url": session["last_audio_url"]}
    return {"ready": False, "audio_url": None}

async def save_chat_messages(session_id: str, child_id: str, age_tier: str, 
                            user_msg: str, assistant_msg: str, audio_url: Optional[str]):
    """Save chat messages to session"""
    # Check if session exists
    session = await db.chat_sessions.find_one({"id": session_id})
    
    if not session:
        # Get parent_id from child
        child = await db.children.find_one({"child_id": child_id}, {"_id": 0})
        parent_id = child.get("parent_id", "unknown") if child else "unknown"
        
        session = ChatSession(
            id=session_id,
            child_id=child_id,
            parent_id=parent_id,
            age_tier=age_tier
        )
        await db.chat_sessions.insert_one(session.dict())
    
    # Add messages
    messages = [
        {"id": str(uuid.uuid4()), "role": "user", "content": user_msg, "timestamp": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "role": "assistant", "content": assistant_msg, "audio_url": audio_url, "timestamp": datetime.now(timezone.utc).isoformat()}
    ]
    
    await db.chat_sessions.update_one(
        {"id": session_id},
        {
            "$push": {"messages": {"$each": messages}},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

# ==================== VOICE ENDPOINTS ====================

@api_router.post("/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio using Deepgram"""
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=503, detail="STT service not configured")
    
    try:
        audio_data = await file.read()
        
        # Use Deepgram REST API directly for simpler integration
        import httpx
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&language=en&smart_format=true&filler_words=true",
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": file.content_type or "audio/wav"
                },
                content=audio_data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Deepgram error: {response.text}")
            
            result = response.json()
            transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
            confidence = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("confidence", 0)
        
        return {
            "success": True,
            "transcript": transcript,
            "confidence": confidence
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/voice/chat")
async def voice_chat(
    file: UploadFile = File(...),
    child_id: str = "",
    age_tier: str = "7-9",
    session_id: Optional[str] = None
):
    """Complete voice chat: transcribe -> respond -> synthesize"""
    
    # Step 1: Transcribe using Deepgram REST API
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=503, detail="STT service not configured")
    
    try:
        audio_data = await file.read()
        
        import httpx
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&language=en&smart_format=true",
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": file.content_type or "audio/wav"
                },
                content=audio_data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Deepgram error: {response.text}")
            
            result = response.json()
            transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
        
        if not transcript.strip():
            return {
                "success": False,
                "error": "Could not understand audio",
                "transcript": ""
            }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    # Step 2: Get AI response
    chat_request = ChatRequest(
        session_id=session_id,
        child_id=child_id,
        message=transcript,
        age_tier=age_tier,
        include_audio=True
    )
    
    chat_response = await chat(chat_request)
    
    return {
        "success": True,
        "transcript": transcript,
        "response": chat_response.response,
        "audio_url": chat_response.audio_url,
        "session_id": chat_response.session_id,
        "bible_verses": chat_response.bible_verses,
        "from_knowledge_base": chat_response.from_knowledge_base
    }

@api_router.post("/tts")
async def text_to_speech(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL"):
    """Generate speech from text"""
    if not eleven_client:
        raise HTTPException(status_code=503, detail="TTS service not configured")
    
    try:
        audio_url = await generate_tts_audio(text, voice_id)
        return {"audio_url": audio_url}
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve cached audio files"""
    audio_path = AUDIO_CACHE_DIR / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(audio_path, media_type="audio/mpeg", headers={"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600"})

async def generate_tts_audio(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL") -> Optional[str]:
    """Generate TTS audio, save to file, and return HTTP URL"""
    if not eleven_client:
        return None
    
    try:
        # Create hash of text+voice for caching (different voice = different cache)
        cache_key = f"{text}_{voice_id}"
        text_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        audio_filename = f"{text_hash}.mp3"
        audio_path = AUDIO_CACHE_DIR / audio_filename
        
        # Return cached if exists
        if audio_path.exists():
            return f"/api/audio/{audio_filename}"
        
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
        
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk
        
        # Save to file
        audio_path.write_bytes(audio_data)
        
        return f"/api/audio/{audio_filename}"
        
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        return None

def extract_bible_verses(text: str) -> List[str]:
    """Extract Bible verse references from text"""
    import re
    patterns = [
        r'\b(\d?\s*[A-Za-z]+\s+\d+:\d+(?:-\d+)?)\b',
        r'\b([A-Za-z]+\s+\d+:\d+(?:-\d+)?)\b',
    ]
    verses = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        verses.extend(matches)
    return list(set(verses))

# ==================== PARENT DASHBOARD (see routes/dashboard.py) ====================
# ==================== KNOWLEDGE BASE (see routes/dashboard.py) ====================
# ==================== TEACHERS (see routes/dashboard.py) ====================
# ==================== SESSIONS (see routes/dashboard.py) ====================


# ==================== DAILY VERSE & CHALLENGE (see routes/verses.py) ====================
DAILY_VERSES = []
from bible_verses import DAILY_VERSES


# ==================== ROUTE MODULES ====================
from routes import notifications as notif_routes
from routes import emails as email_routes
from routes import auth as auth_routes
from routes import children as children_routes
from routes import dashboard as dashboard_routes
from routes import verses as verses_routes
from routes import leaderboard as leaderboard_routes

# Init route modules with dependencies
notif_routes.init(db, get_current_user)
email_routes.init(db, get_current_user)
auth_routes.init(db, get_current_user)
children_routes.init(db, get_current_user, VOICE_OPTIONS, ChildProfile, ChildProfileCreate)
dashboard_routes.init(db, get_current_user, KNOWLEDGE_BASE, FEATURED_TEACHERS)
verses_routes.init(db, DAILY_VERSES, _anthropic_chat, None, ANTHROPIC_API_KEY)
leaderboard_routes.init(db, get_current_user)

# Include all routers
app.include_router(api_router)
app.include_router(auth_routes.router)
app.include_router(children_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(verses_routes.router)
app.include_router(leaderboard_routes.router)
app.include_router(notif_routes.router)
app.include_router(email_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def prewarm_kb_audio():
    """Pre-generate TTS audio for all knowledge base answers at startup"""
    # Start weekly email scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    
    async def weekly_email_job():
        await email_routes.send_all_weekly_summaries()
    
    # Sunday evening 6 PM UTC
    scheduler.add_job(weekly_email_job, 'cron', day_of_week='sun', hour=18, minute=0)

    # Reading Night reminder — runs hourly, checks which families have reading night at this hour
    async def reading_night_job():
        await notif_routes.send_reading_night_reminders()

    scheduler.add_job(reading_night_job, 'cron', minute=0)  # Every hour at :00

    scheduler.start()
    logger.info("Weekly email scheduler started (Sunday 6 PM UTC)")
    logger.info("Reading Night hourly reminder scheduler started")
    
    if not eleven_client:
        logger.info("TTS not configured, skipping audio pre-warming")
        return
    
    cached = 0
    total = len(KNOWLEDGE_BASE)
    for question, item in KNOWLEDGE_BASE.items():
        text_hash = hashlib.md5(item["answer"].encode()).hexdigest()[:16]
        audio_path = AUDIO_CACHE_DIR / f"{text_hash}.mp3"
        if audio_path.exists():
            cached += 1
    
    if cached == total:
        logger.info(f"All {total} KB audio files already cached")
    else:
        async def _generate_all():
            generated = 0
            for question, item in KNOWLEDGE_BASE.items():
                text_hash = hashlib.md5(item["answer"].encode()).hexdigest()[:16]
                audio_path = AUDIO_CACHE_DIR / f"{text_hash}.mp3"
                if not audio_path.exists():
                    try:
                        await generate_tts_audio(item["answer"])
                        generated += 1
                    except Exception as e:
                        logger.error(f"KB audio pre-warm error: {e}")
            logger.info(f"KB audio pre-warming complete: {generated} new files")
        asyncio.create_task(_generate_all())
        logger.info(f"Started KB audio pre-warming ({cached}/{total} cached)")

    # Pre-load KB age cache into memory
    async for doc in db.kb_age_cache.find({}, {"_id": 0}):
        _kb_cache[doc["cache_key"]] = doc["response"]
    logger.info(f"Loaded {len(_kb_cache)} KB age-adapted answers into memory")

    # Pre-warm ALL KB age-adapted answers for all 4 tiers (background)
    AGE_TIERS_ALL = ["4-6", "7-9", "10-12", "13-18"]
    total_combos = len(KNOWLEDGE_BASE) * len(AGE_TIERS_ALL)
    missing = total_combos - len(_kb_cache)
    if missing > 0:
        async def _prewarm_kb_age_cache():
            generated = 0
            age_labels = {
                "4-6": "a 4-6 year old preschooler (very simple tiny words, 2-3 short sentences, playful)",
                "7-9": "a 7-9 year old (clear simple language, 3-4 sentences, explain big words)",
                "10-12": "a 10-12 year old pre-teen (more depth, 3-5 sentences)",
                "13-18": "a teenager (mature mentor tone, 3-5 thoughtful sentences)"
            }
            for question, item in KNOWLEDGE_BASE.items():
                for tier in AGE_TIERS_ALL:
                    cache_key = f"kb_{hashlib.md5((item['answer'] + tier).encode()).hexdigest()[:16]}"
                    if cache_key in _kb_cache:
                        continue
                    try:
                        age_label = age_labels[tier]
                        response_text = await _anthropic_chat(
                            system_message="Rephrase this Bible answer for the specified age group. Keep facts and verses. Adapt language only. Return ONLY the rephrased text.",
                            user_text=f"For {age_label}:\n\n{item['answer']}",
                            max_tokens=400
                        )
                        _kb_cache[cache_key] = response_text
                        await db.kb_age_cache.insert_one({"cache_key": cache_key, "response": response_text, "age_tier": tier})
                        generated += 1
                    except Exception as e:
                        logger.error(f"KB age pre-warm error ({tier}): {e}")
                    await asyncio.sleep(0.3)  # Rate limit
            logger.info(f"KB age pre-warming complete: {generated} new age-adapted answers generated")
        asyncio.create_task(_prewarm_kb_age_cache())
        logger.info(f"Started KB age pre-warming: {missing}/{total_combos} missing, generating in background...")
    else:
        logger.info(f"All {total_combos} KB age-adapted answers already cached")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
