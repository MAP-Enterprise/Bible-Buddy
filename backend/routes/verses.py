from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone, timedelta
import random as _random
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["verses"])

db = None
DAILY_VERSES = []
LlmChat = None
UserMessage = None
EMERGENT_LLM_KEY = ""

def init(database, verses, llm_chat_cls, user_msg_cls, llm_key):
    global db, DAILY_VERSES, LlmChat, UserMessage, EMERGENT_LLM_KEY
    db = database
    DAILY_VERSES = verses
    LlmChat = llm_chat_cls
    UserMessage = user_msg_cls
    EMERGENT_LLM_KEY = llm_key


class ChallengeSubmission(BaseModel):
    child_id: str
    answers: List[str]
    difficulty: str = "medium"


def get_todays_verse_index() -> int:
    today = datetime.now(timezone.utc).date()
    day_of_year = today.timetuple().tm_yday
    return day_of_year % len(DAILY_VERSES)


def _generate_blanks(verse_text: str, difficulty: str, seed: int) -> dict:
    words = verse_text.split()
    eligible = [(i, w) for i, w in enumerate(words) if len(w.strip(".,;:!?'\"\u2014")) >= 4]
    blank_counts = {"easy": 2, "medium": 4, "hard": min(6, max(2, len(eligible) // 2))}
    n_blanks = min(blank_counts.get(difficulty, 4), len(eligible))
    rng = _random.Random(seed)
    chosen = sorted(rng.sample(eligible, n_blanks), key=lambda x: x[0])
    answers = []
    display_words = list(words)
    for idx, original_word in chosen:
        clean = original_word.strip(".,;:!?'\"\u2014")
        answers.append(clean.lower())
        display_words[idx] = original_word.replace(clean, "____")
    return {"display_text": " ".join(display_words), "blank_count": len(answers), "answers": answers}


@router.get("/verse-of-the-day")
async def get_verse_of_the_day(age_tier: str = "7-9"):
    """Get the daily Bible verse with an age-appropriate AI explanation"""
    verse_index = get_todays_verse_index()
    verse_data = DAILY_VERSES[verse_index]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cached = await db.daily_verses.find_one({"date": today_str, "age_tier": age_tier}, {"_id": 0})
    if cached:
        return cached

    explanation = ""
    try:
        age_labels = {"4-6": "a 4-6 year old child", "7-9": "a 7-9 year old child", "10-12": "a 10-12 year old", "13-18": "a teenager"}
        age_label = age_labels.get(age_tier, "a child")
        chat_client = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"votd_{today_str}_{age_tier}",
            system_message=f"You are Bible Buddy, a warm and loving Bible guide for children. Explain Bible verses in a way that {age_label} can understand. Keep it to 2-3 short, encouraging sentences."
        ).with_model("openai", "gpt-4o")
        prompt = f'Explain this Bible verse for {age_label}: "{verse_data["verse"]}" ({verse_data["reference"]})'
        explanation = await chat_client.send_message(UserMessage(text=prompt))
    except Exception as e:
        logger.error(f"VOTD AI error: {e}")
        explanation = f"This verse reminds us about God's {verse_data['theme']}. Take a moment to think about what it means to you!"

    result = {
        "date": today_str, "verse": verse_data["verse"], "reference": verse_data["reference"],
        "theme": verse_data["theme"], "age_tier": age_tier, "explanation": explanation,
    }
    await db.daily_verses.insert_one({**result, "created_at": datetime.now(timezone.utc)})
    return result


@router.get("/verse-challenge")
async def get_verse_challenge(age_tier: str = "7-9", difficulty: str = "auto"):
    """Get today's verse memory challenge"""
    verse_index = get_todays_verse_index()
    verse_data = DAILY_VERSES[verse_index]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if difficulty == "auto":
        difficulty = {"4-6": "easy", "7-9": "medium", "10-12": "medium", "13-18": "hard"}.get(age_tier, "medium")
    seed = hash(f"{today_str}_{difficulty}")
    blanks = _generate_blanks(verse_data["verse"], difficulty, seed)
    return {
        "date": today_str, "reference": verse_data["reference"], "theme": verse_data["theme"],
        "difficulty": difficulty, "display_text": blanks["display_text"],
        "blank_count": blanks["blank_count"], "full_verse": verse_data["verse"],
    }


@router.post("/verse-challenge/submit")
async def submit_verse_challenge(body: ChallengeSubmission):
    """Submit answers for today's verse challenge and get score"""
    verse_index = get_todays_verse_index()
    verse_data = DAILY_VERSES[verse_index]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed = hash(f"{today_str}_{body.difficulty}")
    blanks = _generate_blanks(verse_data["verse"], body.difficulty, seed)
    correct_answers = blanks["answers"]
    user_answers = [a.strip().lower() for a in body.answers]
    correct = 0
    results = []
    for i, expected in enumerate(correct_answers):
        given = user_answers[i] if i < len(user_answers) else ""
        is_correct = given == expected
        if is_correct:
            correct += 1
        results.append({"expected": expected, "given": given, "correct": is_correct})
    total = len(correct_answers)
    score = round((correct / total) * 100) if total > 0 else 0
    if score == 100:
        message = "Perfect! You know this verse by heart!"
    elif score >= 75:
        message = "Amazing work! You almost have it memorized!"
    elif score >= 50:
        message = "Great effort! Keep practicing and you'll get it!"
    else:
        message = "Good try! Read the verse again and try tomorrow!"
    child_id = body.child_id
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    existing = await db.verse_challenges.find_one({"child_id": child_id, "date": today_str}, {"_id": 0})
    prev = await db.verse_challenges.find_one({"child_id": child_id, "date": yesterday_str}, {"_id": 0})
    current_streak = (prev.get("streak", 0) if prev else 0) + (0 if existing else 1)
    if existing:
        current_streak = existing.get("streak", 1)
        if score > existing.get("score", 0):
            await db.verse_challenges.update_one(
                {"child_id": child_id, "date": today_str},
                {"$set": {"score": score, "difficulty": body.difficulty}}
            )
    else:
        await db.verse_challenges.insert_one({
            "child_id": child_id, "date": today_str, "score": score,
            "difficulty": body.difficulty, "streak": current_streak,
            "reference": verse_data["reference"], "created_at": datetime.now(timezone.utc),
        })
    return {
        "score": score, "correct": correct, "total": total, "results": results,
        "message": message, "streak": current_streak, "full_verse": verse_data["verse"],
        "reference": verse_data["reference"],
    }


@router.get("/verse-challenge/stats/{child_id}")
async def get_challenge_stats(child_id: str):
    """Get challenge statistics for a child"""
    challenges = await db.verse_challenges.find(
        {"child_id": child_id}, {"_id": 0}
    ).sort("date", -1).to_list(365)
    if not challenges:
        return {"total_played": 0, "current_streak": 0, "best_streak": 0, "average_score": 0, "perfect_scores": 0, "recent": []}
    total = len(challenges)
    avg_score = round(sum(c.get("score", 0) for c in challenges) / total)
    perfect = sum(1 for c in challenges if c.get("score", 0) == 100)
    today = datetime.now(timezone.utc).date()
    current_streak = 0
    for i in range(365):
        check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if any(c["date"] == check_date for c in challenges):
            current_streak += 1
        else:
            break
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
    return {
        "total_played": total, "current_streak": current_streak, "best_streak": best_streak,
        "average_score": avg_score, "perfect_scores": perfect, "recent": challenges[:7],
    }
