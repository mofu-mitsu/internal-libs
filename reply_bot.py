# reply_bot.py
import os
import json
import subprocess
import traceback
import time
import random
import re
from datetime import datetime, timezone
from atproto import Client
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from atproto_client.models.app.bsky.feed.post import ReplyRef
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, GPTNeoXTokenizerFast
import torch
import psutil

# ------------------------------
# 🔐 環境変数（機密情報はここ！）
# ------------------------------
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ BLUESKY_HANDLEが設定されていません")
APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD") or exit("❌ BLUESKY_APP_PASSWORDが設定されていません")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
GIST_ID = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")

# ★ 機密情報は .env や GitHub Secrets に！ ★
# .env 例:
# BLUESKY_HANDLE=@your_handle.bsky.social
# BLUESKY_APP_PASSWORD=your_app_password
# GIST_TOKEN_REPLY=your_gist_token
# GIST_ID=your_gist_id

print(f"✅ 環境変数読み込み完了: HANDLE={HANDLE[:8]}..., GIST_ID={GIST_ID[:8]}...")

# --- 固定値 ---
REPLIED_GIST_FILENAME = "replied.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GIST_TOKEN_REPLY}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json"
}

# ------------------------------
# ★ カスタマイズポイント1: キャラ設定 ★
# ------------------------------
# ここでBotの名前や性格を決めよう！
BOT_NAME = "みりんてゃ"  # 例: "キミのキャラ", "クール忍者"
CHARACTER_DESCRIPTION = "地雷系ENFPのあざと可愛い女の子！"  # 例: "クールなツンデレお姉さん", "元気な魔法少女"
INTRO_LINES = [
    "えへへ〜、みりんてゃはね〜、",
    "ねぇねぇ、聞いて聞いて〜♡",
    "ん〜今日もふwaふwaしてたのっ♪",
    "きゃ〜っ、君だぁ！やっと会えたのっ♡",
    # 追加例: "やっほー！キミに会えて超ハッピー！"
]
REPLY_ENDINGS = [
    "なのっ♡",
    "よぉ？♡",
    "だもん！",
    "♪",
    # 追加例: "でごさる！", "なのだ！"
]
# ヒント: BOT_NAMEを変えると、通知で反応するハンドル（例: @みりんてゃ）が変わるよ！
#       CHARACTER_DESCRIPTIONはAIの返信の雰囲気（プロンプト）に影響する！

# ------------------------------
# ★ カスタマイズポイント2: キーワード返信（REPLY_TABLE） ★
# ------------------------------
# ユーザーの入力に含まれるキーワードに応じた固定返信
# 形式: "キーワード": "返信テキスト"
REPLY_TABLE = {
    "使い方": "使い方は公式ページ見てね！簡単だよ〜♪",
    "こんにちは": "やっほー！会えて嬉しいな！♪",
    "遊んだよ": "やったぁ〜っ！また遊んでね♪ 他のもいっぱい見てみて！",
    "やってみた": "わ〜！使ってくれてありがと！感想聞かせてくれると超嬉しい！",
    "ツインテ似合うね": "ふふ、そう言われるために生きてるよ！",
    "フォローした": "やった！フォローありがと！めっちゃハッピー！♪",
    # 追加例:
    # "おはよう": "おは！キミの朝、超ハッピーにしてあげるよ！",
    # "大好き": "え、ほんと！？キミにそう言われるとドキドキしちゃう！♡"
}
# ヒント: キーワードは部分一致（例: "こんにちは"は"こんにちは！"にも反応）。
#       好きなキーワードと返信を追加して、キャラの個性を出そう！

# ------------------------------
# ★ カスタマイズポイント3: 特定パターン返信（CUSTOM_REPLIES） ★
# ------------------------------
# 正規表現で特定フレーズ（例: "大好き"）に反応する返信
CUSTOM_REPLIES = [
    {
        "pattern": "大好き|ぎゅー|ちゅー|愛してる|キス|添い寝",
        "replies": [
            "うぅ…ドキドキ止まんないのっ♡ もっと甘やかしてぇ♡",
            "えへへ♡ そんなの言われたら…溶けちゃいそうなのぉ〜♪",
            # 追加例: "きゃー！キミの愛、めっちゃ受け取ったよ！♡"
        ]
    },
    {
        "pattern": "疲れた|しんどい|つらい|泣きたい|ごめん|寝れない",
        "replies": [
            "うぅ、よしよしなのっ♡ 元気になるまでそばにいるよ♪",
            "ぎゅ〜ってしてあげるっ♡ 無理しなくていいよ？",
            # 追加例: "大丈夫、キミの味方だよ！ゆっくり休んでね！"
        ]
    }
]
# ヒント: "pattern"は正規表現（例: "大好き|愛してる"はどちらかに反応）。
#       "replies"に複数の返信を入れて、ランダムに選ばれるよ！

# ------------------------------
# ★ カスタマイズポイント4: フォールバック返信 ★
# ------------------------------
# AIが生成に失敗した時や、キーワードにマッチしない時のデフォルト返信
FALLBACK_REPLIES = [
    "えへへ〜♡ ふwaふwaしちゃった！君のことずーっと好きだよぉ？♪",
    "みりんてゃ、君にドキドキなのっ♡ ね、もっとお話しよ？",
    "うぅ、なんか分かんないけど…君なしじゃダメなのっ♡",
    # 追加例: "ふふ、キミの声、もっと聞きたいな！"
]
# ヒント: キャラの口調に合わせて、楽しくて可愛い返信を増やしてみて！

# ------------------------------
# ★ カスタマイズポイント5: 安全/危険ワード ★
# ------------------------------
# 健全な返信を保つためのフィルター
SAFE_WORDS = ["ちゅ", "ぎゅっ", "ドキドキ", "ぷにっ", "すりすり", "なでなで"]
DANGER_ZONE = ["ちゅぱ", "ちゅぱちゅぷ", "ペロペロ", "ぐちゅ", "ぬぷ", "ビクビク"]
# ヒント: SAFE_WORDSは返信に含めてもOKな可愛い表現。
#       DANGER_ZONEはNGワード。キャラに合わせて調整可能！

# ------------------------------
# ★ カスタマイズポイント6: モデル設定 ★
# ------------------------------
# AIモデルの設定。変更するなら慎重に！
MODEL_NAME = "cyberagent/open-calm-3b"  # 例: "cyberagent/open-calm-7b"
MODEL_SETTINGS = {
    "max_new_tokens": 60,  # 返信の長さ（短めで事故減）
    "temperature": 0.8,   # 創造性（0.7〜1.0が安定）
    "top_p": 0.9,         # 多様性（0.8〜0.95が自然）
}
# ヒント: max_new_tokensを増やすと長編返信、temperatureを上げると個性的な返信に！

# ------------------------------
# 🔗 URI正規化
# ------------------------------
def normalize_uri(uri):
    if not uri or not isinstance(uri, str) or uri in ["replied", "", "None"]:
        return None
    uri = uri.strip()
    if not uri.startswith("at://"):
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(uri)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return None

# ------------------------------
# 📁 Gist操作
# ------------------------------
def load_gist_data():
    for attempt in range(3):
        try:
            curl_command = [
                "curl", "-X", "GET", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json"
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Gist読み込み失敗: {result.stderr}")
            gist_data = json.loads(result.stdout)
            if REPLIED_GIST_FILENAME in gist_data["files"]:
                replied_content = gist_data["files"][REPLIED_GIST_FILENAME]["content"]
                return set(normalize_uri(u) for u in json.loads(replied_content) if normalize_uri(u))
            return set()
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                return set()

def save_gist_data(replied_set):
    cleaned_set = set(normalize_uri(uri) for uri in replied_set if normalize_uri(uri))
    content = json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)
    payload = {"files": {REPLIED_GIST_FILENAME: {"content": content}}}
    for attempt in range(3):
        try:
            curl_command = [
                "curl", "-X", "PATCH", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            raise Exception(f"Gist保存失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                return False

# ------------------------------
# 🧹 テキスト処理
# ------------------------------
def clean_output(text):
    text = re.sub(r'\n{2,}', '\n', text)
    text = re.sub(r'[^\w\sぁ-んァ-ン一-龯。、！？♡（）「」♪〜ー…w笑]+', '', text)
    text = re.sub(r'[。、！？]{2,}', lambda m: m.group(0)[0], text)
    return text.strip()

def is_output_safe(text):
    return not any(word in text.lower() for word in DANGER_ZONE)

def clean_sentence_ending(reply):
    reply = clean_output(reply)
    reply = reply.split("\n")[0].strip()
    reply = re.sub(r"^{}\s*[:：]\s*".format(BOT_NAME), "", reply)
    reply = re.sub(r"^ユーザー\s*[:：]\s*", "", reply)
    reply = re.sub(r"([！？笑])。$", r"\1", reply)

    if re.search(r"(ご利用|誠に|お詫び|貴重なご意見|申し上げます|ございます|お客様|発表|パートナーシップ|ポケモン|アソビズム|企業|世界中|映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|情報|外交|外相|自動更新|\d+(時|分))", reply, re.IGNORECASE):
        return random.choice(FALLBACK_REPLIES)
    if not is_output_safe(reply):
        return random.choice(FALLBACK_REPLIES)
    if not re.search(r"[ぁ-んァ-ン一-龥ー]", reply) or len(reply) < 8:
        return random.choice(FALLBACK_REPLIES)
    if not re.search(r"[。！？♪]$", reply):
        reply += random.choice(REPLY_ENDINGS)
    return reply

# ------------------------------
# 🤖 返信生成
# ------------------------------
def generate_reply(user_input):
    for key, reply in REPLY_TABLE.items():
        if key in user_input:
            return reply

    for rule in CUSTOM_REPLIES:
        if re.search(rule["pattern"], user_input, re.IGNORECASE):
            return random.choice(rule["replies"])

    try:
        tokenizer = GPTNeoXTokenizerFast.from_pretrained(MODEL_NAME, use_fast=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME, torch_dtype=torch.float32, device_map="auto"
        ).eval()

        prompt = (
            f"{random.choice(INTRO_LINES)}\n"
            f"あなたは「{BOT_NAME}」、{CHARACTER_DESCRIPTION}\n"
            f"ユーザー: {user_input}\n"
            f"{BOT_NAME}: "
        )
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=MODEL_SETTINGS["max_new_tokens"],
                temperature=MODEL_SETTINGS["temperature"],
                top_p=MODEL_SETTINGS["top_p"],
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=2
            )
        reply = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
        return clean_sentence_ending(reply)
    except Exception as e:
        print(f"⚠️ 生成エラー: {e}")
        return random.choice(FALLBACK_REPLIES)

# ------------------------------
# 📬 Bluesky操作
# ------------------------------
def get_notifications(client, limit=25):
    return client.app.bsky.notification.list_notifications(params={"limit": limit}).notifications

def post_reply(client, text, reply_ref):
    post_data = {
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    if reply_ref:
        post_data["reply"] = reply_ref
    client.app.bsky.feed.post.create(record=post_data, repo=client.me.did)

# ------------------------------
# 🤖 メイン処理
# ----------------------
def run_reply_bot():
    try:
        client = Client()
        client.login(HANDLE, APP_PASSWORD)
        print("✅ Blueskyログイン成功！")
    except Exception as e:
        print(f"❌ Blueskyログイン失敗: {e}")
        exit(1)

    replied = load_gist_data()
    notifications = get_notifications(client, limit=25)
    print(f"🔔 通知総数: {len(notifications)} 件")
    reply_count = 0
    max_replies = 5
    reply_interval = 5

    for notification in notifications:
        if reply_count >= max_replies:
            print(f"⏹️ 最大返信数（{max_replies}）に達したので終了")
            break

        post_uri = normalize_uri(getattr(notification, "uri", None) or getattr(notification, "reasonSubject", None))
        if not post_uri or post_uri in replied:
            continue

        record = getattr(notification, "record", None)
        author = getattr(notification, "author", None)
        if not record or not author or not hasattr(record, "text"):
            continue

        text = record.text
        if f"@{BOT_NAME}" not in text or author.handle == HANDLE:
            continue

        post_cid = getattr(notification, "cid", None)
        parent_ref = StrongRef(uri=post_uri, cid=post_cid) if post_cid else None
        root_ref = getattr(getattr(record, "reply", None), "root", parent_ref)
        reply_ref = ReplyRef(parent=parent_ref, root=root_ref) if parent_ref else None

        reply_text = generate_reply(text)
        if not reply_text:
            continue

        try:
            post_reply(client, reply_text, reply_ref)
            replied.add(post_uri)
            save_gist_data(replied)
            print(f"✅ @{author.handle} に返信完了！ → {post_uri}")
            reply_count += 1
            time.sleep(reply_interval)
        except Exception as e:
            print(f"⚠️ 投稿エラー: {e}")

# ------------------------------
# 🚀 実行
# ------------------------------
if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()