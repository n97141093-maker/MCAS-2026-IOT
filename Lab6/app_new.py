import os
import threading
import time
import traceback
import uuid
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from openai import OpenAI


# =========================
# Environment Variables
# =========================

load_dotenv()

# 使用 OpenAI 相容 API：
# OpenAI、DeepSeek、Groq、OpenRouter、Ollama（本機）等
# 只要改 .env 的 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 就能切換
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None  # 空白 = OpenAI 官方
LLM_MODEL = os.getenv("LLM_MODEL")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "你是一個友善的助理，請使用繁體中文回答。",
)

# 每個對話最多保留幾則訊息（避免越聊越慢、越貴）
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))

SECRET_KEY = os.getenv("SECRET_KEY")

if not LLM_API_KEY:
    raise RuntimeError(
        "找不到 LLM_API_KEY，請在 .env 填入 API Key。"
        "（Ollama 本機模型可隨便填，例如 ollama）"
    )

if not LLM_MODEL:
    raise RuntimeError(
        "找不到 LLM_MODEL，請在 .env 填入模型名稱。"
    )

if not SECRET_KEY or SECRET_KEY == "CHANGE_ME":
    raise RuntimeError(
        "請在 .env 設定安全的 SECRET_KEY。"
    )


# =========================
# Flask
# =========================

app = Flask(__name__)
app.secret_key = SECRET_KEY


# Lab 用簡化帳號
# 正式系統不應以明文保存密碼
USERS = {
    "admin": "1234",
}


# =========================
# LLM
# =========================

llm_client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    timeout=LLM_TIMEOUT,
)

# 對話紀錄存在伺服器記憶體
# （Flask session 是 cookie，只有約 4KB，放不下對話內容）
# server 重啟後紀錄會清空，Lab 用足夠
CONVERSATIONS = {}
CONVERSATIONS_LOCK = threading.Lock()


def get_history(conv_id):
    with CONVERSATIONS_LOCK:
        return list(CONVERSATIONS.get(conv_id, []))


def save_history(conv_id, history):
    with CONVERSATIONS_LOCK:
        CONVERSATIONS[conv_id] = history[-MAX_HISTORY:]


def ask_llm(message, history):
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": message}]
    )

    print(
        f"[LLM] 送出請求 model={LLM_MODEL}",
        flush=True,
    )
    start = time.time()

    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
    )

    print(
        f"[LLM] 收到回應，耗時 {time.time() - start:.1f} 秒",
        flush=True,
    )

    reply = (
        response.choices[0].message.content or ""
    ).strip()

    if not reply:
        reply = "模型沒有回傳文字內容。"

    return reply


# =========================
# Login Required
# =========================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user" not in session:

            # API 不做 redirect
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "請先登入"
                }), 401

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


# =========================
# Login
# =========================

@app.route(
    "/",
    methods=["GET", "POST"],
)
def login():

    if request.method == "POST":

        username = (
            request.form
            .get("username", "")
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        if (
            username in USERS
            and USERS[username] == password
        ):

            session.clear()

            session["user"] = username

            return redirect(
                url_for("chat_room")
            )

        return render_template(
            "login.html",
            msg="帳號或密碼錯誤",
        )

    if "user" in session:
        return redirect(
            url_for("chat_room")
        )

    return render_template(
        "login.html"
    )


# =========================
# Chat Page
# =========================

@app.get("/chat")
@login_required
def chat_room():

    return render_template(
        "chat.html",
        username=session["user"],
        model=LLM_MODEL,
    )


# =========================
# Chat API
# =========================

@app.post("/api/chat")
@login_required
def api_chat():

    print("[API] 收到 /api/chat 請求", flush=True)

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "error": "訊息不可為空"
        }), 400

    if len(message) > 2000:
        return jsonify({
            "error": "訊息過長"
        }), 400

    # 每個登入者一個對話 ID
    conv_id = session.get("conv_id")
    if not conv_id:
        conv_id = uuid.uuid4().hex
        session["conv_id"] = conv_id

    try:

        history = get_history(conv_id)

        reply = ask_llm(message, history)

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})
        save_history(conv_id, history)

        return jsonify({
            "reply": reply
        })

    except Exception as error:

        print(
            "[LLM API Error]",
            type(error).__name__,
            error,
            flush=True,
        )
        traceback.print_exc()

        return jsonify({
            "error":
            "模型 API 呼叫失敗，"
            "請檢查 API Key、網路或模型設定。"
        }), 502


# =========================
# Reset Conversation
# =========================

@app.post("/api/reset")
@login_required
def reset_chat():

    conv_id = session.pop("conv_id", None)

    if conv_id:
        with CONVERSATIONS_LOCK:
            CONVERSATIONS.pop(conv_id, None)

    return jsonify({
        "ok": True
    })


# =========================
# Logout
# =========================

@app.post("/logout")
@login_required
def logout():

    conv_id = session.get("conv_id")
    if conv_id:
        with CONVERSATIONS_LOCK:
            CONVERSATIONS.pop(conv_id, None)

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================
# Run Server
# =========================

if __name__ == "__main__":

    print("=== Lab6 Flask Server ===")
    print("Listening on http://0.0.0.0:3000")
    print(f"LLM base URL: {LLM_BASE_URL or 'OpenAI 官方'}")
    print(f"LLM model: {LLM_MODEL}")
    print("Debug mode is OFF")

    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False,
        threaded=True,
    )