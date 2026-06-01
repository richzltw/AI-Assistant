# Proposal: Cloud-Native Multimodal AI Study Assistant (GCP)

## 1. Problem Statement
This project build a cloud-hosted AI assistant that can answer questions, summarize findings, automate simple tasks, and support voice interaction.

## 2. Intended Users
People who need support for daily news update, document summary and other simple research task.

## 3. Cloud Platform and Planned Services
Platform: Google Cloud Platform (GCP)

Planned cloud-native components:
- Cloud Run: hosts the assistant backend API.
- Cloud Functions: external tool endpoint for automation actions, in our case, a daily news update.
- Firestore: lightweight persistent storage for assistant notes/facts.
- Cloud Speech-to-Text: transcribes user voice input.
- Cloud Text-to-Speech: converts assistant responses to audio.
- Artifact Registry + Cloud Build: image storage and CI/CD deployment pipeline.

Cross-cloud/hybrid extension:
- Hybrid mode with local client + cloud backend (local user interface calling GCP-hosted API).
- LLM provider integration.

## 4. Type of AI Assistant
This project will implement a multimodal cloud AI assistant with:
- Text chat for Q and A, analysis, and summarization.
- Voice input/output for accessibility and hands-free use.
- Tool-calling support for web search, database lookup and cloud function automation.
- Practical use case: summarizing documents, and running simple AI assisted research.
- Added automation use case: a daily serverless news briefing workflow that compiles headline summaries into Markdown and delivers them to the webpage.

## Proposed Deliverables
- Deployed assistant endpoint running on Cloud Run.
- One AI model/API: Gemini LLM, plus speech services.
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
- Successful daily news update is completed end-to-end.
- Evaluation average score >= 0.70 on rubric-based test set.
- Demonstrated multimodal value over text-only baseline.
