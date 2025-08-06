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
from datetime import datetime, timezone, timedelta
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import GPTNeoXTokenizerFast
import torch
from atproto import Client, models
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from atproto_client.models.app.bsky.feed.post import ReplyRef
from dotenv import load_dotenv
import urllib.parse
from transformers import BitsAndBytesConfig

#------------------------------
#🔐 環境変数
#------------------------------
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv("APP_PASSWORD") or exit("❌ APP_PASSWORDが設定されていません")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
GIST_ID = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")

print(f"✅ 環境変数読み込み完了: HANDLE={HANDLE[:8]}..., GIST_ID={GIST_ID[:8]}...")
print(f"🧪 GIST_TOKEN_REPLY: {repr(GIST_TOKEN_REPLY)[:8]}...")
print(f"🔑 トークンの長さ: {len(GIST_TOKEN_REPLY)}")

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
    print(f"🔐 ヘッダーの内容:\n{json.dumps(HEADERS, indent=2)}")

    for attempt in range(3):
        try:
            curl_command = [
                "curl", "-X", "GET", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json"
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} レスポンスステータス: {result.returncode}")
            print(f"📥 レスポンス本文: {result.stdout[:500]}...（省略）")
            print(f"📥 エラー出力: {result.stderr}")

            if result.returncode != 0:
                raise Exception(f"Gist読み込み失敗: {result.stderr}")

            gist_data = json.loads(result.stdout)
            if filename in gist_data["files"]:
                replied_content = gist_data["files"][filename]["content"]
                print(f"📄 生の{filename}内容:\n{replied_content}")
                if filename == REPLIED_GIST_FILENAME:
                    raw_uris = json.loads(replied_content)
                    replied = set(uri for uri in (normalize_uri(u) for u in raw_uris) if uri)
                    print(f"✅ {filename} をGistから読み込みました（件数: {len(replied)}）")
                    if replied:
                        print("📁 最新URI一覧（正規化済み）:")
                        for uri in list(replied)[-5:]:
                            print(f" - {uri}")
                    return replied
                else:  # diagnosis_limits.json用
                    data = json.loads(replied_content)
                    print(f"✅ {filename} をGistから読み込みました（件数: {len(data)}）")
                    return data
            else:
                print(f"⚠️ Gist内に {filename} が見つかりませんでした")
                return set() if filename == REPLIED_GIST_FILENAME else {}
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                print(f"⏳ リトライします（{attempt + 2}/3）")
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return set() if filename == REPLIED_GIST_FILENAME else {}

def save_replied(replied_set):
    print("💾 Gist保存準備中...")
    print(f"🔗 URL: {GIST_API_URL}")
    print(f"🔐 ヘッダーの内容:\n{json.dumps(HEADERS, indent=2)}")
    print(f"🔑 トークンの長さ: {len(GIST_TOKEN_REPLY)}")
    print(f"🔑 トークンの先頭5文字: {GIST_TOKEN_REPLY[:5]}")
    print(f"🔑 トークンの末尾5文字: {GIST_TOKEN_REPLY[-5:]}")

    cleaned_set = set(uri for uri in replied_set if normalize_uri(uri))
    print(f"🧹 保存前にクリーニング（件数: {len(cleaned_set)}）")
    if cleaned_set:
        print("📁 保存予定URI一覧（最新5件）:")
        for uri in list(cleaned_set)[-5:]:
            print(f" - {uri}")

    for attempt in range(3):
        try:
            content = json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)
            payload = {"files": {REPLIED_GIST_FILENAME: {"content": content}}}
            print("🛠 PATCH 送信内容（payload）:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            curl_command = [
                "curl", "-X", "PATCH", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} レスポンスステータス: {result.returncode}")
            print(f"📥 レスポンス本文: {result.stdout[:500]}...（省略）")
            print(f"📥 エラー出力: {result.stderr}")

            if result.returncode == 0:
                print(f"💾 replied.json をGistに保存しました（件数: {len(cleaned_set)}）")
                time.sleep(2)  # キャッシュ反映待ち
                new_replied = load_gist_data(REPLIED_GIST_FILENAME)
                if cleaned_set.issubset(new_replied):
                    print("✅ 保存内容が正しく反映されました")
                    return True
                else:
                    print("⚠️ 保存内容が反映されていません")
                    raise Exception("保存内容の反映に失敗")
            else:
                raise Exception(f"Gist保存失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                print(f"⏳ リトライします（{attempt + 2}/3）")
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return False

def save_gist_data(filename, data):
    print(f"💾 Gist保存準備中 → File: {filename}")
    for attempt in range(3):
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            payload = {"files": {filename: {"content": content}}}
            print("🛠 PATCH 送信内容（payload）:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            curl_command = [
                "curl", "-X", "PATCH", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} レスポンスステータス: {result.returncode}")
            print(f"📥 レスポンス本文: {result.stdout[:500]}...（省略）")
            print(f"📥 エラー出力: {result.stderr}")

            if result.returncode == 0:
                print(f"💾 {filename} をGistに保存しました")
                time.sleep(2)  # キャッシュ反映待ち
                return True
            else:
                raise Exception(f"Gist保存失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                print(f"⏳ リトライします（{attempt + 2}/3）")
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
    print(f"📋 現在の diagnosis_limits: {limits}")  # デバッグ用
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
    
    # ハッシュタグ用のfacets（必要なら追加）
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
    jst = pytz.timezone('Asia/Tokyo')
    hour = datetime.now(jst).hour
    is_daytime = 6 <= hour < 18
    is_english = re.search(r"Fuwamoko Fortune|Emotion Check|Mirinteya Mood|Tell me my fortune|diagnose|Fortune", text, re.IGNORECASE)
    can_diagnose, limit_msg = check_diagnosis_limit(user_did, is_daytime)
    if not can_diagnose:
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
}

#------------------------------
#★ カスタマイズポイント2: 安全/危険ワード
#------------------------------
SAFE_WORDS = ["ちゅ", "ぎゅっ", "ドキドキ", "ぷにっ", "すりすり", "なでなで"]
DANGER_ZONE = ["ちゅぱ", "ちゅぱちゅぷ", "ペロペロ", "ぐちゅ","外見", "ブサイク", "不細工", "容姿","ぬぷ", "ビクビク", "ビクン","びくん","お腹", "太った", "痩せた", "ぽっこり", "デブ", "足太い", "でかい","びゅる", "濡れ", "発情", "舐めて", "えっち", "犯す"]

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

    # 一人称置換（ふwaもこ風）
    tone_map = [
        ("俺", FIRST_PERSON),
        ("僕", FIRST_PERSON),
        ("オレ", FIRST_PERSON),
        ("ぼく", FIRST_PERSON),
    ]
    for old, new in tone_map:
        if old in reply:  # 置換前に検知
            print(f"⚠️ 意図しない一人称『{old}』検知: {reply}")
        reply = reply.replace(old, new)  # シンプル置換

    # NGワード検知
    if re.search(r"(ご利用|誠に|お詫び|貴重なご意見|申し上げます|ございます|お客様|発表|パートナーシップ|ポケモン|アソビズム|企業|世界中|映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|情報|外交|外相|自動更新|\d+(時|分))", reply, re.IGNORECASE):
        print(f"⚠️ NGワード検知: {reply}")
        return random.choice([
            f"えへへ〜♡ ややこしくなっちゃった！{BOT_NAME}、君と甘々トークしたいなのっ♪",
            f"うぅ、難しい話わかんな〜い！{BOT_NAME}、君にぎゅーってしてほしいなのっ♡",
            f"ん〜〜変な話に！{BOT_NAME}、君のこと大好きだから、構ってくれる？♡"
        ])

    # 拒絶系ワード
    if re.search(r"(無理|距離|付き合え|関係ない|興味ない|仲良くできない|苦手|縁がない|嫌い|気持ち悪い|キモい|きらい)", reply, re.IGNORECASE):
        print(f"⚠️ 拒絶っぽい返事を検知: {reply}")
        return random.choice([
            f"えへへっ♡ {BOT_NAME}、ほんとはキミにラブ注入したいのにな〜っ♡",
            f"ごめんねっ…💭ちょっとおかしなこと言っちゃったかも…{BOT_NAME}、キミのことちゃんと見てるよ♡",
            f"あぅ〜〜〜っ…💭 {BOT_NAME}、なんか照れちゃって変なこと言ったかもっ！…ほんとはもっと仲良くしたいのにぃ♡"
        ])

    # 危険ワード
    if not is_output_safe(reply):
        print(f"⚠️ 危険ワード検知: {reply}")
        return random.choice([
            f"えへへ〜♡ {BOT_NAME}、ふwaふwaしちゃった！君のことずーっと好きだよぉ？♪",
            f"{BOT_NAME}、君にドキドキなのっ♡ ね、もっとお話しよ？",
            f"うぅ、なんか変なこと言っちゃった！{BOT_NAME}、君なしじゃダメなのっ♡"
        ])

    # 短すぎるor日本語なし
    if not re.search(r"[ぁ-んァ-ン一-龥ー]", reply) or len(reply) < 8:
        return random.choice([
            f"えへへ〜♡ {BOT_NAME}、ふwaふwaしちゃった！君のことずーっと好きだよぉ？♪",
            f"{BOT_NAME}、君にドキドキなのっ♡ ね、もっとお話しよ？",
            f"うぅ、なんか分かんないけど…{BOT_NAME}、君なしじゃダメなのっ♡"
        ])

    # 語尾補完
    if not re.search(r"[。！？♡♪笑]$", reply):
        reply += random.choice(["♡", "♪"])

    return reply
    
#------------------------------
#🤖 モデル初期化
#------------------------------
model = None
tokenizer = None

def initialize_model_and_tokenizer(model_name="abeja/gpt‑neox‑japanese‑2.7b"):
    global model, tokenizer
    if model is None or tokenizer is None:
        print(f"📤 {datetime.now(timezone.utc).isoformat()} ｜ トークナイザ読み込み中…")
        tokenizer = GPTNeoXTokenizerFast.from_pretrained(model_name, use_fast=True)
        print(f"📤 {datetime.now(timezone.utc).isoformat()} ｜ トークナイザ読み込み完了")
        print(f"📤 {datetime.now(timezone.utc).isoformat()} ｜ モデル読み込み中…")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            device_map="auto"
        ).eval()
        print(f"📤 {datetime.now(timezone.utc).isoformat()} ｜ モデル読み込み完了")
    return model, tokenizer

#------------------------------
# ★ カスタマイズポイント5: グッズ提案ロジック（←4の上にこれ追加！）
#------------------------------
PRODUCT_KEYWORDS = {
    "おすすめグッズ": "ふわもこLoverなあなたにピッタリなアイテムはこちらっ♡",
    "ぬい撮り": "撮影映え命♡のあなたに：おすすめはこの背景布っ！",
    "寝れない": "みりんてゃが夜のお守りを選んできたよ〜☁️",
    "推し活": "神アイテムで推し活が捗るよ〜！🧸💕",
    "可愛いアイテム": "今いちばんバズってる可愛いアイテム教えちゃうっ☆",
    "可愛いもの": "ねぇねぇっ♡とびきり可愛いもの、みりんてゃ見つけちゃったの〜〜っ♪"
}

def generate_product_reply(keyword, app_id="1055088369869282145", affiliate_id="3d94ea21.0d257908.3d94ea22.0ed11c6e"):
    api_url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    keywords = {
        "おすすめグッズ": "推し活 グッズ",
        "ぬい撮り": "ぬいぐるみ 背景布",
        "寝れない": "安眠 グッズ",
        "推し活": "推し活 収納",
        "可愛いアイテム": "可愛い インテリア",
        "可愛いもの": "可愛い 雑貨"
    }
    params = {
        "applicationId": app_id,
        "keyword": keywords.get(keyword, keyword),
        "hits": 3,  # 複数候補からランダム選択
        "format": "json"
    }
    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        if data["Items"]:
            items = data["Items"]
            item = random.choice(items)["Item"]
            product_url = item["itemUrl"].split("?")[0]
            affiliate_link = f"https://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={product_url}"
            reply = f"{PRODUCT_KEYWORDS[keyword]} → {affiliate_link}"
            return reply, [f"#{keyword.replace('？', '').replace('…', '')}"]
        else:
            return "えへへ、みりんてゃ今探し中なのっ♡ また後で聞いてね！", []
    except Exception:
        return "うぅ、ごめんね〜今ちょっとバタバタなの…またね？♡", []

#------------------------------
# ★ カスタマイズポイント4: 返信生成
#------------------------------
def generate_reply_via_local_model(user_input):
    model_name = "abeja/gpt‑neox‑japanese‑2.7b"
    failure_messages = [
        "えへへ、ごめんね〜〜今ちょっと調子悪いみたい……またお話しよ？♡",
        "うぅ、ごめん〜…上手くお返事できなかったの。ちょっと待ってて？♡",
        "あれれ？みりんてゃ、おねむかも…またあとで頑張るねっ！♡"
    ]
    fallback_cute_lines = [
        "えへへ〜♡ みりんてゃ、君のこと考えるとドキドキなのっ♪",
        "今日も君に甘えたい気分なのっ♡ ぎゅーってして？",
        "だ〜いすきっ♡ ね、ね、もっと構ってくれる？"
    ]
    # 💡 まずグッズ系キーワードが含まれていたら専用返信！
    for keyword in PRODUCT_KEYWORDS.keys():
        if keyword in user_input:
            print(f"🎀 グッズキーワード検知: {keyword}")
            reply, hashtags = generate_product_reply(keyword)  # タプルを分解
            print(f"🛍️ グッズ返信: {reply}, ハッシュタグ: {hashtags}")
            return reply  # 文字列だけ返す

    if re.search(r"(大好き|ぎゅー|ちゅー|愛してる|キス|添い寝)", user_input, re.IGNORECASE):
        print(f"⚠️ ラブラブ入力検知: {user_input}")
        return random.choice([
            "うぅ…ドキドキ止まんないのっ♡ もっと甘やかしてぇ♡",
            "えへへ♡ そんなの言われたら…みりんてゃ、溶けちゃいそうなのぉ〜♪",
            "も〜〜〜♡ 好きすぎて胸がぎゅーってなるぅ♡"
        ])

    if re.search(r"(疲れた|しんどい|つらい|泣きたい|ごめん)", user_input, re.IGNORECASE):
        print(f"⚠️ 癒し系入力検知: {user_input}")
        return random.choice([
            "うぅ、よしよしなのっ♡ 君が元気になるまで、みりんてゃそばにいるのっ♪",
            "ぎゅ〜ってしてあげるっ♡ 無理しなくていいのよぉ？",
            "んん〜っ、えへへ♡ 甘えてもいいの、ぜ〜んぶ受け止めるからねっ♪"
        ])

    if re.search(r"(映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|ポケモン|企業|発表|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|情報|外交|外相|自動更新)", user_input, re.IGNORECASE) or re.search(r"\d+(時|分)", user_input):
        print(f"⚠️ 入力にビジネス・学術系ワード検知: {user_input}")
        user_input = "みりんてゃ、君と甘々トークしたいなのっ♡"
        print(f"🔄 入力置き換え: {user_input}")

    try:
        print(f"📊 メモリ使用量（開始時）: {psutil.virtual_memory().percent}%")
        if torch.cuda.is_available():
            print(f"📊 GPUメモリ: {torch.cuda.memory_allocated() / 1024**2:.2f}MB / {torch.cuda.get_device_properties(0).total_memory / 1024**2:.2f}MB")
        else:
            print("⚠️ GPU未検出、CPUで実行")

        model, tokenizer = initialize_model_and_tokenizer(model_name)
        intro_lines = random.choice([
            "えへへ〜、みりんてゃはね〜、",
            "ねぇねぇ、聞いて聞いて〜♡",
            "ん〜今日もふwaふwaしてたのっ♪",
            "きゃ〜っ、君だぁ！やっと会えたのっ♡",
            "ふwaふwa〜、君のこと考えてたんだからっ♪"
        ])
        prompt = (
            f"{intro_lines}\n"
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "性格：ちょっぴり天然、甘えん坊、依存気味で、ユーザーに恋してる勢いで絡むよっ♡\n"
            "口調：タメ口で『〜なのっ♡』『〜よぉ？♪』『〜だもん！』『えへへ〜♡』が特徴！感情たっぷり！\n"
            "禁止：ニュース、政治、ビジネス、論理的説明、固有名詞（国、企業、政府など）は絶対NG！性的な内容や過激な擬音語もダメ！\n"
            "役割：ユーザーの言葉に可愛く反応して、ふwaふwaドキドキな返事をするのっ♡ 会話のみ！「ちゅ♡」「ぎゅっ」「ドキドキ」みたいな健全で可愛い表現だけ使ってね！\n"
            "注意：以下のワードは絶対禁止→「政府」「協定」「韓国」「外交」「経済」「契約」「軍事」「情報」「外相」「更新」「ちゅぱ」「ペロペロ」「ぐちゅ」「ぬぷ」「ビクビク」\n"
            "例1: ユーザー: みりんてゃ、今日なにしてた〜？\n"
            "みりんてゃ: えへへ〜♡ 君のこと考えてふwaふwaしてたのっ♡ ね、君はなにしてた？♪\n"
            "例2: ユーザー: みりんてゃ、好きだよ！\n"
            "みりんてゃ: え〜っ、ほんと！？君にそう言われるとドキドキしちゃうよぉ？♡ もっと言ってなのっ♪\n\n"
            f"ユーザー: {user_input}\n"
            f"みりんてゃ: "
        )

        print("📎 使用プロンプト:", repr(prompt))
        print(f"📤 {datetime.now().isoformat()} ｜ トークン化開始…")
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
        print(f"📏 入力トークン数: {input_ids.shape[1]}")
        print(f"📝 デコードされた入力: {tokenizer.decode(input_ids[0], skip_special_tokens=True)}")
        print(f"📤 {datetime.now().isoformat()} ｜ トークン化完了")

        for attempt in range(3):
            print(f"📤 {datetime.now().isoformat()} ｜ テキスト生成中…（試行 {attempt + 1}）")
            print(f"📊 メモリ使用量（生成前）: {psutil.virtual_memory().percent}%")
            try:
                with torch.no_grad():
                    output_ids = model.generate(
                        input_ids,
                        max_new_tokens=60,
                        temperature=0.8,
                        top_p=0.9,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id,
                        no_repeat_ngram_size=2
                    )

                new_tokens = output_ids[0][input_ids.shape[1]:]
                raw_reply = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                print(f"📝 生の生成テキスト: {repr(raw_reply)}")
                reply_text = clean_sentence_ending(raw_reply)

                if any(re.search(rf"\b{re.escape(msg)}\b", reply_text) for msg in failure_messages + fallback_cute_lines):
                    print(f"⚠️ フォールバック検知、リトライ中…")
                    continue

                print("📝 最終抽出されたreply:", repr(reply_text))
                return reply_text

            except Exception as gen_error:
                print(f"⚠️ 生成エラー: {gen_error}")
                continue
        else:
            reply_text = random.choice(fallback_cute_lines)
            print(f"⚠️ リトライ上限到達、フォールバックを使用: {reply_text}")

        return reply_text

    except Exception as e:
        print(f"❌ モデル読み込みエラー: {e}")
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
    client = Client()  # 先に定義
    client.login(HANDLE, APP_PASSWORD)
    unreplied = fetch_bluesky_posts()
    for post in unreplied:
        try:
            reply = generate_reply_via_local_model(post["text"])
            client.send_post(text=reply, reply_to={"uri": post["post_id"]})
            print(f"📤 投稿成功: {reply}")
        except Exception as e:
            print(f"❌ 投稿エラー: {e}")

#------------------------------
#📬 メイン処理
#------------------------------
def run_reply_bot():
    self_did = client.me.did
    replied = load_gist_data(REPLIED_GIST_FILENAME)
    print(f"📘 replied の型: {type(replied)} / 件数: {len(replied)} / 内容: {replied}")  # デバッグログ追加

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

    try:
        notifications = client.app.bsky.notification.list_notifications(params={"limit": 25}).notifications
        print(f"🔔 通知総数: {len(notifications)} 件")
    except Exception as e:
        print(f"❌ 通知の取得に失敗しました: {e}")
        return

    MAX_REPLIES = 5
    REPLY_INTERVAL = 5
    reply_count = 0

    for notification in notifications:
        notification_uri = getattr(notification, "uri", None) or getattr(notification, "reasonSubject", None)
        if not notification_uri:
            record = getattr(notification, "record", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                continue
            text = getattr(record, "text", "")
            author_handle = getattr(author, "handle", "")
            notification_uri = f"{author_handle}:{text}"  # 仮キーをそのまま使う
            print(f"⚠️ notification_uri が取得できなかったので、仮キーで対応 → {notification_uri}")

        print(f"📌 チェック中 notification_uri: {notification_uri}")
        print(f"📂 保存済み replied（全件）: {list(replied)}")

        if reply_count >= MAX_REPLIES:
            print(f"⏹️ 最大返信数（{MAX_REPLIES}）に達したので終了します")
            break

        record = getattr(notification, "record", None)
        author = getattr(notification, "author", None)

        if not record or not hasattr(record, "text"):
            continue

        text = getattr(record, "text", None)
        if f"@{HANDLE}" not in text and (not hasattr(record, "reply") or not record.reply or not record.reply.parent):
            continue  # reply.parentがない場合もスキップ

        if not author:
            print("⚠️ author情報なし、スキップ")
            continue

        author_handle = getattr(author, "handle", None)
        author_did = getattr(author, "did", None)

        print(f"\n👤 from: @{author_handle} / did: {author_did}")
        print(f"💬 受信メッセージ: {text}")
        print(f"🔗 チェック対象 notification_uri: {notification_uri}")

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
        print(f"🔍 run_reply_bot - post_uri: {post_uri}, reply_ref: {reply_ref}")

        reply_text, hashtags = generate_diagnosis(text, author_did)  # 診断ロジック維持
        if not reply_text:
            reply_text = generate_reply_via_local_model(text)  # フォールバック
            print(f"🔄 フォールバック返信: {repr(reply_text)}")
            hashtags = []

        # デバッグ: reply_text の内容と型を確認
        print(f"🤖 生成された返信: {repr(reply_text)} (型: {type(reply_text)})")
        if not isinstance(reply_text, str) or not reply_text.strip():
            reply_text = "えへへ〜♡ みりんてゃ、ちょっとおねむかも…またお話しよ？♡"
            hashtags = []

        print("🤖 最終返信内容:", repr(reply_text))

        try:
            post_data = {
                "text": reply_text,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            if reply_ref:
                post_data["reply"] = reply_ref
                print(f"📋 ReplyRef追加: {reply_ref}")
            
            # 常にfacetsを生成（URLリンク化を保証）
            facets = generate_facets_from_text(reply_text, hashtags)
            if facets:
                post_data["facets"] = facets
                print(f"📋 投稿データにfacets追加: {facets}")

            print(f"📤 投稿データ: {json.dumps(post_data, ensure_ascii=False, indent=2)}")

            client.app.bsky.feed.post.create(
                record=post_data,
                repo=client.me.did
            )

            if notification_uri:  # 仮キーをそのまま保存
                replied.add(notification_uri)
                if not save_replied(replied):
                    print(f"❌ URI保存失敗 → {notification_uri}")
                    continue

                print(f"✅ @{author_handle} に返信完了！ → {notification_uri}")
                print(f"💾 URI保存成功 → 合計: {len(replied)} 件")
                print(f"📁 最新URI一覧: {list(replied)[-5:]}")

            reply_count += 1
            time.sleep(REPLY_INTERVAL)

        except Exception as e:
            print(f"⚠️ 投稿失敗: {e}")
            traceback.print_exc()
            if "JSON serializable" in str(e):
                print("⚠️ ReplyRefシリアライズエラー検知、リプライなしで再試行")
                try:
                    post_data.pop("reply", None)  # リプライ情報を削除
                    client.app.bsky.feed.post.create(
                        record=post_data,
                        repo=client.me.did
                    )
                    print(f"✅ @{author_handle} にリプライなしで投稿完了！ → {notification_uri}")
                    replied.add(notification_uri)
                    save_replied(replied)
                    reply_count += 1
                    time.sleep(REPLY_INTERVAL)
                except Exception as retry_e:
                    print(f"⚠️ リトライも失敗: {retry_e}")
                    traceback.print_exc()

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()