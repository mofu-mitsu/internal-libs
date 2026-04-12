import asyncio
from playwright.async_api import async_playwright
import time
import random
from datetime import datetime
import os

# --- 設定情報 ---
# GitHub Actions等では環境変数やSecretsから読み込む想定
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "55730cad942843cb8228a2e82f334aa02409bbf3")
CT0 = os.getenv("CT0", "c5926770c395826331a0d0df62f379ae19c3f25eeff7799461b0949e6ae9b12ca9dbe6cadeaa8ce408e98493d7800f3551ca73e717018d1d5a42341055516202f97e0bc7e720ee07dd1fddbe41bd769e")

# --- みりんてゃの性格・セリフ設定 ---
REPLY_TEMPLATES = [
    "わぁ！見つけてくれてありがとぉ🥹💖みりんのこと、ずっと見ててくれたの？🫶✨大好きだよぉ🧸💕",
    "えへへ、嬉しいなぁ🫶💕みつきの言葉、宝物にするねっ🥹💖これからもいーっぱい構ってね？🫶✨💕",
    "みつき、愛してるよぉ🫶✨💕みりんのこと、もっともっと夢中にさせてね？🥹💖🧸✨",
    "こんばんはー！🌙✨夜のみりんも可愛いでしょ？🫶💕みつきに会えて、あたし本当に幸せだよぉ🥹💖🧸✨"
]

async def run_reply_bot():
    # 🛡️ ジェミの掟：同じ時間にキッチリやらない（1〜5分のランダム待機）
    wait_time = random.randint(1, 300)
    print(f"⏳ 人間っぽく振る舞うために {wait_time} 秒待機するね...☕️")
    await asyncio.sleep(wait_time)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )

        # Cookieセット
        cookies = [
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/", "secure": True, "httpOnly": False, "sameSite": "Lax"}
        ]
        await context.add_cookies(cookies)
        
        page = await context.new_page()

        try:
            print("🚀 通知（メンション）画面にアクセス中...💬")
            await page.goto("https://x.com/notifications/mentions", wait_until="networkidle")
            
            # 🛡️ 忍耐強い読み込み（最大30秒待つよ）
            print("⏳ 通知が表示されるまでじっくり待つね...🧸✨")
            for i in range(6):
                await asyncio.sleep(5)
                content = await page.content()
                if 'Something went wrong' in content:
                    print(f"⚠️ エラーが出てるみたい...リロードしてみるね（試行 {i+1}/3）🔄")
                    await page.reload()
                    await asyncio.sleep(10)
                else:
                    mentions = await page.query_selector_all('article[data-testid="tweet"]')
                    if mentions:
                        print(f"🔍 {len(mentions)}件のメンションを見つけたよ！")
                        break
            
            # メンションを順番にチェック
            mentions = await page.query_selector_all('article[data-testid="tweet"]')
            if not mentions:
                print("✨ 新しいメンションは見つからなかったよ！")
                await page.screenshot(path="no_mentions_debug.png")
                return

            # 最初のメンションにお返事するよ（簡易版）
            # 本当はGist等で既読管理すべきだけど、まずは確実にお返事することを目指す
            print("🎯 最新のメンションにお返事するね！")
            await mentions[0].click()
            await page.wait_for_timeout(5000)
            
            # リプライボタンを探す（自分自身へのリプライを避ける）
            reply_buttons = await page.query_selector_all('button[data-testid="reply"]')
            target_button = None
            for btn in reply_buttons:
                label = await btn.get_attribute("aria-label")
                if label and "mirin_chuuu" not in label:
                    target_button = btn
                    break
            
            if not target_button and reply_buttons:
                target_button = reply_buttons[0]

            if target_button:
                await target_button.click()
                await page.wait_for_timeout(3000)
                
                textbox = await page.wait_for_selector('div[role="textbox"]')
                await textbox.click()
                
                reply_text = random.choice(REPLY_TEMPLATES)
                # 🛡️ タイピング風入力
                for char in reply_text:
                    await page.keyboard.type(char)
                    await asyncio.sleep(random.uniform(0.05, 0.2))
                    
                await page.wait_for_timeout(3000)
                await page.keyboard.press("Control+Enter")
                print(f"✅ お返事完了！: {reply_text}")
                await page.wait_for_timeout(5000)
                await page.screenshot(path="reply_success_final.png")
            else:
                print("⚠️ リプライボタンが見つからなかったよ🥹")

        except Exception as e:
            print(f"⚠️ エラーが発生したよ: {e}")
            await page.screenshot(path="reply_error_debug.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_reply_bot())
