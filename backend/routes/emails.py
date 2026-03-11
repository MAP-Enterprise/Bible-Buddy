from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import logging
import asyncio
import os
import resend

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])

# Will be set by server.py on startup
db = None
get_current_user = None

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

def init(database, auth_func):
    global db, get_current_user
    db = database
    get_current_user = auth_func


def _build_weekly_summary_html(parent_name: str, children_data: list) -> str:
    """Build a beautiful HTML email for the weekly summary"""
    children_sections = ""
    for child in children_data:
        topics_html = ""
        for topic in child.get("topics", [])[:5]:
            topics_html += f'<span style="display:inline-block;background:#EDE9FE;color:#6C5CE7;padding:4px 12px;border-radius:12px;margin:4px;font-size:14px;font-weight:600;">{topic}</span>'
        if not topics_html:
            topics_html = '<span style="color:#999;font-size:14px;">No topics explored yet</span>'

        children_sections += f"""
        <div style="background:#fff;border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="display:flex;align-items:center;margin-bottom:16px;">
                <div style="width:48px;height:48px;border-radius:24px;background:linear-gradient(135deg,#FF6B6B,#FF8E53);display:flex;align-items:center;justify-content:center;color:#fff;font-size:24px;font-weight:800;margin-right:14px;">{child['name'][0].upper()}</div>
                <div>
                    <h3 style="margin:0;font-size:18px;color:#2D3436;">{child['name']}</h3>
                    <p style="margin:2px 0 0;font-size:13px;color:#999;">Age: {child.get('age_tier', '?')} years</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;margin-bottom:16px;">
                <div style="flex:1;background:#FFE8E8;border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:28px;font-weight:800;color:#FF6B6B;">{child.get('conversations', 0)}</div>
                    <div style="font-size:12px;color:#FF6B6B;font-weight:600;">Conversations</div>
                </div>
                <div style="flex:1;background:#E0F7F5;border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:28px;font-weight:800;color:#4ECDC4;">{child.get('messages', 0)}</div>
                    <div style="font-size:12px;color:#4ECDC4;font-weight:600;">Messages</div>
                </div>
            </div>
            <div>
                <p style="font-size:14px;font-weight:700;color:#636E72;margin-bottom:8px;">Topics Explored</p>
                {topics_html}
            </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0;padding:0;background:#F8F9FF;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="max-width:600px;margin:0 auto;padding:20px;">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:24px;padding:32px;text-align:center;margin-bottom:24px;">
                <div style="font-size:48px;margin-bottom:8px;">&#128214;</div>
                <h1 style="color:#fff;margin:0;font-size:28px;">Bible Buddy</h1>
                <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:16px;">Weekly Summary</p>
            </div>
            
            <div style="background:#fff;border-radius:16px;padding:24px;margin-bottom:20px;">
                <h2 style="margin:0 0 8px;font-size:22px;color:#2D3436;">Hi {parent_name}! &#128075;</h2>
                <p style="margin:0;color:#636E72;font-size:15px;line-height:24px;">Here's what your children explored in Bible Buddy this week.</p>
            </div>
            
            {children_sections}
            
            <div style="text-align:center;padding:24px;color:#AAA;font-size:13px;">
                <p>You're receiving this because you have weekly summaries enabled in Bible Buddy.</p>
                <p style="margin-top:8px;">&#x2764;&#xfe0f; Keep encouraging your children's faith journey!</p>
            </div>
        </div>
    </body>
    </html>
    """


async def _gather_weekly_stats(parent_id: str) -> list:
    """Gather stats for all children of a parent for the past week"""
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    children = await db.children.find({"parent_id": parent_id}, {"_id": 0}).to_list(20)
    results = []
    
    for child in children:
        child_id = child["child_id"]
        
        # Count conversations and messages this week
        sessions = await db.chat_sessions.find(
            {"child_id": child_id, "updated_at": {"$gte": one_week_ago}},
            {"_id": 0, "messages": 1}
        ).to_list(100)
        
        total_convs = len(sessions)
        total_msgs = sum(len(s.get("messages", [])) for s in sessions)
        
        # Get topics from user profile
        profile = await db.user_profiles.find_one({"child_id": child_id}, {"_id": 0})
        topics = profile.get("topics_of_interest", [])[:5] if profile else []
        
        results.append({
            "name": child.get("name", "Unknown"),
            "age_tier": child.get("age_tier", "?"),
            "conversations": total_convs,
            "messages": total_msgs,
            "topics": topics,
        })
    
    return results


async def send_weekly_summary_email(parent_id: str):
    """Send weekly summary email to a specific parent"""
    logger.info(f"send_weekly_summary_email called for parent_id={parent_id}, RESEND_API_KEY set={bool(RESEND_API_KEY)}")
    if not RESEND_API_KEY:
        logger.warning("Resend API key not configured, skipping email")
        return False
    
    # Use 'parents' collection (not 'users')
    parent = await db.parents.find_one({"user_id": parent_id}, {"_id": 0})
    logger.info(f"Parent found: {bool(parent)}")
    if not parent:
        return False
    
    # Check if email summaries are enabled
    settings = await db.notification_settings.find_one({"parent_id": parent_id}, {"_id": 0})
    if settings and not settings.get("email_weekly_summary", True):
        logger.info("Email summaries disabled for this parent")
        return False
    
    children_data = await _gather_weekly_stats(parent_id)
    logger.info(f"Children data count: {len(children_data)}")
    if not children_data:
        return False
    
    html = _build_weekly_summary_html(parent.get("name", "Parent"), children_data)
    
    params = {
        "from": SENDER_EMAIL,
        "to": [parent["email"]],
        "subject": "Bible Buddy - Your Child's Weekly Faith Journey \u2728",
        "html": html,
    }
    
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Weekly summary sent to {parent['email']}: {result}")
        return True
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send weekly summary to {parent['email']}: {error_msg}")
        # Re-raise with useful context for API callers
        raise Exception(f"Email send failed: {error_msg}")


async def send_all_weekly_summaries():
    """Send weekly summary emails to ALL parents who have it enabled"""
    logger.info("Starting weekly summary email batch...")
    
    # Find all parents
    parents = await db.parents.find({}, {"_id": 0, "user_id": 1, "email": 1}).to_list(1000)
    
    sent_count = 0
    for parent in parents:
        try:
            success = await send_weekly_summary_email(parent["user_id"])
            if success:
                sent_count += 1
        except Exception as e:
            logger.error(f"Error sending summary to {parent.get('email')}: {e}")
    
    logger.info(f"Weekly summary batch complete: {sent_count}/{len(parents)} sent")
    return sent_count


@router.post("/send-weekly-summary")
async def trigger_weekly_summary(request: Request):
    """Manually trigger weekly summary for the authenticated parent (for testing)"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        success = await send_weekly_summary_email(user["user_id"])
        if success:
            return {"status": "success", "message": f"Weekly summary sent to {user['email']}"}
        else:
            return {"status": "skipped", "message": "No children found or email summaries disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/preview-weekly-summary")
async def preview_weekly_summary(request: Request):
    """Preview the weekly summary email HTML (for testing)"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = await db.parents.find_one({"user_id": user["user_id"]}, {"_id": 0})
    children_data = await _gather_weekly_stats(user["user_id"])
    html = _build_weekly_summary_html(user_data.get("name", "Parent") if user_data else "Parent", children_data)
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.get("/domain-status")
async def get_domain_verification_status(request: Request):
    """Check Resend domain verification status and provide setup instructions"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if custom domain is configured
    sender = SENDER_EMAIL
    is_default = sender == "onboarding@resend.dev" or "resend.dev" in sender
    
    domain_info = {
        "current_sender": sender,
        "is_verified": not is_default,
        "using_default": is_default,
    }
    
    if is_default:
        domain_info["setup_instructions"] = {
            "overview": "To send emails from your own domain (e.g., hello@yourdomain.com), follow these steps:",
            "steps": [
                "1. Go to https://resend.com/domains and click 'Add Domain'",
                "2. Enter your domain name (e.g., yourdomain.com)",
                "3. Resend will provide DNS records (MX, TXT, DKIM) to add to your domain registrar",
                "4. Add the DNS records in your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)",
                "5. Click 'Verify' in Resend — DNS propagation may take up to 72 hours",
                "6. Once verified, update SENDER_EMAIL in the backend .env file",
            ],
            "required_dns_records": [
                {"type": "MX", "purpose": "Routes email through Resend"},
                {"type": "TXT (SPF)", "purpose": "Authorizes Resend to send on your behalf"},
                {"type": "DKIM (CNAME)", "purpose": "Cryptographically signs emails for deliverability"},
            ],
            "resend_dashboard_url": "https://resend.com/domains",
        }
    else:
        domain_info["message"] = f"Emails are being sent from {sender}. Domain is verified and active."
    
    # Attempt to check domain via Resend API
    if RESEND_API_KEY and not is_default:
        try:
            resend.api_key = RESEND_API_KEY
            domains = resend.Domains.list()
            domain_info["resend_domains"] = [
                {"name": d.name, "status": d.status, "created_at": str(d.created_at)}
                for d in (domains.data if hasattr(domains, 'data') else [])
            ]
        except Exception as e:
            logger.error(f"Resend domain check error: {e}")
            domain_info["resend_api_error"] = str(e)
    
    return domain_info

