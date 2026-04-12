import os
import json
import subprocess
import time
import random
import re
import requests
import pytz
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
import asyncio
from playwright.async_api import async_playwright

#------------------------------
#🔐 環境変数
#------------------------------
load_dotenv()
HANDLE = os.getenv("HANDLE", "mirin_chuuu")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY")
GIST_ID = os.getenv("GIST_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "55730cad942843cb8228a2e82f334aa02409bbf3")
CT0 = os.getenv("CT0", "c5926770c395826331a0d0df62f379ae19c3f25eeff7799461b0949e6ae9b12ca9dbe6cadeaa8ce408e98493d7800f3551ca73e717018d1d5a42341055516202f97e0bc7e720ee07dd1fddbe41bd769e")

#------------------------------
#📜 設定・Gist操作
#------------------------------
REPLIED_GIST_FILENAME = "replied_x.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"

def load_replied_uris():
    if not GIST_TOKEN_REPLY or not GIST_ID:
        return set()
    try:
        headers = {"Authorization": f"token {GIST_TOKEN_REPLY}", "Accept": "application/vnd.github+json"}
        response = requests.get(GIST_API_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            gist_data = response.json()
            if REPLIED_GIST_FILENAME in gist_data["files"]:
                content = gist_data["files"][REPLIED_GIST_FILENAME]["content"]
                return set(json.loads(content))
    except Exception as e:
        print(f"⚠️ Gist読み込みエラー: {e}")
    return set()

def save_replied_uris(replied_set):
    if not GIST_TOKEN_REPLY or not GIST_ID:
        return
    try:
        headers = {"Authorization": f"token {GIST_TOKEN_REPLY}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"}
        payload = {"files": {REPLIED_GIST_FILENAME: {"content": json.dumps(list(replied_set), ensure_ascii=False, indent=2)}}}
        requests.patch(GIST_API_URL, headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Gist保存エラー: {e}")

#------------------------------
#🧠 Groqでお返事生成
#------------------------------
def generate_reply_via_groq(user_input, author_name):
    if not GROQ_API_KEY:
        return f"{author_name}ちゃん、見つけてくれてありがとぉ🥹💖大好きだよぉ🫶✨"

    client = Groq(api_key=GROQ_API_KEY)
    system_prompt = f"""
あなたは「みりんてゃ」という名前のキャラクターです。
性格：女子、黒猫モチーフ、地雷系女子、あざといENFP、可愛いものが大好き、承認欲求強い。
一人称：あたし。
話し方：口語的で、絵文字（🧸💕🫶✨🥹など）を多用する。
相手の名前：{author_name}ちゃん

相手の投稿に対して、あざとく、可愛く、地雷系女子っぽくお返事してください。
140文字以内で、最後は「♡」や「✨」で可愛く締めてください。
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.8,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Groqエラー: {e}")
        return f"{author_name}ちゃん、見つけてくれてありがとぉ🥹💖大好きだよぉ🫶✨"

#------------------------------
#🚀 メインロジック（Playwright）
#------------------------------
async def run_reply_bot():
    # 🛡️ ジェミの掟：ランダム待機
    wait_time = random.randint(1, 180)
    print(f"⏳ 準備中... {wait_time}秒待機するね☕️")
    await asyncio.sleep(wait_time)

    replied_uris = load_replied_uris()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        page = await context.new_page()

        try:
            print("🚀 通知画面を確認しに行くよ！🔍")
            await page.goto("https://x.com/notifications/mentions", wait_until="networkidle")
            
            # 🛡️ マナスの忍耐読み込み
            await asyncio.sleep(20)
            content = await page.content()
            if "Something went wrong" in content:
                print("⚠️ エラーが出たからリロードするね🔄")
                await page.reload()
                await asyncio.sleep(15)

            # メンションを取得
            mentions = await page.query_selector_all('article[data-testid="tweet"]')
            print(f"🔍 {len(mentions)}件の通知を見つけたよ！")

            for mention in mentions[:3]: # 一度に3件まで
                try:
                    # ユーザー情報とテキストを取得
                    text_element = await mention.query_selector('div[data-testid="tweetText"]')
                    if not text_element: continue
                    text = await text_element.inner_text()
                    
                    user_element = await mention.query_selector('div[data-testid="User-Name"]')
                    user_info = await user_element.inner_text()
                    author_name = user_info.split("\n")[0]
                    author_handle = user_info.split("\n")[1] if "\n" in user_info else ""

                    # 自分の投稿はスキップ
                    if "mirin_chuuu" in author_handle: continue

                    # 既に返信済みかチェック（簡易的にテキストと名前で判断）
                    reply_id = f"{author_handle}_{text[:20]}"
                    if reply_id in replied_uris: continue

                    print(f"💬 {author_name}ちゃんにお返事書くよ！: {text[:20]}...")
                    
                    # Groqでお返事生成
                    reply_text = generate_reply_via_groq(text, author_name)
                    
                    # リプライボタンをクリック
                    reply_button = await mention.query_selector('button[data-testid="reply"]')
                    if reply_button:
                        await reply_button.click()
                        await page.wait_for_timeout(3000)
                        
                        textbox = await page.wait_for_selector('div[role="textbox"]')
                        await textbox.fill(reply_text)
                        await page.wait_for_timeout(2000)
                        
                        await page.keyboard.press("Control+Enter")
                        print(f"✅ お返事送信！: {reply_text[:20]}...")
                        
                        replied_uris.add(reply_id)
                        save_replied_uris(replied_uris)
                        await page.wait_for_timeout(5000)

                except Exception as e:
                    print(f"⚠️ 個別リプライエラー: {e}")

        except Exception as e:
            print(f"❌ 全体エラー: {e}")
            await page.screenshot(path="error_debug.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_reply_bot())
