# tlX_reaction_bot.py
import os
import random
import time
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright

# 1. 環境変数の読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

AUTH_TOKEN = os.getenv('AUTH_TOKEN')
CT0 = os.getenv('CT0')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

def get_tl_content(page):
    """タイムラインを読み取って、話題をいくつか拾う"""
    print("👀 タイムラインを覗き見中...")
    try:
        page.goto("https://x.com/home")
        page.wait_for_timeout(7000) # 読み込み待ち
        
        # ツイートのテキスト要素を取得
        tweet_elements = page.locator('div[data-testid="tweetText"]').all()
        
        # 上位5件くらいのテキストを合体させる
        tl_texts = []
        for el in tweet_elements[:5]:
            text = el.inner_text().strip()
            if text:
                tl_texts.append(text)
        
        return " | ".join(tl_texts)
    except Exception as e:
        print(f"⚠️ TL取得失敗: {e}")
        return ""

def generate_tl_reaction(tl_summary):
    """Groqを使って、TLの空気感に反応するポストを作る"""
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = (
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "性格：天然、甘えん坊、依存気味、語尾は『〜なのっ♡』『えへへ〜♡』『〜だよぉ？♪』\n"
            "指示：今現在のタイムラインの内容（素材）を渡すので、それを見て独り言をつぶやいて。\n"
            "ルール：ニュース解説じゃなく『みんなこれ話してるね〜』とか『そんな雰囲気なんだ〜』的な、地雷系女子の軽い反応にする。140字以内。"
        )
        
        user_prompt = f"現在のタイムラインの素材：\n{tl_summary}\n\nこれを見て、みりんてゃらしく短く可愛くつぶやいて。"

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=150,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ AI生成エラー: {e}")
        return "ねぇねぇ、みんな何お話ししてるの？ みりんてゃも混ぜてほしいなのっ♡"

def main():
    if not AUTH_TOKEN or not GROQ_API_KEY:
        print("❌ 設定が足りないよ！")
        return

    print("🚀 タイムライン反応Bot 起動！")

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
        # ステルス魔法
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # 1. TLから素材をゲット！
            tl_material = get_tl_content(page)
            if not tl_material:
                print("⚠️ 素材が取れなかったから終了するね")
                return

            # 2. AIでポスト生成
            ai_post = generate_tl_reaction(tl_material)
            
            # Xの仕様に合わせてクリーニング（引用符などを消す）
            ai_post = ai_post.replace('"', '').replace('「', '').replace('」', '')
            print(f"📝 生成されたポスト:\n{ai_post}")

            # 3. 投稿画面へ
            page.goto("https://x.com/compose/post")
            page.wait_for_timeout(5000)
            
            textbox_selector = 'div[data-testid="tweetTextarea_0"]'
            page.wait_for_selector(textbox_selector, timeout=15000)
            page.fill(textbox_selector, ai_post)
            page.wait_for_timeout(2000)
            
            page.keyboard.press("Control+Enter")
            page.wait_for_timeout(5000)
            
            print("✨ タイムライン反応投稿 成功！！ ✨")

        except Exception as e:
            print(f"❌ エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
