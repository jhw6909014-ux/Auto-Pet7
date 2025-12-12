import os
import time
import random
import logging
import smtplib
import re
import urllib.parse
import feedparser
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError, NotFound
from email.mime.text import MIMEText
from email.header import Header

# --- V53 CONFIGURATION ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "專業部落客"
IMG_STYLE = "cute, close up, detailed fur"
KEYWORD_POOL = ["貓砂","貓飼料","狗飼料","寵物零食","貓跳台","寵物推車","魚油","潔牙骨","貓抓板","寵物玩具","牽繩","寵物床"]

# 保底模型 (萬一動態發現失敗)
FALLBACK_MODELS = ['gemini-flash-latest', 'gemini-1.5-flash', 'gemini-pro']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_rss():
    target_keyword = random.choice(KEYWORD_POOL)
    logger.info(f"🎯 鎖定關鍵字: {target_keyword}")
    encoded = urllib.parse.quote(target_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return rss_url, target_keyword

# --- V53 混合核心：動態發現 + 容錯 ---
def get_model_priority_list():
    """
    1. 嘗試問 Google 有什麼模型 (Service Discovery)
    2. 如果失敗，用保底清單
    3. 排序優化
    """
    logger.info("🔍 V53: 執行模型偵測...")
    valid_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
    except Exception as e:
        logger.warning(f"⚠️ 無法獲取模型列表 ({e})，使用保底清單。")
        return FALLBACK_MODELS

    if not valid_models:
        return FALLBACK_MODELS

    # 智慧排序: Flash 優先 (速度快), Pro 其次, 其他墊底
    valid_models.sort(key=lambda x: (
        0 if 'flash' in x and '1.5' in x else
        1 if 'flash' in x else
        2 if '1.5' in x else
        3 if 'pro' in x else
        4
    ))
    
    # 確保保底模型也在清單內 (去重複)
    for fm in FALLBACK_MODELS:
        is_in = False
        for vm in valid_models:
            if fm in vm: is_in = True
        if not is_in: valid_models.append(fm)

    logger.info(f"📋 攻擊清單: {valid_models}")
    return valid_models

def create_shopee_button(keyword):
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    css = """<style>@keyframes pulse{0%{transform:scale(1);}50%{transform:scale(1.05);}100%{transform:scale(1);}}.btn{animation:pulse 2s infinite;}</style>"""
    return css + f"""<div style="margin:50px 0;text-align:center;"><a href="{url}" class="btn" style="background:#e11d48;color:white;padding:15px 30px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:20px;">🔥 查看 {keyword} 最新優惠</a></div>"""

def get_hero_image(keyword):
    try:
        encoded = urllib.parse.quote(f"{keyword}, {IMG_STYLE}")
        seed = random.randint(1, 9999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
        return f'<div style="text-align:center;margin-bottom:30px;"><img src="{url}" style="width:100%;border-radius:10px;"></div>'
    except: return ""

def generate_robust(prompt):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    models = get_model_priority_list()
    
    for model_name in models:
        # 只嘗試 gemini 系列
        if 'gemini' not in model_name: continue
        
        logger.info(f"🚀 V53 嘗試模型: {model_name}")
        
        for attempt in range(3):
            try:
                # 這裡處理完整路徑名稱問題
                m_name = model_name
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                
                if response and response.text:
                    logger.info("✅ 生成成功！")
                    return response
            
            except NotFound:
                logger.warning(f"⚠️ {model_name} 404 Not Found. 跳過。")
                break # 直接換下一個模型
                
            except ResourceExhausted:
                wait = 70
                logger.warning(f"⚠️ {model_name} 429 限流。賴皮等待 {wait} 秒...")
                time.sleep(wait)
                continue # 同一個模型再試一次 (賴皮策略)
            
            except Exception as e:
                logger.error(f"❌ {model_name} 錯誤: {e} -> 換下一個")
                break # 換下一個模型
                
    return None

def main():
    logger.info("====================================")
    logger.info("🔰 V53 UNIFIED ARCHITECTURE BOT 🔰")
    logger.info("====================================")
    
    rss_url, target_keyword = get_dynamic_rss()
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return
        entry = feed.entries[0]
        logger.info(f"Processing: {entry.title}")
        
        prompt = f"""
        你是一位{BOT_PERSONA}。主題：{target_keyword}。新聞：{entry.title}。
        請直接輸出 HTML (不要 Markdown)。
        結構：<h2>副標題</h2><p>內文</p><table>規格表或比較表</table><h2>結論</h2>
        圖片插入 ((IMG: English Desc))
        """
        
        res = generate_robust(prompt)
        
        if res:
            html = res.text.replace("```html", "").replace("```", "")
            
            def replacer(m): 
                return f'<img src="https://image.pollinations.ai/prompt/{urllib.parse.quote(m.group(1))}?nologo=true" style="width:100%;border-radius:10px;margin:20px 0;">'
            html = re.sub(r'\(\(IMG:(.*?)\)\)', replacer, html)
            
            html = html.replace("<p>", '<p style="margin-bottom:25px;line-height:2.0;font-size:18px;color:#333;">')
            html = html.replace("<h2>", '<h2 style="color:#be123c;margin-top:40px;font-size:24px;border-bottom:2px solid #fda4af;padding-bottom:10px;font-weight:bold;">')
            if "<table>" in html:
                html = html.replace("<table>", '<div style="overflow-x:auto;"><table border="1" style="width:100%;border-collapse:collapse;margin:30px 0;border:2px solid #333;">')
                html = html.replace("</table>", '</table></div>')
                html = html.replace("td>", 'td style="padding:15px;border:1px solid #ccc;">')
                html = html.replace("th>", 'th style="background:#fff1f2;padding:15px;border:1px solid #333;font-weight:bold;">')

            final = get_hero_image(target_keyword) + html + create_shopee_button(target_keyword)
            
            sender = os.environ.get("GMAIL_USER")
            pwd = os.environ.get("GMAIL_APP_PASSWORD")
            to = os.environ.get("BLOGGER_EMAIL")
            
            msg = MIMEText(final, 'html', 'utf-8')
            msg['Subject'] = Header(f"🔥 {entry.title}", 'utf-8')
            msg['From'] = sender
            msg['To'] = to
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd)
                s.send_message(msg)
            logger.info("✅ 發送成功")
            
    except Exception as e:
        logger.error(f"Main Error: {e}")

if __name__ == "__main__":
    main()
