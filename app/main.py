import base64
import io
import json

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from google.cloud import speech, texttospeech
from pypdf import PdfReader

from app.assistant import assistant_service
from app.config import settings
from app.history_store import history_store
from app.llm_client import llm_client
from app.models import ChatRequest, ChatResponse, VoiceSynthesisRequest
from app.security import enforce_bearer_token, sanitize_text

app = FastAPI(title="GCP Multimodal Assistant", version="1.0.0")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GCP Multimodal Assistant</title>
            <style>
                :root {
                    color-scheme: light;
                    --bg: #07111f;
                    --panel: rgba(10, 18, 34, 0.86);
                    --panel-2: rgba(16, 28, 50, 0.92);
                    --text: #eef4ff;
                    --muted: #a8b6d3;
                    --accent: #7dd3fc;
                    --accent-2: #34d399;
                    --border: rgba(255, 255, 255, 0.12);
                    --warn: #f59e0b;
                    --danger: #f87171;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    min-height: 100vh;
                    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    color: var(--text);
                    background:
                        radial-gradient(circle at top left, rgba(125, 211, 252, 0.22), transparent 30%),
                        radial-gradient(circle at bottom right, rgba(52, 211, 153, 0.18), transparent 28%),
                        linear-gradient(160deg, #050a14, #0a1222 52%, #081726);
                }
                main {
                    max-width: 1120px;
                    margin: 0 auto;
                    padding: 36px 20px 32px;
                    display: grid;
                    gap: 16px;
                }
                .card {
                    padding: 18px;
                    border-radius: 18px;
                    border: 1px solid var(--border);
                    background: var(--panel);
                    backdrop-filter: blur(10px);
                }
                .hero {
                    padding: 26px;
                    border-radius: 24px;
                    border: 1px solid var(--border);
                    background: linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(9, 16, 31, 0.96));
                    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.35);
                }
                h1 {
                    margin: 0 0 10px;
                    font-size: clamp(2rem, 5.4vw, 3.7rem);
                    line-height: 1;
                    letter-spacing: -0.04em;
                }
                h2 { margin: 0 0 10px; font-size: 1.05rem; }
                p { margin: 0; color: var(--muted); line-height: 1.5; }
                .grid { display: grid; gap: 16px; }
                .chat-shell {
                    display: grid;
                    gap: 14px;
                    grid-template-columns: 1fr;
                }
                @media (min-width: 980px) {
                    .chat-shell {
                        grid-template-columns: 1.1fr 0.9fr;
                        align-items: start;
                    }
                }
                .compose-panel, .history-panel {
                    border: 1px solid var(--border);
                    border-radius: 12px;
                    padding: 12px;
                    background: rgba(255, 255, 255, 0.02);
                }
                .history-list {
                    display: grid;
                    gap: 8px;
                    max-height: 420px;
                    overflow-y: auto;
                }
                .history-item {
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    padding: 10px;
                    background: rgba(255, 255, 255, 0.03);
                    cursor: pointer;
                }
                .history-item.active {
                    border-color: rgba(125, 211, 252, 0.8);
                    background: rgba(125, 211, 252, 0.14);
                }
                .history-preview {
                    color: var(--text);
                    font-size: 0.92rem;
                    line-height: 1.35;
                }
                .history-meta {
                    color: var(--muted);
                    font-size: 0.8rem;
                    margin-top: 6px;
                }
                textarea, input[type="text"], input[type="file"] {
                    width: 100%;
                    padding: 12px;
                    border-radius: 12px;
                    border: 1px solid var(--border);
                    background: var(--panel-2);
                    color: var(--text);
                    margin-top: 8px;
                }
                textarea { min-height: 90px; resize: vertical; }
                .row {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-top: 10px;
                }
                button, a.button {
                    border: 0;
                    border-radius: 999px;
                    padding: 10px 14px;
                    font-weight: 700;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, var(--accent), #bef264);
                    color: #04111f;
                }
                button.secondary, a.button.secondary {
                    background: transparent;
                    color: var(--text);
                    border: 1px solid var(--border);
                }
                .chat-log {
                    border: 1px solid var(--border);
                    border-radius: 12px;
                    padding: 10px;
                    min-height: 320px;
                    max-height: 420px;
                    overflow-y: auto;
                    background: rgba(0, 0, 0, 0.2);
                }
                .bubble {
                    margin: 8px 0;
                    padding: 10px;
                    border-radius: 10px;
                    white-space: pre-wrap;
                }
                .bubble.user { background: rgba(125, 211, 252, 0.14); }
                .bubble.assistant { background: rgba(52, 211, 153, 0.14); }
                .meta {
                    color: var(--muted);
                    font-size: 0.9rem;
                    margin-top: 8px;
                }
                .warn {
                    color: #0f172a;
                    background: linear-gradient(90deg, #fde68a, #fcd34d);
                    border-radius: 10px;
                    padding: 10px;
                    margin-top: 10px;
                    font-size: 0.92rem;
                }
                .pill {
                    display: inline-flex;
                    align-items: center;
                    border-radius: 999px;
                    padding: 6px 10px;
                    font-size: 0.82rem;
                    border: 1px solid var(--border);
                    background: rgba(255, 255, 255, 0.06);
                    color: var(--muted);
                }
                .status { margin-top: 8px; color: var(--muted); font-size: 0.9rem; }
            </style>
        </head>
        <body>
            <main>
                <section class="hero">
                    <h1>GCP Multimodal Assistant</h1>
                    <p>Use this page as a real multimodal assistant: type or speak your question, then read and listen to the reply.</p>
                </section>

                <section class="card">
                    <h2>Assistant Chat (Type or Speak)</h2>
                    <p>Text input and voice input are both supported. Audio reply is played automatically after each assistant response.</p>

                    <div class="chat-shell">
                        <section class="compose-panel">
                            <textarea id="chatInput" placeholder="Type your message, or leave empty and use the microphone button..."></textarea>
                            <div class="row">
                                <button id="actionBtn" class="secondary">&#127908; Use Microphone</button>
                                <button id="newChatBtn" class="secondary">+ New Chat</button>
                            </div>
                            <div class="status" id="voiceStatus">Voice status: idle</div>
                            <div class="meta" id="chatMeta"></div>

                            <div class="row" style="margin-top:8px;">
                                <button id="selectFileBtn" type="button" class="secondary">Select File</button>
                                <input id="chatFile" type="file" accept=".txt,.md,.csv,.json,.pdf" style="display:none;" />
                                <span class="meta" id="selectedFileName">No file selected</span>
                            </div>

                            <h2 style="margin:12px 0 8px;">Current Conversation</h2>
                            <div class="chat-log" id="currentChatLog"></div>

                            <audio id="audioPlayer" controls style="width:100%; margin-top:10px;"></audio>
                            <div class="warn">If the textbox is empty, the action button uses microphone and fills the textbox. If textbox has text, the same button sends it.</div>
                        </section>

                        <section class="history-panel">
                            <h2 style="margin-bottom:8px;">Chat History</h2>
                            <p style="margin-bottom:8px;">Click any summary to continue that conversation.</p>
                            <div class="history-list" id="historyList"></div>
                        </section>
                    </div>
                </section>
            </main>

            <script>
                const chatInput = document.getElementById("chatInput");
                const currentChatLog = document.getElementById("currentChatLog");
                const historyList = document.getElementById("historyList");
                const chatMeta = document.getElementById("chatMeta");
                const actionBtn = document.getElementById("actionBtn");
                const newChatBtn = document.getElementById("newChatBtn");
                const voiceStatus = document.getElementById("voiceStatus");
                const selectFileBtn = document.getElementById("selectFileBtn");
                const chatFile = document.getElementById("chatFile");
                const selectedFileName = document.getElementById("selectedFileName");
                const CHAT_USER_ID = "web-ui-user";

                const audioPlayer = document.getElementById("audioPlayer");
                let isRecording = false;
                let speechRecognition = null;
                let currentSessionId = "";

                function makeSessionId() {
                    return "session-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
                }

                function getSelectedUploadFile() {
                    return chatFile.files && chatFile.files[0] ? chatFile.files[0] : null;
                }

                function updateSelectedFileLabel() {
                    const selected = getSelectedUploadFile();
                    selectedFileName.textContent = selected ? ("Selected: " + selected.name) : "No file selected";
                }

                function inferDocumentModeFromPrompt(text) {
                    const prompt = (text || "").trim().toLowerCase();
                    if (!prompt) return "summary";

                    const extractionHints = [
                        "extract",
                        "extraction",
                        "json",
                        "fields",
                        "structured",
                        "table",
                        "invoice",
                        "entities",
                        "key value",
                    ];
                    return extractionHints.some((hint) => prompt.includes(hint)) ? "extract" : "summary";
                }

                function addBubble(role, text) {
                    const div = document.createElement("div");
                    div.className = "bubble " + role;
                    div.textContent = text;
                    currentChatLog.appendChild(div);
                    currentChatLog.scrollTop = currentChatLog.scrollHeight;
                }

                function formatWhen(isoText) {
                    if (!isoText) return "just now";
                    const d = new Date(isoText);
                    if (Number.isNaN(d.getTime())) return "recent";
                    return d.toLocaleString();
                }

                async function loadConversationMessages(sessionId) {
                    const res = await fetch(
                        "/assistant/conversations/" + encodeURIComponent(sessionId) + "?user_id=" + encodeURIComponent(CHAT_USER_ID) + "&limit=100"
                    );
                    const data = await res.json();
                    if (!res.ok) throw new Error("Failed to load conversation");

                    currentChatLog.innerHTML = "";
                    for (const msg of (data.messages || [])) {
                        addBubble(msg.role === "assistant" ? "assistant" : "user", msg.content || "");
                    }
                }

                function renderConversationSummaries(items) {
                    historyList.innerHTML = "";
                    for (const item of items) {
                        const btn = document.createElement("button");
                        btn.type = "button";
                        btn.className = "history-item" + (item.session_id === currentSessionId ? " active" : "");
                        btn.dataset.sessionId = item.session_id;

                        const preview = document.createElement("div");
                        preview.className = "history-preview";
                        preview.textContent = item.preview || item.last_message || "(empty conversation)";

                        const meta = document.createElement("div");
                        meta.className = "history-meta";
                        meta.textContent = (item.message_count || 0) + " msgs • " + formatWhen(item.updated_at);

                        btn.appendChild(preview);
                        btn.appendChild(meta);

                        btn.addEventListener("click", async () => {
                            currentSessionId = item.session_id;
                            await loadConversationMessages(currentSessionId);
                            await loadConversationSummaries();
                            chatMeta.textContent = "Continuing conversation: " + currentSessionId;
                        });

                        historyList.appendChild(btn);
                    }
                }

                async function loadConversationSummaries() {
                    try {
                        const res = await fetch("/assistant/conversations?user_id=" + encodeURIComponent(CHAT_USER_ID) + "&limit=30");
                        const data = await res.json();
                        if (!res.ok) return;

                        const items = data.conversations || [];
                        renderConversationSummaries(items);
                    } catch (_) {
                        // History loading is best-effort and should not block chat usage.
                    }
                }

                async function setAndPlayAudio(base64Audio) {
                    audioPlayer.src = "data:audio/mp3;base64," + base64Audio;
                    audioPlayer.load();
                    try {
                        await audioPlayer.play();
                        chatMeta.textContent += " | Audio: played";
                    } catch (_) {
                        chatMeta.textContent += " | Audio: use built-in player controls";
                    }
                }

                async function playAudioFromText(text) {
                    const res = await fetch("/assistant/voice/synthesize", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ text })
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error("Audio synthesis failed");
                    await setAndPlayAudio(data.audio_base64);
                }

                async function sendChat() {
                    const prompt = (chatInput.value || "").trim();
                    if (!prompt) return;

                    if (!currentSessionId) {
                        // On fresh page load, start a brand-new session only when user sends first message.
                        currentSessionId = makeSessionId();
                    }

                    addBubble("user", prompt);
                    chatMeta.textContent = "Sending request...";
                    actionBtn.disabled = true;

                    try {
                        const res = await fetch("/assistant/chat", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                user_id: CHAT_USER_ID,
                                text: prompt,
                                session_id: currentSessionId,
                                enable_tools: true
                            })
                        });
                        const data = await res.json();
                        if (!res.ok) {
                            addBubble("assistant", "Request failed: " + JSON.stringify(data));
                            chatMeta.textContent = "Status: " + res.status;
                            return;
                        }

                        addBubble("assistant", data.answer || "(no answer)");
                        chatMeta.textContent = "Tool used: " + (data.used_tool || "none");

                        if (data.answer) {
                            try {
                                await playAudioFromText(data.answer);
                            } catch (audioErr) {
                                chatMeta.textContent += " | Audio: " + audioErr.message;
                            }
                        }

                        await loadConversationSummaries();
                    } catch (err) {
                        addBubble("assistant", "Error: " + err.message);
                        chatMeta.textContent = "Network error";
                    } finally {
                        actionBtn.disabled = false;
                        chatInput.value = "";
                        updateActionButton();
                    }
                }

                async function analyzeUploadedDocument() {
                    const selected = getSelectedUploadFile();
                    if (!selected) return;

                    if (!currentSessionId) {
                        currentSessionId = makeSessionId();
                    }

                    const mode = inferDocumentModeFromPrompt(chatInput.value || "");
                    const instructions = (chatInput.value || "").trim();

                    addBubble("user", "Analyze file: " + selected.name + " (" + mode + ")");
                    chatMeta.textContent = "Analyzing document...";
                    actionBtn.disabled = true;

                    try {
                        const form = new FormData();
                        form.append("file", selected);
                        form.append("mode", mode);
                        form.append("instructions", instructions);
                        form.append("user_id", CHAT_USER_ID);
                        form.append("session_id", currentSessionId);

                        const res = await fetch("/assistant/document/analyze", {
                            method: "POST",
                            body: form,
                        });
                        const data = await res.json();
                        if (!res.ok) {
                            addBubble("assistant", "Document analysis failed: " + JSON.stringify(data));
                            chatMeta.textContent = "Status: " + res.status;
                            return;
                        }

                        if (data.session_id) {
                            currentSessionId = data.session_id;
                        }

                        const resultText = data.result_json
                            ? JSON.stringify(data.result_json, null, 2)
                            : (data.result || "(no result)");
                        addBubble("assistant", resultText);
                        chatMeta.textContent = "Document analysis complete";
                        await loadConversationSummaries();
                    } catch (err) {
                        addBubble("assistant", "Error: " + err.message);
                        chatMeta.textContent = "Network error";
                    } finally {
                        actionBtn.disabled = false;
                        chatInput.value = "";
                        chatFile.value = "";
                        updateSelectedFileLabel();
                        updateActionButton();
                    }
                }

                function updateActionButton() {
                    if (isRecording) {
                        actionBtn.innerHTML = "&#9632; End Voice Input";
                        actionBtn.classList.add("secondary");
                        return;
                    }

                    const hasFile = !!getSelectedUploadFile();
                    if (hasFile) {
                        const inferredMode = inferDocumentModeFromPrompt(chatInput.value || "");
                        actionBtn.innerHTML = inferredMode === "extract" ? "&#10148; Extract Data" : "&#10148; Analyze Document";
                        actionBtn.classList.remove("secondary");
                        return;
                    }

                    const hasText = (chatInput.value || "").trim().length > 0;
                    if (hasText) {
                        actionBtn.innerHTML = "&#10148; Send";
                        actionBtn.classList.remove("secondary");
                    } else {
                        actionBtn.innerHTML = "&#127908; Use Microphone";
                        actionBtn.classList.add("secondary");
                    }
                }

                function createSpeechRecognition() {
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    if (!SpeechRecognition) return null;

                    const rec = new SpeechRecognition();
                    rec.lang = "en-US";
                    rec.interimResults = true;
                    rec.maxAlternatives = 1;
                    return rec;
                }

                function startSpeechCapture() {
                    speechRecognition = createSpeechRecognition();
                    if (!speechRecognition) {
                        voiceStatus.textContent = "Voice status: speech recognition unsupported in this browser";
                        return;
                    }

                    let finalTranscript = "";
                    isRecording = true;
                    voiceStatus.textContent = "Voice status: listening...";
                    updateActionButton();

                    speechRecognition.onresult = (event) => {
                        let interim = "";
                        for (let i = event.resultIndex; i < event.results.length; i += 1) {
                            const text = event.results[i][0].transcript;
                            if (event.results[i].isFinal) {
                                finalTranscript += text + " ";
                            } else {
                                interim += text;
                            }
                        }
                        const combined = (finalTranscript + interim).trim();
                        if (combined) {
                            chatInput.value = combined;
                            updateActionButton();
                        }
                    };

                    speechRecognition.onerror = () => {
                        voiceStatus.textContent = "Voice status: microphone permission denied or unavailable";
                    };

                    speechRecognition.onend = () => {
                        isRecording = false;
                        const captured = (chatInput.value || "").trim();
                        if (captured) {
                            voiceStatus.textContent = "Voice status: captured speech. Review/edit and send.";
                        } else {
                            voiceStatus.textContent = "Voice status: no speech captured";
                        }
                        updateActionButton();
                    };

                    try {
                        speechRecognition.start();
                    } catch (_) {
                        isRecording = false;
                        voiceStatus.textContent = "Voice status: could not start microphone";
                        updateActionButton();
                    }
                }

                function stopSpeechCapture() {
                    if (speechRecognition && isRecording) {
                        voiceStatus.textContent = "Voice status: ending capture...";
                        try {
                            speechRecognition.stop();
                        } catch (_) {
                            isRecording = false;
                            updateActionButton();
                        }
                    }
                }

                actionBtn.addEventListener("click", async () => {
                    if (isRecording) {
                        stopSpeechCapture();
                        return;
                    }

                    if (getSelectedUploadFile()) {
                        await analyzeUploadedDocument();
                        return;
                    }

                    const hasText = (chatInput.value || "").trim().length > 0;
                    if (hasText) {
                        await sendChat();
                    } else {
                        startSpeechCapture();
                    }
                });

                newChatBtn.addEventListener("click", async () => {
                    if (isRecording) {
                        stopSpeechCapture();
                    }

                    currentSessionId = "";
                    currentChatLog.innerHTML = "";
                    chatInput.value = "";
                    chatFile.value = "";
                    voiceStatus.textContent = "Voice status: idle";
                    chatMeta.textContent = "Started a new chat";
                    updateSelectedFileLabel();
                    updateActionButton();
                    await loadConversationSummaries();
                });

                selectFileBtn.addEventListener("click", () => {
                    chatFile.click();
                });
                chatFile.addEventListener("change", () => {
                    updateSelectedFileLabel();
                    updateActionButton();
                });

                chatInput.addEventListener("input", updateActionButton);
                updateSelectedFileLabel();
                updateActionButton();
                currentChatLog.innerHTML = "";
                loadConversationSummaries();
            </script>
        </body>
        </html>
        """


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


def _transcribe_bytes(data: bytes, file_name: str, content_type: str) -> str:
    name = (file_name or "").lower()
    ctype = (content_type or "").lower()

    encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    sample_rate_hertz = None

    if name.endswith(".wav") or "wav" in ctype:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        sample_rate_hertz = 16000
    elif name.endswith(".webm") or "webm" in ctype:
        encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    elif name.endswith(".ogg") or "ogg" in ctype:
        encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=data)

    config_kwargs = {
        "encoding": encoding,
        "language_code": "en-US",
    }
    if sample_rate_hertz:
        config_kwargs["sample_rate_hertz"] = sample_rate_hertz

    config = speech.RecognitionConfig(**config_kwargs)
    response = client.recognize(config=config, audio=audio)
    return " ".join([r.alternatives[0].transcript for r in response.results]).strip()


def _synthesize_text_to_base64(text: str) -> str:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    return base64.b64encode(response.audio_content).decode("ascii")


def _extract_document_text(data: bytes, file_name: str, content_type: str) -> str:
    if not data:
        return ""

    name = (file_name or "").lower()
    ctype = (content_type or "").lower()

    if name.endswith(".pdf") or "pdf" in ctype:
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n".join(pages).strip()
        except Exception:
            return ""

    if name.endswith(".json") or "json" in ctype:
        raw = data.decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(raw)
            return json.dumps(parsed, ensure_ascii=True, indent=2)
        except Exception:
            # Keep processing even if JSON is malformed.
            return raw.strip()

    # For text-like files (.txt, .md, .csv, .log), fallback to utf-8 decode.
    return data.decode("utf-8", errors="ignore").strip()


@app.post("/assistant/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    enforce_bearer_token(authorization, settings.function_router_token)

    clean_text = sanitize_text(request.text, settings.max_input_chars)
    resolved_session_id = history_store.save_message(
        user_id=request.user_id,
        role="user",
        content=clean_text,
        input_mode="text",
        session_id=request.session_id,
    )

    answer, used_tool, tool_result = await assistant_service.respond(clean_text, enable_tools=request.enable_tools)

    history_store.save_message(
        user_id=request.user_id,
        role="assistant",
        content=answer,
        input_mode="text",
        used_tool=used_tool,
        session_id=resolved_session_id or request.session_id,
    )
    return ChatResponse(answer=answer, used_tool=used_tool, tool_result=tool_result)


@app.get("/assistant/conversations")
def get_conversations(user_id: str, limit: int = 20) -> JSONResponse:
    clean_user = user_id.strip()
    if not clean_user or len(clean_user) > 128:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    bounded_limit = max(1, min(limit, 100))
    items = history_store.get_conversation_summaries(clean_user, bounded_limit)
    return JSONResponse({"user_id": clean_user, "count": len(items), "conversations": items})


@app.get("/assistant/conversations/{session_id}")
def get_conversation_messages(session_id: str, user_id: str, limit: int = 100) -> JSONResponse:
    clean_user = user_id.strip()
    clean_session = session_id.strip()
    if not clean_user or len(clean_user) > 128:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    if not clean_session or len(clean_session) > 128:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    bounded_limit = max(1, min(limit, 200))
    messages = history_store.get_conversation_messages(clean_user, clean_session, bounded_limit)
    return JSONResponse(
        {
            "user_id": clean_user,
            "session_id": clean_session,
            "count": len(messages),
            "messages": messages,
        }
    )


@app.get("/assistant/history")
def get_history(user_id: str, limit: int = 20) -> JSONResponse:
    clean_user = user_id.strip()
    if not clean_user or len(clean_user) > 128:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    bounded_limit = max(1, min(limit, 100))
    messages = history_store.get_recent_messages(clean_user, bounded_limit)
    return JSONResponse({"user_id": clean_user, "count": len(messages), "messages": messages})


@app.post("/assistant/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    transcript = _transcribe_bytes(data, file.filename or "", file.content_type or "")
    return JSONResponse({"transcript": transcript})


@app.post("/assistant/voice/synthesize")
def synthesize_voice(request: VoiceSynthesisRequest) -> JSONResponse:
    text = sanitize_text(request.text, 1000)
    audio_b64 = _synthesize_text_to_base64(text)
    return JSONResponse({"audio_base64": audio_b64})


@app.post("/assistant/voice/chat")
async def voice_chat(
    file: UploadFile = File(...),
    user_id: str = Form(default="web-voice-user"),
    session_id: str = Form(default=""),
    enable_tools: bool = Form(default=True),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    enforce_bearer_token(authorization, settings.function_router_token)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    transcript = _transcribe_bytes(data, file.filename or "", file.content_type or "")
    clean_text = sanitize_text(transcript, settings.max_input_chars)

    resolved_session_id = history_store.save_message(
        user_id=user_id,
        role="user",
        content=clean_text,
        input_mode="voice",
        session_id=session_id,
    )

    answer, used_tool, tool_result = await assistant_service.respond(clean_text, enable_tools=enable_tools)
    history_store.save_message(
        user_id=user_id,
        role="assistant",
        content=answer,
        input_mode="voice",
        used_tool=used_tool,
        session_id=resolved_session_id or session_id,
    )
    answer_clean = sanitize_text(answer, 1000)
    audio_b64 = _synthesize_text_to_base64(answer_clean)

    return JSONResponse(
        {
            "user_id": user_id,
            "session_id": resolved_session_id or session_id,
            "transcript": transcript,
            "answer": answer,
            "used_tool": used_tool,
            "tool_result": tool_result,
            "audio_base64": audio_b64,
        }
    )


@app.post("/assistant/image/describe")
async def describe_image(file: UploadFile = File(...)) -> JSONResponse:
    # Minimal multimodal endpoint placeholder. If Gemini multimodal is configured,
    # route image bytes to model in a future extension.
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Image file is empty")

    size_kb = round(len(data) / 1024, 2)
    return JSONResponse(
        {
            "message": "Image received. Connect Gemini Vision call in llm_client for detailed captioning.",
            "size_kb": size_kb,
            "filename": file.filename,
        }
    )


@app.post("/assistant/document/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    mode: str = Form(default="summary"),
    instructions: str = Form(default=""),
    user_id: str = Form(default="web-ui-user"),
    session_id: str = Form(default=""),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Document file is empty")

    clean_mode = (mode or "summary").strip().lower()
    if clean_mode not in {"summary", "extract"}:
        raise HTTPException(status_code=400, detail="mode must be 'summary' or 'extract'")

    extracted = _extract_document_text(data, file.filename or "", file.content_type or "")
    if not extracted:
        raise HTTPException(
            status_code=400,
            detail=(
                "No text could be extracted from this file. "
                "Use a text-based PDF/TXT/CSV/JSON file, or provide OCR output for scanned documents."
            ),
        )

    doc_text = sanitize_text(extracted, 20000)
    raw_instructions = (instructions or "").strip()
    user_instructions = ""
    if raw_instructions:
        user_instructions = sanitize_text(raw_instructions, 1000)

    if clean_mode == "summary":
        prompt = (
            "You are a document summarization assistant. "
            "Write a concise summary with key points and action items.\n\n"
            f"Document text:\n{doc_text}\n"
        )
    else:
        schema_hint = user_instructions or "Return JSON with keys: key_points, entities, dates, amounts, action_items"
        prompt = (
            "You are a document data extraction assistant. "
            "Extract requested fields and return valid JSON only.\n\n"
            f"Extraction instructions: {schema_hint}\n\n"
            f"Document text:\n{doc_text}\n"
        )

    result = llm_client.generate_text(prompt)

    clean_user = user_id.strip() or "web-ui-user"
    resolved_session_id = history_store.save_message(
        user_id=clean_user,
        role="user",
        content=f"Analyze file: {file.filename or 'uploaded-file'} ({clean_mode})",
        input_mode="text",
        session_id=session_id,
    )
    history_store.save_message(
        user_id=clean_user,
        role="assistant",
        content=result,
        input_mode="text",
        used_tool="document_analyze",
        session_id=resolved_session_id or session_id,
    )

    parsed_json = None
    if clean_mode == "extract":
        candidate = result.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                candidate = "\n".join(lines[1:-1]).strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
        try:
            parsed_json = json.loads(candidate)
        except Exception:
            parsed_json = None

    return JSONResponse(
        {
            "filename": file.filename,
            "mode": clean_mode,
            "user_id": clean_user,
            "session_id": resolved_session_id or session_id,
            "text_preview": doc_text[:500],
            "result": result,
            "result_json": parsed_json,
        }
    )
