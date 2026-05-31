# GCP Multimodal AI Assistant

This repository contains a complete assignment-ready implementation for a cloud-native AI assistant with multimodal I/O, tool calling, security controls, and evaluation scripts.

## What is implemented
- Deployed target: Cloud Run service (FastAPI backend)
- AI model/API: Gemini via Vertex AI on GCP (primary), optional OpenAI fallback
- Multimodal support: voice-to-text and text-to-speech endpoints, image upload endpoint
- Homepage supports both typed input and microphone voice input, with audio playback for assistant replies
- Firestore stores chat history (user and assistant turns) for retrieval on reload
- Cloud-native components: Cloud Run, Cloud Functions, Firestore, Cloud Build, Artifact Registry
- Tool calling: web search API, Firestore lookup, cloud function call, allow-listed shell commands, allow-listed HTTP APIs
- Security mitigation implemented: input sanitization + shell command allow-list + optional bearer token check
- Hybrid mode: local client connecting to cloud backend

## Project structure
- app/: backend source code
- scripts/: deployment scripts and sample cloud function
- evaluation/: test cases and evaluation runner
- docs/proposal.md: short proposal
- docs/final_report.md: final report draft
- docs/architecture.mmd: architecture diagram source
- client/: local hybrid client example

## Quick start (local)
1. Create and activate environment:
   - python -m venv .venv
   - .venv\\Scripts\\Activate.ps1
2. Install dependencies:
   - pip install -r requirements.txt
3. Configure environment:
   - copy .env.example .env
   - set GOOGLE_API_KEY and PROJECT_ID
4. Run API:
   - uvicorn app.main:app --host 0.0.0.0 --port 8080
5. Test health endpoint:
   - http://localhost:8080/health
6. Open homepage for multimodal chat:
   - http://localhost:8080/
   - If textbox is empty, click the microphone action button to start/stop capture
   - Captured speech fills the textbox; the same action button becomes Send (arrow)
   - Assistant response is shown as text and played as audio

## Deploy to GCP (Cloud Run)
1. Authenticate gcloud and set permissions.
2. Run:
   - ./scripts/deploy.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1 -Service gcp-multimodal-assistant
3. Confirm deployed URL from script output.

Notes:
- The Cloud Run deployment sets GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT so Gemini can run with GCP application default credentials.

## New task automation: Daily 7am news briefing digest
This repository now includes a dedicated serverless automation that:
- Runs every morning at 7:00 AM via Cloud Scheduler.
- Pulls top headlines from configurable RSS feeds.
- Produces a clean Markdown digest with Gemini summarization (fallback included).
- Delivers the digest to Slack DM by email (bot token flow), Slack webhook, and/or SMS (Twilio) based on configured env vars.

Source files:
- scripts/news_digest_function/main.py
- scripts/news_digest_function/requirements.txt
- scripts/deploy_news_digest.ps1

Deploy command example:
- ./scripts/deploy_news_digest.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1 -TimeZone "America/Chicago"

Optional delivery arguments:
- -SlackWebhookUrl "https://hooks.slack.com/services/..."
- -SlackBotToken "xoxb-..." -SlackDmEmail "lizhi1@seas.upenn.edu"
- -TwilioAccountSid "AC..." -TwilioAuthToken "..." -TwilioFromNumber "+1..." -TwilioToNumber "+1..."

Slack DM notes:
- Slack DM mode is preferred when both -SlackBotToken and -SlackDmEmail are set.
- Required bot scopes typically include users:read.email, conversations:write, and chat:write.
- If DM delivery fails and a webhook is configured, the function falls back to webhook posting.

Schedule defaults:
- Cron: 0 7 * * *
- Time zone: America/Chicago

Notes:
- Function is deployed as private (no unauthenticated access).
- Scheduler calls it using OIDC from a dedicated service account.
- You can run it immediately with:
   - gcloud scheduler jobs run daily-news-digest-7am --location=us-central1

## Evaluate assistant
1. Run deployed or local service.
2. Execute:
   - python evaluation/run_eval.py
3. Record scores and sample outputs in final report.

## Key API endpoints for multimodal flow
- POST /assistant/chat: text input -> text response
- POST /assistant/voice/chat: voice input -> transcript + text response + audio response
- POST /assistant/voice/transcribe: voice input -> transcript only
- POST /assistant/voice/synthesize: text input -> audio only
- GET /assistant/history?user_id=<id>&limit=<n>: recent persisted chat messages

## Homepage interaction model
- Single adaptive action button in chat UI:
   - Empty textbox -> microphone mode (start/end voice capture)
   - Non-empty textbox -> send mode (arrow)
- Voice capture writes transcript into textbox for user visibility/editing before send.
- Audio reply auto-plays when allowed by browser autoplay policy.
- Recent conversation history is loaded from Firestore for the same user id when homepage opens.

## Required assignment mapping
- Deployed AI assistant: Cloud Run deployment script included.
- AI/ML model/API: Gemini Vertex AI integration in app/llm_client.py.
- Cloud-native components: Cloud Run, Cloud Functions, Firestore, Speech, TTS.
- Written report: docs/proposal.md and docs/final_report.md.
- Multi-modal: voice + image endpoint support.
- External tool use: cloud function, APIs, database, shell.
- Security risks and mitigation: documented and implemented.
- Cross-cloud/hybrid: local + cloud hybrid mode, optional secondary provider fallback.

## Notes
- For production, move secrets to Secret Manager and add IAM-based service-to-service auth.
- For full image understanding, connect Gemini vision inference in app/main.py and app/llm_client.py.
