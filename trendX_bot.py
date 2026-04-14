# trendX_bot.py
import os
import random
import time
import urllib.parse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright

# 1. 環境変数の読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

AUTH_TOKEN = os.getenv('AUTH_TOKEN')
CT0 = os.getenv('CT0')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# ------------------------------
# ★ みりんてゃの「いまの気分」リスト（よりエモく改造！）
# ------------------------------
MOOD_LABELS = [
    "おなかすいた", "ねむい", "ひま", "だるい", "かまってほしい", "ちょっと寂しい",
    "アイス食べたい", "お散歩したい", "スマホ見てる", "前髪決まらない", "きゅんきゅんしたい",
    "逃避行したい", "おふとん最高", "推しが尊い", "猫になりたい", "雨やだね", "夜更かし中"
]

def get_trend_word(page):
    """日本のトレンドを取得する"""
    print("🔍 トレンドサイトを確認中...")
    try:
        page.goto("https://getdaytrends.com/japan/", timeout=60000)
        page.wait_for_timeout(5000)
        
        # トレンドのリンクを抽出
        trends = page.locator('table tr td a[href*="/japan/trend/"]').all_inner_texts()
        
        # #がついているもの、かつ適切な長さのものをフィルタリング
        valid_trends = [t.strip() for t in trends if t.startswith("#") and 3 <= len(t) <= 15]
        
        if not valid_trends:
            return "#ふわふわ" # 失敗した時の保険
            
        # 上位10個の中からランダムに1つ選ぶ
        word = random.choice(valid_trends[:10])
        print(f"✅ トレンドGET: {word}")
        return word
    except Exception as e:
        print(f"⚠️ トレンド取得失敗: {e}")
        return "#かわいい"

def generate_mirin_poem(trend_word, mood):
    """Groqを使って、トレンドに反応するあざといポエムを作る"""
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = (
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "性格：天然、甘えん坊、依存気味、語尾は『〜なのっ♡』『えへへ〜♡』『〜だよぉ？♪』\n"
            "指示：現在の気分とトレンドワードを絡めた、140文字以内の短いつぶやきを作って。\n"
            "ルール：ニュース解説じゃなくて、あくまで『地雷系女子の独白』にすること。二人称は『きみ』。ハッシュタグは不要。"
        )
        
        user_prompt = f"いまの気分：{mood}、見つけたトレンド：{trend_word}。これについて短く可愛くつぶやいて。"

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=100,
            temperature=0.8
        )
        poem = response.choices[0].message.content.strip()
        # 140文字制限
        return poem[:120]
    except Exception as e:
        print(f"❌ AI生成エラー: {e}")
        return f"ねぇねぇ、いま『{trend_word}』が流行ってるの？ {mood}なみりんてゃも気になるなぁ…♡"

def main():
    if not AUTH_TOKEN or not GROQ_API_KEY:
        print("❌ 必要な設定が足りないよ！")
        return

    mood = random.choice(MOOD_LABELS)
    print(f"🚀 トレンドBot起動！ 今のみりんてゃは「{mood}」な気分♡")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # 1. トレンド取得
            trend_word = get_trend_word(page)
            
            # 2. ポエム生成
            poem = generate_mirin_poem(trend_word, mood)
            
            # 3. メッセージ組み立て
            full_message = f"いま「{mood}」なんだけどさ…💭\n\n{poem}\n\n{trend_word}"
            print(f"📝 投稿内容:\n{full_message}")

            # 4. Xへ投稿
            page.goto("https://x.com/compose/post")
            page.wait_for_timeout(7000)
            
            textbox_selector = 'div[data-testid="tweetTextarea_0"]'
            page.wait_for_selector(textbox_selector, timeout=15000)
            page.fill(textbox_selector, full_message)
            page.wait_for_timeout(2000)
            
            page.keyboard.press("Control+Enter")
            page.wait_for_timeout(5000)
            
            print("✨ トレンド投稿成功！みりんてゃは今日も最先端！ ✨")

        except Exception as e:
            print(f"❌ エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
