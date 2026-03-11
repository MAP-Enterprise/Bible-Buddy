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
- **Integrations:** OpenAI, ElevenLabs, Deepgram

## Completed Features
- [x] Phase 1: Core AI conversation engine, safety filtering, knowledge base
- [x] Phase 2: Voice I/O (STT + TTS), polished chat UI, onboarding
- [x] Adaptive AI coaching with user profiles (fears, strengths, topics)
- [x] Teacher wisdom integration (natural, no name-dropping)
- [x] Verse of the Day with age-appropriate explanations
- [x] Performance optimization (text-first, audio-later, in-memory caching)
- [x] **Full Authentication System** (register, login, JWT sessions) - Mar 2026
- [x] **Multi-child Profile Management** (one parent, multiple children) - Mar 2026
- [x] **Connected Parent Dashboard** (real stats, conversation history, child selector) - Mar 2026
- [x] **Auth-aware UI** (sign-in/sign-up screens, auth guards, personalized home) - Mar 2026

## Current State (Mar 2026)
The app is fully functional with authentication, multi-child support, and a connected parent dashboard. The auth system uses session tokens stored in secure storage, with JWT-protected API endpoints for user and child data.

## Key Technical Decisions
- Session tokens (not JWTs) for simple, revocable auth
- `expo-secure-store` on native, `localStorage` on web for cross-platform storage
- File-based audio serving (MP3 files from `/app/backend/audio_cache/`)
- Text-first, audio-later response pattern for low latency

## P0 (Next Priority)
- Pre-warm ALL KB age-adapted answers at startup (all 4 tiers)
- Persistent conversation history (save all messages to DB)

## P1 (Upcoming)
- COPPA-compliant parental consent flow
- Refactor server.py into modular FastAPI routers

## P2 (Future)
- True streaming responses (SSE word-by-word)
- Full QA on iOS/Android native
- Production deployment
