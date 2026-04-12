# replyX_bot.py
#------------------------------
#🌐 基本ライブラリ・API
#------------------------------
import os
import json
import subprocess
import traceback
import time
import random
import re
import requests
import psutil
import pytz
import unicodedata
import base64
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import urllib.parse
from groq import Groq
import fcntl
import torch
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

#------------------------------
#🔐 環境変数
#------------------------------
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
GIST_ID = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or exit("❌ GROQ_API_KEYが設定されていません")
HF_TOKEN = os.getenv("HF_TOKEN")
AUTH_TOKEN = os.getenv("AUTH_TOKEN") or exit("❌ AUTH_TOKENが設定されていません")
CT0 = os.getenv("CT0") or exit("❌ CT0が設定されていません")

print(f"✅ 環境変数読み込み完了: HANDLE={HANDLE}, GIST_ID={GIST_ID[:8]}...")
print("✅ Module imports completed")

#------------------------------
#📜 固定値・設定
#------------------------------
REPLIED_GIST_FILENAME = "replied_x.json" # X用にファイル名を変更推奨（競合防止）
DIAGNOSIS_LIMITS_GIST_FILENAME = "diagnosis_limits_x.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GIST_TOKEN_REPLY}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json"
}
LOCK_FILE = "bot_x.lock"
IMAGE_KEYWORDS = re.compile(r"(.*?)(\s*(画像生成して|画像作成して|画像作って|画像お願い|画像生成お願い|画像作成お願い|描いて|絵を描いて|絵描いて)\s*(.*))", re.IGNORECASE)

FALLBACK_CUTE_LINES = [
    "えへへ〜♡ みりんてゃ、君のこと考えるとドキドキなのっ♪",
    "今日も君に甘えたい気分なのっ♡ ぎゅーってして？",
    "だ〜いすきっ♡ ね、ね、もっと構ってくれる？"
]
failure_messages = [
    "えへへ、ごめんね〜……今ちょっと調子悪いみたい…またお話しよ？♡",
    "うぅ、ごめん〜〜…上手くお返事できなかったの。ちょっと待ってて？♡",
    "あれれ？みりんてゃ、おねむかも……またあとで頑張るねっ！♡"
]
image_failure_message = "ごめん…画像生成失敗しちゃった♡ また試してみてね！"

PRODUCT_KEYWORDS = {
    "おすすめグッズ": "推し活おすすめグッズだよ〜♡",
    "ぬい撮り": "ぬい撮りにピッタリなアイテムだよ〜♡",
    "寝れない": "ぐっすり安眠グッズだよ〜♡",
    "推し活": "推し活がもっと楽しくなるグッズだよ〜♡",
    "可愛いアイテム": "みりんてゃイチオシの可愛いアイテムだよ〜♡",
    "可愛いもの": "ふわふわ可愛い雑貨だよ〜♡"
}

DIAGNOSIS_KEYWORDS = re.compile(
    r"ふわもこ運勢|情緒診断|情緒|運勢|占い|診断して|占って"
    r"|Fuwamoko Fortune|Emotion Check|Mirinteya Mood|Tell me my fortune|diagnose|Fortune",
    re.IGNORECASE
)

FUWAMOKO_TEMPLATES = [{"level": range(90, 101), "item": "ピンクリボン", "msg": "超あまあま♡ 推し活でキラキラしよ！"}, {"level": range(85, 90), "item": "きらきらレターセット", "msg": "今日は推しにお手紙書いてみよ♡ 感情だだもれでOK！"}, {"level": range(70, 85), "item": "パステルマスク", "msg": "ふわふわ気分♪ 推しの画像見て癒されよ～！"}, {"level": range(60, 70), "item": "チュルチュルキャンディ", "msg": "テンション高め！甘いものでさらにご機嫌に〜♡"}, {"level": range(50, 60), "item": "ハートクッキー", "msg": "まあまあふわもこ！推しに想い伝えちゃお♡"}, {"level": range(40, 50), "item": "ふわもこマスコット", "msg": "ちょっとゆる〜く、推し動画でまったりタイム🌙"}, {"level": range(30, 40), "item": "星のキーホルダー", "msg": "ちょっとしょんぼり…推しの曲で元気出そ！"}, {"level": range(0, 30), "item": "ふわもこ毛布", "msg": "ふわふわ不足…みりんてゃがぎゅーってするよ♡"}]
EMOTION_TEMPLATES = [{"level": range(40, 51), "coping": "推しと妄想デート♡", "weather": "晴れ時々キラキラ", "msg": "みりんてゃも一緒にときめくよ！"}, {"level": range(20, 40), "coping": "甘いもの食べてほっこり", "weather": "薄曇り", "msg": "キミの笑顔、みりんてゃ待ってるよ♡"}, {"level": range(0, 20), "coping": "推しの声で脳内会話", "weather": "もやもや曇り", "msg": "妄想会話で乗り切って…！みりんてゃが一緒にうなずくよ♡"}, {"level": range(-10, 0), "coping": "推しの画像で脳溶かそ", "weather": "くもり", "msg": "みりんてゃ、そっとそばにいるよ…"}, {"level": range(-30, -10), "coping": "推しの曲で心リセット", "weather": "くもり時々涙", "msg": "泣いてもいいよ、みりんてゃがいるから…"}, {"level": range(-45, -30), "coping": "ぬいにぎって深呼吸", "weather": "しとしと雨", "msg": "しょんぼりでも…ぬいと、みりんてゃがいるから大丈夫♡"}, {"level": range(-50, -45), "coping": "ふわもこ動画で寝逃げ", "weather": "小雨ぽつぽつ", "msg": "明日また頑張ろ、みりんてゃ応援してる…"}]
FUWAMOKO_TEMPLATES_EN = [{"level": range(90, 101), "item": "Pink Ribbon", "msg": "Super sweet vibe♡ Shine with your oshi!"}, {"level": range(0, 30), "item": "Fluffy Blanket", "msg": "Low on fuwa-fuwa… Mirinteya hugs you tight♡"}] # 簡略化
EMOTION_TEMPLATES_EN = [{"level": range(40, 51), "coping": "Daydream a date with your oshi♡", "weather": "Sunny with sparkles", "msg": "Mirinteya’s sparkling with you!"}, {"level": range(-50, -45), "coping": "Binge fuwamoko vids and sleep", "weather": "Light rain", "msg": "Let’s try again tomorrow, Mirinteya’s rooting for you…"}] # 簡略化

REPLY_TABLE = {
    "画像生成できる？": "もちろんできるよっ♡ 『○○の画像生成して』か『画像生成して ○○』で言ってくれると、みりんてゃがふわもこ絵を描くよぉ♪",
}
SAFE_WORDS = ["ちゅ", "ぎゅっ", "ドキドキ", "ぷにっ", "すりすり", "なでなで"]
DANGER_ZONE = ["ちゅぱ", "えっち", "犯す", "nsfw", "nude", "gore"]
BOT_NAME = "みりんてゃ"
FIRST_PERSON = "みりんてゃ"

#------------------------------
#🔗 URI正規化 (X用に変更)
#------------------------------
def normalize_uri(uri):
    if not uri or not isinstance(uri, str): return None
    uri = uri.strip()
    return uri if uri.startswith("https://x.com/") else None

#------------------------------
#📁 Gist操作
#------------------------------
def load_gist_data(filename):
    print(f"🌐 Gistデータ読み込み開始: {filename}")
    for attempt in range(5):
        try:
            curl_command = ["curl", "-X", "GET", GIST_API_URL, "-H", f"Authorization: token {GIST_TOKEN_REPLY}", "-H", "Accept: application/vnd.github+json"]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode != 0: raise Exception(result.stderr)
            gist_data = json.loads(result.stdout)
            if filename in gist_data["files"]:
                content = gist_data["files"][filename]["content"]
                if filename == REPLIED_GIST_FILENAME:
                    raw_uris = json.loads(content)
                    replied = set(uri for uri in (normalize_uri(u) for u in raw_uris) if uri)
                    return replied
                return json.loads(content)
            return set() if filename == REPLIED_GIST_FILENAME else {}
        except Exception as e:
            if attempt < 4: time.sleep(2)
            else: return set() if filename == REPLIED_GIST_FILENAME else {}

def save_replied(replied_set):
    cleaned_set = set(uri for uri in replied_set if normalize_uri(uri))
    for attempt in range(5):
        try:
            payload = {"files": {REPLIED_GIST_FILENAME: {"content": json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)}}}
            curl_command = ["curl", "-X", "PATCH", GIST_API_URL, "-H", f"Authorization: token {GIST_TOKEN_REPLY}", "-H", "Accept: application/vnd.github+json", "-H", "Content-Type: application/json", "-d", json.dumps(payload, ensure_ascii=False)]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode == 0: return True
        except:
            if attempt < 4: time.sleep(2)
    return False

def save_gist_data(filename, data):
    for attempt in range(5):
        try:
            payload = {"files": {filename: {"content": json.dumps(data, ensure_ascii=False, indent=2)}}}
            curl_command = ["curl", "-X", "PATCH", GIST_API_URL, "-H", f"Authorization: token {GIST_TOKEN_REPLY}", "-H", "Accept: application/vnd.github+json", "-H", "Content-Type: application/json", "-d", json.dumps(payload, ensure_ascii=False)]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode == 0: return True
        except:
            if attempt < 4: time.sleep(2)
    return False

#------------------------------
#🆕 診断機能
#------------------------------
def check_diagnosis_limit(user_handle, is_daytime):
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.now(jst).date().isoformat()
    limits = load_gist_data(DIAGNOSIS_LIMITS_GIST_FILENAME)
    period = "day" if is_daytime else "night"
    if user_handle in limits and limits[user_handle].get(period) == today:
        return False, "今日はもうこの診断済みだよ〜♡ 明日またね！💖"
    if user_handle not in limits: limits[user_handle] = {}
    limits[user_handle][period] = today
    save_gist_data(DIAGNOSIS_LIMITS_GIST_FILENAME, limits)
    return True, None

def generate_diagnosis(text, user_handle):
    if not DIAGNOSIS_KEYWORDS.search(text): return None, []
    jst = pytz.timezone('Asia/Tokyo')
    hour = datetime.now(jst).hour
    is_daytime = 6 <= hour < 18
    can_diagnose, limit_msg = check_diagnosis_limit(user_handle, is_daytime)
    if not can_diagnose: return limit_msg, []
    
    if is_daytime:
        level = random.randint(0, 100)
        template = next(t for t in FUWAMOKO_TEMPLATES if level in t["level"])
        reply_text = f"✨キミのふわもこ運勢✨\n💖ふわもこ度：{level}％\n🎀ラッキーアイテム：{template['item']}\n💭{template['msg']}"
        return reply_text, []
    else:
        level = random.randint(-50, 50)
        template = next(t for t in EMOTION_TEMPLATES if level in t["level"])
        reply_text = f"⸝⸝ キミの情緒バロメーター ⸝⸝\n💭情緒：{level}％\n☁️情緒天気：{template['weather']}\n💭対処法：{template['coping']}\nみりんてゃもそばにいるよ…"
        return reply_text, []

#------------------------------
#🆕 画像生成機能（軽量版）
#------------------------------
def check_kudos():
    try:
        url = "https://stablehorde.net/api/v2/find_user"
        headers = {"apikey": os.getenv("STABLE_HORDE_API_KEY", "0000000000")}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200: return response.json().get("kudos", 0)
    except: pass
    return 0

def generate_image(prompt):
    print(f"🖼️ API画像生成開始: プロンプト={prompt}")
    if not HF_TOKEN: return None
    
    cleaned_prompt = f"solo, single subject, 1girl, cute anime girl, {prompt}, masterpiece, best quality, highly detailed"
    negative_prompt = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, nsfw, nude"
    
    api_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-dev"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": cleaned_prompt}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=120)
        if response.status_code == 200:
            image_data = response.content
            image = Image.open(BytesIO(image_data))
            image_path = "output_hf.png"
            image.save(image_path, "PNG", optimize=True)
            print("✅ 画像生成成功！")
            return image_path
    except Exception as e:
        print(f"⚠️ 画像生成エラー: {e}")
    return None

#------------------------------
#🧹 テキスト処理・グッズ・AI返信
#------------------------------
def clean_sentence_ending(reply):
    reply = re.sub(r'\n{2,}', '\n', reply).strip()
    reply = reply.replace("俺", FIRST_PERSON).replace("僕", FIRST_PERSON)
    if not re.search(r"[。！？♡♪笑]$", reply): reply += "♡"
    return reply

def generate_product_reply(keyword):
    return f"推し活おすすめグッズだよ〜♡ → https://hb.afl.rakuten.co.jp/hgc/xxxx", []

def generate_reply_via_groq(user_input, author_display_name="", author_handle=""):
    raw_name = author_display_name.strip() or author_handle.replace(".bsky.social", "")
    call_name = raw_name[:10] + "ちゃん" if len(raw_name.encode('utf-8')) > 32 else raw_name or "きみ"

    diagnosis_result = generate_diagnosis(user_input, author_handle)
    if diagnosis_result[0]: return diagnosis_result[0].replace("キミ", call_name)

    image_match = re.search(r"(.*?)(画像生成して|画像作って|描いて)(.*)", user_input, re.IGNORECASE)
    if image_match:
        prompt = image_match.group(3).strip()
        image = generate_image(prompt)
        if image: return {"type": "image", "image": image, "prompt": prompt}
        return image_failure_message

    for keyword in PRODUCT_KEYWORDS.keys():
        if keyword.lower() in user_input.lower():
            return generate_product_reply(keyword)[0]

    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        system_prompt = f"あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！相手の名前は「{call_name}」！タメ口で『〜なのっ♡』『えへへ〜♡』を語尾に使ってね。"
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
            max_tokens=60, temperature=0.8
        )
        return clean_sentence_ending(response.choices[0].message.content)
    except:
        return random.choice(FALLBACK_CUTE_LINES)

#------------------------------
#📬 Xでのメイン処理（Playwright）
#------------------------------
def get_x_mentions(page):
    print("🔔 Xのメンション通知欄を確認中...")
    page.goto("https://x.com/notifications/mentions")
    page.wait_for_timeout(5000)
    mentions = []
    tweets = page.locator('article[data-testid="tweet"]').all()
    for tweet in tweets[:5]:
        try:
            time_element = tweet.locator('a[href*="/status/"]').first
            tweet_url = "https://x.com" + time_element.get_attribute("href")
            text_locator = tweet.locator('div[data-testid="tweetText"]')
            text = text_locator.inner_text() if text_locator.count() > 0 else ""
            handle_locator = tweet.locator('div[dir="ltr"]').filter(has_text="@").first
            author_handle = handle_locator.inner_text().replace("@", "") if handle_locator.count() > 0 else ""
            name_locator = tweet.locator('div[data-testid="User-Name"] span').first
            author_display_name = name_locator.inner_text() if name_locator.count() > 0 else author_handle
            if author_handle.lower() == HANDLE.lower() or not text: continue
            mentions.append({"url": tweet_url, "text": text, "handle": author_handle, "display_name": author_display_name})
        except: continue
    return mentions

def run_reply_bot():
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        replied_urls = load_gist_data(REPLIED_GIST_FILENAME)
        if not isinstance(replied_urls, set): replied_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_cookies([
                {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
                {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
            ])
            page = context.new_page()
            mentions = get_x_mentions(page)

            reply_count = 0
            for mention in mentions:
                if reply_count >= 3: break
                tweet_url = mention["url"]
                if tweet_url in replied_urls: continue

                print(f"💬 返信対象: @{mention['handle']} / {mention['text']}")
                reply_result = generate_reply_via_groq(mention["text"], mention["display_name"], mention["handle"])
                
                reply_text = ""
                image_path = None
                if isinstance(reply_result, dict) and reply_result.get("type") == "image":
                    image_path = reply_result["image"]
                    reply_text = f"みりんてゃが描いたよ♡"
                else:
                    reply_text = reply_result[:135] + "♡" if len(reply_result) > 135 else reply_result

                try:
                    page.goto(tweet_url)
                    page.wait_for_timeout(5000)
                    page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=10000)

                    if image_path and os.path.exists(image_path):
                        page.locator('input[data-testid="fileInput"]').set_input_files(image_path)
                        page.wait_for_timeout(3000)

                    page.fill('div[data-testid="tweetTextarea_0"]', reply_text)
                    page.wait_for_timeout(2000)
                    page.keyboard.press("Control+Enter")
                    page.wait_for_timeout(5000)

                    replied_urls.add(tweet_url)
                    save_replied(replied_urls)
                    print(f"✅ リプライ完了！ → {tweet_url}")
                    reply_count += 1
                    time.sleep(random.randint(15, 30))

                    if image_path and os.path.exists(image_path): os.remove(image_path)
                except Exception as e:
                    print(f"⚠️ 投稿エラー: {e}")

            browser.close()
    except Exception as e: print(f"❌ 実行エラー: {e}")
    finally:
        if lock_fd: fcntl.flock(lock_fd, fcntl.LOCK_UN); lock_fd.close()
        try: os.remove(LOCK_FILE)
        except: pass

if __name__ == "__main__":
    run_reply_bot()
