import os
import smtplib
import feedparser
import time
import urllib.parse
import random
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/1qUmD7Hdfp", 
    "cat": "https://s.shopee.tw/1LYVcCJXgk", "kitten": "https://s.shopee.tw/1LYVcCJXgk", "meow": "https://s.shopee.tw/1LYVcCJXgk",
    "dog": "https://s.shopee.tw/1VrvoVIuLn", "puppy": "https://s.shopee.tw/1VrvoVIuLn", "bark": "https://s.shopee.tw/1VrvoVIuLn",
    "food": "https://s.shopee.tw/10vfDaKoMi", "treat": "https://s.shopee.tw/10vfDaKoMi", "eat": "https://s.shopee.tw/10vfDaKoMi",
    "toy": "https://s.shopee.tw/1BF5PtKB1l", "play": "https://s.shopee.tw/1BF5PtKB1l", "pet": "https://s.shopee.tw/1BF5PtKB1l"
}

genai.configure(api_key=GOOGLE_API_KEY)
def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return genai.GenerativeModel(m.name)
    except: return None
model = get_valid_model()
RSS_URL = "https://news.google.com/rss/search?q=pet+care+cute+animals&hl=en-US&gl=US&ceid=US:en"

def get_pet_image(title):
    magic_prompt = f"{title}, cute fluffy animals, close up shot, adorable eyes, highly detailed, 8k resolution, cinematic lighting"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>'

def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default": return link
    return SHOPEE_LINKS["default"]

def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    
    # === 寵物人格轉盤 ===
    styles = [
        "風格：一位『卑微的鏟屎官』，對家裡的貓主子唯命是從，語氣幽默自嘲，稱呼寵物為『皇上』或『主子』。",
        "風格：一位『寵物溝通師』(自稱)，喜歡模擬寵物的內心獨白，用第一人稱『本喵』或『本汪』來寫作。",
        "風格：一位『溺愛毛孩的傻爸爸』，覺得自家寵物做什麼都對，語氣充滿溺愛和誇張的讚美。",
        "風格：一位『嚴肅的獸醫助理』，重視健康和營養，會認真分析飼料成分，給出專業建議。"
    ]
    selected_style = random.choice(styles)
    print(f"🤖 AI 今日人格：{selected_style}")

    prompt = f"""
    任務：將以下英文新聞改寫成「寵物趣聞」部落格文章。
    【標題】{title}
    【摘要】{summary}
    
    【寫作指令】
    1. **請嚴格扮演此角色**：{selected_style}
    2. **SEO標題**：必須包含「推薦、評價、必買、鏟屎官必看、貓砂推薦」其中之一。
    3. **中段導購**：在第二段結束後，自然插入一句「💡 我家毛孩最愛的都在這 (點此查看)」，並設為超連結({shopee_link})。
    
    【回傳 JSON】：{{"category": "寵物日記", "html_body": "HTML內容"}}
    【文末按鈕】：<br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#FF9900;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;">🐾 毛孩最愛好物 (蝦皮特價)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "寵物日記"), data.get("html_body", "")
    except: return "寵物快訊", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

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
        print(f"✅ 發布成功：{category}")
    except: pass

if __name__ == "__main__":
    if not GMAIL_APP_PASSWORD or not model: exit(1)
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_pet_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html: send_email(entry.title, category, img_html + text_html)
    else: print("📭 無新文章")
