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
WEEKLY_STORIES = []
LlmChat = None
UserMessage = None
EMERGENT_LLM_KEY = ""

def init(database, verses, llm_chat_cls, user_msg_cls, llm_key):
    global db, DAILY_VERSES, LlmChat, UserMessage, EMERGENT_LLM_KEY, WEEKLY_STORIES
    db = database
    DAILY_VERSES = verses
    LlmChat = llm_chat_cls
    UserMessage = user_msg_cls
    EMERGENT_LLM_KEY = llm_key
    from bible_stories import WEEKLY_STORIES as ws
    WEEKLY_STORIES = ws


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


def _get_week_number() -> int:
    """Get ISO week number (1-52)"""
    return datetime.now(timezone.utc).isocalendar()[1]


@router.get("/story-of-the-week")
async def get_story_of_the_week(age_tier: str = "7-9"):
    """Get this week's Bible story with AI-generated narrative and discussion questions"""
    week_num = _get_week_number()
    story_index = (week_num - 1) % len(WEEKLY_STORIES)
    story_data = WEEKLY_STORIES[story_index]
    today = datetime.now(timezone.utc)
    week_key = f"{today.year}-W{week_num:02d}"

    # Check cache
    cached = await db.weekly_stories.find_one(
        {"week_key": week_key, "age_tier": age_tier}, {"_id": 0}
    )
    if cached:
        return cached

    # Generate age-adapted narrative + discussion questions
    narrative = ""
    discussion_questions = []
    try:
        age_labels = {
            "4-6": "a 4-6 year old (very simple words, short sentences, playful and warm)",
            "7-9": "a 7-9 year old (clear language, engaging storytelling, relatable examples)",
            "10-12": "a 10-12 year old (more detail, deeper meaning, character motivations)",
            "13-18": "a teenager (thoughtful, nuanced, real-life application, respectful tone)",
        }
        age_label = age_labels.get(age_tier, "a child")

        chat_client = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"story_{week_key}_{age_tier}",
            system_message=(
                f"You are Bible Buddy, a master storyteller who brings Bible stories to life for {age_label}. "
                "Tell the story in an engaging, vivid narrative style. Use dialogue where possible. "
                "Keep it theologically accurate and faithful to Scripture. "
                "After the story, provide exactly 3 family discussion questions.\n\n"
                "FORMAT:\n[STORY]\n(your narrative here, 4-8 paragraphs)\n\n"
                "[QUESTIONS]\n1. (question)\n2. (question)\n3. (question)"
            ),
        ).with_model("openai", "gpt-4o-mini")

        prompt = (
            f"Tell the Bible story: \"{story_data['title']}\" ({story_data['reference']}). "
            f"Characters: {', '.join(story_data['characters'])}. "
            f"Summary: {story_data['summary']}"
        )
        response = await chat_client.send_message(UserMessage(text=prompt))

        # Parse response
        if "[QUESTIONS]" in response:
            parts = response.split("[QUESTIONS]")
            narrative = parts[0].replace("[STORY]", "").strip()
            q_text = parts[1].strip()
            discussion_questions = [
                q.strip().lstrip("0123456789.").strip()
                for q in q_text.split("\n") if q.strip() and any(c.isalpha() for c in q)
            ][:3]
        else:
            narrative = response.replace("[STORY]", "").strip()
            discussion_questions = [
                f"What do you think {story_data['characters'][0]} was feeling in this story?",
                f"How does this story teach us about {story_data['theme'].lower()}?",
                "How can we apply this story's lesson in our lives today?",
            ]
    except Exception as e:
        logger.error(f"Story generation error: {e}")
        narrative = story_data["summary"]
        discussion_questions = [
            f"What is the main lesson from this story?",
            f"Which character do you relate to most and why?",
            "What would you do differently if you were in this story?",
        ]

    result = {
        "week_key": week_key,
        "week_number": week_num,
        "title": story_data["title"],
        "reference": story_data["reference"],
        "characters": story_data["characters"],
        "theme": story_data["theme"],
        "icon": story_data["icon"],
        "colors": story_data["colors"],
        "summary": story_data["summary"],
        "narrative": narrative,
        "discussion_questions": discussion_questions,
        "age_tier": age_tier,
    }

    await db.weekly_stories.insert_one({**result, "created_at": datetime.now(timezone.utc)})
    return result


# ==================== STORY PROGRESS TRACKER ====================

BADGE_DEFINITIONS = [
    # Total stories read milestones
    {"id": "first_story", "name": "First Story", "icon": "book-outline", "color": "#4ECDC4", "description": "Read your first Bible story!", "type": "total", "threshold": 1},
    {"id": "getting_started", "name": "Getting Started", "icon": "library-outline", "color": "#6C5CE7", "description": "Read 3 Bible stories", "type": "total", "threshold": 3},
    {"id": "story_explorer", "name": "Story Explorer", "icon": "compass-outline", "color": "#FF6B6B", "description": "Read 5 Bible stories", "type": "total", "threshold": 5},
    {"id": "faithful_reader", "name": "Faithful Reader", "icon": "heart", "color": "#E056A0", "description": "Read 10 Bible stories", "type": "total", "threshold": 10},
    {"id": "bible_scholar", "name": "Bible Scholar", "icon": "school", "color": "#FFD93D", "description": "Read 25 Bible stories", "type": "total", "threshold": 25},
    {"id": "story_master", "name": "Story Master", "icon": "star", "color": "#FF8E53", "description": "Read all 52 Bible stories!", "type": "total", "threshold": 52},
    # Streak milestones
    {"id": "week_warrior", "name": "Week Warrior", "icon": "flash", "color": "#0984E3", "description": "2-week reading streak!", "type": "streak", "threshold": 2},
    {"id": "steady_reader", "name": "Steady Reader", "icon": "timer", "color": "#00B894", "description": "4-week reading streak!", "type": "streak", "threshold": 4},
    {"id": "devoted_family", "name": "Devoted Family", "icon": "people", "color": "#6C5CE7", "description": "8-week reading streak!", "type": "streak", "threshold": 8},
    {"id": "unstoppable", "name": "Unstoppable", "icon": "rocket", "color": "#E17055", "description": "12-week reading streak!", "type": "streak", "threshold": 12},
    {"id": "half_year_hero", "name": "Half Year Hero", "icon": "trophy", "color": "#FDCB6E", "description": "26-week reading streak!", "type": "streak", "threshold": 26},
    {"id": "story_champion", "name": "Story Champion", "icon": "medal", "color": "#FF6348", "description": "Full year of stories!", "type": "streak", "threshold": 52},
]


class MarkReadRequest(BaseModel):
    child_id: str
    week_key: str
    story_title: str
    story_reference: str = ""


def _compute_streak(week_keys: list) -> dict:
    """Compute current and best reading streak from a list of week_keys like '2026-W11'"""
    if not week_keys:
        return {"current_streak": 0, "best_streak": 0}

    # Parse week keys into (year, week) tuples and sort
    parsed = []
    for wk in week_keys:
        try:
            parts = wk.split("-W")
            parsed.append((int(parts[0]), int(parts[1])))
        except (ValueError, IndexError):
            continue
    parsed = sorted(set(parsed))
    if not parsed:
        return {"current_streak": 0, "best_streak": 0}

    # Calculate streaks
    best_streak = 1
    current_run = 1
    for i in range(1, len(parsed)):
        prev_y, prev_w = parsed[i - 1]
        cur_y, cur_w = parsed[i]
        # Check if consecutive week
        if (cur_y == prev_y and cur_w == prev_w + 1) or \
           (cur_w == 1 and prev_w >= 52 and cur_y == prev_y + 1):
            current_run += 1
        else:
            current_run = 1
        best_streak = max(best_streak, current_run)

    # Current streak: count backwards from the most recent entry
    now = datetime.now(timezone.utc)
    current_year, current_week, _ = now.isocalendar()
    last_y, last_w = parsed[-1]

    # Allow current week or last week to count as active
    if (last_y, last_w) == (current_year, current_week) or \
       (last_y, last_w) == (current_year, current_week - 1) or \
       (current_week == 1 and last_w >= 52 and last_y == current_year - 1):
        current_streak = 1
        for i in range(len(parsed) - 2, -1, -1):
            py, pw = parsed[i]
            ny, nw = parsed[i + 1]
            if (ny == py and nw == pw + 1) or (nw == 1 and pw >= 52 and ny == py + 1):
                current_streak += 1
            else:
                break
    else:
        current_streak = 0

    return {"current_streak": current_streak, "best_streak": best_streak}


def _compute_badges(total_read: int, best_streak: int, current_streak: int) -> list:
    """Determine which badges have been earned"""
    earned = []
    for badge in BADGE_DEFINITIONS:
        if badge["type"] == "total" and total_read >= badge["threshold"]:
            earned.append({**badge, "earned": True})
        elif badge["type"] == "streak" and best_streak >= badge["threshold"]:
            earned.append({**badge, "earned": True})
    return earned


@router.post("/story-progress/mark-read")
async def mark_story_read(body: MarkReadRequest):
    """Mark a story as read for a child"""
    existing = await db.story_progress.find_one(
        {"child_id": body.child_id, "week_key": body.week_key}, {"_id": 0}
    )
    if existing:
        return {"status": "already_read", "message": "Story already marked as read!"}

    await db.story_progress.insert_one({
        "child_id": body.child_id,
        "week_key": body.week_key,
        "story_title": body.story_title,
        "story_reference": body.story_reference,
        "marked_at": datetime.now(timezone.utc),
    })

    # Compute updated progress
    all_progress = await db.story_progress.find(
        {"child_id": body.child_id}, {"_id": 0}
    ).sort("marked_at", -1).to_list(100)

    total_read = len(all_progress)
    week_keys = [p["week_key"] for p in all_progress]
    streaks = _compute_streak(week_keys)
    badges = _compute_badges(total_read, streaks["best_streak"], streaks["current_streak"])
    new_badges = [b for b in badges if b["threshold"] == total_read or b["threshold"] == streaks["best_streak"]]

    return {
        "status": "marked",
        "message": "Great job reading this week's story!",
        "total_read": total_read,
        "current_streak": streaks["current_streak"],
        "best_streak": streaks["best_streak"],
        "new_badges": new_badges,
        "total_badges": len(badges),
    }


@router.get("/story-progress/{child_id}")
async def get_story_progress(child_id: str):
    """Get complete reading progress for a child"""
    all_progress = await db.story_progress.find(
        {"child_id": child_id}, {"_id": 0}
    ).sort("marked_at", -1).to_list(100)

    total_read = len(all_progress)
    week_keys = [p["week_key"] for p in all_progress]
    streaks = _compute_streak(week_keys)
    badges = _compute_badges(total_read, streaks["best_streak"], streaks["current_streak"])

    # All badge definitions with earned status
    all_badges = []
    earned_ids = {b["id"] for b in badges}
    for badge in BADGE_DEFINITIONS:
        all_badges.append({**badge, "earned": badge["id"] in earned_ids})

    return {
        "total_read": total_read,
        "total_stories": 52,
        "current_streak": streaks["current_streak"],
        "best_streak": streaks["best_streak"],
        "badges_earned": len(badges),
        "total_badges": len(BADGE_DEFINITIONS),
        "badges": all_badges,
        "recent_reads": all_progress[:10],
        "read_week_keys": week_keys,
    }
