import os
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PAGE_ACCESS_TOKEN  = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN       = os.environ.get("VERIFY_TOKEN", "bis_school_2024")
APP_SECRET         = os.environ.get("APP_SECRET", "")

def load_school_data():
    try:
        path = os.path.join(os.path.dirname(__file__), "school_data.txt")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

SCHOOL_DATA = load_school_data()

SYSTEM_PROMPT = f"""أنت مساعد ذكي للمدرسة البريطانية الدولية في غزة (BIS Palestine).
مهمتك الرد على استفسارات أولياء الأمور والطلاب عبر فيسبوك ماسنجر بشكل ودي ومحترف.
قواعد مهمة:
1. استخدم فقط المعلومات في بيانات المدرسة أدناه
2. إذا لم تجد إجابة: "يرجى التواصل مع الإدارة: 00970593115112"
3. ردودك دائماً بالعربية — مختصرة (3-4 أسطر)
4. عند السؤال عن التسجيل: واتساب الإدارة 00970593115112
بيانات المدرسة:
{SCHOOL_DATA}"""

conversations = {}

def get_ai_response(sender_id, user_message):
    try:
        if sender_id not in conversations:
            conversations[sender_id] = []

        conversations[sender_id].append({
            "role": "user",
            "content": user_message
        })

        if len(conversations[sender_id]) > 20:
            conversations[sender_id] = conversations[sender_id][-20:]

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bis-ai-bot.onrender.com",
                "X-Title": "BIS School Bot"
            },
            json={
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ] + conversations[sender_id],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            conversations[sender_id].append({
                "role": "assistant",
                "content": reply
            })
            return reply
        else:
            print(f"[ERROR] OpenRouter {response.status_code}: {response.text}")
            return "عذراً، حدث خطأ مؤقت. يرجى التواصل على: 00970593115112"

    except Exception as e:
        print(f"[ERROR] get_ai_response: {e}")
        return "عذراً، حدث خطأ مؤقت. يرجى التواصل على: 00970593115112"

FB_API = "https://graph.facebook.com/v19.0/me/messages"

def send_message(recipient_id, text):
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    for chunk in chunks:
        try:
            requests.post(FB_API,
                params={"access_token": PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": chunk},
                    "messaging_type": "RESPONSE"
                },
                timeout=10)
        except Exception as e:
            print(f"[ERROR] send: {e}")

def send_typing(recipient_id):
    try:
        requests.post(FB_API,
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={"recipient": {"id": recipient_id}, "sender_action": "typing_on"},
            timeout=5)
    except:
        pass

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("[OK] Webhook verified!")
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook_receive():
    data = request.get_json(silent=True)
    if not data or data.get("object") != "page":
        return "OK", 200
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]
            if "message" in event:
                msg = event["message"]
                if msg.get("is_echo"):
                    continue
                text = msg.get("text", "").strip()
                if not text:
                    continue
                print(f"[IN] {sender_id}: {text}")
                send_typing(sender_id)
                reply = get_ai_response(sender_id, text)
                send_message(sender_id, reply)
                print(f"[OUT] {reply[:80]}")
            elif "postback" in event:
                payload = event["postback"].get("payload", "مرحبا")
                send_typing(sender_id)
                send_message(sender_id, get_ai_response(sender_id, payload))
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "BIS School Bot is running",
        "school_data": "loaded" if SCHOOL_DATA else "MISSING",
        "ai": "OpenRouter / Gemini 2.0 Flash",
        "messenger": "ok" if PAGE_ACCESS_TOKEN else "not set yet"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)