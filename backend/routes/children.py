from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["children"])

db = None
get_current_user = None
VOICE_OPTIONS = []
ChildProfile = None
ChildProfileCreate = None

def init(database, auth_func, voice_options, profile_cls, create_cls):
    global db, get_current_user, VOICE_OPTIONS, ChildProfile, ChildProfileCreate
    db = database
    get_current_user = auth_func
    VOICE_OPTIONS = voice_options
    ChildProfile = profile_cls
    ChildProfileCreate = create_cls


class ConsentRequest(BaseModel):
    child_name_confirmation: str
    consent_method: str = "name_verification"

class VoiceUpdateRequest(BaseModel):
    voice_id: str


@router.post("/children", response_model=dict)
async def create_child(child: dict, request: Request):
    """Create a child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child_create = ChildProfileCreate(**child)
    child_profile = ChildProfile(parent_id=user["user_id"], **child_create.dict())
    await db.children.insert_one(child_profile.dict())
    
    child_data = await db.children.find_one({"child_id": child_profile.child_id}, {"_id": 0})
    return child_data


@router.get("/children")
async def get_children(request: Request):
    """Get all children for current parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    children = await db.children.find({"parent_id": user["user_id"]}, {"_id": 0}).to_list(20)
    return {"children": children}


@router.get("/children/{child_id}")
async def get_child(child_id: str, request: Request):
    """Get specific child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]}, {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@router.put("/children/{child_id}")
async def update_child(child_id: str, updates: dict, request: Request):
    """Update child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    update_data = ChildProfileCreate(**updates).dict()
    result = await db.children.update_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Child not found")
    
    child = await db.children.find_one({"child_id": child_id}, {"_id": 0})
    return child


@router.post("/children/{child_id}/consent")
async def give_parental_consent(child_id: str, body: ConsentRequest, request: Request):
    """Record COPPA-compliant verifiable parental consent for child"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    child = await db.children.find_one(
        {"child_id": child_id, "parent_id": user["user_id"]}, {"_id": 0}
    )
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    if body.child_name_confirmation.strip().lower() != child["name"].strip().lower():
        raise HTTPException(status_code=400, detail="Child name does not match.")
    
    consent_record = {
        "parental_consent_given": True,
        "consent_timestamp": datetime.now(timezone.utc).isoformat(),
        "consent_method": body.consent_method,
        "consent_parent_id": user["user_id"],
        "consent_parent_email": user.get("email", ""),
    }
    await db.children.update_one({"child_id": child_id}, {"$set": consent_record})
    
    await db.consent_log.insert_one({
        "child_id": child_id, "parent_id": user["user_id"],
        "parent_email": user.get("email", ""), "child_name": child["name"],
        "method": body.consent_method, "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    return {"message": "COPPA parental consent recorded", "child_id": child_id}


@router.get("/coppa-policy")
async def get_coppa_policy():
    """Return COPPA disclosure information"""
    return {
        "data_collected": [
            "Child's first name and age group",
            "Bible-related questions asked",
            "Voice recordings (for speech-to-text, not stored permanently)",
        ],
        "data_usage": [
            "Provide age-appropriate Bible answers",
            "Track learning progress for parents",
            "Improve answer quality over time",
        ],
        "data_not_collected": [
            "Last name or full name", "Location or address",
            "Photos or videos", "Contact information from children",
        ],
        "retention": "Conversation history is retained until the parent deletes the child profile.",
        "parent_rights": [
            "View all conversation history in the Parent Dashboard",
            "Delete child profile and all associated data at any time",
            "Modify notification and privacy settings",
            "Revoke consent and deactivate child access",
        ],
    }


@router.patch("/children/{child_id}/voice")
async def update_child_voice(child_id: str, body: VoiceUpdateRequest, request: Request):
    """Update only the voice_id for a child profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    valid_ids = [v["id"] for v in VOICE_OPTIONS]
    if body.voice_id not in valid_ids:
        raise HTTPException(status_code=400, detail="Invalid voice_id")
    
    result = await db.children.update_one(
        {"child_id": child_id, "parent_id": user["user_id"]},
        {"$set": {"voice_id": body.voice_id}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Child not found")
    
    child = await db.children.find_one({"child_id": child_id}, {"_id": 0})
    return child
