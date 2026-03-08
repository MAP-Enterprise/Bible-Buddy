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

## Architecture
- **Backend:** FastAPI + MongoDB + OpenAI (Emergent LLM Key) + ElevenLabs TTS + Deepgram STT
- **Frontend:** Expo React Native (web + native) with expo-router

## What's Implemented (as of March 8, 2026)

### Phase 1 ✅
- Core AI conversation engine with age-tier prompts
- Safety/content filtering layer
- Knowledge base (56 questions)
- Featured teachers integration

### Phase 2 (In Progress)
- ✅ Multi-screen app with expo-router (Home, Onboarding, Chat, Parent Dashboard)
- ✅ Chat UI with gradient message bubbles, Bible verse chips, suggestion cards
- ✅ 3-step onboarding flow (Name → Age Selection → Parental Consent)
- ✅ Home screen with features grid, teachers section, navigation buttons
- ✅ Parent Dashboard with conversation history, stats, topic tracking
- ✅ Cross-platform storage (localStorage for web, AsyncStorage for native)
- ✅ TTS fallback (Web Speech API when ElevenLabs unavailable)
- ⚠️ ElevenLabs TTS — key flagged by provider, falls back to browser TTS
- ❌ STT frontend integration (backend ready, frontend mic capture not wired)
- ❌ Full authentication (using local storage, not proper auth)

### Bug Fixes (March 8, 2026) ✅
- Fixed age selection screen — text/emojis now visible in 2-column grid
- Fixed home screen features grid — all 4 features rendering correctly
- Fixed post-onboarding navigation error
- Updated ElevenLabs API key (still flagged by provider)

## Prioritized Backlog

### P0
- None currently blocking

### P1
- Implement STT frontend (wire mic button to Deepgram backend endpoint)
- Implement full authentication (parent accounts, child profiles)
- Connect Parent Dashboard to real backend data

### P2
- COPPA-compliant parental consent flow
- Persistent conversation history in MongoDB
- Resolve ElevenLabs API key issue (user needs paid plan)

### P3
- Full QA testing across iOS and Android
- Production deployment
