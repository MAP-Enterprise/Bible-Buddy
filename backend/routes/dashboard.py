from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])

db = None
get_current_user = None
KNOWLEDGE_BASE = {}
FEATURED_TEACHERS = {}

def init(database, auth_func, kb, teachers):
    global db, get_current_user, KNOWLEDGE_BASE, FEATURED_TEACHERS
    db = database
    get_current_user = auth_func
    KNOWLEDGE_BASE = kb
    FEATURED_TEACHERS = teachers


@router.get("/dashboard/stats/{child_id}")
async def get_child_stats(child_id: str, request: Request):
    """Get usage statistics for a child"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]}, {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    sessions = await db.chat_sessions.find({"child_id": child_id}, {"_id": 0}).to_list(1000)
    
    total_messages = 0
    topics = {}
    last_active = None
    
    for session in sessions:
        messages = session.get("messages", [])
        total_messages += len(messages)
        if session.get("updated_at"):
            updated = session["updated_at"]
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            if not last_active or updated > last_active:
                last_active = updated
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                for topic in ["jesus", "god", "bible", "prayer", "heaven", "angel", "sin", "forgive"]:
                    if topic in content:
                        topics[topic] = topics.get(topic, 0) + 1
    
    sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "child_id": child_id,
        "child_name": child.get("name"),
        "total_conversations": len(sessions),
        "total_messages": total_messages,
        "most_asked_topics": [t[0] for t in sorted_topics],
        "last_active": last_active.isoformat() if last_active else None
    }


@router.get("/dashboard/conversations/{child_id}")
async def get_child_conversations(child_id: str, request: Request, limit: int = 20):
    """Get conversation history for a child"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]}, {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    sessions = await db.chat_sessions.find(
        {"child_id": child_id}, {"_id": 0}
    ).sort("updated_at", -1).limit(limit).to_list(limit)
    
    return {"conversations": sessions}


@router.get("/dashboard/conversation/{session_id}")
async def get_conversation_detail(session_id: str, request: Request):
    """Get detailed conversation"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.chat_sessions.find_one(
        {"id": session_id, "parent_id": user["user_id"]}, {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return session


@router.get("/knowledge-base")
async def get_knowledge_base_list():
    """Get all knowledge base questions"""
    questions = [
        {"question": key, "topic": value.get("topic")}
        for key, value in KNOWLEDGE_BASE.items()
    ]
    return {"questions": questions, "total": len(questions)}


@router.get("/knowledge-base/{topic}")
async def get_knowledge_by_topic(topic: str):
    """Get questions by topic"""
    questions = [
        {"question": key, "answer": value["answer"][:200] + "...", "verses": value.get("verses", [])}
        for key, value in KNOWLEDGE_BASE.items()
        if value.get("topic") == topic
    ]
    return {"topic": topic, "questions": questions}


@router.get("/teachers")
async def get_teachers():
    """Get featured teachers"""
    teachers_list = [
        {"id": tid, "name": t["name"], "ministry": t["ministry"], "style": t["style"]}
        for tid, t in FEATURED_TEACHERS.items()
    ]
    return {"teachers": teachers_list}


@router.get("/teachers/{teacher_id}")
async def get_teacher(teacher_id: str):
    """Get teacher details"""
    if teacher_id not in FEATURED_TEACHERS:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return {"id": teacher_id, **FEATURED_TEACHERS[teacher_id]}


@router.get("/sessions/{child_id}")
async def get_child_sessions(child_id: str):
    """Get all chat sessions for a child"""
    sessions = await db.chat_sessions.find(
        {"child_id": child_id}, {"_id": 0}
    ).sort("updated_at", -1).to_list(50)
    return {"sessions": sessions}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get specific session with messages"""
    session = await db.chat_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
