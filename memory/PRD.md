# Bible Buddy - Product Requirements Document

## Original Problem Statement
Build a mobile application called "Bible Buddy" — an interactive app for children to ask questions about the Bible and receive safe, age-appropriate answers. Features both text and voice-based interaction.

## Core Requirements
- Age-appropriate AI chat for children (4-6, 7-9, 10-12, 13-18 age tiers)
- Safety content filtering for inappropriate topics
- Knowledge base of 56+ common faith questions for instant answers
- Featured Christian teachers (Apostle Selman, Stephanie Ike, Steven Furtick, Priscilla Shirer) integrated into AI responses
- Text-to-Speech (TTS) for reading responses aloud
- Speech-to-Text (STT) for voice input
- Parent Dashboard with conversation history and usage stats
- Multi-step onboarding with parental consent
- Daily Bible Verse feature with AI explanations

## Architecture
- **Backend:** FastAPI + MongoDB + OpenAI (Emergent LLM Key) + ElevenLabs TTS + Deepgram STT
- **Frontend:** Expo React Native (web + native) with expo-router

## What's Implemented

### Phase 1 — Complete
- Core AI conversation engine with age-tier prompts
- Safety/content filtering layer
- Knowledge base (56 questions)
- Featured teachers integration

### Phase 2 — In Progress
- Multi-screen app: Home, Onboarding (3-step), Chat, Parent Dashboard
- Chat UI: gradient message bubbles, Bible verse chips, suggestion cards
- Onboarding: Name → Age Selection (2x2 grid) → Parental Consent
- Home screen: features grid, Verse of the Day, teachers section
- Parent Dashboard: conversation history, stats, topic tracking
- Cross-platform storage (localStorage/AsyncStorage)
- TTS: ElevenLabs (upgraded to paid) + Web Speech API fallback
- **Daily Bible Verse** (NEW): 31 curated verses, AI-generated age-appropriate explanations, daily rotation, share/copy feature, MongoDB caching

### Not Yet Implemented
- STT frontend (backend Deepgram integration ready, frontend mic capture missing)
- Full authentication (using local storage, not proper auth)
- Real parent dashboard data (UI present, data static)
- COPPA-compliant parental consent flow

## API Endpoints
- `POST /api/chat` — Main chat with AI
- `POST /api/tts` — Text-to-Speech (ElevenLabs)
- `GET /api/teachers` — Featured teachers list
- `GET /api/knowledge-base` — All knowledge base questions
- `GET /api/verse-of-the-day?age_tier=7-9` — Daily Bible verse with AI explanation (NEW)
- `POST /api/voice-chat` — STT endpoint (frontend not wired)
- `POST /api/onboarding` — Save user setup
- `GET /api/sessions/{child_id}` — Chat session history

## Prioritized Backlog

### P1
- Wire STT frontend (mic button → Deepgram backend)
- Implement full authentication (parent accounts, child profiles)
- Connect Parent Dashboard to real backend conversation data

### P2
- COPPA-compliant parental consent flow
- Persistent conversation history in MongoDB

### P3
- Full QA testing across iOS and Android
- Production deployment
