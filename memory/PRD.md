# Bible Buddy - Product Requirements Document

## Original Problem Statement
Build a mobile application called "Bible Buddy" — an interactive app for children to ask questions about the Bible and receive safe, age-appropriate answers with voice interaction.

## Architecture
- **Backend:** FastAPI + MongoDB + OpenAI (gpt-4o-mini via Emergent LLM Key) + ElevenLabs TTS + Deepgram STT
- **Frontend:** Expo React Native (web + native) with expo-router
- **Storage:** expo-secure-store (native) / localStorage (web)
- **Audio:** expo-av with HTTP-served MP3 files (not base64)

## What's Implemented

### Core Features ✅
- AI chat with safety filtering and age-tier prompts (4-6, 7-9, 10-12, 13-18)
- Knowledge base: 56 instant answers with pre-cached ElevenLabs audio
- Featured teachers: Apostle Selman, Stephanie Ike, Steven Furtick, Priscilla Shirer
- Daily Verse of the Day with AI explanations
- Multi-screen app: Home, Onboarding, Chat, Parent Dashboard
- Cross-platform storage (expo-secure-store for native, localStorage for web)

### Voice/Audio ✅
- ElevenLabs TTS: audio saved as MP3 files on disk, served via HTTP URL
- 56 KB answers pre-cached at startup (~0ms audio playback)
- Background TTS generation for AI responses (text returns immediately)
- 3-tier fallback: ElevenLabs → Backend TTS → Device speech synthesis
- Visual feedback: "Bible Buddy is speaking..." bar + Stop button

### Performance Optimizations ✅
- KB answers: ~200ms (instant text + pre-cached audio)
- AI answers: ~200ms text response (gpt-4o-mini), audio follows in background
- Concise system prompt for faster LLM inference
- Audio file caching with content-based hashing
- Background TTS generation (never blocks text response)

## API Endpoints
- `POST /api/chat` — Main chat (text returns instantly, audio in background)
- `GET /api/audio/{filename}` — Serve cached MP3 audio files
- `GET /api/audio-status/{session_id}` — Poll audio generation status
- `POST /api/tts` — Direct TTS generation
- `GET /api/verse-of-the-day` — Daily Bible verse
- `GET /api/teachers` — Featured teachers
- `GET /api/knowledge-base` — All KB questions

## Prioritized Backlog

### P1
- Wire STT frontend (mic button → Deepgram backend)
- Full authentication (parent accounts, child profiles)
- Connect Parent Dashboard to real backend data

### P2
- COPPA-compliant parental consent flow
- Persistent conversation history

### P3
- Full QA on iOS/Android native
- Production deployment
