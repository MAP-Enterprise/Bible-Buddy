# Bible Buddy - Product Requirements Document

## Original Problem Statement
Build a mobile application called "Bible Buddy" — an interactive app for children to ask questions about the Bible and receive safe, age-appropriate answers.

## Architecture
- **Frontend:** Expo (React Native) with TypeScript, expo-router, zustand, expo-av
- **Backend:** FastAPI with modular APIRouter structure, motor (async MongoDB)
- **Database:** MongoDB
- **AI:** OpenAI GPT-4o-mini via Emergent LLM Key
- **TTS:** ElevenLabs
- **STT:** Deepgram (REST API)
- **Email:** Resend

## What's Been Implemented

### Core Features (Complete)
- Full JWT authentication system (sign-up, sign-in, sessions)
- Multiple child profile management per parent
- Age-tiered AI chat (4-6, 7-9, 10-12, 13-18)
- Knowledge base with 56 pre-loaded questions × 4 age tiers = 224 cached answers
- Content safety filtering
- Adaptive user profiling (learns from conversations)
- Featured teacher wisdom integration

### Voice Features (Complete)
- Text-to-Speech via ElevenLabs (10 voice options)
- Speech-to-Text via Deepgram
- Voice selection during onboarding and in parent dashboard

### Engagement Features (Complete)
- 365-day Verse of the Day system
- Verse Memory Challenge (fill-in-the-blank game)
- Family Leaderboard
- Bible Story of the Week (52 stories, AI-generated narratives, discussion questions)
- Story Progress Tracker (mark stories read, 12 achievement badges, reading streaks, progress bar)
- **Family Reading Night Reminder** (weekly push notification, configurable day/time, story preview, home screen banner)

### Parent Features (Complete)
- Parent Dashboard (manage children, view stats, notifications, reading progress, reading night settings)
- COPPA-compliant parental consent flow
- Challenge statistics per child
- Notification system (push + email via Resend)
- Resend domain verification guide

### Architecture (Complete)
- Backend refactored from monolithic server.py to modular APIRouter files
- KB pre-warming at startup for instant responses
- Hourly reading night reminder scheduler

## Key API Endpoints
- `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`
- `POST /api/chat`, `POST /api/voice-chat`
- `GET /api/verse-of-the-day`, `GET /api/verse-challenge`, `POST /api/verse-challenge/submit`
- `GET /api/story-of-the-week`
- `POST /api/story-progress/mark-read`, `GET /api/story-progress/{child_id}`
- `GET /api/notifications/reading-night`, `PUT /api/notifications/reading-night`, `GET /api/notifications/reading-night-preview`
- `GET /api/family-leaderboard`
- `GET /api/children/{parent_id}`, `POST /api/children`, `POST /api/children/consent`
- `GET /api/voices`, `POST /api/voices/preview`
- `GET /api/health`

## DB Collections
- `parents`, `children`, `user_sessions`
- `sessions` (chat), `user_profiles`, `safety_logs`
- `daily_verses`, `kb_age_cache`, `age_adapted_kb_cache`
- `verse_challenges`, `weekly_stories`, `story_progress`
- `notification_settings` (includes reading_night_enabled, reading_night_day, reading_night_hour)
- `knowledge_base`, `teachers`

## Prioritized Backlog

### P1 - Full QA Testing
- Comprehensive testing across all major flows

### P1 - Implement True Streaming
- Upgrade AI chat responses to word-by-word streaming via SSE

### P2 - Refine Parent Dashboard UI
- Break down large components into smaller sub-components

### P3 - Internationalization (i18n)
- Add multi-language support

## File Structure
```
/app/backend/
├── server.py (orchestrator + schedulers)
├── bible_stories.py (52 weekly stories)
├── bible_verses.py (365 daily verses)
├── routes/ (auth, children, dashboard, emails, kb, notifications, sessions, teachers, verses)
└── audio_cache/

/app/frontend/
├── app/ (index, chat, bible-story, verse-challenge, leaderboard, parent-dashboard, sign-in, sign-up, onboarding)
├── components/
├── contexts/ (AuthContext)
├── helpers/ (storage)
└── hooks/
```
