# Bible Buddy - Product Requirements Document

## Original Problem Statement
An interactive mobile application for children to ask questions about the Bible and receive safe, age-appropriate answers, featuring both text and voice-based interaction.

## User Personas
- **Children (4-18):** Primary users who interact with Bible Buddy to ask faith-based questions
- **Parents:** Manage child profiles, monitor conversations, set safety preferences, view leaderboards

## Architecture
- **Backend:** FastAPI (modular routers), MongoDB, GPT-4o-mini (via Emergent LLM Key)
- **Frontend:** Expo (React Native), TypeScript, expo-router
- **Integrations:** OpenAI, ElevenLabs, Deepgram, Resend (email), Expo Push Notifications
- **Collections:** parents, children, chat_sessions, user_profiles, notification_settings, knowledge_base, teachers, safety_logs, daily_verses, kb_age_cache, verse_challenges, consent_log

## Backend Structure (Refactored)
```
backend/
  server.py              — App setup, middleware, chat/voice/TTS, startup (1594 lines)
  bible_verses.py        — 365 daily verses by monthly theme
  routes/
    auth.py              — Register, login, session, me, logout
    children.py          — CRUD, COPPA consent, voice update
    dashboard.py         — Stats, conversations, KB, teachers, sessions
    verses.py            — Verse-of-the-day, memory challenge
    leaderboard.py       — Family leaderboard
    notifications.py     — Push notifications
    emails.py            — Weekly summaries, domain verification
```

## Completed Features
- [x] Core AI conversation engine, safety filtering, knowledge base (56 questions)
- [x] Voice I/O (STT via Deepgram + TTS via ElevenLabs)
- [x] Adaptive AI coaching with user profiles
- [x] Teacher wisdom integration (Selman, Ike, Furtick, Shirer)
- [x] 365 Verse of the Day with age-appropriate explanations
- [x] KB Pre-warming (224 age-adapted answers, all 4 tiers)
- [x] Full Auth System (register, login, JWT sessions)
- [x] Multi-child Profile Management
- [x] Parent Dashboard (stats, conversations, child selector)
- [x] Push Notifications + Weekly Email Summaries (Resend)
- [x] AI Theological Realignment (Scripture-rooted)
- [x] Voice Selection (10 voices, onboarding + dashboard)
- [x] Verse Memory Challenge (fill-in-the-blank, 3 difficulties, streaks)
- [x] Persistent Conversation History
- [x] **Challenge Stats in Parent Dashboard** — Mar 2026
- [x] **COPPA-Compliant Parental Consent** (name verification, audit log, policy endpoint) — Mar 2026
- [x] **Modular Router Refactor** (server.py 2296→1594 lines, 7 route modules) — Mar 2026
- [x] **Family Leaderboard** (ranked children, family aggregate stats) — Mar 2026
- [x] **Resend Domain Verification** (status check, DNS setup instructions) — Mar 2026

## Key API Endpoints
- Auth: POST /api/auth/register, /login, /logout, GET /me
- Children: POST/GET/PUT /api/children, PATCH voice, POST consent
- Chat: POST /api/chat
- Dashboard: GET /api/dashboard/stats/{id}, /conversations/{id}
- Verses: GET /api/verse-of-the-day, /verse-challenge, POST /submit, GET /stats
- Leaderboard: GET /api/leaderboard
- COPPA: GET /api/coppa-policy
- Email: GET /api/email/domain-status

## P1 (Next)
- True streaming responses (SSE word-by-word)
- Daily reward/badge system for challenge streaks
- Full QA on iOS/Android native

## P2 (Future)
- Production deployment
- Shareable results cards (social sharing)
- Multi-language Bible support
