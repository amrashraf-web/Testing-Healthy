import os
import threading
from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import telebot

app = Flask(__name__)

# حطي مفاتيحك هنا أو في متغيرات البيئة على Render
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYSTEM_PROMPT = (
    "أنت أخصائي تغذية مصري شاطر وبسيط. المستخدم بيكلمك عشان تحسب له سعراته "
    "أو تقترح عليه وجبة بالمكونات المتاحة عنده في البيت. "
    "رد عليه باللهجة المصرية الدارجة وبشكل عملي وسهل (استخدم المعلقة، الرغيف، والقطعة بدل الجرامات المعقدة)."
)

# --- 1. جزء موقع الويب (Frontend & API) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شيف السعرات المصري</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 480px; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #2c3e50; }
        textarea { width: 100%; height: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px; font-size: 16px; box-sizing: border-box; }
        button { width: 100%; background: #27ae60; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 18px; cursor: pointer; }
        button:hover { background: #219653; }
        .result { margin-top: 20px; background: #e8f8f5; padding: 15px; border-radius: 8px; white-space: pre-wrap; font-size: 16px; color: #111; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🍽️ شيف السعرات المصري</h2>
        <p style="color: #666; font-size: 14px;">اكتب أكلك أو سعراتك المطلوبة، وهقولك تعمل إيه!</p>
        <textarea id="userInput" placeholder="مثال: عندي بيض وجبن وعايز 500 سعرة..."></textarea>
        <button onclick="sendData()">احسب الوجبة</button>
        <div class="result" id="resultBox">الرد هيظهر هنا...</div>
    </div>
    <script>
        async function sendData() {
            const text = document.getElementById('userInput').value;
            const resultBox = document.getElementById('resultBox');
            if(!text) { alert('اكتب حاجة الأول!'); return; }
            resultBox.innerText = 'جاري التفكير وتظبيط السعرات... ⏳';
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            resultBox.innerText = data.reply;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask', methods=['POST'])
def ask():
    user_message = request.json.get('message', '')
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        reply = chat_completion.choices[0].message.content
    except Exception as e:
        reply = f"خطأ تقني: {str(e)}"
    return jsonify({'reply': reply})


# --- 2. جزء بوت تليجرام (دعم الريكوردات الصوتية باللهجة المصرية) ---
@bot.message_handler(content_types=['voice', 'text'])
def handle_telegram_input(message):
    user_text = ""
    if message.content_type == 'text':
        user_text = message.text
    elif message.content_type == 'voice':
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            voice_path = "user_voice.ogg"
            with open(voice_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            # استخدام Whisper من Groq لتحويل الصوت المصري لنص بدقة رهيبة
            with open(voice_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(voice_path, audio_file.read()),
                    model="whisper-large-v3",
                    language="ar",
                    response_format="text"
                )
            user_text = transcription
            if os.path.exists(voice_path):
                os.remove(voice_path)
        except Exception as e:
            bot.reply_to(message, "معلش، مسمعتش الريكورد كويس، جرب تسجله تاني.")
            return

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        ai_response = chat_completion.choices[0].message.content
    except Exception:
        ai_response = "حصل خطأ بسيط، جرب تاني كمان شوية."

    bot.reply_to(message, ai_response)


# تشغيل بوت تليجرام في خلفية السيرفر عشان يفضل شغال مع الموقع في نفس السيرفر
def run_telegram_bot():
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception:
        pass

if __name__ == '__main__':
    # تشغيل بوت تليجرام في خيط منفصل (Background Thread)
    t = threading.Thread(target=run_telegram_bot)
    t.daemon = True
    t.start()
    
    # تشغيل موقع الويب
    app.run(host='0.0.0.0', port=5000)
