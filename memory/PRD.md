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
- **Collections:** parents, children, chat_sessions, user_profiles, notification_settings, knowledge_base, teachers, safety_logs, daily_verses, age_adapted_kb_cache

## Completed Features
- [x] Phase 1: Core AI conversation engine, safety filtering, knowledge base
- [x] Phase 2: Voice I/O (STT + TTS), polished chat UI, onboarding
- [x] Adaptive AI coaching with user profiles (fears, strengths, topics)
- [x] Teacher wisdom integration (natural, no name-dropping)
- [x] Verse of the Day with age-appropriate explanations
- [x] Performance optimization (text-first, audio-later, in-memory caching)
- [x] Full Authentication System (register, login, JWT sessions) - Mar 2026
- [x] Multi-child Profile Management (one parent, multiple children) - Mar 2026
- [x] Connected Parent Dashboard (real stats, conversation history, child selector) - Mar 2026
- [x] Auth-aware UI (sign-in/sign-up screens, auth guards, personalized home) - Mar 2026
- [x] **Push Notifications** (Expo Push API, configurable per parent) - Mar 2026
- [x] **Weekly Summary Emails** (Resend, Sunday evening, HTML template) - Mar 2026
- [x] **Notification Settings Dashboard** (3 configurable toggles + test email button) - Mar 2026

## Current State (Mar 2026)
The app is fully functional with authentication, multi-child support, connected parent dashboard, push notifications, and weekly summary emails. Notification settings are configurable via the parent dashboard.

## Key Files
- `/app/backend/server.py` - Main backend (chat, auth, dashboard, voice)
- `/app/backend/routes/notifications.py` - Push notification routes and logic
- `/app/backend/routes/emails.py` - Weekly email summary routes (Resend)
- `/app/frontend/hooks/useAuth.ts` - Auth hook with token management
- `/app/frontend/contexts/AuthContext.tsx` - Auth context provider
- `/app/frontend/helpers/notifications.ts` - Push token registration helper
- `/app/frontend/app/sign-in.tsx` - Sign in screen
- `/app/frontend/app/sign-up.tsx` - Sign up screen
- `/app/frontend/app/parent-dashboard.tsx` - Dashboard with settings

## P0 (Next Priority)
- Pre-warm ALL KB age-adapted answers at startup (all 4 tiers)
- Persistent conversation history (save all messages to DB)

## P1 (Upcoming)
- COPPA-compliant parental consent flow
- Refactor server.py into modular FastAPI routers
- Verify a custom domain in Resend for production emails

## P2 (Future)
- True streaming responses (SSE word-by-word)
- Full QA on iOS/Android native
- Production deployment
