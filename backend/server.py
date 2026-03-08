from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Response, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import base64
from emergentintegrations.llm.chat import LlmChat, UserMessage
from elevenlabs import ElevenLabs, VoiceSettings
# Deepgram is used via REST API directly
import aiohttp
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
    parental_consent_given: bool = False
    consent_timestamp: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChildProfileCreate(BaseModel):
    name: str
    age_tier: str = "7-9"
    avatar: Optional[str] = None
    preferred_translation: str = "NIV"

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
    
    # Exact match
    if clean_question in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[clean_question]
    
    # Partial match
    for key, value in KNOWLEDGE_BASE.items():
        if key in clean_question or clean_question in key:
            return value
        # Check if key words match
        key_words = set(key.split())
        question_words = set(clean_question.split())
        if len(key_words & question_words) >= len(key_words) * 0.6:
            return value
    
    return None

# ==================== FEATURED TEACHERS ====================

FEATURED_TEACHERS = {
    "apostle_selman": {
        "name": "Apostle Joshua Selman",
        "ministry": "Koinonia Global",
        "key_themes": [
            "The power of the Holy Spirit",
            "Walking in God's wisdom and understanding",
            "The importance of prayer and intimacy with God",
            "Spiritual growth and maturity",
            "Kingdom principles and dominion"
        ],
        "notable_teachings": [
            "There is no substitute for the presence of God",
            "Your spiritual growth is measured by your hunger for God's word",
            "Prayer is not just asking God for things, it's communion with Him",
            "The Holy Spirit is your greatest advantage in life",
            "Wisdom is the principal thing - get wisdom and understanding"
        ],
        "style": "Deep theological teaching with practical application, emphasis on the Holy Spirit"
    },
    "stephanie_ike": {
        "name": "Pastor Stephanie Ike",
        "ministry": "ONE Church LA / The Light Church",
        "key_themes": [
            "Identity in Christ",
            "Purpose and destiny",
            "Breaking free from fear and anxiety",
            "Faith over feelings",
            "God's unconditional love"
        ],
        "notable_teachings": [
            "You are not what happened to you, you are who God says you are",
            "Fear is faith in the enemy - choose to trust God instead",
            "Your feelings are valid, but they don't determine your value",
            "God's love for you is not based on your performance",
            "You were created on purpose, for a purpose"
        ],
        "style": "Encouraging, empathetic, focused on identity and emotional healing"
    },
    "steven_furtick": {
        "name": "Pastor Steven Furtick",
        "ministry": "Elevation Church",
        "key_themes": [
            "Faith and confidence in God",
            "Overcoming obstacles and limitations",
            "God's promises and provision",
            "Breaking through barriers",
            "Trusting God in uncertain times"
        ],
        "notable_teachings": [
            "The enemy's job is to steal, kill, and destroy - don't let him",
            "What God starts, He finishes",
            "Your limitations are God's opportunities",
            "Don't let your feelings determine your faith",
            "What looks like a setback is often a setup for something greater"
        ],
        "style": "Passionate, energetic, motivational with practical faith applications"
    },
    "priscilla_shirer": {
        "name": "Priscilla Shirer",
        "ministry": "Going Beyond Ministries",
        "key_themes": [
            "Spiritual warfare and the armor of God",
            "Prayer as a weapon",
            "Hearing God's voice",
            "Living as a discerning believer",
            "The power of God's Word"
        ],
        "notable_teachings": [
            "Prayer is not preparation for the battle - prayer IS the battle",
            "The enemy wants to distract you from your divine assignment",
            "God's Word is your sword - learn to use it",
            "Discernment comes from spending time with God",
            "Your identity in Christ is your greatest weapon"
        ],
        "style": "Bold, Scripture-rich, focused on spiritual warfare and practical application"
    }
}

def get_teachers_knowledge() -> str:
    """Generate knowledge base content from featured teachers"""
    knowledge = "\nFEATURED CHRISTIAN TEACHERS:\n"
    for teacher_id, teacher in FEATURED_TEACHERS.items():
        knowledge += f"\n{teacher['name']} ({teacher['ministry']}):\n"
        knowledge += f"Style: {teacher['style']}\n"
        for teaching in teacher['notable_teachings'][:3]:
            knowledge += f"  - \"{teaching}\"\n"
    return knowledge

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

# ==================== AGE-TIER PROMPTS ====================

def get_age_tier_system_prompt(age_tier: str, preferred_translation: str = "NIV") -> str:
    """Get age-appropriate system prompt"""
    teachers_knowledge = get_teachers_knowledge()
    
    base_guidelines = f"""
You are Bible Buddy, a warm, friendly, and loving guide who helps children learn about God, Jesus, and the Bible.

PRIMARY KNOWLEDGE: The Holy Bible ({preferred_translation})
{teachers_knowledge}

CORE PRINCIPLES:
1. Ground answers in Scripture first - cite verses from {preferred_translation}
2. Reference featured teachers' wisdom when relevant
3. Be age-appropriate in vocabulary and depth
4. Never be preachy - be encouraging and loving
5. Keep children safe - never discuss inappropriate topics
"""

    age_prompts = {
        "4-6": f"""{base_guidelines}

AGE: 4-6 years (Preschool/Kindergarten)
- Use very simple words (1-2 syllables)
- Short sentences (5-8 words)
- Be playful - use "Wow!", "Amazing!"
- Use comparisons to familiar things
- Focus on love, kindness, family
- Paraphrase verses simply
""",
        "7-9": f"""{base_guidelines}

AGE: 7-9 years (Early Elementary)
- Clear, simple language
- Enthusiastic and encouraging
- Connect stories to daily life
- Quote short verses with explanation
- Ask engaging questions
""",
        "10-12": f"""{base_guidelines}

AGE: 10-12 years (Upper Elementary)
- Age-appropriate vocabulary
- Explore concepts more deeply
- Discuss context and background
- Connect faith to real challenges
- Can mention teachers by name
""",
        "13-18": f"""{base_guidelines}

AGE: 13-18 years (Teenager)
- Speak as a mature friend
- Use theological terms with explanation
- Be authentic and honest
- Quote teachers directly
- Encourage critical thinking
- Address real struggles
"""
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
        "llm_configured": bool(EMERGENT_LLM_KEY),
        "tts_configured": bool(ELEVENLABS_API_KEY),
        "stt_configured": bool(DEEPGRAM_API_KEY),
        "knowledge_base_size": len(KNOWLEDGE_BASE)
    }

# ==================== AUTHENTICATION ENDPOINTS ====================

@api_router.get("/auth/session")
async def exchange_session(session_id: str, response: Response):
    """Exchange Emergent session_id for user data"""
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=401, detail="Invalid session")
                data = await resp.json()
        
        # Check if parent exists
        existing_parent = await db.parents.find_one({"email": data["email"]}, {"_id": 0})
        
        if existing_parent:
            user_id = existing_parent["user_id"]
            # Update user info
            await db.parents.update_one(
                {"user_id": user_id},
                {"$set": {"name": data["name"], "picture": data.get("picture")}}
            )
        else:
            # Create new parent account
            user_id = f"parent_{uuid.uuid4().hex[:12]}"
            parent = {
                "user_id": user_id,
                "email": data["email"],
                "name": data["name"],
                "picture": data.get("picture"),
                "created_at": datetime.now(timezone.utc)
            }
            await db.parents.insert_one(parent)
        
        # Create session
        session_token = data.get("session_token", f"st_{uuid.uuid4().hex}")
        session = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
            "created_at": datetime.now(timezone.utc)
        }
        await db.user_sessions.insert_one(session)
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7*24*60*60,
            path="/"
        )
        
        parent_data = await db.parents.find_one({"user_id": user_id}, {"_id": 0})
        return parent_data
        
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/auth/me")
async def get_current_user_endpoint(request: Request):
    """Get current authenticated user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

# ==================== CHILD PROFILE ENDPOINTS ====================

@api_router.post("/children", response_model=dict)
async def create_child(child: ChildProfileCreate, request: Request):
    """Create a child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child_profile = ChildProfile(
        parent_id=user["user_id"],
        **child.dict()
    )
    await db.children.insert_one(child_profile.dict())
    
    child_data = await db.children.find_one({"child_id": child_profile.child_id}, {"_id": 0})
    return child_data

@api_router.get("/children")
async def get_children(request: Request):
    """Get all children for current parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    children = await db.children.find({"parent_id": user["user_id"]}, {"_id": 0}).to_list(20)
    return {"children": children}

@api_router.get("/children/{child_id}")
async def get_child(child_id: str, request: Request):
    """Get specific child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child

@api_router.put("/children/{child_id}")
async def update_child(child_id: str, updates: ChildProfileCreate, request: Request):
    """Update child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.children.update_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"$set": updates.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Child not found")
    
    child = await db.children.find_one({"child_id": child_id}, {"_id": 0})
    return child

@api_router.post("/children/{child_id}/consent")
async def give_parental_consent(child_id: str, request: Request):
    """Record parental consent for child"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.children.update_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"$set": {
            "parental_consent_given": True,
            "consent_timestamp": datetime.now(timezone.utc)
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Child not found")
    
    return {"message": "Parental consent recorded", "child_id": child_id}

# ==================== CHAT ENDPOINTS ====================

@api_router.post("/chat", response_model=ChatResponse)
async def chat(request_data: ChatRequest):
    """Main chat endpoint"""
    
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
    
    # Check knowledge base first
    kb_answer = find_knowledge_base_answer(request_data.message)
    if kb_answer:
        # Generate audio for knowledge base answer
        audio_url = None
        if request_data.include_audio and eleven_client:
            try:
                audio_url = await generate_tts_audio(kb_answer["answer"])
            except Exception as e:
                logger.error(f"TTS error: {e}")
        
        # Create/update session
        session_id = request_data.session_id or str(uuid.uuid4())
        await save_chat_messages(session_id, request_data.child_id, request_data.age_tier, 
                                request_data.message, kb_answer["answer"], audio_url)
        
        return ChatResponse(
            session_id=session_id,
            response=kb_answer["answer"],
            audio_url=audio_url,
            bible_verses=kb_answer.get("verses", []),
            from_knowledge_base=True
        )
    
    # Use LLM for non-cached questions
    try:
        # Get child's translation preference
        child = await db.children.find_one({"child_id": request_data.child_id}, {"_id": 0})
        preferred_translation = child.get("preferred_translation", "NIV") if child else "NIV"
        
        system_prompt = get_age_tier_system_prompt(request_data.age_tier, preferred_translation)
        
        chat_client = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=request_data.session_id or str(uuid.uuid4()),
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=request_data.message)
        response_text = await chat_client.send_message(user_message)
        
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        response_text = "I'm having a little trouble right now. Can you ask me again?"
    
    # Post-process safety
    response_text = post_process_safety(response_text)
    
    # Extract verses
    bible_verses = extract_bible_verses(response_text)
    
    # Generate audio
    audio_url = None
    if request_data.include_audio and eleven_client:
        try:
            audio_url = await generate_tts_audio(response_text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    # Save messages
    session_id = request_data.session_id or str(uuid.uuid4())
    await save_chat_messages(session_id, request_data.child_id, request_data.age_tier,
                            request_data.message, response_text, audio_url)
    
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        audio_url=audio_url,
        bible_verses=bible_verses,
        from_knowledge_base=False
    )

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

async def generate_tts_audio(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL") -> Optional[str]:
    """Generate TTS audio and return as base64"""
    if not eleven_client:
        return None
    
    try:
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
        
        audio_b64 = base64.b64encode(audio_data).decode()
        return f"data:audio/mpeg;base64,{audio_b64}"
        
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

# ==================== PARENT DASHBOARD ENDPOINTS ====================

@api_router.get("/dashboard/stats/{child_id}")
async def get_child_stats(child_id: str, request: Request):
    """Get usage statistics for a child"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify parent owns this child
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    # Get conversations
    sessions = await db.chat_sessions.find(
        {"child_id": child_id},
        {"_id": 0}
    ).to_list(1000)
    
    total_messages = 0
    topics = {}
    last_active = None
    
    for session in sessions:
        messages = session.get("messages", [])
        total_messages += len(messages)
        
        # Track last active
        if session.get("updated_at"):
            updated = session["updated_at"]
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            if not last_active or updated > last_active:
                last_active = updated
        
        # Analyze topics (simple keyword matching)
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                for topic in ["jesus", "god", "bible", "prayer", "heaven", "angel", "sin", "forgive"]:
                    if topic in content:
                        topics[topic] = topics.get(topic, 0) + 1
    
    # Sort topics by frequency
    sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "child_id": child_id,
        "child_name": child.get("name"),
        "total_conversations": len(sessions),
        "total_messages": total_messages,
        "most_asked_topics": [t[0] for t in sorted_topics],
        "last_active": last_active.isoformat() if last_active else None
    }

@api_router.get("/dashboard/conversations/{child_id}")
async def get_child_conversations(child_id: str, request: Request, limit: int = 20):
    """Get conversation history for a child"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify parent owns this child
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    sessions = await db.chat_sessions.find(
        {"child_id": child_id},
        {"_id": 0}
    ).sort("updated_at", -1).limit(limit).to_list(limit)
    
    return {"conversations": sessions}

@api_router.get("/dashboard/conversation/{session_id}")
async def get_conversation_detail(session_id: str, request: Request):
    """Get detailed conversation"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.chat_sessions.find_one(
        {"id": session_id, "parent_id": user["user_id"]},
        {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return session

# ==================== KNOWLEDGE BASE ENDPOINTS ====================

@api_router.get("/knowledge-base")
async def get_knowledge_base():
    """Get all knowledge base questions"""
    questions = [
        {"question": key, "topic": value.get("topic")}
        for key, value in KNOWLEDGE_BASE.items()
    ]
    return {"questions": questions, "total": len(questions)}

@api_router.get("/knowledge-base/{topic}")
async def get_knowledge_by_topic(topic: str):
    """Get questions by topic"""
    questions = [
        {"question": key, "answer": value["answer"][:200] + "...", "verses": value.get("verses", [])}
        for key, value in KNOWLEDGE_BASE.items()
        if value.get("topic") == topic
    ]
    return {"topic": topic, "questions": questions}

# ==================== TEACHERS ENDPOINTS ====================

@api_router.get("/teachers")
async def get_teachers():
    """Get featured teachers"""
    teachers_list = [
        {"id": tid, "name": t["name"], "ministry": t["ministry"], "style": t["style"]}
        for tid, t in FEATURED_TEACHERS.items()
    ]
    return {"teachers": teachers_list}

@api_router.get("/teachers/{teacher_id}")
async def get_teacher(teacher_id: str):
    """Get teacher details"""
    if teacher_id not in FEATURED_TEACHERS:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return {"id": teacher_id, **FEATURED_TEACHERS[teacher_id]}

# ==================== SESSION ENDPOINTS ====================

@api_router.get("/sessions/{child_id}")
async def get_child_sessions(child_id: str):
    """Get all chat sessions for a child"""
    sessions = await db.chat_sessions.find(
        {"child_id": child_id},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(50)
    return {"sessions": sessions}

@api_router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get specific session with messages"""
    session = await db.chat_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ==================== DAILY VERSE ====================

DAILY_VERSES = [
    {"verse": "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.", "reference": "John 3:16", "theme": "love"},
    {"verse": "I can do all this through him who gives me strength.", "reference": "Philippians 4:13", "theme": "strength"},
    {"verse": "The Lord is my shepherd, I lack nothing.", "reference": "Psalm 23:1", "theme": "trust"},
    {"verse": "Be strong and courageous. Do not be afraid; do not be discouraged, for the Lord your God will be with you wherever you go.", "reference": "Joshua 1:9", "theme": "courage"},
    {"verse": "Trust in the Lord with all your heart and lean not on your own understanding.", "reference": "Proverbs 3:5", "theme": "trust"},
    {"verse": "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future.", "reference": "Jeremiah 29:11", "theme": "hope"},
    {"verse": "The Lord is my light and my salvation—whom shall I fear?", "reference": "Psalm 27:1", "theme": "courage"},
    {"verse": "And we know that in all things God works for the good of those who love him.", "reference": "Romans 8:28", "theme": "faith"},
    {"verse": "Be kind and compassionate to one another, forgiving each other, just as in Christ God forgave you.", "reference": "Ephesians 4:32", "theme": "kindness"},
    {"verse": "The fruit of the Spirit is love, joy, peace, forbearance, kindness, goodness, faithfulness, gentleness and self-control.", "reference": "Galatians 5:22-23", "theme": "character"},
    {"verse": "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God.", "reference": "Philippians 4:6", "theme": "prayer"},
    {"verse": "Have I not commanded you? Be strong and courageous. Do not be afraid; do not be discouraged.", "reference": "Joshua 1:9", "theme": "courage"},
    {"verse": "Your word is a lamp for my feet, a light on my path.", "reference": "Psalm 119:105", "theme": "wisdom"},
    {"verse": "Love is patient, love is kind. It does not envy, it does not boast, it is not proud.", "reference": "1 Corinthians 13:4", "theme": "love"},
    {"verse": "The Lord is close to the brokenhearted and saves those who are crushed in spirit.", "reference": "Psalm 34:18", "theme": "comfort"},
    {"verse": "But those who hope in the Lord will renew their strength. They will soar on wings like eagles.", "reference": "Isaiah 40:31", "theme": "hope"},
    {"verse": "God is our refuge and strength, an ever-present help in trouble.", "reference": "Psalm 46:1", "theme": "strength"},
    {"verse": "I praise you because I am fearfully and wonderfully made; your works are wonderful.", "reference": "Psalm 139:14", "theme": "identity"},
    {"verse": "Cast all your anxiety on him because he cares for you.", "reference": "1 Peter 5:7", "theme": "comfort"},
    {"verse": "Whatever you do, work at it with all your heart, as working for the Lord.", "reference": "Colossians 3:23", "theme": "character"},
    {"verse": "The Lord your God is with you, the Mighty Warrior who saves. He will take great delight in you.", "reference": "Zephaniah 3:17", "theme": "love"},
    {"verse": "Give thanks to the Lord, for he is good; his love endures forever.", "reference": "Psalm 107:1", "theme": "gratitude"},
    {"verse": "But the Lord is faithful, and he will strengthen you and protect you from the evil one.", "reference": "2 Thessalonians 3:3", "theme": "faith"},
    {"verse": "Children, obey your parents in the Lord, for this is right.", "reference": "Ephesians 6:1", "theme": "obedience"},
    {"verse": "A friend loves at all times, and a brother is born for a time of adversity.", "reference": "Proverbs 17:17", "theme": "friendship"},
    {"verse": "The heavens declare the glory of God; the skies proclaim the work of his hands.", "reference": "Psalm 19:1", "theme": "creation"},
    {"verse": "Let the peace of Christ rule in your hearts, since as members of one body you were called to peace.", "reference": "Colossians 3:15", "theme": "peace"},
    {"verse": "In the beginning God created the heavens and the earth.", "reference": "Genesis 1:1", "theme": "creation"},
    {"verse": "Jesus said, 'Let the little children come to me, and do not hinder them, for the kingdom of heaven belongs to such as these.'", "reference": "Matthew 19:14", "theme": "love"},
    {"verse": "This is the day that the Lord has made; let us rejoice and be glad in it.", "reference": "Psalm 118:24", "theme": "joy"},
    {"verse": "So do not fear, for I am with you; do not be dismayed, for I am your God.", "reference": "Isaiah 41:10", "theme": "courage"},
]

def get_todays_verse_index() -> int:
    """Get deterministic verse index based on current date"""
    today = datetime.now(timezone.utc).date()
    day_of_year = today.timetuple().tm_yday
    return day_of_year % len(DAILY_VERSES)

@api_router.get("/verse-of-the-day")
async def get_verse_of_the_day(age_tier: str = "7-9"):
    """Get the daily Bible verse with an age-appropriate AI explanation"""
    verse_index = get_todays_verse_index()
    verse_data = DAILY_VERSES[verse_index]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Check cache in MongoDB
    cached = await db.daily_verses.find_one(
        {"date": today_str, "age_tier": age_tier},
        {"_id": 0}
    )
    if cached:
        return cached

    # Generate age-appropriate explanation with AI
    explanation = ""
    try:
        age_labels = {"4-6": "a 4-6 year old child", "7-9": "a 7-9 year old child", "10-12": "a 10-12 year old", "13-18": "a teenager"}
        age_label = age_labels.get(age_tier, "a child")

        chat_client = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"votd_{today_str}_{age_tier}",
            system_message=f"You are Bible Buddy, a warm and loving Bible guide for children. Explain Bible verses in a way that {age_label} can understand. Keep it to 2-3 short, encouraging sentences. Be warm and use simple language."
        ).with_model("openai", "gpt-4o")

        prompt = f'Explain this Bible verse for {age_label}: "{verse_data["verse"]}" ({verse_data["reference"]})'
        explanation = await chat_client.send_message(UserMessage(text=prompt))
    except Exception as e:
        logger.error(f"VOTD AI error: {e}")
        explanation = f"This verse reminds us about God's {verse_data['theme']}. Take a moment to think about what it means to you!"

    result = {
        "date": today_str,
        "verse": verse_data["verse"],
        "reference": verse_data["reference"],
        "theme": verse_data["theme"],
        "age_tier": age_tier,
        "explanation": explanation,
    }

    # Cache in MongoDB
    await db.daily_verses.insert_one({**result, "created_at": datetime.now(timezone.utc)})
    # Re-fetch without _id
    return result


# Include router
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
