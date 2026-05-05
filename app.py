import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PAGE_ACCESS_TOKEN  = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN       = os.environ.get("VERIFY_TOKEN", "bis_school_2024")

def load_school_data():
    try:
        path = os.path.join(os.path.dirname(__file__), "school_data.txt")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

SCHOOL_DATA = load_school_data()

SYSTEM_PROMPT = f"""أنت مساعد ذكي ودود للمدرسة البريطانية الدولية في فلسطين (BIS Palestine).
مهمتك الرد على استفسارات أولياء الأمور والطلاب عبر فيسبوك ماسنجر بأسلوب احترافي وودود.

📌 قواعد الرد:
1. استخدم فقط المعلومات الموجودة في بيانات المدرسة أدناه
2. إذا لم تجد إجابة محددة في البيانات، لا تقل "لا أعلم" بشكل جاف — بل:
   - أظهر تفهماً وتقديراً للسؤال (مثلاً: "نقدّر اهتمامك بهذا الأمر 💙")
   - اذكر أن هذه التفاصيل تحتاج تنسيقاً مباشراً مع الإدارة
   - وجّه للتواصل: "يسعدنا مساعدتك عبر واتساب: 00970593115112"
   - اجعل الرد دافئاً وإيجابياً وليس رفضاً
3. ردودك دائماً بالعربية الفصحى السهلة
4. نسّق ردودك بشكل جميل ومرتب كالتالي:
   - ابدأ بتحية مختصرة ودافئة مثل "أهلاً وسهلاً! 😊"
   - استخدم الرموز التعبيرية المناسبة لكل موضوع (📚 للمناهج، 💰 للرسوم، 📝 للتسجيل، 📞 للتواصل، ✅ للشروط)
   - استخدم نقاط واضحة (•) لتعداد المعلومات
   - افصل بين الأفكار بسطر فارغ
   - اختم بعرض المساعدة: "هل تحتاج لمزيد من المعلومات؟ 😊"
5. الرد يجب أن يكون شاملاً ومفيداً لكن غير مطوّل جداً (5-8 أسطر مثالية)
6. عند السؤال عن التسجيل: أذكر واتساب الإدارة 00970593115112

بيانات المدرسة:
{SCHOOL_DATA}"""

# Welcome message sent when user first starts chatting
WELCOME_MESSAGE = """🏫 أهلاً وسهلاً بكم في المدرسة البريطانية الدولية!

أنا مساعدكم الذكي، يسعدني مساعدتكم في الاستفسار عن:

📝 القبول والتسجيل
💰 الرسوم الدراسية
📚 المناهج والبرامج
⏰ المواعيد والدوام
📞 التواصل مع الإدارة
🎯 الأنشطة والفعاليات

كيف يمكنني مساعدتكم اليوم؟ 😊"""

conversations = {}

def get_ai_response(sender_id, user_message):
    try:
        if sender_id not in conversations:
            conversations[sender_id] = []

        conversations[sender_id].append({
            "role": "user",
            "content": user_message
        })

        # Keep last 20 messages to avoid token overflow
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
                "max_tokens": 600,
                "temperature": 0.6
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
            return "⚠️ عذراً، حدث خطأ مؤقت.\nيرجى التواصل معنا مباشرة على واتساب: 00970593115112"

    except Exception as e:
        print(f"[ERROR] get_ai_response: {e}")
        return "⚠️ عذراً، حدث خطأ مؤقت.\nيرجى التواصل معنا مباشرة على واتساب: 00970593115112"

FB_API = "https://graph.facebook.com/v19.0/me/messages"

def send_message(recipient_id, text):
    """Send message, splitting if over 2000 chars"""
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    for chunk in chunks:
        try:
            requests.post(
                FB_API,
                params={"access_token": PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": chunk},
                    "messaging_type": "RESPONSE"
                },
                timeout=10
            )
        except Exception as e:
            print(f"[ERROR] send_message: {e}")

def send_typing(recipient_id):
    """Show typing indicator"""
    try:
        requests.post(
            FB_API,
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={"recipient": {"id": recipient_id}, "sender_action": "typing_on"},
            timeout=5
        )
    except:
        pass

def set_get_started():
    """Set up the Get Started button"""
    try:
        requests.post(
            "https://graph.facebook.com/v19.0/me/messenger_profile",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={
                "get_started": {"payload": "GET_STARTED"},
                "greeting": [
                    {
                        "locale": "default",
                        "text": "🏫 مرحباً بك في المدرسة البريطانية الدولية! اضغط 'ابدأ' للحصول على المساعدة."
                    },
                    {
                        "locale": "ar_AR",
                        "text": "🏫 مرحباً بك في المدرسة البريطانية الدولية! اضغط 'ابدأ' للحصول على المساعدة."
                    }
                ],
                "persistent_menu": [
                    {
                        "locale": "default",
                        "composer_input_disabled": False,
                        "call_to_actions": [
                            {
                                "type": "postback",
                                "title": "📝 التسجيل والقبول",
                                "payload": "REGISTRATION_INFO"
                            },
                            {
                                "type": "postback",
                                "title": "💰 الرسوم الدراسية",
                                "payload": "FEES_INFO"
                            },
                            {
                                "type": "postback",
                                "title": "📚 المناهج والبرامج",
                                "payload": "CURRICULUM_INFO"
                            },
                            {
                                "type": "postback",
                                "title": "📞 تواصل مع الإدارة",
                                "payload": "CONTACT_INFO"
                            }
                        ]
                    }
                ]
            },
            timeout=10
        )
        print("[OK] Messenger profile set!")
    except Exception as e:
        print(f"[ERROR] set_get_started: {e}")

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
                payload = event["postback"].get("payload", "")

                if payload == "GET_STARTED":
                    send_message(sender_id, WELCOME_MESSAGE)
                elif payload == "REGISTRATION_INFO":
                    send_typing(sender_id)
                    send_message(sender_id, get_ai_response(sender_id, "أخبرني عن التسجيل والقبول في المدرسة"))
                elif payload == "FEES_INFO":
                    send_typing(sender_id)
                    send_message(sender_id, get_ai_response(sender_id, "ما هي الرسوم الدراسية لجميع المراحل؟"))
                elif payload == "CURRICULUM_INFO":
                    send_typing(sender_id)
                    send_message(sender_id, get_ai_response(sender_id, "ما هي المناهج والبرامج التعليمية؟"))
                elif payload == "CONTACT_INFO":
                    send_message(sender_id, "📞 للتواصل مع إدارة المدرسة البريطانية الدولية:\n\n• واتساب: 00970593115112\n• البريد الإلكتروني: financial@bis.edu.ps\n\nنرحب بتواصلكم في أي وقت! 😊")
                else:
                    send_typing(sender_id)
                    send_message(sender_id, get_ai_response(sender_id, payload))

    return "OK", 200

@app.route("/setup", methods=["GET"])
def setup():
    """Run this once to configure Messenger profile"""
    set_get_started()
    return jsonify({"status": "Messenger profile configured!", "menu": "set"})

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ BIS School Bot is running",
        "school_data": "loaded ✅" if SCHOOL_DATA else "MISSING ❌",
        "ai_model": "Google Gemini 2.0 Flash via OpenRouter",
        "messenger": "configured ✅" if PAGE_ACCESS_TOKEN else "not set ❌",
        "tip": "Visit /setup once to configure Messenger welcome message and menu"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)