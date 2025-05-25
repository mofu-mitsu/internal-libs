# reply_bot.py
import os
import json
import subprocess
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

# ------------------------------
# 🛠️ 環境変数と設定読み込み
# ------------------------------
load_dotenv()  # .envファイルから環境変数を読み込み

def load_config(path="config.json"):
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        # 環境変数から機密情報を取得
        config["bluesky_handle"] = os.getenv("BLUESKY_HANDLE") or exit("❌ BLUESKY_HANDLEが設定されていません")
        config["bluesky_app_password"] = os.getenv("BLUESKY_APP_PASSWORD") or exit("❌ BLUESKY_APP_PASSWORDが設定されていません")
        config["gist_token_reply"] = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
        config["gist_id"] = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")
        return config
    except Exception as e:
        print(f"❌ 設定ファイル読み込みエラー: {e}")
        exit(1)

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
def load_gist_data(config):
    gist_url = f"https://api.github.com/gists/{config['gist_id']}"
    headers = {
        "Authorization": f"token {config['gist_token_reply']}",
        "Accept": "application/vnd.github+json"
    }
    for attempt in range(3):
        try:
            curl_command = [
                "curl", "-X", "GET", gist_url,
                "-H", f"Authorization: token {config['gist_token_reply']}",
                "-H", "Accept: application/vnd.github+json"
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Gist読み込み失敗: {result.stderr}")
            gist_data = json.loads(result.stdout)
            if config['gist_filename'] in gist_data["files"]:
                replied_content = gist_data["files"][config['gist_filename']]["content"]
                return set(normalize_uri(u) for u in json.loads(replied_content) if normalize_uri(u))
            return set()
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                return set()

def save_gist_data(config, replied_set):
    gist_url = f"https://api.github.com/gists/{config['gist_id']}"
    cleaned_set = set(normalize_uri(uri) for uri in replied_set if normalize_uri(uri))
    content = json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)
    payload = {"files": {config['gist_filename']: {"content": content}}}
    for attempt in range(3):
        try:
            curl_command = [
                "curl", "-X", "PATCH", gist_url,
                "-H", f"Authorization: token {config['gist_token_reply']}",
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

def is_output_safe(text, danger_words):
    return not any(word in text.lower() for word in danger_words)

def clean_sentence_ending(reply, fallback_replies, config):
    reply = clean_output(reply)
    reply = reply.split("\n")[0].strip()
    reply = re.sub(r"^(みりんてゃ|{config['bot_name']})\s*[:：]\s*", "", reply)
    reply = re.sub(r"^ユーザー\s*[:：]\s*", "", reply)
    reply = re.sub(r"([！？笑])。$", r"\1", reply)

    if re.search(r"(ご利用|誠に|お詫び|貴重なご意見|申し上げます|ございます|お客様|発表|パートナーシップ|ポケモン|アソビズム|企業|世界中|映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|情報|外交|外相|自動更新|\d+(時|分))", reply, re.IGNORECASE):
        return random.choice(fallback_replies)
    if not is_output_safe(reply, config["danger_words"]):
        return random.choice(fallback_replies)
    if not re.search(r"[ぁ-んァ-ン一-龥ー]", reply) or len(reply) < 8:
        return random.choice(fallback_replies)
    if not re.search(r"[。！？♪]$", reply):
        reply += random.choice(config.get("reply_endings", ["だよ！♪"]))
    return reply

# ------------------------------
# 🤖 返信生成
# ------------------------------
def generate_reply(user_input, config):
    model_name = config["model_settings"]["model_name"]
    fallback_replies = config["fallback_replies"]

    # キーワードマッチ（REPLY_TABLE）
    for key, reply in config["reply_table"].items():
        if key in user_input:
            return reply

    # 特定パターンへのカスタム返信
    for rule in config.get("custom_replies", []):
        if re.search(rule["pattern"], user_input, re.IGNORECASE):
            return random.choice(rule["replies"])

    # モデル生成
    try:
        tokenizer = GPTNeoXTokenizerFast.from_pretrained(model_name, use_fast=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float32, device_map="auto"
        ).eval()

        prompt = (
            f"{random.choice(config.get('intro_lines', ['やっほー！']))}\n"
            f"あなたは「{config['bot_name']}」、{config.get('character_description', '地雷系ENFPのあざと可愛い女の子！')}\n"
            f"ユーザー: {user_input}\n"
            f"{config['bot_name']}: "
        )
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=config["model_settings"]["max_new_tokens"],
                temperature=config["model_settings"]["temperature"],
                top_p=config["model_settings"]["top_p"],
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=2
            )
        reply = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
        return clean_sentence_ending(reply, fallback_replies, config)
    except Exception as e:
        print(f"⚠️ 生成エラー: {e}")
        return random.choice(fallback_replies)

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
def run_reply_bot(config):
    # Blueskyログイン
    try:
        client = Client()
        client.login(config["bluesky_handle"], config["bluesky_app_password"])
        print("✅ Blueskyログイン成功！")
    except Exception as e:
        print(f"❌ Blueskyログイン失敗: {e}")
        exit(1)

    replied = load_gist_data(config)
    notifications = get_notifications beam(25)
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
        if f"@{config['bot_name']}" not in text or author.handle == config["bluesky_handle"]:
            continue

        post_cid = getattr(notification, "cid", None)
        parent_ref = StrongRef(uri=post_uri, cid=post_cid) if post_cid else None
        root_ref = getattr(getattr(record, "reply", None), "root", parent_ref)
        reply_ref = ReplyRef(parent=parent_ref, root=root_ref) if parent_ref else None

        reply_text = generate_reply(text, config)
        if not reply_text:
            continue

        try:
            post_reply(client, reply_text, reply_ref)
            replied.add(post_uri)
            save_gist_data(config, replied)
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
    config = load_config("config.json")
    run_reply_bot(config)