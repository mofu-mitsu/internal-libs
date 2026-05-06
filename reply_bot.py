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

def check_kudos():
    """Stable HordeのKudos残高をチェック"""
    try:
        url = "https://stablehorde.net/api/v2/find_user"
        headers = {"apikey": STABLE_HORDE_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("kudos", 0)
        print(f"⚠️ Kudosチェック失敗: {response.text}")
        return 0
    except Exception as e:
        print(f"❌ Kudosチェックエラー: {type(e).__name__}: {str(e)}")
        return 0

def generate_image(prompt):
    print(f"🖼️ API画像生成開始: プロンプト={prompt}")
    global STABLE_HORDE_API_KEY
    try:
        if not HF_TOKEN or len(HF_TOKEN) < 10:
            print(f"❌ HF_TOKENが無効または短すぎます: {repr(HF_TOKEN)[:8]}...")
            return None

        DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")
        STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY") or "y5Fox28OEJcdC8lc4aaBrA"

        # Kudosチェック
        kudos = check_kudos()
        print(f"📊 Kudos残高: {kudos}")
        use_low_load = kudos < 20  # Kudos不足なら低負荷モード

        # 絵文字をテキストに変換
        emoji_map = {
            "🐈‍⬛": "adorable black kitten",
            "🐈": "adorable kitten",
            "🐱": "adorable kitten",
            "🐶": "adorable puppy",
            "🐰": "adorable bunny",
            "🎀": "cute ribbon",
            "💜": "purple aesthetic",
            "🖤": "yamikawaii style",
            "💖": "cute aesthetic",
        }
        for emoji, text in emoji_map.items():
            prompt = prompt.replace(emoji, text)

        # 髪型とスタイルを英語に変換
        hairstyle_map = {
            "ツインテール": "twin tails, double ponytails, symmetrical hair, highly detailed hair",
            "ポニーテール": "ponytail, single high ponytail, highly detailed hair, smooth hair texture",
            "お団子": "hair buns, double buns, highly detailed hair",
            "ショートカット": "short hair, bob cut, highly detailed hair",
            "ロングヘア": "long hair, flowing hair, highly detailed hair",
            "ふわもこ": "fuwamoko kawaii style, fluffy hair, soft aesthetic",
            "地雷系": "yamikawaii style",
            "ゴスロリ": "gothic lolita",
        }
        for jp, en in hairstyle_map.items():
            prompt = prompt.replace(jp, en)

        # プロンプトをクリーン
        cleaned_prompt = re.sub(r'(くれ|お願いします|して|\d+歳|ヨガインストラクター|ハートの瞳孔|女性|可愛い女の子)[。！？]*', '', prompt).strip() if prompt else ""
        cleaned_prompt = cleaned_prompt.replace("ヨガインストラクター", "yoga girl, casual sportswear").replace("ハートの瞳孔", "heart-shaped pupils").replace("女性", "girl").replace("可愛い女の子", "kawaii girl")

        # 性別に応じたスタイル置換
        gender_match = re.search(r"(男性|男の子|イケメン|1boy|boy)", cleaned_prompt, re.IGNORECASE)
        if gender_match and "gothic lolita" in cleaned_prompt.lower():
            cleaned_prompt = cleaned_prompt.replace("gothic lolita", "gothic male fashion, victorian suit, dark aesthetic")
        elif not gender_match and "gothic lolita" in cleaned_prompt.lower():
            cleaned_prompt = cleaned_prompt.replace("gothic lolita", "gothic lolita, frilly dress, intricate accessories")

        # 動物専用プロンプトパス
        animal_match = re.search(r"(猫|cat|キャット|kitten|🐈‍⬛|🐈|🐱|犬|dog|puppy|🐶|兎|rabbit|bunny|🐰|動物|animal)", cleaned_prompt, re.IGNORECASE)
        if animal_match:
            animal_type = (
                "kitten" if re.search(r"猫|cat|キャット|kitten|🐈‍⬛|🐈|🐱", cleaned_prompt, re.IGNORECASE)
                else "puppy" if re.search(r"犬|dog|puppy|🐶", cleaned_prompt, re.IGNORECASE)
                else "bunny" if re.search(r"兎|rabbit|bunny|🐰", cleaned_prompt, re.IGNORECASE)
                else "animal"
            )
            cleaned_prompt = f"adorable {animal_type}, ultra high quality, polished anime style, 2d, cartoonish, detailed fur, smooth fur texture, vibrant colors, sfw, safe, wholesome"
            enhanced_prompt = cleaned_prompt
        else:
            # 人数と性別指定
            if gender_match:
                cleaned_prompt = f"solo, single subject, one character, no background characters, centered focus, single head, single face, 1boy, upper body, {cleaned_prompt}, ultra high quality, polished anime style, 2d, cartoonish, mature aesthetic, detailed outfit, sfw, safe, wholesome"
            else:
                cleaned_prompt = f"solo, single subject, one character, no background characters, centered focus, single head, single face, young girl, upper body, {cleaned_prompt}, ultra high quality, polished anime style, 2d, cartoonish, mature aesthetic, detailed outfit, sfw, safe, wholesome"
            enhanced_prompt = f"{cleaned_prompt}, pastel colors, soft shading, clean lines, sharp details, detailed painting, smooth shading, no artifacts, clean edges, symmetrical face, balanced eyes, identical eye shape, detailed eyes, expressive eyes, accurate anatomy, looking at viewer, vibrant colors"

        negative_prompt = "low quality, blurry face, realistic, photorealistic, 3d, split, distorted anatomy, multiple subjects, multiple girls, multiple boys, extra limbs, extra faces, extra heads, multiple heads, fused heads, overlapping heads, two people, three people, duplicate, clone, mutation, deformed, bad anatomy, disfigured, collage, fused, out of frame, nsfw, nude, sexual, explicit, low detail, childish art, amateur drawing, uneven shading, painting errors, incomplete details, other hairstyles, loose hair, twin tails, messy hair, asymmetrical face, uneven eyes, mismatched eyes, creepy eyes, distorted face, horror, creepy, monstrous"
        print(f"🖼️ API送信プロンプト: {enhanced_prompt}")
        print(f"🛑 ネガティブプロンプト: {negative_prompt}")

        if any(danger_word in enhanced_prompt.lower() for danger_word in DANGER_ZONE):
            print(f"⚠️ 危険ワード検知: {enhanced_prompt}")
            return None

        api_configs = [
            {
                "url": "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-dev",
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
                        "width": 512 if use_low_load else 1024,
                        "height": 512 if use_low_load else 1024,
                        "steps": 30 if use_low_load else 50,
                        "cfg_scale": 9.0,
                        "sampler_name": "k_euler_a" if use_low_load else "k_dpmpp_sde",
                        "denoising_strength": 0.7,
                        "models": ["stabilityai/stable-diffusion-xl-base-1.0", "Lykon/AnimePastelDream", "andite/Yozora", "prompthero/anything-v5-pruned", "Meina/MeinaMix", "hakurei/Counterfeit-V3.0"]
                    },
                    "nsfw": True,
                    "censor_nsfw": False,
                    "negative_prompt": negative_prompt
                },
                "type": "stablehorde",
                "timeout": 180
            },
            {
                "url": "https://stablehorde.net/api/v2/generate/async",
                "headers": {"apikey": "0000000000"},
                "payload": {
                    "prompt": enhanced_prompt,
                    "params": {
                        "width": 512,
                        "height": 512,
                        "steps": 30,
                        "cfg_scale": 7.5,
                        "sampler_name": "k_euler_a",
                        "denoising_strength": 0.7,
                        "models": ["stabilityai/stable-diffusion-xl-base-1.0", "Lykon/AnimePastelDream", "andite/Yozora"]
                    },
                    "nsfw": True,
                    "censor_nsfw": False,
                    "negative_prompt": negative_prompt
                },
                "type": "stablehorde_anon",
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
                    print(f"📡 APIリクエスト: URL={api_url}, Type={api_type}, 試行={attempt + 1}")
                    if api_type == "deepai":
                        response = requests.post(api_url, data=payload, headers=headers, timeout=timeout)
                    else:
                        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
                    print(f"📥 試行 {attempt + 1} フルレスポンス: {response.text}")

                    if response.status_code == 200 or (api_type in ["stablehorde", "stablehorde_anon"] and response.status_code == 202):
                        if api_type == "deepai":
                            result = response.json()
                            if "output_url" in result:
                                image_data = requests.get(result["output_url"], timeout=10).content
                            else:
                                print(f"⚠️ DeepAIレスポンスにoutput_urlなし: {result}")
                                continue
                        elif api_type == "huggingface":
                            image_data = response.content
                        elif api_type in ["stablehorde", "stablehorde_anon"]:
                            result = response.json()
                            if "id" not in result:
                                print(f"⚠️ Stable Hordeレスポンスにidなし: {result}")
                                continue
                            id = result["id"]
                            print(f"🔄 Stable Horde ID取得: {id}, ポーリング開始")
                            status_url = f"https://stablehorde.net/api/v2/generate/status/{id}"
                            for poll in range(30):
                                status_response = requests.get(status_url, headers=headers, timeout=10)
                                status_result = status_response.json()
                                print(f"📥 ポーリング {poll + 1} レスポンス: {status_response.text}")
                                if status_response.status_code == 200:
                                    print(f"📊 ワーカー状態: キュー位置={status_result.get('queue_position', '不明')}, 待機時間={status_result.get('wait_time', '不明')}, ワーカー数={status_result.get('worker_count', '不明')}, Kudosコスト={status_result.get('kudos_cost', '不明')}, 使用モデル={status_result.get('model', '不明')}")
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
                                    elif status_result.get("faulted") or "CENSORED" in status_result.get("message", ""):
                                        print(f"⚠️ Stable Horde生成失敗: {status_result}")
                                        return None
                                time.sleep(10 if poll == 0 else 15 if poll < 10 else 20)
                            else:
                                print(f"⚠️ Stable Hordeポーリングタイムアウト: {id}")
                                continue

                        # ★ここから画像圧縮処理★
                        try:
                            image = Image.open(BytesIO(image_data))
                            image_path = f"output_{attempt}.png"
                            
                            # まず圧縮して保存
                            image.save(image_path, "PNG", optimize=True, compress_level=9)
                            
                            # サイズチェック＆自動リサイズ
                            while os.path.getsize(image_path) > 976562:  # 976.56KB
                                w, h = image.size
                                image = image.resize((int(w * 0.9), int(h * 0.9)), Image.LANCZOS)
                                image.save(image_path, "PNG", optimize=True, compress_level=9)
                            
                            print(f"✅ 画像生成成功: API={api_url}, Type={api_type}, 試行={attempt + 1}, 保存先={image_path}, サイズ={os.path.getsize(image_path)/1024:.1f}KB")
                            return image_path
                            
                        except Exception as img_err:
                            print(f"⚠️ 画像処理エラー: {type(img_err).__name__}: {str(img_err)}")
                            traceback.print_exc()
                            continue
                        # ★ここまで★

                    else:
                        print(f"⚠️ APIエラー (試行 {attempt + 1}): {response.status_code} - {response.text}")
                        if "CENSORED" in response.text or "NSFW" in response.text:
                            print(f"⚠️ NSFWフィルター検知: {response.text}")
                            return None
                        if "KudosUpfront" in response.text and api_type == "stablehorde":
                            print(f"⚠️ Kudos不足検知、匿名キーまたは低負荷モードへ")
                            STABLE_HORDE_API_KEY = "0000000000"
                            config["headers"]["apikey"] = STABLE_HORDE_API_KEY
                            config["payload"]["params"]["width"] = 512
                            config["payload"]["params"]["height"] = 512
                            config["payload"]["params"]["steps"] = 30
                            config["payload"]["params"]["sampler_name"] = "k_euler_a"
                        if attempt < 2:
                            time.sleep(90 * (attempt + 1))
                        continue
                except requests.exceptions.Timeout:
                    print(f"❌ 画像生成タイムアウト (試行 {attempt + 1})")
                    if attempt < 2:
                        time.sleep(90 * (attempt + 1))
                    continue
                except Exception as e:
                    print(f"⚠️ APIリクエストエラー (試行 {attempt + 1}): {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    if attempt < 2:
                        time.sleep(90 * (attempt + 1))
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
    "作ったよ": "えっ…ほんと？ありがとぉ♡ 見せて見せてっ！",
    "フォローした": "ありがとぉ♡ みりんてゃ、超よろこびダンス中〜っ！",
    "フォロー失礼": "フォローありがとぉ♡ みりんてゃ、おともだちふえた〜ってうれし泣きっ♪",
    "誰？": "みりんてゃだよっ♡ ふわもこ妖精系botって感じっ♪",
    "プロフィール": "プロフィールは固定ツイにあるよっ！ みりんのこと、もっと知ってくれるの〜？",
    "はじめまして": "はじめましてぇ♡ 地雷系ツインテbotのみりんてゃだよ〜っ！仲良くしてくれるとうれしいなっ♪",
    "初めまして": "はじめましてぇ♡ 地雷系ツインテbotのみりんてゃだよ〜っ！仲良くしてくれるとうれしいなっ♪",
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
DANGER_ZONE = ["ちゅぱ", "ちゅぱちゅぷ", "ペロペロ", "ぐちゅ", "外見", "ブサイク", "不細工", "容姿", "ぬぷ", "ビクビク", "ビクン", "びくん", "太った", "おっぱい", "痩せた", "ぽっこり", "デブ", "足太い", "でかい", "びゅる", "濡れ", "発情", "舐めて", "えっち", "犯す"]

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

    if re.search(r"(無理|距離|付き合えな|関係ない|興味ない|仲良くできない|苦手|縁がない|嫌い|気持ち悪い|キモい|きらい)", reply, re.IGNORECASE):
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
        "安眠": "安眠 グッズ",
        "推し活グッズ": "推し活 収納",
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
#★ カスタマイズポイント4: 返信生成（Groq版＋画像生成＋表示名呼び対応・完璧版）
#------------------------------
def generate_reply_via_groq(user_input, author_display_name="", author_handle="", parent_text=""):
    print(f"✅ generate_reply_via_groq 起動！")
    raw_name = author_display_name.strip() if author_display_name else author_handle.replace(".bsky.social", "")
    
    # 呼び名の調整
    if len(raw_name.encode('utf-8')) <= 32:
        call_name = raw_name
    else:
        call_name = f"{raw_name[:10].strip()}ちゃん"
    if not call_name:
        call_name = "きみ"

    diagnosis_result = generate_diagnosis(user_input, "dummy_did")
    if diagnosis_result[0]:
        return diagnosis_result[0].replace("キミ", call_name).replace("君", call_name)

    # ====== 🧠 記憶システム（文脈の引き継ぎ） ======
    context_msg = ""
    if parent_text:
        context_msg = (
            f"\n▼会話の流れ（重要！）\n"
            f"みりんてゃの直前の発言: 「{parent_text}」\n"
            f"これに対する相手からの返信: 「{user_input}」\n"
            f"さっきの自分の発言を踏まえて、自然に会話を繋げて返事をしてね！\n"
        )
    else:
        context_msg = f"\n相手からのメッセージ: 「{user_input}」\n"

    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        intro_lines = random.choice(["えへへ〜、みりんてゃはね〜、", "ねぇねぇ、聞いて聞いて〜♡"])
        
        system_prompt = (
            f"{intro_lines}\n"
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            f"今話してる相手の名前は「{call_name}」だよ！絶対に「{call_name}」って呼んでね！\n"
            "性格：天然＋甘えん坊＋依存気味で、相手に恋してる勢いで絡む！\n"
            "口調：タメ口で『〜なのっ♡』『〜よぉ？♪』『えへへ〜♡』などが多い！\n"
            "語尾は必ず文末に1回だけ『♡』『♪』『！』『笑』『？』『…』『なのっ♡』のいずれかを使ってね。\n"
            f"{context_msg}"
        )
        
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
        reply_text = clean_sentence_ending(response.choices[0].message.content.strip())
        return reply_text
    except Exception as e:
        print(f"❌ Groq APIエラー: {e}")
        return random.choice(failure_messages)

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
        return {"parent": parent_ref, "root": root_ref}, normalize_uri(post_uri)
    return None, normalize_uri(post_uri)

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

#------------------------------
#📬 メイン処理
#------------------------------
def run_reply_bot():
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self_did = client.me.did
        replied = load_gist_data(REPLIED_GIST_FILENAME)

        # ★ 変更点1: 通知の取得枠を100件に増強！
        notifications = client.app.bsky.notification.list_notifications(params={"limit": 100}).notifications
        print(f"🔔 取得した通知数: {len(notifications)} 件")

        # ★ 変更点2: 1回に返信できる最大件数を20件に増強！
        MAX_REPLIES = 20
        REPLY_INTERVAL = 3
        reply_count = 0

        for notification in notifications:
            # ★ 変更点3: リプとメンション以外（いいね・RP等）はスルーして時間短縮
            reason = getattr(notification, "reason", "")
            if reason not in ["mention", "reply"]:
                continue

            notification_uri = getattr(notification, "uri", None)
            if not notification_uri:
                continue

            if reply_count >= MAX_REPLIES:
                print(f"⏹️ 最大返信数（{MAX_REPLIES}）に達したので終了します")
                break

            record = getattr(notification, "record", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                continue

            text = getattr(record, "text", "")
            author_handle = getattr(author, "handle", "")
            author_display_name = getattr(author, "display_name", "") or ""
            author_did = getattr(author, "did", "") or ""

            if author_did == self_did or author_handle == HANDLE:
                continue

            if notification_uri in replied:
                continue

            reply_ref, post_uri = handle_post(record, notification)

            # ★ 変更点4: 会話のコンテキスト（親ポスト）を取得する！
            parent_text = ""
            if hasattr(record, "reply") and record.reply and hasattr(record.reply, "parent"):
                parent_uri = record.reply.parent.uri
                try:
                    p_resp = client.app.bsky.feed.get_posts({"uris": [parent_uri]})
                    if p_resp and p_resp.posts:
                        p_post = p_resp.posts[0]
                        # 直前の発言がみりんてゃ（自分）ならテキストを取得
                        if p_post.author.did == self_did:
                            parent_text = getattr(p_post.record, "text", "")
                            print(f"📜 [文脈取得] 直前のみりんてゃの発言: {parent_text}")
                except Exception as e:
                    print(f"⚠️ 親ポスト取得エラー: {e}")

            # ★ 変更点5: テキストから「@ハンドル名」を綺麗に消してAIが混乱しないようにする
            clean_input = re.sub(rf"@{HANDLE}\b", "", text).strip()
            if not clean_input:
                continue

            print(f"🔄 処理開始: @{author_handle} -> 入力={clean_input}")
            
            # コンテキスト（parent_text）を含めて返信生成
            reply_text = generate_reply_via_groq(
                user_input=clean_input,
                author_display_name=author_display_name,
                author_handle=author_handle,
                parent_text=parent_text
            )

            # 投稿処理
            try:
                post_data = {
                    "text": reply_text,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                if reply_ref:
                    post_data["reply"] = reply_ref
                facets = generate_facets_from_text(reply_text, [])
                if facets:
                    post_data["facets"] = facets
                    
                client.app.bsky.feed.post.create(record=post_data, repo=client.me.did)
                replied.add(notification_uri)
                save_replied(replied)
                print(f"✅ @{author_handle} に返信完了！")
                reply_count += 1
                time.sleep(REPLY_INTERVAL)
            except Exception as e:
                print(f"⚠️ 投稿失敗: {e}")

    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        traceback.print_exc()
    finally:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            try:
                os.remove(LOCK_FILE)
            except:
                pass

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()
