import os
import threading
from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import telebot

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYSTEM_PROMPT = (
    "أنت أخصائي تغذية مصري شاطر وبسيط. المستخدم بيكلمك عشان تحسب له سعراته "
    "أو تقترح عليه وجبة بالمكونات المتاحة عنده في البيت. "
    "رد عليه باللهجة المصرية الدارجة وبشكل عملي وسهل (استخدم المعلقة، الرغيف، والقطعة بدل الجرامات المعقدة)."
)

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
        textarea { width: 100%; height: 90px; padding: 10px; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px; font-size: 16px; box-sizing: border-box; }
        .btn-group { display: flex; gap: 10px; margin-bottom: 10px; }
        button { flex: 1; background: #27ae60; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; cursor: pointer; }
        button.mic-btn { background: #e74c3c; }
        button:hover { opacity: 0.9; }
        .result { margin-top: 20px; background: #e8f8f5; padding: 15px; border-radius: 8px; white-space: pre-wrap; font-size: 16px; color: #111; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🍽️ شيف السعرات المصري</h2>
        <p style="color: #666; font-size: 14px; text-align: center;">اكتب طلبك أو سجل صوتي باللي في ثلاجتك!</p>
        
        <textarea id="userInput" placeholder="مثال: عندي بيض وجبن وعايز 500 سعرة..."></textarea>
        
        <div class="btn-group">
            <button onclick="sendData()">احسب الوجبة</button>
            <button class="mic-btn" id="micBtn" onclick="toggleRecord()">🎤 تسجيل صوتي</button>
        </div>

        <div class="result" id="resultBox">الرد هيظهر هنا...</div>
    </div>

    <script>
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;

        async function sendData() {
            const text = document.getElementById('userInput').value;
            const resultBox = document.getElementById('resultBox');
            if(!text) { alert('اكتب حاجة أو سجل صوت الأول!'); return; }
            resultBox.innerText = 'جاري التفكير وتظبيط السعرات... ⏳';
            
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            resultBox.innerText = data.reply;
        }

        async function toggleRecord() {
            const micBtn = document.getElementById('micBtn');
            const resultBox = document.getElementById('resultBox');

            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const formData = new FormData();
                        formData.append('audio', audioBlob, 'voice.webm');

                        resultBox.innerText = 'جاري سماع وتحليل الريكورد المصري... 🎙️';

                        const response = await fetch('/voice-ask', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        resultBox.innerText = data.reply;
                    };

                    mediaRecorder.start();
                    isRecording = true;
                    micBtn.innerText = '⏹️ إيقاف وإرسال';
                    micBtn.style.background = '#c0392b';
                } catch (err) {
                    alert('مصرّح لى بالوصول للمايك؟ تأكد من السماح له من المتصفح.');
                }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                micBtn.innerText = '🎤 تسجيل صوتي';
                micBtn.style.background = '#e74c3c';
            }
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
            model="llama-3.1-8b-instant",  # الموديل المستقر الجديد
            temperature=0.7,
        )
        reply = chat_completion.choices[0].message.content
    except Exception as e:
        reply = f"خطأ تقني: {str(e)}"
    return jsonify({'reply': reply})

@app.route('/voice-ask', methods=['POST'])
def voice_ask():
    if 'audio' not in request.files:
        return jsonify({'reply': 'مفيش صوت وصل للسيرفر!'})
    
    audio_file = request.files['audio']
    audio_path = "temp_web_voice.webm"
    audio_file.save(audio_path)

    try:
        # تحويل الصوت لنص باستخدام Whisper من Groq
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(audio_path, f.read()),
                model="whisper-large-v3",
                language="ar",
                response_format="text"
            )
        user_text = transcription
        
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # الرد بالذكاء الاصطناعي
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        reply = f"🗣️ سمعت منك: \"{user_text}\"\n\n{chat_completion.choices[0].message.content}"
    except Exception as e:
        reply = f"خطأ في معالجة الصوت: {str(e)}"
        
    return jsonify({'reply': reply})

# بوت تليجرام
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
            with open(voice_path, 'wb') as f:
                f.write(downloaded_file)
            
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
        except Exception:
            bot.reply_to(message, "معلش مسمعتش الريكورد، جرب تاني.")
            return

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            model="llama3-8b-8192",
            temperature=0.7,
        )
        ai_response = chat_completion.choices[0].message.content
    except Exception:
        ai_response = "حصل خطأ بسيط، جرب تاني."

    bot.reply_to(message, ai_response)

def run_telegram_bot():
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception:
        pass

if __name__ == '__main__':
    t = threading.Thread(target=run_telegram_bot)
    t.daemon = True
    t.start()
    
    app.run(host='0.0.0.0', port=5000)
