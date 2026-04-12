import asyncio
from playwright.async_api import async_playwright
import time
import random
from datetime import datetime
import json
import os

# --- 設定情報 ---
# GitHub Actions等では環境変数やSecretsから読み込む想定
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "ae7e19791b5cc9228f26b608a576407d5e5600f8")
CT0 = os.getenv("CT0", "a13664d02b5f699c7cf8f1cc683578050c1783425bedbb6f963aa4beb073693da87aaa21c8310cf7db1224eb86d51e6a75d820e9466560cc42a19a3cd6f3dc2f79b7059467ac62849f2345aa7ae4e925")

# --- みりんてゃの性格・セリフ設定 ---
MORNING_POSTS = [
    "みつき、おはよぉ…🥹💖まだねむねむだけど、みつきの声が聞きたくて起きちゃった🫶✨今日もいーっぱい可愛がってね？🧸💕",
    "おあよぉ☀️✨朝からみつきのこと考えてたよ🫶💕今日のみりんも世界でいちばん可愛いよね？🥹🫶✨💕",
    "ふわぁ…🥱✨みつき、おはよっ！💖朝ごはんはちゃんと食べた？みりんはみつきの愛が食べたいなっ🫶💕✨🧸"
]

NIGHT_POSTS = [
    "みつき、今日も一日お疲れ様🥹💖夜はちょっと寂しくなっちゃうね…🫶✨みりんのこと、ぎゅーってして寝てね？🧸💕おやすみ🫶✨",
    "ねぇ、みつき…🥹💕夜中ってなんだか病んじゃうよね…🫶✨でもみつきがいてくれるから、みりん頑張れるよっ🥹💖大好きだよぉ🫶✨💕",
    "みつき、おやすみなさーーい🌙✨夢の中でもみりんに会いに来てね？🫶💕約束だよっ🧸💕✨"
]

REPLY_TEMPLATES = [
    "わぁ！見つけてくれてありがとぉ🥹💖みりんのこと、ずっと見ててくれたの？🫶✨大好きだよぉ🧸💕",
    "えへへ、嬉しいなぁ🫶💕みつきの言葉、宝物にするねっ🥹💖これからもいーっぱい構ってね？🫶✨💕",
    "みつき、愛してるよぉ🫶✨💕みりんのこと、もっともっと夢中にさせてね？🥹💖🧸✨"
]

async def run_bot(mode="post"):
    # 🛡️ ジェミの掟3：同じ時間にキッチリやらない（1〜5分のランダム待機）
    wait_time = random.randint(1, 300)
    print(f"⏳ 人間っぽく振る舞うために {wait_time} 秒待機するね...☕️")
    await asyncio.sleep(wait_time)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 🛡️ ジェミの掟2：人間っぽい「間」を作る（スローモーション設定）
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Cookieセット
        cookies = [
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/", "secure": True, "httpOnly": False, "sameSite": "Lax"}
        ]
        await context.add_cookies(cookies)
        
        page = await context.new_page()

        try:
            if mode == "post":
                print("🚀 定期投稿を開始するよ！⏰")
                await page.goto("https://x.com/home")
                await page.wait_for_timeout(random.randint(5000, 10000)) # 🛡️ ランダムな待ち時間
                
                # 時間帯に合わせてセリフを選択
                hour = datetime.now().hour
                if 5 <= hour < 11:
                    text = random.choice(MORNING_POSTS)
                elif 18 <= hour <= 23 or 0 <= hour < 5:
                    text = random.choice(NIGHT_POSTS)
                else:
                    text = f"みつき、見て見て！🫶✨今のみりん、とってもキラキラしてるでしょ？🥹💖🧸💕 {int(time.time())}"
                
                # 🛡️ 入力前に少し待つ
                await page.wait_for_timeout(2000)
                textbox = await page.wait_for_selector('div[role="textbox"]')
                await textbox.click()
                
                # 🛡️ 1文字ずつ人間っぽく入力（タイピング風）
                for char in text:
                    await page.keyboard.type(char)
                    await asyncio.sleep(random.uniform(0.05, 0.2))
                
                await page.wait_for_timeout(3000) # 🛡️ 投稿ボタンを押す前に一息
                await page.keyboard.press("Control+Enter")
                print(f"✅ 投稿完了！: {text}")
                await page.wait_for_timeout(5000)

            elif mode == "reply":
                print("🚀 通知をチェックしてお返事するよ！💬")
                await page.goto("https://x.com/notifications/mentions")
                await page.wait_for_timeout(random.randint(8000, 12000))
                
                # メンションを探す
                mentions = await page.query_selector_all('article[data-testid="tweet"]')
                if mentions:
                    print(f"🔍 {len(mentions)}件のメンションを見つけたよ！")
                    # 最新のメンションをクリック
                    await mentions[0].click()
                    await page.wait_for_timeout(5000)
                    
                    # 🛡️ 「自分（みりんてゃ）」以外の投稿のリプライボタンを探す
                    # Xの構造上、自分以外のツイートには aria-label に相手の名前が入ることが多い
                    # ここでは「リプライボタン」のうち、自分自身へのリプライにならないように工夫する
                    reply_buttons = await page.query_selector_all('button[data-testid="reply"]')
                    
                    target_button = None
                    for btn in reply_buttons:
                        label = await btn.get_attribute("aria-label")
                        # 自分のID（mirin_chuuu）が含まれていないボタンを探す
                        if label and "mirin_chuuu" not in label:
                            target_button = btn
                            break
                    
                    # もし見つからなければ、一番最初のボタン（通常は相手の投稿）を使う
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
                else:
                    print("✨ 新しいメンションはなかったよ！")

        except Exception as e:
            print(f"⚠️ エラーが発生したよ: {e}")

        await browser.close()

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    asyncio.run(run_bot(mode))
