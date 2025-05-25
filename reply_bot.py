# reply_bot.py
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
from datetime import datetime, timezone
from transformers import AutoModelForCausalLM, GPTNeoXTokenizerFast
import torch
from atproto import Client
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from atproto_client.models.app.bsky.feed.post import ReplyRef
from dotenv import load_dotenv
import urllib.parse

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
    except Exception:
        return None

# ------------------------------
# 📁 Gist操作
# ------------------------------
def load_gist_data():
    print(f"🌐 Gistデータ読み込み開始 → URL: {GIST_API_URL}")
    for attempt in range(3):
        try:
            curl_command = [
                "curl", "-X", "GET", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json"
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            print(f"📥 試行 {attempt + 1} ステータス: {result.returncode}")
            if result.returncode != 0:
                raise Exception(f"Gist読み込み失敗: {result.stderr}")
            gist_data = json.loads(result.stdout)
            if REPLIED_GIST_FILENAME in gist_data["files"]:
                replied_content = gist_data["files"][REPLIED_GIST_FILENAME]["content"]
                replied = set(normalize_uri(u) for u in json.loads(replied_content) if normalize_uri(u))
                print(f"✅ replied.json 読み込み完了（件数: {len(replied)}）")
                return replied
            print(f"⚠️ Gistに {REPLIED_GIST_FILENAME} なし")
            return set()
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} エラー: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return set()

def save_replied(replied_set):
    print(f"💾 Gist保存開始 → URL: {GIST_API_URL}")
    cleaned_set = set(normalize_uri(uri) for uri in replied_set if normalize_uri(uri))
    print(f"🧹 保存前クリーニング（件数: {len(cleaned_set)}）")
    for attempt in range(3):
        try:
            content = json.dumps(list(cleaned_set), ensure_ascii=False, indent=2)
            payload = {"files": {REPLIED_GIST_FILENAME: {"content": content}}}
            curl_command = [
                "curl", "-X", "PATCH", GIST_API_URL,
                "-H", f"Authorization: token {GIST_TOKEN_REPLY}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "Content-Type: \"application/json\"",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"💾 replied.json 保存完了（件数: {len(cleaned_set)}）")
                time.sleep(2)
                new_replied = load_gist_data()
                if cleaned_set.issubset(new_replied):
                    print("✅ 保存内容反映確認")
                    return True
                raise Exception("保存内容の反映に失敗")
            raise Exception(f"Gist保存失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} エラー: {e}")
            if attempt < 2:
                time.sleep(2)
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
# ユーザーの入力に含まれるキーワードに応じた固定返信
REPLY_TABLE = {
    "使い方": "使い方は「♡推しプロフィールメーカー♡」のページにあるよ〜！かんたんっ♪",
    '作ったよ': 'えっ…ほんとに？ありがとぉ♡ 見せて見せてっ！',
    '作ってみる': 'えっ…ほんとに？ありがとぉ♡ 見せて見せてっ！',
    '遊んだよ': 'やったぁ〜っ！また遊んでね♡ 他のもいっぱいあるから見てみて〜っ',
    '使ったよ': 'えっ！？ほんとに使ってくれたの！？ うれしすぎてとける〜〜♡',
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
    # 追加例: "おはよう": "おは！{BOT_NAME}、キミの朝をハッピーにしちゃうよ！"
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
BOT_NAME = "みりんてゃ"  # キャラ名（例: "クマちゃん", "ツンデレ姫"）
FIRST_PERSON = "みりんてゃ"  # 一人称（例: "私", "君", "あたし", "ボク"）
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

    # 意図しない一人称を検知
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
            f"うぅ、なんか分かんないけど…{BOT_NAME}、君なしじゃダメなのっ♡"
        ])

    if not re.search(r"[。！？♡♪笑]$", reply):
        reply += random.choice(["なのっ♡", "よぉ？♡", "のっ♡", "♪"])

    return reply

# ------------------------------
# 🤖 モデル初期化
# ------------------------------
model = None
tokenizer = None

def initialize_model_and_tokenizer(model_name="cyberagent/open-calm-3b"):
    global model, tokenizer
    if model is None or tokenizer is None:
        print(f"📤 {datetime.now().isoformat()} ｜ トークナイザ読み込み中…")
        tokenizer = GPTNeoXTokenizerFast.from_pretrained(model_name, use_fast=True)
        print(f"📤 {datetime.now().isoformat()} ｜ トークナイザ読み込み完了")
        print(f"📤 {datetime.now().isoformat()} ｜ モデル読み込み中…")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            device_map="auto"
        ).eval()
        print(f"📤 {datetime.now().isoformat()} ｜ モデル読み込み完了")
    return model, tokenizer

# ------------------------------
# ★ カスタマイズポイント4: 返信生成（generate_reply_via_local_model）
# ------------------------------
def generate_reply_via_local_model(user_input):
    model_name = "cyberagent/open-calm-3b"
    # 失敗時のメッセージ
    failure_messages = [
        f"えへへ、ごめんね〜〜今ちょっと調子悪いみたい……{BOT_NAME}、またお話しよ？♡",
        f"うぅ、ごめん〜…上手くお返事できなかったの。{BOT_NAME}、ちょっと待ってて？♡",
        f"あれれ？{BOT_NAME}、おねむかも…またあとで頑張るねっ！♡"
    ]
    # フォールバック返信
    fallback_cute_lines = [
        f"えへへ〜♡ {BOT_NAME}、君のこと考えるとドキドキなのっ♪",
        f"今日も君に甘えたい気分なのっ♡ {BOT_NAME}、ぎゅーってして？",
        f"だ〜いすきっ♡ ね、ね、{BOT_NAME}、もっと構ってくれる？"
    ]
    # イントロライン
    intro_lines = [
        f"えへへ〜、{BOT_NAME}はね〜、",
        f"ねぇねぇ、聞いて聞いて〜♡",
        f"ん〜今日もふwaふwaしてたのっ♪",
        f"きゃ〜っ、君だぁ！{BOT_NAME}、やっと会えたのっ♡",
        f"ふwaふwa〜、{BOT_NAME}、君のこと考えてたんだからっ♪",
        # 追加例: f"やっほー！{BOT_NAME}、キミに会えて超ハッピー！"
    ]

    # 特定パターン返信
    if re.search(r"(大好き|ぎゅー|ちゅー|愛してる|キス|添い寝)", user_input, re.IGNORECASE):
        print(f"⚠️ ラブラブ入力検知: {user_input}")
        return random.choice([
            f"うぅ…{BOT_NAME}、ドキドキ止まんないのっ♡ もっと甘やかしてぇ♡",
            f"えへへ♡ そんなの言われたら…{BOT_NAME}、溶けちゃいそうなのぉ〜♪",
            f"も〜〜〜♡ {BOT_NAME}、好きすぎて胸がぎゅーってなるぅ♡"
        ])

    if re.search(r"(疲れた|しんどい|つらい|泣きたい|ごめん|寝れない)", user_input, re.IGNORECASE):
        print(f"⚠️ 癒し系入力検知: {user_input}")
        return random.choice([
            f"うぅ、よしよしなのっ♡ {BOT_NAME}、君が元気になるまでそばにいるのっ♪",
            f"ぎゅ〜ってしてあげるっ♡ {BOT_NAME}、無理しなくていいのよぉ？",
            f"んん〜っ、えへへ♡ {BOT_NAME}、甘えてもいいの、ぜ〜んぶ受け止めるからねっ♪"
        ])

    if re.search(r"(映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|ポケモン|企業|発表|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス|政府|協定|軍事|情報|外交|外相|自動更新|\d+(時|分))", user_input, re.IGNORECASE):
        print(f"⚠️ ビジネス・学術系ワード検知: {user_input}")
        user_input = f"{BOT_NAME}、君と甘々トークしたいなのっ♡"
        print(f"🔄 入力置き換え: {user_input}")

    # REPLY_TABLEチェック
    for key, reply in REPLY_TABLE.items():
        if key in user_input:
            return reply.replace("{BOT_NAME}", BOT_NAME)

    try:
        print(f"📊 メモリ使用量: {psutil.virtual_memory().percent}%")
        if torch.cuda.is_available():
            print(f"📊 GPUメモリ: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")
        else:
            print("⚠️ GPU未検出、CPU実行")

        model, tokenizer = initialize_model_and_tokenizer(model_name)

        intro = random.choice(intro_lines)
        prompt = (
            f"{intro}\n"
            f"あなたは『{BOT_NAME}』、ふwaふwaな地雷系女の子！一人称は『{FIRST_PERSON}』！\n"
            f"タメ口で「〜なのっ♡」「〜よぉ？♪」「えへへ〜♡」な可愛い口調で話すよ！\n"
            f"ニュース、政治、過激な表現はNG！『ちゅ♡』『ぎゅっ』みたいな可愛い言葉だけで！\n"
            f"例: ユーザー: {BOT_NAME}、好きだよ！\n"
            f"{BOT_NAME}: え〜っ、ほんと！？{FIRST_PERSON}、君にそう言われるとドキドキなのっ♡\n"
            f"ユーザー: {user_input}\n"
            f"{BOT_NAME}: "
        )

        input_ids = tokenizer.encode(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
        print(f"📏 入力トークン数: {input_ids.shape[1]}")

        for attempt in range(3):
            print(f"📤 テキスト生成中（試行 {attempt + 1}）")
            try:
                with torch.no_grad():
                    output_ids = model.generate(
                        input_ids,
                        max_new_tokens=50,
                        temperature=0.7,
                        top_p=0.9,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id,
                        no_repeat_ngram_size=2
                    )
                raw_reply = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
                reply_text = clean_sentence_ending(raw_reply)
                if any(re.search(rf"\b{re.escape(msg)}\b", reply_text) for msg in failure_messages + fallback_cute_lines):
                    print(f"⚠️ フォールバック検知、リトライ")
                    continue
                print(f"📝 生成テキスト: {reply_text}")
                return reply_text
            except Exception as e:
                print(f"⚠️ 生成エラー: {e}")
                continue
        return random.choice(fallback_cute_lines).replace("{BOT_NAME}", BOT_NAME)
    except Exception as e:
        print(f"❌ モデルエラー: {e}")
        return random.choice(failure_messages).replace("{BOT_NAME}", BOT_NAME)

# ------------------------------
# 📬 メイン処理
# ------------------------------
def handle_post(record, notification):
    post_uri = getattr(notification, "uri", None)
    post_cid = getattr(notification, "cid", None)
    if post_uri and post_cid:
        parent_ref = StrongRef(uri=post_uri, cid=post_cid)
        root_ref = getattr(getattr(record, "reply", None), "root", parent_ref)
        reply_ref = ReplyRef(parent=parent_ref, root=root_ref)
        return reply_ref, normalize_uri(post_uri)
    return None, normalize_uri(post_uri)

def run_reply_bot():
    self_did = client.me.did
    replied = load_gist_data()
    print(f"📘 replied 件数: {len(replied)}")

    # ゴミデータ整理
    garbage_items = ["replied", None, "None", "", "://replied"]
    removed = False
    for garbage in garbage_items:
        while garbage in replied:
            replied.remove(garbage)
            print(f"🧹 ゴミデータ '{garbage}' 削除")
            removed = True
    if removed and not save_replied(replied):
        print("❌ ゴミデータ削除後保存失敗")
        return

    try:
        notifications = client.app.bsky.notification.list_notifications(params={"limit": 25}).notifications
        print(f"🔔 通知総数: {len(notifications)} 件")
    except Exception as e:
        print(f"❌ 通知取得失敗: {e}")
        return

    MAX_REPLIES = 5
    REPLY_INTERVAL = 5
    reply_count = 0

    for notification in notifications:
        if reply_count >= MAX_REPLIES:
            print(f"⏹️ 最大返信数（{MAX_REPLIES}）到達")
            break

        notification_uri = normalize_uri(getattr(notification, "uri", None) or getattr(notification, "reasonSubject", None))
        if not notification_uri:
            record = getattr(notification, "record", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                print("⚠️ 無効な通知、スキップ")
                continue
            text = getattr(record, "text", "")
            author_handle = getattr(author, "handle", "")
            notification_uri = f"{author_handle}:{text}"
            print(f"⚠️ URIなし、仮キー: {notification_uri}")

        print(f"📌 チェック中 URI: {notification_uri}")
        if notification_uri in replied:
            print(f"⏭️ 既回复: {notification_uri}")
            continue

        record = getattr(notification, "record", None)
        author = getattr(notification, "author", None)
        if not record or not hasattr(record, "text") or not author:
            print("⚠️ レコード/著者なし、スキップ")
            continue

        text = record.text
        if f"@{HANDLE}" not in text and (not hasattr(record, "reply") or not record.reply):
            print(f"⚠️ メンション/リプライなし、スキップ: {text}")
            continue

        author_handle = getattr(author, "handle", None)
        author_did = getattr(author, "did", None)
        print(f"👤 from: @{author_handle} / did: {author_did}")
        print(f"💬 メッセージ: {text}")

        if author_did == self_did or author_handle == HANDLE:
            print("🛑 自己投稿、スキップ")
            continue

        if not text:
            print(f"⚠️ テキスト空: @{author_handle}")
            continue

        reply_ref, post_uri = handle_post(record, notification)
        reply_text = generate_reply_via_local_model(text)
        if not reply_text:
            print("⚠️ 返信テキスト生成失敗")
            continue

        try:
            post_data = {
                "text": reply_text,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            if reply_ref:
                post_data["reply"] = reply_ref

            client.app.bsky.feed.post.create(
                record=post_data,
                repo=client.me.did
            )

            normalized_uri = normalize_uri(notification_uri)
            if normalized_uri:
                replied.add(normalized_uri)
                if not save_replied(replied):
                    print(f"❌ URI保存失敗: {normalized_uri}")
                    continue
                print(f"✅ @{author_handle} に返信完了: {normalized_uri}")
                print(f"💾 URI保存成功、合計: {len(replied)} 件")
            else:
                print(f"⚠️ 無効なURI: {notification_uri}")

            reply_count += 1
            time.sleep(REPLY_INTERVAL)

        except Exception as e:
            print(f"⚠️ 投稿失敗: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()