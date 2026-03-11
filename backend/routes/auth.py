from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])

db = None
get_current_user = None

def init(database, auth_func):
    global db, get_current_user
    db = database
    get_current_user = auth_func


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/register")
async def register_parent(req: RegisterRequest, response: Response):
    """Register a new parent account with email/password"""
    existing = await db.parents.find_one({"email": req.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    import bcrypt
    password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    
    user_id = f"parent_{uuid.uuid4().hex[:12]}"
    parent = {
        "user_id": user_id,
        "email": req.email.lower(),
        "name": req.name,
        "password_hash": password_hash,
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.parents.insert_one(parent)
    
    session_token = f"st_{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"user_id": user_id, "name": req.name, "email": req.email.lower(), "token": session_token}


@router.post("/auth/login")
async def login_parent(req: LoginRequest, response: Response):
    """Login with email/password"""
    import bcrypt
    parent = await db.parents.find_one({"email": req.email.lower()}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not parent.get("password_hash"):
        raise HTTPException(status_code=401, detail="Account uses social login")
    
    if not bcrypt.checkpw(req.password.encode(), parent["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    session_token = f"st_{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "user_id": parent["user_id"],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"user_id": parent["user_id"], "name": parent["name"], "email": parent["email"], "token": session_token}


@router.get("/auth/session")
async def exchange_session(session_id: str, response: Response):
    """Exchange Emergent session_id for user data"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=401, detail="Invalid session")
                data = await resp.json()
        
        existing_parent = await db.parents.find_one({"email": data["email"]}, {"_id": 0})
        
        if existing_parent:
            user_id = existing_parent["user_id"]
            await db.parents.update_one(
                {"user_id": user_id},
                {"$set": {"name": data["name"], "picture": data.get("picture")}}
            )
        else:
            user_id = f"parent_{uuid.uuid4().hex[:12]}"
            parent = {
                "user_id": user_id,
                "email": data["email"],
                "name": data["name"],
                "picture": data.get("picture"),
                "created_at": datetime.now(timezone.utc)
            }
            await db.parents.insert_one(parent)
        
        session_token = data.get("session_token", f"st_{uuid.uuid4().hex}")
        session = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
            "created_at": datetime.now(timezone.utc)
        }
        await db.user_sessions.insert_one(session)
        
        response.set_cookie(
            key="session_token", value=session_token,
            httponly=True, secure=True, samesite="none",
            max_age=7*24*60*60, path="/"
        )
        
        parent_data = await db.parents.find_one({"user_id": user_id}, {"_id": 0})
        return parent_data
        
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/me")
async def get_current_user_endpoint(request: Request):
    """Get current authenticated user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return safe_user


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}
