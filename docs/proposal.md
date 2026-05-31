# Proposal: Cloud-Native Multimodal AI Study Assistant (GCP)

## 1. Problem Statement
This project build a cloud-hosted AI assistant that can answer questions, summarize findings, automate simple tasks, and support voice interaction.

## 2. Intended Users
- People s who need quick decision support for scheduling, research, or planning.
- Personal use: personal assistant for daily update and simple research.

## 3. Cloud Platform and Planned Services
Platform: Google Cloud Platform (GCP)

Planned cloud-native components:
- Cloud Run: hosts the assistant backend API.
- Cloud Functions (2nd gen): external tool endpoint for automation actions.
- Firestore: lightweight persistent storage for assistant notes/facts.
- Cloud Speech-to-Text: transcribes user voice input.
- Cloud Text-to-Speech: converts assistant responses to audio.
- Artifact Registry + Cloud Build: image storage and CI/CD deployment pipeline.

Cross-cloud/hybrid extension:
- Hybrid mode with local client + cloud backend (local user interface calling GCP-hosted API).
- Optional fallback LLM provider integration for interoperability testing.

## 4. Type of AI Assistant
This project will implement a multimodal cloud AI assistant with:
- Text chat for Q and A, planning, and summarization.
- Voice input/output for accessibility and hands-free use.
- Tool-calling support for web search, database lookup, cloud function automation, and sandboxed shell commands.
- Practical use case: generating weekly study plans, summarizing recent topic updates, and running automation actions (for example, getting UTC time).
- Added automation use case: a daily 7:00 AM serverless news briefing workflow that compiles headline summaries into Markdown and delivers them via Slack or SMS.

## Proposed Deliverables
- Deployed assistant endpoint running on Cloud Run.
- At least one AI model/API: Gemini LLM, plus speech services.
- Cloud-native architecture with serverless services and storage.
- Evaluation results using defined test cases.
- Final report with architecture, data flow, metrics, limitations, and future work.

## Security and Privacy Approach
Identified risks:
- API key leakage from source code or logs.
- Command injection through tool-calling shell interface.

Mitigations:
- API keys stored in environment variables (or Secret Manager in production), never hard-coded.
- Input sanitization and strict allow-list policy for shell commands.

## Success Criteria
- Assistant can accept input and return useful AI-generated output.
- At least one practical scenario is completed end-to-end.
- Evaluation average score >= 0.70 on rubric-based test set.
- Demonstrated multimodal value over text-only baseline.
