import os
from flask import Flask, request, jsonify, render_template_string
from groq import Groq

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "أنت نظام ذكي لتصميم الوجبات المصرية. مطلوب منك بناءً على المكونات أو السعرات المطلوبة "
    "أن ترد بتنسيق منظم وواضح جداً (مش فقرة كلام طويلة)، يحتوي على: "
    "1. اسم الوجبة المقترحة. "
    "2. إجمالي السعرات الحرارية بدقة قريبة من الرقم المطلوب. "
    "3. المكونات بالكميات البلدية العملية (رغيف، معلقة، قطعه، كوب). "
    "رد باللهجة المصرية البسيطة والعملية."
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شيف الثلاجة المصري الذكي</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f0f2f5; margin: 0; padding: 15px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 480px; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h2 { text-align: center; color: #2c3e50; margin-bottom: 5px; }
        p.subtitle { text-align: center; color: #7f8c8d; font-size: 13px; margin-bottom: 20px; }
        
        .section-title { font-weight: bold; color: #34495e; margin-bottom: 8px; font-size: 14px; display: flex; justify-content: space-between; align-items: center; }
        
        /* أزرار المكونات السريعة */
        .chips-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
        .chip { background: #eef2f7; border: 1px solid #dcdde1; padding: 10px; border-radius: 10px; text-align: center; font-size: 13px; cursor: pointer; transition: 0.2s; user-select: none; }
        .chip.active { background: #27ae60; color: white; border-color: #27ae60; }
        
        /* إضافة مكون مخصص */
        .add-box { display: flex; gap: 8px; margin-bottom: 20px; }
        .add-box input { flex: 1; padding: 10px; border: 1px solid #dcdde1; border-radius: 8px; font-size: 14px; }
        .add-btn { background: #2980b9; color: white; border: none; padding: 0 15px; border-radius: 8px; cursor: pointer; font-weight: bold; }

        /* شريط السعرات */
        .slider-box { background: #f8f9fa; padding: 12px; border-radius: 10px; border: 1px solid #e9ecef; margin-bottom: 20px; }
        .slider-box input[type=range] { width: 100%; accent-color: #27ae60; cursor: pointer; }
        .calories-value { color: #27ae60; font-weight: bold; font-size: 16px; }

        .action-btn { width: 100%; background: #27ae60; color: white; border: none; padding: 14px; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; }
        .action-btn:hover { background: #219653; }
        
        .result-card { margin-top: 20px; background: #e8f8f5; border-right: 5px solid #27ae60; padding: 15px; border-radius: 8px; white-space: pre-wrap; font-size: 15px; color: #2c3e50; display: none; line-height: 1.6; }
        .loading { text-align: center; color: #e67e22; font-weight: bold; margin-top: 15px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🍽️ شيف الثلاجة المصري</h2>
        <p class="subtitle">فصل وجبتك على ذوقك بالسعرات والمكونات المتاحة!</p>
        
        <div class="section-title">1. اختر المكونات المتوفرة عندك:</div>
        <div class="chips-grid" id="chipsContainer">
            <div class="chip active" onclick="toggleChip(this)" data-val="بيض">🥚 بيض</div>
            <div class="chip" onclick="toggleChip(this)" data-val="جبنة قريش">🧀 جبنة قريش</div>
            <div class="chip" onclick="toggleChip(this)" data-val="عيش بلدي">🫓 عيش بلدي</div>
            <div class="chip" onclick="toggleChip(this)" data-val="فول">🫘 فول</div>
            <div class="chip" onclick="toggleChip(this)" data-val="طعمية">🧆 طعمية</div>
            <div class="chip" onclick="toggleChip(this)" data-val="صدور فراخ/بانيه">🍗 فراخ / بانيه</div>
            <div class="chip" onclick="toggleChip(this)" data-val="رز مصري">🍚 رز</div>
            <div class="chip" onclick="toggleChip(this)" data-val="تونا">🐟 تونة</div>
            <div class="chip" onclick="toggleChip(this)" data-val="خضار وسلطة">🥗 سلطة وخضار</div>
        </div>

        <!-- إضافة مكون جديد -->
        <div class="add-box">
            <input type="text" id="customItemInput" placeholder="أضف منتج تاني (مثلاً: لانشون، بطاطس)...">
            <button class="add-btn" onclick="addCustomItem()">إضافة</button>
        </div>

        <!-- شريط السعرات المرن -->
        <div class="slider-box">
            <div class="section-title" style="margin-bottom: 5px;">
                <span>2. حدد السعرات المطلوبة للوجبة:</span>
                <span class="calories-value" id="calNum">500 سعرة</span>
            </div>
            <input type="range" id="caloriesRange" min="300" max="2000" step="50" value="500" oninput="updateCalories(this.value)">
        </div>

        <button class="action-btn" onclick="generateMeal()">اقتراح الوجبة المظبوطة ✨</button>
        
        <div class="loading" id="loadingDiv">جاري تظبيط السعرات وتصميم الوجبة... 🍳</div>
        <div class="result-card" id="resultCard"></div>
    </div>

    <script>
        function toggleChip(element) {
            element.classList.toggle('active');
        }

        function updateCalories(val) {
            document.getElementById('calNum').innerText = val + ' سعرة';
        }

        function addCustomItem() {
            const input = document.getElementById('customItemInput');
            const itemName = input.value.trim();
            if(!itemName) return;

            const grid = document.getElementById('chipsContainer');
            const newChip = document.createElement('div');
            newChip.className = 'chip active';
            newChip.setAttribute('data-val', itemName);
            newChip.innerText = '➕ ' + itemName;
            newChip.onclick = function() { toggleChip(this); };
            
            grid.appendChild(newChip);
            input.value = '';
        }

        async function generateMeal() {
            const selectedChips = document.querySelectorAll('.chip.active');
            let ingredients = Array.from(selectedChips).map(c => c.getAttribute('data-val')).join('، ');
            const targetCalories = document.getElementById('caloriesRange').value;

            if(!ingredients) {
                alert('من فضلك اختر أو أضف مكون واحد على الأقل!');
                return;
            }

            const promptText = `المكونات المتاحة عندي: ${ingredients}. والهدف بتاعي: تصميم وجبة تقترب من ${targetCalories} سعرة حرارية بالضبط. اقترح عليا الوجبة والمكونات بالكميات.`;

            const loadingDiv = document.getElementById('loadingDiv');
            const resultCard = document.getElementById('resultCard');
            
            loadingDiv.style.display = 'block';
            resultCard.style.display = 'none';

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: promptText })
                });
                const data = await response.json();
                resultCard.innerText = data.reply;
                resultCard.style.display = 'block';
            } catch (err) {
                resultCard.innerText = 'حصل خطأ، حاول تاني.';
                resultCard.style.display = 'block';
            } finally {
                loadingDiv.style.display = 'none';
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
            model="openai/gpt-oss-20b",
            temperature=0.7,
        )
        reply = chat_completion.choices[0].message.content
    except Exception as e:
        reply = f"خطأ تقني: {str(e)}"
    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
