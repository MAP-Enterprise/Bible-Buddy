# Bible Buddy - Product Requirements Document

## Original Problem Statement
An interactive mobile application for children to ask questions about the Bible and receive safe, age-appropriate answers, featuring both text and voice-based interaction.

## User Personas
- **Children (4-18):** Primary users who interact with Bible Buddy to ask faith-based questions
- **Parents:** Manage child profiles, monitor conversations, and set safety preferences

## Core Requirements
- Age-appropriate AI responses (4 tiers: 4-6, 7-9, 10-12, 13-18)
- Voice input (STT via Deepgram) and voice output (TTS via ElevenLabs)
- Safety/content filtering layer
- Knowledge base for instant answers (56 questions)
- Adaptive AI coaching with user profile tracking
- Teacher wisdom integration (Selman, Ike, Furtick, Shirer)

## Architecture
- **Backend:** FastAPI, MongoDB, GPT-4o-mini (via Emergent LLM Key)
- **Frontend:** Expo (React Native), TypeScript, expo-router
- **Integrations:** OpenAI, ElevenLabs, Deepgram, Resend (email), Expo Push Notifications
- **Collections:** parents, children, chat_sessions, user_profiles, notification_settings, knowledge_base, teachers, safety_logs, daily_verses, kb_age_cache

## Completed Features
- [x] Phase 1: Core AI conversation engine, safety filtering, knowledge base
- [x] Phase 2: Voice I/O (STT + TTS), polished chat UI, onboarding
- [x] Adaptive AI coaching with user profiles (fears, strengths, topics)
- [x] Teacher wisdom integration (natural, no name-dropping)
- [x] Verse of the Day with age-appropriate explanations
- [x] Performance optimization (text-first, audio-later, in-memory caching)
- [x] Full Authentication System (register, login, JWT sessions)
- [x] Multi-child Profile Management (one parent, multiple children)
- [x] Connected Parent Dashboard (real stats, conversation history, child selector)
- [x] Auth-aware UI (sign-in/sign-up screens, auth guards, personalized home)
- [x] Push Notifications (Expo Push API, configurable per parent)
- [x] Weekly Summary Emails (Resend, Sunday evening, HTML template)
- [x] Notification Settings Dashboard (3 configurable toggles + test email button)
- [x] AI Theological Realignment (Scripture-rooted answers, not generic)
- [x] Voice Selection (10 voices: 5F/5M, American/British/African accents, onboarding + dashboard)
- [x] **365 Verse of the Day** — Unique verse every day, themed by month (love, faith, courage, hope, wisdom, prayer, joy, identity, creation, Jesus, gratitude, promises) — Mar 2026
- [x] **KB Age Pre-warming** — All 224 age-adapted answers (56 questions × 4 tiers) pre-generated at startup, 100% cached — Mar 2026
- [x] **Persistent Conversation History** — All chat messages saved to DB, viewable in parent dashboard with session detail — Mar 2026

## Current State (Mar 2026)
Fully functional app with authentication, multi-child support, parent dashboard, notifications, voice selection, 365 daily verses, instant KB responses for all age tiers, and persistent conversation history.

## Key Files
- `/app/backend/server.py` - Main backend orchestrator
- `/app/backend/bible_verses.py` - 365 verses organized by monthly themes
- `/app/backend/routes/notifications.py` - Push notification routes
- `/app/backend/routes/emails.py` - Weekly email summary routes
- `/app/frontend/hooks/useAuth.ts` - Auth hook + updateChildVoice
- `/app/frontend/contexts/AuthContext.tsx` - Auth context provider
- `/app/frontend/components/VoicePicker.tsx` - Voice selection UI
- `/app/frontend/app/onboarding.tsx` - 4-step onboarding (name → age → voice → consent)
- `/app/frontend/app/parent-dashboard.tsx` - Dashboard with voice/notification settings, stats, conversations
- `/app/frontend/app/index.tsx` - Home screen with verse of the day
- `/app/frontend/app/chat.tsx` - Chat interface

## P1 (Next Priority)
- COPPA-compliant parental consent flow
- Refactor server.py into modular FastAPI routers
- Verify a custom domain in Resend for production emails

## P2 (Future)
- True streaming responses (SSE word-by-word)
- Full QA on iOS/Android native
- Production deployment
