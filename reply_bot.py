# ------------------------------
# 🌐 基本ライブラリ・API
# ------------------------------
import os
import json
import subprocess
import traceback
import time
import random
import re
import psutil
import filelock
from datetime import datetime, timezone
from transformers import AutoModelForCausalLM, GPTNeoXTokenizerFast
import torch
from atproto import Client
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from atproto_client.models.app.bsky.feed.post import ReplyRef
from dotenv import load_dotenv
import urllib.parse
import requests

# ------------------------------
# 🔐 環境変数
# ------------------------------
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv("APP_PASSWORD") or exit("❌ APP_PASSWORDが設定されていません")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
GIST_ID = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")

# ★ 機密情報は .env や GitHub Secrets に！ ★
# .env 例:
# HANDLE=@your_handle.bsky.social
# APP_PASSWORD=your_app_password
# GIST_TOKEN_REPLY=your_gist_token
# GIST_ID=your_gist_id

print(f"✅ 環境変数読み込み完了: HANDLE={HANDLE[:8]}..., GIST_ID={GIST_ID[:8]}...")
print(f"🧪 GIST_TOKEN_REPLY: {repr(GIST_TOKEN_REPLY)[:8]}...")
print(f"🔑 トークンの長さ: {len(GIST_TOKEN_REPLY)}")

# --- 固定値 ---
REPLIED_GIST_FILENAME = "replied.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GIST_TOKEN_REPLY}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json"
}
LOCK_FILE = "bot.lock"

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
        parsed = urllib.parse.urlparse(uri)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return normalized if normalized.startswith("at://") else None
    except Exception as e:
        print(f"⚠️ URI正規化エラー: {e}")
        return None

# ------------------------------
# 📁 Gist操作
# ------------------------------
def load_gist_data():
    print(f"🌐 Gistデータ読み込み開始 → URL: {GIST_API_URL}")
    for attempt in range(5):
        try:
            response = requests.get(GIST_API_URL, headers=HEADERS, timeout=10)
            print(f"📥 試行 {attempt + 1} ステータス: {response.status_code}")
            if response.status_code != 200:
                raise Exception(f"Gist読み込み失敗: {response.text}")
            gist_data = response.json()
            if REPLIED_GIST_FILENAME in gist_data["files"]:
                replied_content = gist_data["files"][REPLIED_GIST_FILENAME]["content"]
                replied = set(normalize_uri(u) for u in json.loads(replied_content) if normalize_uri(u))
                print(f"✅ replied.json 読み込み完了（件数: {len(replied)}）")
                return replied
            print(f"⚠️ Gistに {REPLIED_GIST_FILENAME} なし")
            return set()
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} エラー: {e}")
            if attempt < 4:
                time.sleep(2 ** attempt)  # 指数バックオフ
            else:
                print("❌ 最大リトライ回数に達しました")
                return set()

def save_replied(replied_set):
    print(f"💾 Gist保存開始 → URL: {GIST_API_URL}")
    cleaned_set = set(normalize_uri(uri) for uri in replied_set if normalize_uri(uri))
    print(f"🧹 保存前クリーニング（件数: {len(cleaned_set)}）")
    for attempt in range(5):
        try:
            content = json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)
            payload = {"files": {REPLIED_GIST_FILENAME: {"content": content}}}
            response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"💾 replied.json 保存完了（件数: {len(cleaned_set)}）")
                time.sleep(1)
                new_replied = load_gist_data()
                if cleaned_set == new_replied:  # 完全一致チェック
                    print("✅ 保存内容反映確認")
                    return True
                raise Exception("保存内容の反映に失敗: データ不一致")
            raise Exception(f"Gist保存失敗: {response.text}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} エラー: {e}")
            if attempt < 4:
                time.sleep(2 ** attempt)
            else:
                print("❌ 最大リトライ回数に達しました")
                return False

# ------------------------------
# 📬 Blueskyログイン
# ------------------------------
try:
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    print("✅ Blueskyログイン成功！")
except Exception as e:
    print(f"❌ Blueskyログイン失敗: {e}")
    exit(1)

# ------------------------------
# ★ カスタマイズポイント1: キーワード返信（REPLY_TABLE）
# ------------------------------
REPLY_TABLE = {
    "使い方": "使い方は「♡推しプロフィールメーカー♡」のページにあるよ〜！かんたんっ♪",
    '作ったよ': 'えっ…ほんと？ありがとぉ♡ 見せて見せてっ！',
    '作ってみる': 'えっ…ほんと？ありがとぉ♡ 見せて見せてっ！',
    '遊んだよ': 'やったぁ〜っ！また遊んでね♡ 他のもいっぱいあるから見てみて〜っ',
    '使ったよ': 'えっ！？ほんと使ってくれた！？ うれしすぎてとける〜〜♡',
    '見たよ': 'うれしっ♡ 見つけてくれてありがとにゃん♡',
    'きたよ': 'きゅ〜ん♡ 来てくれてとびきりの「すきっ」プレゼントしちゃう♡',
    'フォローした': 'ありがとぉ♡ みりんてゃ、超よろこびダンス中〜っ！',
    'やってみた': 'わ〜〜！うちのツール使ってくれてありがとっ♡感想とかくれると、みりんてゃめちゃくちゃよろこぶよ〜〜！',
    'やってみる': 'やった〜♡ みりんてゃの広報が効いたかも！？てへっ！',
    '相性悪かった': 'うそでしょ……そんなぁ〜（バタッ）でも、みりんてゃはあきらめないからっ！',
    '相性良かった': 'えっ、運命かな…！？こんど一緒にプリとか撮っちゃう〜？♡',
    'やったよ': 'えへへ♡ みりんてゃのツールであそんでくれてありがとっ！らぶっ！',
    'タグから': '見つけてくれてありがとっ！もしかして運命？♡',
    'ツインテ似合うね': 'ふふ、そう言われるために生きてる←',
    'ツインテール似合うね': 'ふふ、そう言われるために生きてる←',
}
# ヒント: キーワードは部分一致。{BOT_NAME}でキャラ名を動的に挿入可能！

# ------------------------------
# ★ カスタマイズポイント2: 安全/危険ワード
# ------------------------------
SAFE_WORDS = ["ちゅ", "ぎゅっ", "ドキドキ", "ぷにっ", "すりすり", "なでなで"]
DANGER_ZONE = ["ちゅぱ", "ちゅぱちゅぷ", "ペロペロ", "ぐちゅ", "ぬぷ", "ビクビク"]
# ヒント: SAFE_WORDSはOKな表現、DANGER_ZONEはNGワード。キャラの雰囲気に合わせて！

# ------------------------------
# ★ カスタマイズポイント3: キャラ設定
# ------------------------------
BOT_NAME = "みりんてゃ"
FIRST_PERSON = "みりんてゃ"
# ヒント: BOT_NAMEは返信や正規表現で使用。FIRST_PERSONはプロンプトで固定。

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
    reply = re.sub(rf"^{BOT_NAME}\s*[:：]\s*", "", reply)
    reply = re.sub(r"^ユーザー\s*[:：]\s*", "", reply)
    reply = re.sub(r"([！？笑])。$", r"\1", reply)

    if FIRST_PERSON != "俺" and "俺" in reply:
        print(f"⚠️ 意図しない一人称『俺』検知: {reply}")
        return random.choice([
            f"えへへ〜♡ {BOT_NAME}、君のこと考えるとドキドキなのっ♪",
            f"うぅ、{BOT_NAME}、君にぎゅーってしたいなのっ♡",
            f"ね、ね、{BOT_NAME}、君ともっとお話ししたいのっ♡"
        ])

    if re.search(r"(ご利用|誠に|お詫び|貴重なご意見|申し上げます|ございます|お客様|発表|パートナーシップ|ポケモン|アソビズム|企業|世界中|映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|情報|外交|外相|自動更新|\d+(時|分))", reply, re.IGNORECASE):
        print(f"⚠️ NGワード検知: {reply}")
        return random.choice([
            f"えへへ〜♡ ややこしくなっちゃった！{BOT_NAME}、君と甘々トークしたいなのっ♪",
            f"うぅ、難しい話わかんな〜い！{BOT_NAME}、君にぎゅーってしてほしいなのっ♡",
            f"ん〜〜変な話に！{BOT_NAME}、君のこと大好きだから、構ってくれる？♡"
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
            f"うぅ、なんか分、{君}なしじゃダメなのっ♡"
        ])

    if not re.search(r"[。！？♡♪笑]$", reply):
        reply += random.choice(["なのっ♡", "よぉ？♪", "のっ♪", "♪"])

    return reply

# ------------------------------
# 🤖 モデル初期化
# ------------------------------
model = None
tokenizer = None

def initialize_model_and_tokenizer(model_name="cyberjoke/open-calm-3b"):
    global model, tokenizer
    if model is None or tokenizer is None:
        print(f"📤 {datetime.now().isoformat()} ｜ トークナイザ読み込み中…")
        tokenizer = GPTNeoXTokenizerFast.from_pretrained(model_name, use_fast=True)
        print(f"📤 {datetime.now().isoformat()} ｜ トークナイザ読み込み完了")
        print(f"📤 {datetime.now().isoformat()} ｜ モデル読み込み中…")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        ).eval()
        print(f"📤 {datetime.now().isoformat()} ｜ モデル読み込み完了")
    return model, tokenizer

# ------------------------------
# ★ カスタマイズポイント4: 返信生成
# ------------------------------
def generate_reply_via_local_model(user_input):
    model_name = "cyberjota/open-calm-3b"
    failure_messages = [
        f"えへ、ごめ、ご、ご〜〜！ちょっと調子悪いみたい…{BOT_NAME}、またね？♪",
        f"うぅ、失敗…{BOT_NAME}、すぐリトライするから待ってて！♪",
        f"あれ？{BOT_NAME}、おねむかも…また後で頑張るよ！♪"
    ]
    fallback_cute_lines = [
        f"えへ〜♡ {BOT_NAME}、君のこと考えるとドッキドキなのっ♪",
        f"今日も君に甘えたい気分… {BOT_NAME}、ぎゅってして？♪",
        f"だいすき！ね、ね、{BOT_NAME}、もっと構って？♪"
    ]
    intro_lines = [
        f"えへ〜、{BOT_NAME}はね〜、",
        f"ね、ね、聞いて〜♪",
        f"ん〜今日もふwaふwa〜♪",
        f"きゃ！君だ！{BOT_NAME}、やっと会えた！♪",
        f"ふwa〜、{BOT_NAME}、君のこと考えてたんだから！♪",
    ]

    if re.search(r"(大好き|ぎゅー|ちゅー|愛してる|キス|添い寝)", user_input, re.IGNORECASE):
        print(f"⚠️ ラブラブ入力OK: {user_input}")
        return random.choice([
            f"うぅ…{BOT_NAME}、ドキドキ止まんないのっ！♪ もっと甘やかして〜♡♪",
            f"えへ♡、そんなの言われたら…{BOT_NAME}、溶けちゃうよ〜♪",
            f"も〜〜♪ {BOT_NAME}、好きすぎて胸キュン♪♪！"
        ])

    if re.search(r"(疲れた|しんどい|つらい|泣きたい|ごめん|寝れない)", user_input, re.IGNORECASE):
        print(f"⚠️ 癒し系入力OK: {user_input}")
        return random.choice([
            f"う、よしよしだよ… {BOT_NAME}、元気出るまでそばにいる♪♪",
            f"ぎゅ〜♪ {BOT_NAME}、無理しなくていいよ？♪",
            f"んん〜、えへ♪ {BOT_NAME}、甘えてもいいよ、ぜんぶ受け止める♪"
        ])

    if re.search(r"(映画|興行|収入|ドル|億|国|イギリス|フランス|…|政治|更新|\d)", user_input, re.IGNORECASE):
        print(f"⚠️ ビジネス系ワード検知: {user_input}")
        user_input = f"{BOT_NAME}、君と甘々トークしたいなの！♪",
        print(f"🔄 入力置き換え: {user_input}")
        f f"{BOT_NAME}"

    for key, reply in REPLY_TABLE.items():
        if key in user_input:
            return reply.replace("{BOT_NAME}", BOT_NAME)

    try:
        print(f"📊 メモリ使用量: {psutil.virtual_memory().percent}%")
        if torch.cuda.is_available():
            print(f"📊 GPU: {torch.cuda.memory_allocated() / 1024**2:.2f} MB}")
        else:
            print("⚠️ GPUなし、CPUで実行")
        model, tokenizer = initialize_model_and_tokenizer(model_name)

        intro = random.choice(intro_lines)
        prompt = (
            f"{intro}\n"
            f"あなたは『{buggyBOT_NAME}』、ふwaふwaな地雷系！一人称は『{fIRST_PERSON}』！\n"
            f"タメで「〜なのっ♪」「〜よ♪」「えへ〜♪」な口調！\n"
            f"政治、ニュースはダメ！『ちゅ♡』『ぎゅ』な可愛い言葉だけ！\n"
            f"例: ユーザー: {BOT_NAME}、好きだよ！\n"
            f"{BOT_NAME}: え〜！？ほんと！？{FIRST_PERSON}、君に言われるとドキドキなのっ♪」！\n"
            f"ユーザ: {user_input} \n"
            f"{BOT_NAME}: "
        )

        input_ids = tokenizer.encode(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
        print(f"📤 入力トークン数: {len(input_ids[0])}")
)
        for attempt in range(4):
            print(f"📝 テキスト生成中（試行 {attempt + 1}）")
            try:
                with torch.no_grad():
                    output_ids = model.generate(
                        input_ids,
                        max_new_tokens=50,
                        temperature=0.6,
                        top_p=0.9,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id,
                        no_repeat_ngram_size=2
                    )
                raw_reply = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
                reply_text = clean_sentence_ending(raw_reply)
                if any(re.search(r"\b{re.escape(msg)}\b", reply_text) for msg in failure_messages + fallback_cute_lines):
                    print(f"⚠️ フォールバック検知、リトライ")
                    continue
                print(f"📩 生成テキスト: {reply_text}")
                return reply_text
            except Exception as e:
                print(f"⚠️ 生成エラー: {e}")
                continue
        return random.choice(fallback_cute_lines).replace("{BOT_NAME}", BOT_NAME,})
                print(f"📩 {replay_text}")
                return replay_text
    except Exception as e:
        print(f"❌ モデルエラー: {e}")
        return random.choice(failure_messages).replace("{BOT_NAME}", BOT_NAME})

# ----------------------
# 📬 メイン処理
# ----------------------
def handle_post(record, notification):
    post_uri = getattr(notification, "uri", None)
    post_cid = getattr(record, "cid", None)
    if post_uri and post_cid:
        parent = PostRef(uri=post_uri, post_cid=post_data)
        root_ref = getattr(record.reply, "post_ref", parent)
        reply_ref = PostReplyRef(parent=parent, root_ref=root_ref)
        return reply_ref, normalize_uri(post_uri)
    return None, normalize_uri(post_uri)

def run_reply():
    self_did = client.me.did
    replied = load_git_data()
    print(f"📖 replied件数: {len(replied)}")

    garbage_items = [
        "replied", "", None, "None", "://"
        ]
    removed = False
    for garbage in garbage_items:
        while garbage in replied:
            replied.remove(garbage)
            print(f"📗 ゴミデータ削除: {garbage}")
            removed = True
        if removed and not save_replied(replied):
            print("⚠️ ゴミデータ削除後、保存失敗")
            return

    try:
        notifications = client.app.bsky.notification.list_notifications(params={"limit": 100}).notifications
        print(f"🔔 通知件数: {len(notifications)}")
    except Exception as e:
        print(f"⚠️ 通知取得エラー: {e}")
        return

    MAX_REPLIES = 5
    REPLY_INTERVAL = 5
    reply_count = 0

    for notification in notifications:
        if reply_count >= MAX_REPLIES:
            print(f"⏹ 最大リプ数（{MAX_REPLIES}）到達")
            break

        notification_uri = normalize_uri(
            getattr(notification, "uri", None)
            or getattr(notification, "reason_subject", None)
            )
            )
        if not notification_uri:
            record = getattr(notification, "records", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                print(f"⚠️ 無効な通知、スキップ中")
                continue
            text = getattr(record, "text", "")
            author_handle = getattr(author, "handle", "")
            notification_uri = f"{author_handle}: {text}"
            print(f"⚠️ URIなし、仮: {notification_uri}")

        print(f"📌 チェック中: {notification_uri}")
        if notification_uri in replied:
            print(f"⏩ すでに処理済み: {notification_uri}")
            continue

        record = getattr(notification, "record", None)
        if not record or not hasattr(record, "text"):
            print(f"⚠️ レコード/テキストなし、スキップ中")
            continue

        text = record.text
        if f"@{HANDLE}" not in text and (not hasattr(record, "reply") or not record.reply):
            print(f"⚠️ メンション/リプライなし、スキップ: {text}")
            continue

        author_handle = getattr(author, "handle", None)
        author_did = = getattr(author, "did", None)
        print(f"👤 From: {author_handle} / DID: {author_did}")
        print(f"💬 メッセージ: {text}")

        if author_did == self_did or author_handle == HANDLE:
            print(f"⚖️ 自己投稿、スキップ")
            continue

        if not text:
            print(f"⚠️ テキストが空: {author_handle}")
            continue

        reply_ref, post_uri = handle_post(record, notification)
        reply_text = generate_reply_via_local_model(text)
        if not reply_text:
            print(f"⚠️ リプテキスト生成失敗")
            continue

        try:
            post_data = {"text": reply_text, "createdAt": datetime.now().time().isoformat()}
            if reply_ref:
                post_data["reply"] = reply_ref

            client.app_post(
                record=post_data,
                repo=client.me.did
            )

            normalized_uri = normalize_uri(notification_uri)
            if normalized_uri:
                replied.add(normalized_uri)
                if not save_replied(replied):
                    print(f"⚠️ 保存失敗: {normalized_uri}")
                    continue
                print(f"✅ 投稿成功: {normalized_uri}")
                print(f"📖 保存成功: {len(replied)} 件")
            else:
                print(f"⚠️ 無効なURI: {notification_uri}")

            reply_count += 1
            time.sleep(1)

        except Exception as e:
            print(f"⚠️ error: {e}")
            continue

if __name__ == "__main__":
    print("Bot 起動…")
    run_reply()