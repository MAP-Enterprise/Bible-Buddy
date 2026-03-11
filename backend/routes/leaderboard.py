from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["leaderboard"])

db = None
get_current_user = None

def init(database, auth_func):
    global db, get_current_user
    db = database
    get_current_user = auth_func


@router.get("/leaderboard")
async def get_family_leaderboard(request: Request):
    """Get leaderboard for all children under the authenticated parent"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    children = await db.children.find(
        {"parent_id": user["user_id"]}, {"_id": 0}
    ).to_list(20)
    
    if not children:
        return {"leaderboard": [], "family_stats": {}}
    
    today = datetime.now(timezone.utc).date()
    leaderboard = []
    
    for child in children:
        child_id = child["child_id"]
        challenges = await db.verse_challenges.find(
            {"child_id": child_id}, {"_id": 0}
        ).sort("date", -1).to_list(365)
        
        total_played = len(challenges)
        avg_score = round(sum(c.get("score", 0) for c in challenges) / total_played) if total_played else 0
        perfect_scores = sum(1 for c in challenges if c.get("score", 0) == 100)
        
        # Current streak
        current_streak = 0
        for i in range(365):
            check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if any(c["date"] == check_date for c in challenges):
                current_streak += 1
            else:
                break
        
        # Best streak
        best_streak = 0
        streak = 0
        all_dates = sorted(set(c["date"] for c in challenges))
        for i, d in enumerate(all_dates):
            if i == 0:
                streak = 1
            else:
                prev = datetime.strptime(all_dates[i-1], "%Y-%m-%d").date()
                curr = datetime.strptime(d, "%Y-%m-%d").date()
                streak = streak + 1 if (curr - prev).days == 1 else 1
            best_streak = max(best_streak, streak)
        
        # Total messages
        sessions = await db.chat_sessions.find({"child_id": child_id}, {"_id": 0}).to_list(1000)
        total_messages = sum(len(s.get("messages", [])) for s in sessions)
        
        leaderboard.append({
            "child_id": child_id,
            "name": child.get("name", "Unknown"),
            "age_tier": child.get("age_tier", "7-9"),
            "challenge_stats": {
                "total_played": total_played,
                "average_score": avg_score,
                "perfect_scores": perfect_scores,
                "current_streak": current_streak,
                "best_streak": best_streak,
            },
            "chat_stats": {
                "total_conversations": len(sessions),
                "total_messages": total_messages,
            },
        })
    
    # Sort by avg score, then streak
    leaderboard.sort(key=lambda x: (x["challenge_stats"]["average_score"], x["challenge_stats"]["current_streak"]), reverse=True)
    
    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    # Family aggregate stats
    family_stats = {
        "total_children": len(children),
        "total_challenges_completed": sum(e["challenge_stats"]["total_played"] for e in leaderboard),
        "family_average_score": round(sum(e["challenge_stats"]["average_score"] for e in leaderboard) / len(leaderboard)) if leaderboard else 0,
        "total_perfect_scores": sum(e["challenge_stats"]["perfect_scores"] for e in leaderboard),
    }
    
    return {"leaderboard": leaderboard, "family_stats": family_stats}
