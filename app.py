import os
from flask import Flask, request, jsonify, render_template_string
from groq import Groq

app = Flask(__name__)

# حط مفتاح Groq المجاني بتاعك هنا
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

# صفحة الواجهة الأمامية كود واحد مدمج عشان تسهل عليكِ الرفع
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حاسبة السعرات الذكية - مصر</title>
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
        <p style="text-align: color: #666; font-size: 14px;">اكتب أكل ايه اللي عندك في الثلاجة أو سعراتك المطلوبة، وهقولك تعمل إيه!</p>
        <textarea id="userInput" placeholder="مثال: عندي بيض وجبن وزيت وعايز 500 سعرة للفطار..."></textarea>
        <button onclick="sendData()">احسب الوجبة</button>
        <div class="result" id="resultBox">الرد هيظهر هنا...</div>
    </div>

    <script>
        async function sendData() {
            const text = document.getElementById('userInput').value;
            const resultBox = document.getElementById('resultBox');
            if(!text) { alert('اكتب حاجة الأول!'); return; }
            
            resultBox.innerText = 'جاري التفكير وتظظبيط السعرات... ⏳';
            
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
    
    system_prompt = (
        "أنت أخصائي تغذية مصري شاطر وبسيط. المستخدم بيكلمك عشان تحسب له سعراته "
        "أو تقترح عليه وجبة بالمكونات المتاحة عنده في البيت. "
        "رد عليه باللهجة المصرية الدارجة وبشكل عملي وسهل (استخدم المعلقة، الرغيف، والقطعة بدل الجرامات المعقدة)."
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        )
        reply = chat_completion.choices[0].message.content
    except Exception as e:
        reply = "حصل خطأ بسيط، جرب تاني كمان شوية."

    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
