import os
import time
import traceback
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
from google import genai
from google.genai import types


# =========================
# Environment Variables
# =========================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)

# Gemini API 逾時秒數（避免請求卡住、畫面沒有任何回應）
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "30"))

if not GEMINI_API_KEY:
    raise RuntimeError(
        "找不到 GEMINI_API_KEY，請先建立 .env 並填入 API Key。"
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
# Gemini
# =========================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    # timeout 單位是毫秒
    http_options=types.HttpOptions(
        timeout=GEMINI_TIMEOUT * 1000,
    ),
)


def extract_text(interaction):
    """
    取出 Gemini 回傳的文字。
    先試 output_text，沒有的話再從 outputs 裡找 text。
    """

    text = getattr(interaction, "output_text", None)
    if text:
        return text

    parts = []
    for output in getattr(interaction, "outputs", None) or []:
        output_text = getattr(output, "text", None)
        if output_text:
            parts.append(output_text)

    return "\n".join(parts)


def ask_gemini(
    message,
    previous_interaction_id=None,
):
    params = {
        "model": GEMINI_MODEL,
        "input": message,
    }

    if previous_interaction_id:
        params["previous_interaction_id"] = (
            previous_interaction_id
        )

    print(
        f"[Gemini] 送出請求 model={GEMINI_MODEL}",
        flush=True,
    )
    start = time.time()

    interaction = (
        gemini_client.interactions.create(
            **params
        )
    )

    print(
        f"[Gemini] 收到回應，耗時 {time.time() - start:.1f} 秒",
        flush=True,
    )

    reply = extract_text(interaction).strip()

    if not reply:
        reply = "Gemini 沒有回傳文字內容。"

    return reply, interaction.id


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
    )


# =========================
# Gemini API
# =========================

@app.post("/api/chat")
@login_required
def api_chat():

    # 請求一進來就印出，確認前端有沒有送到後端
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

    try:

        previous_id = session.get(
            "gemini_interaction_id"
        )

        reply, interaction_id = (
            ask_gemini(
                message,
                previous_id,
            )
        )

        # 保存本次 interaction ID
        # 下一輪即可延續對話
        session[
            "gemini_interaction_id"
        ] = interaction_id

        return jsonify({
            "reply": reply
        })

    except Exception as error:

        # 印出完整錯誤，方便除錯
        print(
            "[Gemini API Error]",
            type(error).__name__,
            error,
            flush=True,
        )
        traceback.print_exc()

        return jsonify({
            "error":
            "Gemini API 呼叫失敗，"
            "請檢查 API Key、網路或模型設定。"
        }), 502


# =========================
# Reset Conversation
# =========================

@app.post("/api/reset")
@login_required
def reset_chat():

    session.pop(
        "gemini_interaction_id",
        None,
    )

    return jsonify({
        "ok": True
    })


# =========================
# Logout
# =========================

@app.post("/logout")
@login_required
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================
# Run Server
# =========================

if __name__ == "__main__":

    print(
        "=== Lab6 Flask Server ==="
    )

    print(
        "Listening on "
        "http://0.0.0.0:3000"
    )

    print(
        f"Gemini model: {GEMINI_MODEL}"
    )

    print(
        "Debug mode is OFF"
    )

    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False,
        threaded=True,
    )