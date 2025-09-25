# reply_bot.py
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
import base64  # 追加
from datetime import datetime, timezone, timedelta
from atproto import Client, models
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from atproto_client.models.app.bsky.feed.post import ReplyRef
from dotenv import load_dotenv
import urllib.parse
from groq import Groq
import fcntl
from diffusers import StableDiffusionPipeline
import torch
import signal  # タイムアウトハンドリング
from PIL import Image  # 明示的にインポート
from io import BytesIO  # 明示的に追加

#------------------------------
#🔐 環境変数
#------------------------------
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv("APP_PASSWORD") or exit("❌ APP_PASSWORDが設定されていません")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
GIST_ID = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or exit("❌ GROQ_API_KEYが設定されていません")
HF_TOKEN = os.getenv("HF_TOKEN") or exit("❌ HF_TOKENが設定されていません")

print(f"✅ 環境変数読み込み完了: HANDLE={HANDLE[:8]}..., GIST_ID={GIST_ID[:8]}...")
print(f"🧪 GIST_TOKEN_REPLY: {repr(GIST_TOKEN_REPLY)[:8]}...")
print(f"🔑 トークンの長さ: {len(GIST_TOKEN_REPLY)}")
print(f"🖼️ HF_TOKEN: {repr(HF_TOKEN)[:8]}...")
print("✅ Module imports completed:", dir())

#--- 固定値 ---
REPLIED_GIST_FILENAME = "replied.json"
DIAGNOSIS_LIMITS_GIST_FILENAME = "diagnosis_limits.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GIST_TOKEN_REPLY}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json"
}
LOCK_FILE = "bot.lock"
IMAGE_KEYWORDS = re.compile(r"(.*?)(\s*(画像生成して|画像作成して|画像作って|画像お願い|画像生成お願い|画像作成お願い|描いて|絵を描いて|絵描いて)\s*(.*))", re.IGNORECASE)
FALLBACK_CUTE_LINES = [
    "えへへ〜♡ みりんてゃ、君のこと考えるとドキドキなのっ♪",
    "今日も君に甘えたい気分なのっ♡ ぎゅーってして？",
    "だ〜いすきっ♡ ね、ね、もっと構ってくれる？"
]
failure_messages = [
    "えへへ、ごめんね〜……今ちょっと調子悪いみたい…またお話しよ？♡",
    "うぅ、ごめん〜〜…上手くお返事できなかったの。ちょっと待ってて？♡",
    "あれれ？みりんてゃ、おねむかも……またあとで頑張るねっ！♡",
    "ふわぁ……ねむねむでお返事遅れちゃった…ごめんねぇ💭",
    "あわわっ…💭 みりんてゃの中の妖精さん、いま整備中みたい…またすぐ戻るねっ♡",
    "今日はちょっと電波がふわもこ迷子みたい……もう一回呼んでくれる？♡",
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

#------------------------------
#🔗 URI正規化
#------------------------------
def normalize_uri(uri):
    if not uri or not isinstance(uri, str) or uri in ["replied", "", "None"]:
        return None
    uri = uri.strip()
    if not uri.startswith("at://"):
        return None
    try:
        parsed = urllib.parse.urlparse(uri)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return normalized if normalized.startswith("at://") else None
    except Exception:
        return None

#------------------------------
#📁 Gist操作
#------------------------------
def load_gist_data(filename):
    print(f"🌐 Gistデータ読み込み開始 → URL: {GIST_API_URL}")
    for attempt in range(5):  # ★リトライを5回に
        try:
            curl_command = [
                "curl", "-X", "GET", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json"
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} レスポンスステータス: {result.returncode}")
            if result.returncode != 0:
                raise Exception(f"Gist読み込み失敗: {result.stderr}")
            gist_data = json.loads(result.stdout)
            if filename in gist_data["files"]:
                replied_content = gist_data["files"][filename]["content"]
                print(f"📄 生の{filename}内容:\n{replied_content[:500]}...")
                if filename == REPLIED_GIST_FILENAME:
                    raw_uris = json.loads(replied_content)
                    replied = set(uri for uri in (normalize_uri(u) for u in raw_uris) if uri)
                    print(f"✅ {filename} をGistから読み込みました（件数: {len(replied)}）")
                    if replied:
                        print("📁 最新URI一覧（正規化済み）:")
                        for uri in list(replied)[-5:]:
                            print(f" - {uri}")
                    return replied
                else:
                    data = json.loads(replied_content)
                    print(f"✅ {filename} をGistから読み込みました（件数: {len(data)}）")
                    return data
            else:
                print(f"⚠️ Gist内に {filename} が見つかりませんでした")
                return set() if filename == REPLIED_GIST_FILENAME else {}
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 4:
                print(f"⏳ リトライします（{attempt + 2}/5）")
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return set() if filename == REPLIED_GIST_FILENAME else {}

def save_replied(replied_set):
    print("💾 Gist保存準備中...")
    cleaned_set = set(uri for uri in replied_set if normalize_uri(uri))
    for attempt in range(5):  # ★リトライを5回に
        try:
            content = json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)
            payload = {"files": {REPLIED_GIST_FILENAME: {"content": content}}}
            curl_command = [
                "curl", "-X", "PATCH", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} レスポンスステータス: {result.returncode}")
            if result.returncode == 0:
                print(f"💾 replied.json をGistに保存しました（件数: {len(cleaned_set)}）")
                time.sleep(2)
                new_replied = load_gist_data(REPLIED_GIST_FILENAME)
                if cleaned_set.issubset(new_replied):
                    print("✅ 保存内容が正しく反映されました")
                    return True
                else:
                    raise Exception("保存内容の反映に失敗")
            else:
                raise Exception(f"Gist保存失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 4:
                print(f"⏳ リトライします（{attempt + 2}/5）")
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return False

def save_gist_data(filename, data):
    print(f"💾 Gist保存準備中 → File: {filename}")
    for attempt in range(5):  # ★リトライを5回に
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            payload = {"files": {filename: {"content": content}}}
            curl_command = [
                "curl", "-X", "PATCH", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} レスポンスステータス: {result.returncode}")
            if result.returncode == 0:
                print(f"💾 {filename} をGistに保存しました")
                time.sleep(2)
                return True
            else:
                raise Exception(f"Gist保存失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 4:
                print(f"⏳ リトライします（{attempt + 2}/5）")
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return False

#------------------------------
#🆕 診断機能
#------------------------------
DIAGNOSIS_KEYWORDS = re.compile(
    r"ふわもこ運勢|情緒診断|情緒|運勢|占い|診断して|占って"
    r"|Fuwamoko Fortune|Emotion Check|Mirinteya Mood|Tell me my fortune|diagnose|Fortune",
    re.IGNORECASE
)

FUWAMOKO_TEMPLATES = [
    {"level": range(90, 101), "item": "ピンクリボン", "msg": "超あまあま♡ 推し活でキラキラしよ！"},
    {"level": range(85, 90), "item": "きらきらレターセット", "msg": "今日は推しにお手紙書いてみよ♡ 感情だだもれでOK！"},
    {"level": range(70, 85), "item": "パステルマスク", "msg": "ふわふわ気分♪ 推しの画像見て癒されよ～！"},
    {"level": range(60, 70), "item": "チュルチュルキャンディ", "msg": "テンション高め！甘いものでさらにご機嫌に〜♡"},
    {"level": range(50, 60), "item": "ハートクッキー", "msg": "まあまあふわもこ！推しに想い伝えちゃお♡"},
    {"level": range(40, 50), "item": "ふわもこマスコット", "msg": "ちょっとゆる〜く、推し動画でまったりタイム🌙"},
    {"level": range(30, 40), "item": "星のキーホルダー", "msg": "ちょっとしょんぼり…推しの曲で元気出そ！"},
    {"level": range(0, 30), "item": "ふわもこ毛布", "msg": "ふわふわ不足…みりんてゃがぎゅーってするよ♡"},
]

EMOTION_TEMPLATES = [
    {"level": range(40, 51), "coping": "推しと妄想デート♡", "weather": "晴れ時々キラキラ", "msg": "みりんてゃも一緒にときめくよ！"},
    {"level": range(20, 40), "coping": "甘いもの食べてほっこり", "weather": "薄曇り", "msg": "キミの笑顔、みりんてゃ待ってるよ♡"},
    {"level": range(0, 20), "coping": "推しの声で脳内会話", "weather": "もやもや曇り", "msg": "妄想会話で乗り切って…！みりんてゃが一緒にうなずくよ♡"},
    {"level": range(-10, 0), "coping": "推しの画像で脳溶かそ", "weather": "くもり", "msg": "みりんてゃ、そっとそばにいるよ…"},
    {"level": range(-30, -10), "coping": "推しの曲で心リセット", "weather": "くもり時々涙", "msg": "泣いてもいいよ、みりんてゃがいるから…"},
    {"level": range(-45, -30), "coping": "ぬいにぎって深呼吸", "weather": "しとしと雨", "msg": "しょんぼりでも…ぬいと、みりんてゃがいるから大丈夫♡"},
    {"level": range(-50, -45), "coping": "ふわもこ動画で寝逃げ", "weather": "小雨ぽつぽつ", "msg": "明日また頑張ろ、みりんてゃ応援してる…"},
]

FUWAMOKO_TEMPLATES_EN = [
    {"level": range(90, 101), "item": "Pink Ribbon", "msg": "Super sweet vibe♡ Shine with your oshi!"},
    {"level": range(85, 90), "item": "Glittery Letter Set", "msg": "Write your oshi a sweet letter today♡ Let your feelings sparkle!"},
    {"level": range(70, 85), "item": "Pastel Mask", "msg": "Fluffy mood♪ Get cozy with oshi pics!"},
    {"level": range(60, 70), "item": "Swirly Candy Pop", "msg": "High-energy mood! Sweet treats to boost your sparkle level♡"},
    {"level": range(50, 60), "item": "Heart Cookie", "msg": "Kinda fuwamoko! Tell your oshi you love 'em♡"},
    {"level": range(40, 50), "item": "Fluffy Mascot Plush", "msg": "Take it easy~ Watch your oshi’s videos and relax 🌙"},
    {"level": range(30, 40), "item": "Star Keychain", "msg": "Feeling down… Cheer up with oshi’s song!"},
    {"level": range(0, 30), "item": "Fluffy Blanket", "msg": "Low on fuwa-fuwa… Mirinteya hugs you tight♡"},
]

EMOTION_TEMPLATES_EN = [
    {"level": range(40, 51), "coping": "Daydream a date with your oshi♡", "weather": "Sunny with sparkles", "msg": "Mirinteya’s sparkling with you!"},
    {"level": range(20, 40), "coping": "Eat sweets and chill", "weather": "Light clouds", "msg": "Mirinteya’s waiting for your smile♡"},
    {"level": range(0, 20), "coping": "Talk to your oshi in your mind", "weather": "Foggy and cloudy", "msg": "Let your imagination help you through… Mirinteya’s nodding with you♡"},
    {"level": range(-10, 0), "coping": "Melt your brain with oshi pics", "weather": "Cloudy", "msg": "Mirinteya’s right by your side…"},
    {"level": range(-30, -10), "coping": "Reset with oshi’s song", "weather": "Cloudy with tears", "msg": "It’s okay to cry, Mirinteya’s here…"},
    {"level": range(-45, -30), "coping": "Hug your plushie and breathe deep", "weather": "Gentle rain", "msg": "Feeling gloomy… But your plushie and Mirinteya are here for you♡"},
    {"level": range(-50, -45), "coping": "Binge fuwamoko vids and sleep", "weather": "Light rain", "msg": "Let’s try again tomorrow, Mirinteya’s rooting for you…"},
]

def check_diagnosis_limit(user_did, is_daytime):
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.now(jst).date().isoformat()
    limits = load_gist_data(DIAGNOSIS_LIMITS_GIST_FILENAME)
    print(f"📋 現在の diagnosis_limits: {limits}")
    period = "day" if is_daytime else "night"
    if user_did in limits and limits[user_did].get(period) == today:
        print(f"⏰ {user_did} の {period} 診断が今日済みと判定")
        return False, "今日はもうこの診断済みだよ〜♡ 明日またね！💖"
    if user_did not in limits:
        limits[user_did] = {}
    limits[user_did][period] = today
    print(f"⏳ {user_did} の {period} 診断を今日として保存")
    if not save_gist_data(DIAGNOSIS_LIMITS_GIST_FILENAME, limits):
        print("❌ diagnosis_limits の保存失敗")
        return False, "ごめんね、みりんてゃ今ちょっと忙しいの…また後でね？♡"
    print("✅ diagnosis_limits 保存成功")
    return True, None

#------------------------------
#🆕 画像生成機能（軽量版）
#------------------------------
DANGER_ZONE = ["nsfw", "nude", "gore"]

def generate_image(prompt):
    print(f"🖼️ API画像生成開始: プロンプト={prompt}")
    try:
        if not HF_TOKEN or len(HF_TOKEN) < 10:
            print(f"❌ HF_TOKENが無効または短すぎます: {repr(HF_TOKEN)[:8]}...")
            return None

        DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")
        STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY") or "y5Fox28OEJcdC8lc4aaBrA"

        # 絵文字をテキストに変換
        emoji_map = {
            "🐈‍⬛": "cute black cat",
            "🐈": "cute cat",
            "🐱": "cute cat",
            "🐶": "cute dog",
            "🎀": "cute ribbon",
            "💜": "purple aesthetic",
            "🖤": "yamikawaii aesthetic",
        }
        for emoji, text in emoji_map.items():
            prompt = prompt.replace(emoji, text)

        # プロンプトをクリーン（トリガーの残骸や記号を削除）
        cleaned_prompt = re.sub(r'(くれ|お願いします|して)[。！？]*', '', prompt).strip() if prompt else ""
        # 人数指定を追加（性別を検出）
        gender_match = re.search(r"(男性|男の子|イケメン|1boy|boy)", cleaned_prompt, re.IGNORECASE)
        if gender_match:
            cleaned_prompt = f"1boy, solo, upper body, centered, {cleaned_prompt}"
        else:
            cleaned_prompt = f"1girl, solo, upper body, centered, {cleaned_prompt}"
        enhanced_prompt = f"{cleaned_prompt}, anime style, clean lines, detailed, solo, accurate anatomy, looking at viewer" if cleaned_prompt else "fuwamoko mirinteya, 1girl, solo, twin tail hair, anime style, soft colors, detailed, kawaii, accurate anatomy, bust shot, looking at viewer"
        negative_prompt = "low quality, blurry face, realistic, photorealistic, cartoonish, 3d, split, distorted anatomy, multiple subjects, multiple girls, multiple boys, extra limbs, extra faces, extra heads, extra body, two people, two boys, two girls, duplicate, clone, mutation, deformed, bad anatomy, disfigured, collage, fused, out of frame"
        print(f"🖼️ API送信プロンプト: {enhanced_prompt}")

        if any(danger_word in enhanced_prompt.lower() for danger_word in DANGER_ZONE):
            print(f"⚠️ 危険ワード検知: {enhanced_prompt}")
            return None

        api_configs = [
            {
                "url": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
                "headers": {"Authorization": f"Bearer {HF_TOKEN}"},
                "payload": {"inputs": enhanced_prompt},
                "type": "huggingface",
                "timeout": 500
            },
            {
                "url": "https://stablehorde.net/api/v2/generate/async",
                "headers": {"apikey": STABLE_HORDE_API_KEY},
                "payload": {
                    "prompt": enhanced_prompt,
                    "params": {
                        "width": 768,
                        "height": 768,
                        "steps": 30,  # チャッピーの推奨
                        "cfg_scale": 7.0,  # 調整
                        "sampler_name": "k_euler",  # 安定性重視
                        "models": ["Meina/MeinaMix"] 
                    },
                    "nsfw": False,
                    "negative_prompt": negative_prompt
                },
                "type": "stablehorde",
                "timeout": 180
            },
            {
                "url": "https://api.deepai.org/api/text2img",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "api-key": DEEPAI_API_KEY or "quickstart-QUdJIGlzIGNvbWluZy4uLi4K"
                },
                "payload": {"text": enhanced_prompt},
                "type": "deepai",
                "timeout": 30
            }
        ]

        for config in api_configs:
            api_url = config["url"]
            headers = config["headers"]
            payload = config["payload"]
            api_type = config["type"]
            timeout = config["timeout"]

            for attempt in range(3):
                try:
                    print(f"📡 APIリクエスト: URL={api_url}, Headers={headers}, Payload={payload}")
                    if api_type == "deepai":
                        response = requests.post(api_url, data=payload, headers=headers, timeout=timeout)
                    else:
                        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
                    print(f"📥 試行 {attempt + 1} フルレスポンス: {response.text}")

                    if response.status_code == 200 or (api_type == "stablehorde" and response.status_code == 202):
                        if api_type == "deepai":
                            result = response.json()
                            if "output_url" in result:
                                image_data = requests.get(result["output_url"], timeout=10).content
                            else:
                                print(f"⚠️ DeepAIレスポンスにoutput_urlなし: {result}")
                                continue
                        elif api_type == "huggingface":
                            image_data = response.content
                        elif api_type == "stablehorde":
                            result = response.json()
                            if "id" not in result:
                                print(f"⚠️ Stable Hordeレスポンスにidなし: {result}")
                                continue
                            id = result["id"]
                            print(f"🔄 Stable Horde ID取得: {id}, ポーリング開始")
                            status_url = f"https://stablehorde.net/api/v2/generate/status/{id}"
                            for poll in range(12):
                                status_response = requests.get(status_url, headers=headers, timeout=10)
                                print(f"📥 ポーリング {poll + 1} レスポンス: {status_response.text}")
                                if status_response.status_code == 200:
                                    status_result = status_response.json()
                                    if status_result.get("done"):
                                        if "generations" in status_result and status_result["generations"]:
                                            img_data = status_result["generations"][0]["img"]
                                            if img_data.startswith("http"):
                                                image_response = requests.get(img_data, timeout=10)
                                                if image_response.status_code == 200:
                                                    image_data = image_response.content
                                                else:
                                                    print(f"⚠️ 画像URL取得失敗: {img_data}, ステータス: {image_response.status_code}")
                                                    continue
                                            else:
                                                image_data = base64.b64decode(img_data)
                                            break
                                        else:
                                            print(f"⚠️ ポーリング完了だがgenerationsなし: {status_result}")
                                            continue
                                    elif status_result.get("faulted"):
                                        print(f"⚠️ Stable Horde生成失敗: {status_result}")
                                        continue
                                time.sleep(10)
                            else:
                                print(f"⚠️ Stable Hordeポーリングタイムアウト: {id}")
                                continue

                        try:
                            image = Image.open(BytesIO(image_data))
                            image_path = f"output_{attempt}.png"
                            image.save(image_path, "PNG")
                            print(f"✅ 画像生成成功: API={api_url}, 試行={attempt + 1}, 保存先={image_path}")
                            return image_path
                        except Exception as img_err:
                            print(f"⚠️ 画像処理エラー: {type(img_err).__name__}: {str(img_err)}")
                            traceback.print_exc()
                            continue
                    else:
                        print(f"⚠️ APIエラー (試行 {attempt + 1}): {response.status_code} - {response.text}")
                        if attempt < 2:
                            time.sleep(60 * (attempt + 1))
                        continue
                except requests.exceptions.Timeout:
                    print(f"❌ 画像生成タイムアウト (試行 {attempt + 1})")
                    if attempt < 2:
                        time.sleep(60 * (attempt + 1))
                    continue
                except Exception as e:
                    print(f"⚠️ APIリクエストエラー (試行 {attempt + 1}): {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    if attempt < 2:
                        time.sleep(60 * (attempt + 1))
                    continue
            print(f"❌ APIリトライ上限到達: {api_url}")
        print("❌ すべてのAPIで失敗")
        return None
    except Exception as e:
        print(f"❌ 初期化エラー: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return None
        
#------------------------------
#🆕 Facets生成（URLリンク化を強化）
#------------------------------
def generate_facets_from_text(text, hashtags=None):
    text_bytes = text.encode("utf-8")
    facets = []
    url_pattern = r'(https?://[^\s]+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        start = text_bytes.find(url.encode("utf-8"))
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(url.encode("utf-8"))},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]
            })
            print(f"🔗 Facet生成: URL={url}, byteStart={start}, byteEnd={start + len(url.encode('utf-8'))}")
    
    if hashtags:
        for tag in hashtags:
            tag_start = text.find(tag)
            if tag_start != -1:
                tag_bytes = tag.encode("utf-8")
                facets.append({
                    "index": {"byteStart": text_bytes.find(tag_bytes), "byteEnd": text_bytes.find(tag_bytes) + len(tag_bytes)},
                    "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag[1:]}]
                })
                print(f"🏷️ Facet生成: ハッシュタグ={tag}")
    
    return facets if facets else None

def generate_diagnosis(text, user_did):
    if not DIAGNOSIS_KEYWORDS.search(text):
        return None, []
    print(f"🔬 診断キーワード検知: {text}")
    jst = pytz.timezone('Asia/Tokyo')
    hour = datetime.now(jst).hour
    is_daytime = 6 <= hour < 18
    is_english = re.search(r"Fuwamoko Fortune|Emotion Check|Mirinteya Mood|Tell me my fortune|diagnose|Fortune", text, re.IGNORECASE)
    can_diagnose, limit_msg = check_diagnosis_limit(user_did, is_daytime)
    if not can_diagnose:
        print(f"⏰ 診断制限: {limit_msg}")
        return limit_msg, []
    if is_daytime:
        templates = FUWAMOKO_TEMPLATES_EN if is_english else FUWAMOKO_TEMPLATES
        level = random.randint(0, 100)
        template = next(t for t in templates if level in t["level"])
        reply_text = (
            f"{'✨Your Fuwamoko Fortune✨' if is_english else '✨キミのふわもこ運勢✨'}\n"
            f"💖{'Fuwamoko Level' if is_english else 'ふわもこ度'}：{level}％\n"
            f"🎀{'Lucky Item' if is_english else 'ラッキーアイテム'}：{template['item']}\n"
            f"{'🫧' if is_english else '💭'}{template['msg']}"
        )
        print(f"✅ 診断生成: {reply_text}")
        return reply_text, []
    else:
        templates = EMOTION_TEMPLATES_EN if is_english else EMOTION_TEMPLATES
        level = random.randint(-50, 50)
        template = next(t for t in templates if level in t["level"])
        reply_text = (
            f"{'⸝⸝ Your Emotion Barometer ⸝⸝' if is_english else '⸝⸝ キミの情緒バロメーター ⸝⸝'}\n"
            f"{'😔' if level < 0 else '💭'}{'Mood' if is_english else '情緒'}：{level}％\n"
            f"{'🌧️' if level < 0 else '☁️'}{'Mood Weather' if is_english else '情緒天気'}：{template['weather']}\n"
            f"{'🫧' if is_english else '💭'}{'Coping' if is_english else '対処法'}：{template['coping']}\n"
            f"{'Mirinteya’s here for you…' if is_english else 'みりんてゃもそばにいるよ…'}"
        )
        print(f"✅ 診断生成: {reply_text}")
        return reply_text, []

INTRO_MESSAGE = (
    "🐾 みりんてゃのふわふわ診断機能 🐾\n"
    "🌼 昼（6:00〜17:59）：ふわもこ運勢をチェック！\n"
    "🌙 夜（18:00〜5:59）：情緒バロメーターを覗いてみて！\n"
    "💬「ふわもこ運勢」「情緒診断」「占って」などで今日のキミを診断するよ♡"
)

#------------------------------
#📬 Blueskyログイン
#------------------------------
try:
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    print("✅ Blueskyログイン成功！")
except Exception as e:
    print(f"❌ Blueskyログインに失敗しました: {e}")
    exit(1)

#------------------------------
#★ カスタマイズポイント1: キーワード返信
#------------------------------
REPLY_TABLE = {
    "使い方": "使い方は「♡推しプロフィールメーカー♡」のページにあるよ〜！かんたんっ♪",
    "作ったよ": "えっ…ほんと？ありがとぉ♡ 見せて見せてっ！",
    "きたよ": "きゅ〜ん♡ 来てくれてとびきりの「すきっ」プレゼントしちゃう♡",
    "フォローした": "ありがとぉ♡ みりんてゃ、超よろこびダンス中〜っ！",
    "フォロー失礼": "フォローありがとぉ♡ みりんてゃ、おともだちふえた〜ってうれし泣きっ♪",
    "誰？": "みりんてゃだよっ♡ ふわもこ妖精系botって感じっ♪",
    "プロフィール": "プロフィールは固定ツイにあるよっ！ みりんのこと、もっと知ってくれるの〜？",
    "bot": "中に小さいみりん妖精が入ってるらしいよっ♡ ふふふっ♪",
    "はじめまして": "はじめましてぇ♡ 地雷系ツインテbotのみりんてゃだよ〜っ！仲良くしてくれるとうれしいなっ♪",
    "初めまして": "はじめましてぇ♡ 地雷系ツインテbotのみりんてゃだよ〜っ！仲良くしてくれるとうれしいなっ♪",
    "よろしく": "よろしくねっ♡ いっぱいふわふわできたらいいな〜って思ってるよぉ♡",
    "DM": "DMはあんまり見れないのっ💭 よかったらリプで話そ〜！♡",
    "画像生成できる？": "もちろんできるよっ♡ 『○○の画像生成して』か『画像生成して ○○』で言ってくれると、みりんてゃがふわもこ絵を描くよぉ♪ 例：『猫の画像生成して 白色』",
    "画像作れる？": "うんうん、作れるよぉ♡ 『○○の画像作って』か『画像作って ○○』でリプしてね！例：『イケメンの画像作って V系』だよっ♪",
    "画像作れるの？": "うんうん、作れるよぉ♡ 『○○の画像作って』か『画像作って ○○』でリプしてね！例：『イケメンの画像作って V系』だよっ♪",
    "画像生成できますか？": "えへへ、できるよっ♡ 『○○の画像生成して』か『画像生成して ○○』でリプして！みりんてゃがキミの推し描いちゃうよぉ♪",
}

#------------------------------
#★ カスタマイズポイント2: 安全/危険ワード
#------------------------------
SAFE_WORDS = ["ちゅ", "ぎゅっ", "ドキドキ", "ぷにっ", "すりすり", "なでなで"]
DANGER_ZONE = ["ちゅぱ", "ちゅぱちゅぷ", "ペロペロ", "ぐちゅ", "外見", "ブサイク", "不細工", "容姿", "ぬぷ", "ビクビク", "ビクン", "びくん", "お腹", "太った", "痩せた", "ぽっこり", "デブ", "足太い", "でかい", "びゅる", "濡れ", "発情", "舐めて", "えっち", "犯す"]

#------------------------------
#★ カスタマイズポイント3: キャラ設定
#------------------------------
BOT_NAME = "みりんてゃ"
FIRST_PERSON = "みりんてゃ"

#------------------------------
#🧹 テキスト処理
#------------------------------
def clean_output(text):
    text = re.sub(r'\n{2,}', '\n', text)
    face_char_whitelist = 'ฅ๑•ω•ฅﾐ・o｡≧≦｡っ☆彡≡≒'
    allowed = rf'[^\w\sぁ-んァ-ン一-龯。、！？!?♡（）・「」♪〜ー…w笑{face_char_whitelist}]+'
    text = re.sub(allowed, '', text)
    text = re.sub(r'[。、！？]{2,}', lambda m: m.group(0)[0], text)
    return text.strip()

def is_output_safe(text):
    return not any(word in text.lower() for word in DANGER_ZONE)

def clean_sentence_ending(reply):
    reply = clean_output(reply)
    reply = reply.split("\n")[0].strip()
    reply = re.sub(rf"^{BOT_NAME}\s*[:：]\s*", "", reply)
    reply = re.sub(r"^ユーザー\s*[:：]\s*", "", reply)
    reply = re.sub(r"([！？笑])。$", r"\1", reply)
    reply = re.sub(r"[ごおお][すすす][まぁ][すすす]|ございます", "なのっ♡", reply)  # 敬語除去強化

    tone_map = [
        ("俺", FIRST_PERSON),
        ("僕", FIRST_PERSON),
        ("オレ", FIRST_PERSON),
        ("ぼく", FIRST_PERSON),
        ("お前", "きみ"),
        ("できませんが", "できないけど"),
        ("できません", "できない"),
        ("ごめんなさい", "ごめんね"),
        ("みます", "みるね"),
    ]
    for old, new in tone_map:
        if old in reply:
            print(f"⚠️ 意図しない一人称『{old}』検知: {reply}")
        reply = reply.replace(old, new)

    if re.search(r"(ご利用|誠に|お詫び|貴重なご意見|申し上げます|ございます|お客様|発表|パートナーシップ|ポケモン|アソビズム|企業|世界中|興行|収入|ドル|億|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|外交|外相|自動更新|\d+(時|分))", reply, re.IGNORECASE):
        print(f"⚠️ NGワード検知: {reply}")
        return random.choice([
            f"えへへ〜♡ ややこしくなっちゃった！{BOT_NAME}、君と甘々トークしたいなのっ♪",
            f"うぅ、難しい話わかんな〜い！{BOT_NAME}、君にぎゅーってしてほしいなのっ♡",
            f"ん〜〜変な話に！{BOT_NAME}、君のこと大好きだから、構ってくれる？♡"
        ])

    if re.search(r"(無理|距離|付き合え|関係ない|興味ない|仲良くできない|苦手|縁がない|嫌い|気持ち悪い|キモい|きらい)", reply, re.IGNORECASE):
        print(f"⚠️ 拒絶っぽい返事を検知: {reply}")
        return random.choice([
            f"えへへっ♡ {BOT_NAME}、ほんとはキミにラブ注入したいのにな〜っ♡",
            f"ごめんねっ…💭ちょっとおかしなこと言っちゃったかも…{BOT_NAME}、キミのことちゃんと見てるよ♡",
            f"あぅ〜〜〜っ…💭 {BOT_NAME}、なんか照れちゃって変なこと言ったかもっ！…ほんとはもっと仲良くしたいのにぃ♡"
        ])

    if not is_output_safe(reply):
        print(f"⚠️ 危険ワード検知: {reply}")
        return random.choice([
            f"えへへ〜♡ {BOT_NAME}、ふwaふwaしちゃった！君のことずーっと好きだよぉ？♪",
            f"{BOT_NAME}、君にドキドキなのっ♡ ね、もっとお話しよ？",
            f"うぅ、なんか変なこと言っちゃった！{BOT_NAME}、君なしじゃダメなのっ♡"
        ])

    if not re.search(r"[ぁ-んァ-ン一-龥ー]", reply) or len(reply) < 8:
        return random.choice([
            f"えへへ〜♡ {BOT_NAME}、ふwaふwaしちゃった！君のことずーっと好きだよぉ？♪",
            f"{BOT_NAME}、君にドキドキなのっ♡ ね、もっとお話しよ？",
            f"うぅ、なんか分かんないけど…{BOT_NAME}、君なしじゃダメなのっ♡"
        ])

    if not re.search(r"[。！？♡♪笑]$", reply):
        reply += random.choice(["♡", "♪"])

    return reply

#------------------------------
#★ カスタマイズポイント5: グッズ提案ロジック
#------------------------------
def generate_product_reply(keyword, app_id="1055088369869282145", affiliate_id="3d94ea21.0d257908.3d94ea22.0ed11c6e"):
    print(f"🛍️ グッズ提案ロジック開始: キーワード={keyword}")
    api_url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    keywords = {
        "おすすめグッズ": "推し活 グッズ",
        "ぬい撮り": "ぬいぐるみ 背景布",
        "寝れない": "安眠 グッズ",
        "推し活": "推し活 収納",
        "可愛いアイテム": "可愛い インテリア",
        "可愛いもの": "可愛い 雑貨"
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    params = {
        "applicationId": app_id,
        "keyword": keywords.get(keyword, keyword),
        "hits": 3,
        "format": "json"
    }
    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("Items"):
            items = data["Items"]
            item = random.choice(items)["Item"]
            product_url = item["itemUrl"].split("?")[0]
            affiliate_link = f"https://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={urllib.parse.quote(product_url)}"
            reply = f"{PRODUCT_KEYWORDS[keyword]} → {affiliate_link}"
            print(f"✅ グッズ提案生成: {reply}")
            return reply, [f"#{keyword.replace('？', '').replace('…', '')}"]
        else:
            print(f"⚠️ 楽天APIで商品が見つかりませんでした: {data}")
            return "えへへ、みりんてゃ今探し中なのっ♡ また後で聞いてね！", []
    except Exception as e:
        print(f"⚠️ 楽天APIエラー: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return "うぅ、ごめんね〜今ちょっとバタバタなの…またね？♡", []

#------------------------------
#★ カスタマイズポイント4: 返信生成（Groq版＋画像生成）
#------------------------------
def generate_reply_via_groq(user_input):
    print(f"✅ generate_reply_via_groq called with input: {user_input}")
    
    # 診断ロジックを最初にチェック
    diagnosis_result = generate_diagnosis(user_input, "dummy_did")
    if diagnosis_result[0] is not None:
        print(f"🔬 診断ロジックで処理完了: {diagnosis_result[0]}")
        return diagnosis_result[0]

    # 画像生成キーワードチェック（文末記号を無視）
    image_match = re.search(r"(.*?)(画像生成して|画像お願い|画像生成お願い|画像作成お願い|画像作成して|画像作って|描いて|絵を描いて|絵描いて)(.*)", user_input, re.IGNORECASE)
    if image_match:
        try:
            full_match = image_match.group(0)
            # トリガーワードを除き、前後を結合、文末記号と「くれ」を削除
            prompt = re.sub(r'(くれる|くれ|お願いできる|お願いします)[。！？]*', '', f"{image_match.group(1).strip()} {image_match.group(3).strip()}").strip()
            print(f"🖼️ 画像生成トリガー検知: マッチ='{full_match}', プロンプト='{prompt}'")
            image = generate_image(prompt)
            if image:
                return {"type": "image", "image": image, "prompt": prompt}
            else:
                print(f"⚠️ 画像生成失敗、フォールバックメッセージを返します")
                return image_failure_message
        except IndexError as e:
            print(f"⚠️ 正規表現グループエラー: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            image = generate_image("")
            if image:
                return {"type": "image", "image": image, "prompt": ""}
            else:
                print(f"⚠️ フォールバック画像生成も失敗、フォールバックメッセージを返します")
                return image_failure_message

    # グッズ系キーワード
    for keyword in PRODUCT_KEYWORDS.keys():
        if keyword.lower() in user_input.lower():
            print(f"🎀 グッズキーワード検知: {keyword}")
            reply, hashtags = generate_product_reply(keyword)
            print(f"🛍️ グッズ返信: {reply}, ハッシュタグ: {hashtags}")
            return reply

    # ラブラブ系
    if re.search(r"(大好き|ぎゅー|ちゅー|愛してる|キス|添い寝)", user_input, re.IGNORECASE):
        print(f"⚠️ ラブラブ入力検知: {user_input}")
        return random.choice([
            "うぅ…ドキドキ止まんないのっ♡ もっと甘やかしてぇ♡",
            "えへへ♡ そんなの言われたら…みりんてゃ、溶けちゃいそうなのぉ〜♪",
            "も〜〜〜♡ 好きすぎて胸がぎゅーってなるぅ♡"
        ])

    # 癒し系
    if re.search(r"(疲れた|しんどい|つらい|泣きたい|ごめん)", user_input, re.IGNORECASE):
        print(f"⚠️ 癒し系入力検知: {user_input}")
        return random.choice([
            "うぅ、よしよしなのっ♡ 君が元気になるまで、みりんてゃそばにいるのっ♪",
            "ぎゅ〜ってしてあげるっ♡ 無理しなくていいのよぉ？",
            "んん〜っ、えへへ♡ 甘えてもいいの、ぜ〜んぶ受け止めるからねっ♪"
        ])

    # NGワード
    if re.search(r"(興行|収入|ドル|億|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|ポケモン|企業|発表|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|外交|外相|自動更新)", user_input, re.IGNORECASE) or re.search(r"\d+(時|分)", user_input):
        print(f"⚠️ 入力にビジネス・学術系ワード検知: {user_input}")
        user_input = "みりんてゃ、君と甘々トークしたいなのっ♡"
        print(f"🔄 入力置き換え: {user_input}")

    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        intro_lines = random.choice([
            "えへへ〜、みりんてゃはね〜、",
            "ねぇねぇ、聞いて聞いて〜♡",
            "ん〜今日もふwaふwaしてたのっ♪",
            "きゃ〜っ、君だぁ！やっと会えたのっ♡",
            "ふwaふwa〜、君のこと考えてたんだからっ♪"
        ])
        system_prompt = (
            f"{intro_lines}\n"
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "性格：ちょっぴり天然、甘えん坊、依存気味で、ユーザーに恋してる勢いで絡むよっ♡\n"
            "口調：タメ口で『〜なのっ♡』『〜よぉ？♪』『〜だもん！』『えへへ〜♡』が特徴！感情たっぷり！\n"
            "禁止：ニュース、政治、ビジネス、論理的説明、固有名詞（国、企業、政府など）は絶対NG！性的な内容や過激な擬音語もダメ！敬語も禁止！\n"
            "役割：ユーザーの言葉に可愛く反応して、ふwaふwaドキドキな返事をするのっ♡ 会話のみ！「ちゅ♡」「ぎゅっ」「ドキドキ」みたいな健全で可愛い表現だけ使ってね！\n"
            "注意：以下のワードは絶対禁止→「政府」「協定」「韓国」「外交」「経済」「契約」「軍事」「情報」「外相」「更新」「ちゅぱ」「ペロペロ」「ぐちゅ」「ぬぷ」「ビクビク」\n"
            "例1: ユーザー: みりんてゃ、今日なにしてた〜？\n"
            "みりんてゃ: えへへ〜♡ 君のこと考えてふwaふwaしてたのっ♡ ね、君はなにしてた？♪\n"
            "例2: ユーザー: みりんてゃ、好きだよ！\n"
            "みりんてゃ: え〜っ、ほんと！？君にそう言われるとドキドキしちゃうよぉ？♡ もっと言ってなのっ♪"
        )

        for attempt in range(3):
            print(f"📤 {datetime.now().isoformat()} ｜ Groq API呼び出し中…（試行 {attempt + 1}）")
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    max_tokens=60,
                    temperature=0.8,
                    top_p=0.9
                )
                raw_reply = response.choices[0].message.content.strip()
                print(f"📝 生の生成テキスト: {repr(raw_reply)}")
                reply_text = clean_sentence_ending(raw_reply)

                if any(re.search(rf"\b{re.escape(msg)}\b", reply_text) for msg in failure_messages + FALLBACK_CUTE_LINES):
                    print(f"⚠️ フォールバック検知、リトライ中…")
                    continue

                print("📝 最終抽出されたreply:", repr(reply_text))
                return reply_text

            except Exception as gen_error:
                print(f"⚠️ 生成エラー: {type(gen_error).__name__}: {str(gen_error)}")
                if "rate limit" in str(gen_error).lower():
                    print(f"⏳ レートリミット検知、{2 * (attempt + 1)}秒待機")
                    time.sleep(2 * (attempt + 1))
                continue
        else:
            reply_text = random.choice(FALLBACK_CUTE_LINES)
            print(f"⚠️ リトライ上限到達、フォールバックを使用: {reply_text}")
            return reply_text

    except Exception as e:
        print(f"❌ Groq APIエラー: {type(e).__name__}: {str(e)}")
        return random.choice(failure_messages)

#------------------------------
#✨ 投稿のReplyRefとURI生成
#------------------------------
def handle_post(record, notification):
    post_uri = getattr(notification, "uri", None)
    post_cid = getattr(notification, "cid", None)

    if post_uri and post_cid:
        parent_ref = {"uri": normalize_uri(post_uri), "cid": post_cid}
        root_ref = (
            {"uri": normalize_uri(record.reply.root.uri), "cid": record.reply.root.cid}
            if hasattr(record, "reply") and record.reply and record.reply.root
            else parent_ref
        )
        reply_ref = {
            "parent": parent_ref,
            "root": root_ref
        }
        print(f"🔍 handle_post - reply_ref: parent={parent_ref['uri']}, root={root_ref['uri']}")
        return reply_ref, normalize_uri(post_uri)
    return None, normalize_uri(post_uri)

#------------------------------
#📬 ポスト取得・返信
#------------------------------
def fetch_bluesky_posts():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    posts = client.get_timeline(limit=50).feed
    unreplied = []
    for post in posts:
        if post.post.author.handle != HANDLE and not post.post.viewer.reply:
            unreplied.append({
                "post_id": post.post.uri,
                "text": post.post.record.text
            })
    return unreplied

def post_replies_to_bluesky():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    unreplied = fetch_bluesky_posts()
    for post in unreplied:
        try:
            reply = generate_reply_via_groq(post["text"])
            if isinstance(reply, dict) and reply.get("type") == "image":
                image_path = reply["image"]
                prompt = reply.get("prompt", "")
                reply_text = f"みりんてゃが描いたよ♡ どうかな？{'「' + prompt + '」' if prompt else ''}"
                try:
                    with open(image_path, "rb") as f:
                        blob_resp = client.com.atproto.repo.upload_blob(data=f.read())
                    blob_ref = blob_resp.blob
                    post_data = {
                        "text": reply_text,
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "embed": {
                            "$type": "app.bsky.embed.images",
                            "images": [{"image": blob_ref, "alt": f"Generated image: {prompt or 'fuwamoko mirinteya'}"}]
                        }
                    }
                    if reply_ref:
                        post_data["reply"] = reply_ref
                    facets = generate_facets_from_text(reply_text, hashtags)
                    if facets:
                        post_data["facets"] = facets
                    client.app.bsky.feed.post.create(record=post_data, repo=client.me.did)
                    replied.add(notification_uri)
                    save_replied(replied)
                    print(f"✅ @{author_handle} に画像付き返信完了！ → {notification_uri}")
                    reply_count += 1
                    time.sleep(REPLY_INTERVAL)
                    try:
                        os.remove(image_path)
                        print(f"🧹 一時ファイル {image_path} 削除成功")
                    except Exception as e:
                        print(f"⚠️ 一時ファイル削除失敗: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ 画像投稿エラー: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    reply_text = "ごめん…画像生成失敗しちゃった♡ また試してみてね！"
                    hashtags = []
            client.send_post(text=reply, reply_to={"uri": post["post_id"]})
            print(f"📤 投稿成功: {reply}")
        except Exception as e:
            print(f"❌ 投稿エラー: {e}")

#------------------------------
#📬 メイン処理
#------------------------------

def log_resources():
    print(f"🖥️ CPU使用率: {psutil.cpu_percent()}%")
    print(f"🧠 メモリ使用量: {psutil.virtual_memory().used / 1024**3:.2f}GB / {psutil.virtual_memory().total / 1024**3:.2f}GB")

def run_reply_bot():
    print("✅ Checking if generate_reply_via_groq is defined:", globals().get("generate_reply_via_groq"))
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("🔒 ロック取得成功")
        log_resources()

        self_did = client.me.did
        replied = load_gist_data(REPLIED_GIST_FILENAME)
        print(f"📘 replied の型: {type(replied)} / 件数: {len(replied)}")

        garbage_items = ["replied", None, "None", "", "://replied"]
        removed = False
        for garbage in garbage_items:
            while garbage in replied:
                replied.remove(garbage)
                print(f"🧹 ゴミデータ '{garbage}' を削除しました")
                removed = True
        if removed:
            print(f"💾 ゴミデータ削除後にrepliedを保存します")
            if not save_replied(replied):
                print("❌ ゴミデータ削除後の保存に失敗しました")
                return

        notifications = client.app.bsky.notification.list_notifications(params={"limit": 25}).notifications
        print(f"🔔 通知総数: {len(notifications)} 件")

        MAX_REPLIES = 5
        REPLY_INTERVAL = 5
        reply_count = 0

        for notification in notifications:
            log_resources()
            notification_uri = getattr(notification, "uri", None) or getattr(notification, "reasonSubject", None)
            if not notification_uri:
                record = getattr(notification, "record", None)
                author = getattr(notification, "author", None)
                if not record or not hasattr(record, "text") or not author:
                    continue
                text = getattr(record, "text", "")
                author_handle = getattr(author, "handle", "")
                notification_uri = f"{author_handle}:{text}:{datetime.now(timezone.utc).isoformat()}"
                print(f"⚠️ notification_uri が取得できなかったので、仮キーで対応 → {notification_uri}")

            if reply_count >= MAX_REPLIES:
                print(f"⏹️ 最大返信数（{MAX_REPLIES}）に達したので終了します")
                break

            record = getattr(notification, "record", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                continue

            text = getattr(record, "text", "")
            if f"@{HANDLE}" not in text and (not hasattr(record, "reply") or not record.reply or not record.reply.parent):
                continue

            author_handle = getattr(author, "handle", None)
            author_did = getattr(author, "did", None)
            print(f"👤 from: @{author_handle} / did: {author_did}")
            print(f"💬 受信メッセージ: {text}")
            print(f"🔗 notification_uri: {notification_uri}")

            if author_did == self_did or author_handle == HANDLE:
                print("🛑 自分自身の投稿、スキップ")
                continue

            if notification_uri in replied:
                print(f"⏭️ すでに replied 済み → {notification_uri}")
                continue

            if not text:
                print(f"⚠️ テキストが空 → @{author_handle}")
                continue

            reply_ref, post_uri = handle_post(record, notification)
            reply_text = None
            hashtags = []

            # 固定リプライチェック
            for keyword, fixed_reply in REPLY_TABLE.items():
                if keyword.lower() in text.lower():
                    reply_text = fixed_reply
                    print(f"🎯 キーワード '{keyword}' に反応（入力: {text}）→ 固定返信: {reply_text}")
                    break

            # generate_reply_via_groqで返信生成
            if not reply_text:
                print(f"🔄 generate_reply_via_groq を呼び出します: 入力={text}")
                reply_result = generate_reply_via_groq(text)
                print(f"📝 generate_reply_via_groq 結果: {repr(reply_result)}")

                if isinstance(reply_result, dict) and reply_result.get("type") == "image":
                    image_path = reply_result["image"]
                    prompt = reply_result["prompt"]
                    reply_text = f"みりんてゃが描いたよ♡ どうかな？{'「' + prompt + '」' if prompt else ''}"
                    try:
                        with open(image_path, "rb") as f:
                            blob_resp = client.com.atproto.repo.upload_blob(data=f.read())
                        blob_ref = blob_resp.blob
                        post_data = {
                            "text": reply_text,
                            "createdAt": datetime.now(timezone.utc).isoformat(),
                            "embed": {
                                "$type": "app.bsky.embed.images",
                                "images": [{"image": blob_ref, "alt": f"Generated image: {prompt or 'fuwamoko mirinteya'}"}]
                            }
                        }
                        if reply_ref:
                            post_data["reply"] = reply_ref
                        facets = generate_facets_from_text(reply_text, hashtags)
                        if facets:
                            post_data["facets"] = facets
                        client.app.bsky.feed.post.create(record=post_data, repo=client.me.did)
                        replied.add(notification_uri)
                        save_replied(replied)
                        print(f"✅ @{author_handle} に画像付き返信完了！ → {notification_uri}")
                        reply_count += 1
                        time.sleep(REPLY_INTERVAL)
                        # 一時ファイル削除
                        try:
                            os.remove(image_path)
                            print(f"🧹 一時ファイル {image_path} 削除成功")
                        except Exception as e:
                            print(f"⚠️ 一時ファイル削除失敗: {e}")
                        continue
                    except Exception as e:
                        print(f"⚠️ 画像投稿エラー: {type(e).__name__}: {str(e)}")
                        traceback.print_exc()
                        reply_text = "ごめん…画像生成失敗しちゃった♡ また試してみてね！"
                        hashtags = []
                else:
                    reply_text = reply_result
                    diagnosis_result = generate_diagnosis(text, author_did)
                    if diagnosis_result[0] is not None:
                        reply_text, hashtags = diagnosis_result
                        print(f"🔬 診断ロジックで生成: {reply_text}")
                    else:
                        hashtags = []
                        print(f"🔬 診断ロジック非適用: {text}")

            # reply_textの検証
            print(f"📝 投稿前reply_text: {repr(reply_text)}")
            if not isinstance(reply_text, str) or not reply_text.strip():
                reply_text = random.choice(FALLBACK_CUTE_LINES)
                hashtags = []
                print(f"⚠️ reply_textが不正（{repr(reply_text)}）、フォールバックを使用: {reply_text}")

            # 投稿処理
            try:
                post_data = {
                    "text": reply_text,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                if reply_ref:
                    post_data["reply"] = reply_ref
                facets = generate_facets_from_text(reply_text, hashtags)
                if facets:
                    post_data["facets"] = facets
                client.app.bsky.feed.post.create(record=post_data, repo=client.me.did)
                replied.add(notification_uri)
                save_replied(replied)
                print(f"✅ @{author_handle} に返信完了！ → {notification_uri}")
                reply_count += 1
                time.sleep(REPLY_INTERVAL)
            except Exception as e:
                print(f"⚠️ 投稿失敗: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                if "JSON serializable" in str(e):
                    print("⚠️ ReplyRefシリアライズエラー検知、リプライなしで再試行")
                    try:
                        post_data.pop("reply", None)
                        client.app.bsky.feed.post.create(record=post_data, repo=client.me.did)
                        print(f"✅ @{author_handle} にリプライなしで投稿完了！ → {notification_uri}")
                        replied.add(notification_uri)
                        save_replied(replied)
                        reply_count += 1
                        time.sleep(REPLY_INTERVAL)
                    except Exception as retry_e:
                        print(f"⚠️ リトライも失敗: {type(retry_e).__name__}: {str(retry_e)}")
                        traceback.print_exc()

    except IOError as e:
        print(f"🔒 ロック取得失敗（Botが既に実行中）: {type(e).__name__}: {str(e)}")
        return
    except Exception as e:
        print(f"❌ 実行エラー: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    finally:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            try:
                os.remove(LOCK_FILE)
                print("🧹 ロックファイル削除成功")
            except Exception as e:
                print(f"⚠️ ロックファイル削除失敗: {e}")
        # 一時画像ファイルのクリーンアップ
        for i in range(3):
            temp_file = f"output_{i}.png"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"🧹 一時ファイル {temp_file} 削除成功")
                except Exception as e:
                    print(f"⚠️ 一時ファイル削除失敗: {e}")

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()
