from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Will be set by server.py on startup
db = None
get_current_user = None

def init(database, auth_func):
    global db, get_current_user
    db = database
    get_current_user = auth_func


class PushTokenRequest(BaseModel):
    token: str
    device_id: Optional[str] = None
    platform: Optional[str] = "web"

class NotificationSettingsUpdate(BaseModel):
    notify_on_session_start: Optional[bool] = None
    notify_on_every_message: Optional[bool] = None
    email_weekly_summary: Optional[bool] = None

class ReadingNightSettings(BaseModel):
    enabled: bool = True
    day: str = "friday"  # monday, tuesday, wednesday, thursday, friday, saturday, sunday
    hour: int = 19  # 0-23 (UTC)


async def _get_or_create_settings(parent_id: str) -> dict:
    """Get or create notification settings for a parent"""
    settings = await db.notification_settings.find_one({"parent_id": parent_id}, {"_id": 0})
    if not settings:
        settings = {
            "parent_id": parent_id,
            "push_tokens": [],
            "notify_on_session_start": True,
            "notify_on_every_message": False,
            "email_weekly_summary": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.notification_settings.insert_one(settings)
        settings.pop("_id", None)
    return settings


@router.post("/register-token")
async def register_push_token(req: PushTokenRequest, request: Request):
    """Register a push notification token for the parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    parent_id = user["user_id"]
    await _get_or_create_settings(parent_id)
    
    # Remove old entry for same device, then add new
    await db.notification_settings.update_one(
        {"parent_id": parent_id},
        {"$pull": {"push_tokens": {"device_id": req.device_id}}} if req.device_id else {"$set": {}}
    )
    
    token_entry = {
        "token": req.token,
        "device_id": req.device_id or "unknown",
        "platform": req.platform,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.notification_settings.update_one(
        {"parent_id": parent_id},
        {"$addToSet": {"push_tokens": token_entry}}
    )
    
    return {"status": "success", "message": "Push token registered"}


@router.get("/settings")
async def get_notification_settings(request: Request):
    """Get notification settings for the authenticated parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    settings = await _get_or_create_settings(user["user_id"])
    return {
        "notify_on_session_start": settings.get("notify_on_session_start", True),
        "notify_on_every_message": settings.get("notify_on_every_message", False),
        "email_weekly_summary": settings.get("email_weekly_summary", True),
        "push_tokens_count": len(settings.get("push_tokens", [])),
    }


@router.put("/settings")
async def update_notification_settings(update: NotificationSettingsUpdate, request: Request):
    """Update notification settings for the authenticated parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    parent_id = user["user_id"]
    await _get_or_create_settings(parent_id)
    
    update_fields = {k: v for k, v in update.dict().items() if v is not None}
    if update_fields:
        await db.notification_settings.update_one(
            {"parent_id": parent_id},
            {"$set": update_fields}
        )
    
    return {"status": "success", "message": "Settings updated"}


async def send_push_to_parent(parent_id: str, title: str, body: str, data: dict = None):
    """Send push notification to all of a parent's registered devices via Expo Push API"""
    settings = await db.notification_settings.find_one({"parent_id": parent_id}, {"_id": 0})
    if not settings:
        return
    
    tokens = [t["token"] for t in settings.get("push_tokens", []) if t.get("token")]
    if not tokens:
        return
    
    messages = []
    for token in tokens:
        msg = {
            "to": token,
            "sound": "default",
            "title": title,
            "body": body,
        }
        if data:
            msg["data"] = data
        messages.append(msg)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            if response.status_code != 200:
                logger.error(f"Expo push error: {response.text}")
            else:
                logger.info(f"Push sent to {len(tokens)} devices for parent {parent_id}")
    except Exception as e:
        logger.error(f"Push notification error: {e}")


async def notify_parent_on_chat(child_id: str, child_name: str, message: str, is_new_session: bool):
    """Check parent's notification settings and send push if appropriate"""
    child = await db.children.find_one({"child_id": child_id}, {"_id": 0})
    if not child:
        return
    
    parent_id = child.get("parent_id")
    if not parent_id:
        return
    
    settings = await db.notification_settings.find_one({"parent_id": parent_id}, {"_id": 0})
    if not settings:
        return
    
    should_notify = False
    if is_new_session and settings.get("notify_on_session_start", True):
        should_notify = True
    elif settings.get("notify_on_every_message", False):
        should_notify = True
    
    if not should_notify:
        return
    
    name = child_name or child.get("name", "Your child")
    if is_new_session:
        title = f"{name} started a Bible session!"
        body = f"{name} is exploring: \"{message[:60]}...\""
    else:
        title = f"{name} is chatting"
        body = f"{name} asked: \"{message[:60]}...\""
    
    await send_push_to_parent(parent_id, title, body, {"child_id": child_id, "type": "chat_activity"})


# ==================== READING NIGHT SETTINGS ====================

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

@router.get("/reading-night")
async def get_reading_night_settings(request: Request):
    """Get Family Reading Night settings for the authenticated parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    parent_id = user["user_id"]
    settings = await db.notification_settings.find_one({"parent_id": parent_id}, {"_id": 0})
    return {
        "enabled": settings.get("reading_night_enabled", False) if settings else False,
        "day": settings.get("reading_night_day", "friday") if settings else "friday",
        "hour": settings.get("reading_night_hour", 19) if settings else 19,
    }


@router.put("/reading-night")
async def update_reading_night_settings(body: ReadingNightSettings, request: Request):
    """Update Family Reading Night settings"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if body.day not in DAYS_OF_WEEK:
        raise HTTPException(status_code=400, detail=f"Invalid day. Use one of: {DAYS_OF_WEEK}")
    if not (0 <= body.hour <= 23):
        raise HTTPException(status_code=400, detail="Hour must be 0-23")

    parent_id = user["user_id"]
    await _get_or_create_settings(parent_id)

    await db.notification_settings.update_one(
        {"parent_id": parent_id},
        {"$set": {
            "reading_night_enabled": body.enabled,
            "reading_night_day": body.day,
            "reading_night_hour": body.hour,
        }}
    )
    return {"status": "success", "message": f"Reading Night set for {body.day.title()}s at {body.hour}:00 UTC"}


@router.get("/reading-night-preview")
async def get_reading_night_preview():
    """Get a preview of this week's story for notification content"""
    from bible_stories import WEEKLY_STORIES
    now = datetime.now(timezone.utc)
    _, week_num, _ = now.isocalendar()
    story_index = (week_num - 1) % len(WEEKLY_STORIES)
    story = WEEKLY_STORIES[story_index]
    return {
        "title": story["title"],
        "reference": story["reference"],
        "theme": story["theme"],
        "summary": story["summary"],
        "icon": story["icon"],
        "colors": story["colors"],
        "week_number": week_num,
    }


async def send_reading_night_reminders():
    """Called hourly by the scheduler. Sends push notifications to families whose reading night matches now."""
    from bible_stories import WEEKLY_STORIES
    now = datetime.now(timezone.utc)
    current_day = DAYS_OF_WEEK[now.weekday()]
    current_hour = now.hour
    _, week_num, _ = now.isocalendar()
    story_index = (week_num - 1) % len(WEEKLY_STORIES)
    story = WEEKLY_STORIES[story_index]

    cursor = db.notification_settings.find({
        "reading_night_enabled": True,
        "reading_night_day": current_day,
        "reading_night_hour": current_hour,
    }, {"_id": 0})

    count = 0
    async for settings in cursor:
        parent_id = settings.get("parent_id")
        if not parent_id:
            continue
        title = "It's Family Reading Night!"
        body = f"This week's story: '{story['title']}' ({story['reference']}) — gather the family for an adventure in {story['theme'].lower()}!"
        await send_push_to_parent(parent_id, title, body, {"type": "reading_night", "route": "/bible-story"})
        count += 1

    if count > 0:
        logger.info(f"Sent {count} reading night reminders for {current_day} {current_hour}:00 UTC")
