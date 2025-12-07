import os
import smtplib
import feedparser
import time
import urllib.parse
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 【賺錢核心】寵物用品蝦皮連結 =================
SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/1qUmD7Hdfp", 
    "cat": "https://s.shopee.tw/1LYVcCJXgk", "kitten": "https://s.shopee.tw/1LYVcCJXgk", "meow": "https://s.shopee.tw/1LYVcCJXgk",
    "dog": "https://s.shopee.tw/1VrvoVIuLn", "puppy": "https://s.shopee.tw/1VrvoVIuLn", "bark": "https://s.shopee.tw/1VrvoVIuLn",
    "food": "https://s.shopee.tw/10vfDaKoMi", "treat": "https://s.shopee.tw/10vfDaKoMi", "eat": "https://s.shopee.tw/10vfDaKoMi",
    "toy": "https://s.shopee.tw/1BF5PtKB1l", "play": "https://s.shopee.tw/1BF5PtKB1l", "pet": "https://s.shopee.tw/1BF5PtKB1l"
}

# ================= 3. AI 設定 =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    return genai.GenerativeModel(m.name)
        return None
    except:
        return None

model = get_valid_model()
# 🔥 優化：改用 Google News RSS (寵物關鍵字)
RSS_URL = "https://news.google.com/rss/search?q=pet+care+cute+animals&hl=en-US&gl=US&ceid=US:en"

# ================= 4. 萌寵風格圖片生成 =================
def get_pet_image(title):
    magic_prompt = f"{title}, cute fluffy animals, close up shot, adorable eyes, highly detailed, 8k resolution, cinematic lighting"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>'

# ================= 5. 智慧選連結 =================
def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default":
            print(f"💰 偵測到毛孩商機：[{keyword}]")
            return link
    return SHOPEE_LINKS["default"]

# ================= 6. AI 寫作 (SEO 優化版) =================
def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    print(f"🤖 AI 正在撰寫寵物文章：{title}...")
    
    # 🔥 SEO 優化 Prompt
    prompt = f"""
    任務：將以下英文新聞改寫成「繁體中文」的「寵物趣聞/好物推薦」部落格文章。
    
    【標題】{title}
    【摘要】{summary}
    
    【SEO 關鍵字策略 (標題必填)】
    1. 標題必須包含：推薦、評價、必買、Dcard熱推、鏟屎官必看、貓砂推薦 (擇一使用)。
    2. 標題範例：「{title}？飼主實測心得分享」。

    【內文結構要求】
    1. **可愛開頭**：用「各位奴才們好」或「毛孩爸媽看過來」開頭。
    2. **新聞/知識分享**：用簡單易懂的方式說明。
    3. **中段廣告 (重要)**：在第二段結束後，自然插入一句「💡 我家毛孩最愛的都在這 (點此查看)」，並設為超連結({shopee_link})。
    4. **重點整理**：條列式重點。
    5. **結尾**：呼籲大家對毛孩好一點。
    
    【回傳格式 (JSON)】：
    {{
        "category": "寵物日記",
        "html_body": "這裡填 HTML 內容"
    }}
    
    【文末按鈕】：
    <br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#FF9900;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🐾 毛孩最愛好物 (蝦皮特價)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "寵物日記"), data.get("html_body", "")
    except Exception as e:
        print(f"❌ AI 處理失敗: {e}")
        return "寵物快訊", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

# ================= 7. 寄信 =================
def send_email(subject, category, body_html):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = f"{subject} #{category}"
    msg.attach(MIMEText(body_html, 'html'))
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 寵物文章已發布！分類：{category}")
    except Exception as e:
        print(f"❌ 寄信失敗: {e}")

# ================= 8. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (萌寵版)...")
    if not GMAIL_APP_PASSWORD or not model: exit(1)
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        print(f"📄 處理文章：{entry.title}")
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_pet_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html:
            send_email(entry.title, category, img_html + text_html)
    else:
        print("📭 無新文章")
