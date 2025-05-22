# ------------------------------
# 🌐 基本ライブラリ・API
# ------------------------------
import os
import json
import requests
import traceback
import time

# ------------------------------
# 🕒 日時関連（UTC→JST）
# ------------------------------
from datetime import datetime, timezone, timedelta

# ------------------------------
# 🧠 モデル関係（transformers）
# ------------------------------
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ------------------------------
# 🔵 Bluesky / atproto ライブラリ
# ------------------------------
from atproto import Client, models
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef

# ------------------------------
# 🔐 環境変数
# ------------------------------
from dotenv import load_dotenv

# --- 環境変数読み込み ---
load_dotenv()
HANDLE = os.environ["HANDLE"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
HF_API_TOKEN = os.environ["HF_API_TOKEN"]
GIST_ID = os.getenv("GIST_ID")
GIST_TOKEN = os.getenv("GIST_TOKEN")

REPLIED_GIST_FILENAME = "replied.json"
REPLIED_JSON_URL = f"https://gist.githubusercontent.com/{GIST_ID}/raw/{REPLIED_GIST_FILENAME}"

# --- Gist API設定 ---
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GIST_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# --- replied.json 読み書き ---
def load_replied():
    try:
        response = requests.get(GIST_API_URL, headers=HEADERS)
        response.raise_for_status()
        gist_data = response.json()
        content = gist_data["files"][REPLIED_GIST_FILENAME]["content"]
        data = set(json.loads(content))
        print(f"✅ replied.json をGistから読み込みました（件数: {len(data)}）")
        return data
    except Exception as e:
        print(f"⚠️ replied.json の読み込み中にエラーが発生しました: {e}")
        return set()

def save_replied(replied_set):
    try:
        content = json.dumps(list(replied_set), ensure_ascii=False, indent=2)
        payload = { "files": { REPLIED_GIST_FILENAME: { "content": content } } }
        response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"💾 replied.json をGistに保存しました（件数: {len(replied_set)}）")
    except Exception as e:
        print(f"⚠️ replied.json の保存中にエラーが発生しました: {e}")

# --- replied_texts.json 読み書き ---
def load_replied_texts():
    try:
        response = requests.get(GIST_API_URL, headers=HEADERS)
        response.raise_for_status()
        gist_data = response.json()
        content = gist_data["files"][REPLIED_TEXTS_FILE]["content"]
        raw_data = json.loads(content)
        # ISO形式から datetime に変換
        data = {k: datetime.fromisoformat(v) for k, v in raw_data.items()}
        print(f"✅ replied_texts.json をGistから読み込みました（件数: {len(data)}）")
        return data
    except Exception as e:
        print(f"⚠️ replied_texts.json の読み込みエラー: {e}")
        return {}

def save_replied_texts(data):
    try:
        # datetime を ISO文字列に変換
        serializable_data = {k: v.isoformat() for k, v in data.items()}
        content = json.dumps(serializable_data, ensure_ascii=False, indent=2)
        payload = { "files": { REPLIED_TEXTS_FILE: { "content": content } } }
        response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"💾 replied_texts.json をGistに保存しました（件数: {len(data)}）")
    except Exception as e:
        print(f"⚠️ replied_texts.json の保存中にエラーが発生しました: {e}")

# --- HuggingFace API設定 ---
HF_API_URL = "https://api-inference.huggingface.co/"
HF_HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json"
}

# --- Blueskyログイン ---
client = Client()
client.login(HANDLE, APP_PASSWORD)

HF_API_URL = "https://api-inference.huggingface.co/"  # ← 共通URL！

HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json"
}

REPLY_TABLE = {
     "使い方": "使い方は「♡推しプロフィールメーカー♡」のページにあるよ〜！かんたんっ♪",
    "おすすめ": "えへへ♡ いちばんのおすすめは「♡推しプロフィールメーカー♡」だよっ！",
    'ねえ': 'ん〜？呼んだ〜？みりんてゃのお耳はず〜っとリスナー向き♡',
    '好き': 'えっ！？…みりんもすきかも〜っ♡',
    'ひま': 'ひまなの〜？じゃあいっしょに遊ぼっ♡',
    'つらい': 'え〜ん…つらいの？みりんがなでなでしてあげるぅ…',
    'ねむい': 'おねむなの？おふとんかけてあげるね…おやすみ♡',
    'すき': 'もっかい言って？うそでもうれしすぎる〜っ♡',
    'おはよう': 'おっはよ〜♡ 今日もあざとく生きてこっ？',
    'こんにちは': 'こんにちみり〜ん♡ 会えてうれしぃ〜っ！',
    'こんばんは': 'こんばんみり〜ん♡ 夜もかわいさ全開でいっちゃうよ♡',
    '作ったよ': 'えっ…ほんとに？ありがとぉ♡ 見せて見せてっ！',
    '作ってみる': 'えっ…ほんとに？ありがとぉ♡ 見せて見せてっ！',
    '遊んだよ': 'やったぁ〜っ！また遊んでね♡ 他のもいっぱいあるから見てみて〜っ',
    '使ったよ': 'えっ！？ほんとに使ってくれたの！？ うれしすぎてとける〜〜♡',
    '見たよ': 'うれしっ♡ 見つけてくれてありがとにゃん♡',
    'きたよ': 'きゅ〜ん♡ 来てくれてとびきりの「すきっ」プレゼントしちゃう♡',
    'フォローした': 'ありがとぉ♡ みりんてゃ、超よろこびダンス中〜っ！',
    'おやすみ': 'おやすみりん♡ 夢の中でもあざとく会いにいっちゃうから〜っ♪',
    '起きた': 'おはみりん♡ 今日も世界一かわいく生きてこっ！',
    '疲れ': 'えらすぎっ♡ いっぱい頑張ったキミに、みりんから癒しビーム〜っ！',
    '嫌い': 'うぅ…キライって言われたら泣いちゃうかも……',
    'ありがと': 'こちらこそありがと〜っ♡ みりんてゃ、めちゃうれしいっ！',
    'かわいい': 'ほんとに？♡ もっと言ってもっと〜♡',
    '可愛い': 'ほんとに？♡ もっと言ってもっと〜♡',
    'メンヘラ': 'やだ♡ あたしのことかな？図星ぃ〜♡',
    '構って': 'かまちょちゃ〜ん♡ 今すぐぎゅーっ♡',
    '寝れない': 'おやすみのちゅ〜〜♡ 一緒に寝よ？',
    'やばい': 'やばいって言われるのちょ〜〜うれし〜〜っ♡ もっと沼ってぇ！',
    '作ってみた': 'え〜〜！めちゃうれしいぃ♡ それ、ぜったい似合ってたでしょ！？',
    '使ってみる': 'やった〜♡ みりんてゃの広報が効いたかも！？てへっ！',
    'かっこいい': 'え〜っ！？ほんとに？照れちゃう〜〜っ♡ でももっかい言って？',
    'スキ': 'みりんてゃ、スキって言われると元気でちゃう〜♡',
    '特別': '特別って……ほんと？ ほんとにほんと？ それ、録音してもいい？（じわっ）',
    'やってみた': 'わ〜〜！うちのツール使ってくれてありがとっ♡感想とかくれると、みりてゃめちゃくちゃよろこぶよ〜〜！',
    'やってみる': 'やった〜♡ みりんてゃの広報が効いたかも！？てへっ！',
    '相性悪かった': 'うそでしょ……そんなぁ〜（バタッ）でも、みりんてゃはあきらめないからっ！',
    '相性良かった': 'えっ、運命かな…！？こんど一緒にプリとか撮っちゃう〜？♡',
    'すごい': 'え！？ほんとに！？……もっと褒めてっ（ドヤ顔で照れ）',
    'えらい': 'え！？ほんとに！？……もっと褒めてっ（ドヤ顔で照れ）',
    'ｷﾞｭｰ': 'えへへ〜、もっと〜♡ぎゅーだいすきっ！',
    'ぎゅー': 'えへへ〜、もっと〜♡ぎゅーだいすきっ！',
    'ぎゅ〜': 'えへへ〜、もっと〜♡ぎゅーだいすきっ！',
    'よしよし': 'あ〜〜、そこそこ〜っ…もっとなでて〜♡（甘え）',
    'ヨシヨシ': 'あ〜〜、そこそこ〜っ…もっとなでて〜♡（甘え）',
    'なでなで': 'あ〜〜、そこそこ〜っ…もっとなでて〜♡（甘え）',
    'ﾅﾃﾞﾅﾃﾞ': 'あ〜〜、そこそこ〜っ…もっとなでて〜♡（甘え）',
    'ﾖｼﾖｼ': 'あ〜〜、そこそこ〜っ…もっとなでて〜♡（甘え）',
    'おもしろ': 'おもしろいって言ってもらえたら、みりんてゃ、がんばっちゃうかんねっ！',
    '面白': 'おもしろいって言ってもらえたら、みりんてゃ、がんばっちゃうかんねっ！',
    '当たった': '当たったの！？すごっ！みりんてゃ、見る目あるかも〜っ♡',
    'やったよ': 'えへへ♡ みりんてゃのツールであそんでくれてありがとっ！らぶっ！',
    'タグから': '見つけてくれてありがとっ！もしかして運命？♡',
    '嫌': 'え〜ん…でもお願い、今回だけっ',
    '駄目': 'みりんてゃ泣いちゃうよ？それでもいいの〜？',
    'ダメ': 'みりんてゃ泣いちゃうよ？それでもいいの〜？',
    'いいよ': 'えへへ、じゃあ…調子のっていい？（こら）',
    '良いよ': 'えへへ、じゃあ…調子のっていい？（こら）',
    '何かあった？': 'ううん、大丈夫。って言うまでがセットなの（甘えていい？）',
    'どうかした？': 'ううん、大丈夫。って言うまでがセットなの（甘えていい？）',
    '大丈夫？': 'ありがと…そう言ってもらえるだけで、ちょっと泣きそう',
    'どうしたの？': 'ううん、大丈夫。って言うまでがセットなの（甘えていい？）',
    'おなかすいた': 'みりんてゃが何か作ろっか？（たぶん焦がす）',
    '病みそう': 'いっそ病んじゃお？一緒に沈むのも悪くないよ…',
    '推し語り': 'むしろ語って！そのために生きてる！',
    '泣いちゃ': 'よしよし、なでなでしちゃう…ぎゅーもいる？',
    'ツインテ似合うね': 'ふふ、そう言われるために生きてる←',
    'ツインテール似合うね': 'ふふ、そう言われるために生きてる←',
    'さみしい': 'ぎゅーしにいってもいい？（もう行ってる）',
    'しんど': 'しんどいときはぎゅーしてあげるしかできないけど、そばにいるよ…？',
    'ﾁｭｯﾁｭ': 'だめ〜っ！もっと雰囲気だいじにしよぉ……でも、すき（ぽそ）',
    'ㄘゅ': 'ちゅーって……もう……すき……（きゅん）',
    'ちゅー': 'え、いきなりちゅーとか……責任とってよね…っ（照）',
    'ちゅ〜': 'え、いきなりちゅーとか……責任とってよね…っ（照）',
}

# --- Gistから読み込み ---
def load_replied():
    print(f"🌐 Gistから読み込み中: {REPLIED_JSON_URL}")
    try:
        res = requests.get(REPLIED_JSON_URL)
        if res.status_code == 200:
            data = set(json.loads(res.text))
            print("✅ Gistからの読み込みに成功")
            print(f"📄 保存済みURI読み込み完了 → 件数: {len(data)}")

            if len(data) > 0:
                print("📁 最新URI一覧:")
                for uri in list(data)[-5:]:  # 最新5件だけ表示（多すぎないように）
                    print(f" - {uri}")

            return data
        else:
            print(f"⚠️ Gist読み込み失敗: {res.status_code}")
    except Exception as e:
        print(f"⚠️ Gist読み込みエラー: {e}")
    return set()

# --- Gistに上書き保存 ---
def upload_gist_content(content, filename=REPLIED_GIST_FILENAME, gist_id=GIST_ID, token=GIST_TOKEN):
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "files": {
            filename: {
                "content": content
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"🚀 Gist（{filename}）の更新に成功しました")
    else:
        print(f"❌ Gistの更新に失敗しました: {response.status_code} {response.text}")
        
# --- Gistに保存 ---

def generate_reply_via_local_model(user_input):
    model_name = "cl-tohoku/bert-base-japanese-v2"

    try:
        print(f"📤 {datetime.now().isoformat()} ｜ モデルとトークナイザを読み込み中…")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)

        prompt = f"ユーザー: {user_input}\nみりんてゃ（甘えん坊で地雷系ENFPっぽい）:"
        token_ids = tokenizer.encode(prompt, return_tensors="pt")

        print(f"📤 {datetime.now().isoformat()} ｜ テキスト生成中…")
        with torch.no_grad():
            output_ids = model.generate(
                token_ids,
                max_new_tokens=100,
                temperature=0.8,
                top_p=0.95,
                do_sample=True
            )

        output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        reply = output_text.split("みりんてゃ（甘えん坊で地雷系ENFPっぽい）:")[-1].strip()
        print(f"🤖 AI返答: {reply}")
        return reply

    except Exception as e:
        print(f"❌ モデル読み込みエラー: {e}")
        return "えへへ、ごめんね〜〜今ちょっと調子悪いみたい…またお話しよ？"
        
# --- テンプレ or AI返し ---
def get_reply(text):
    for keyword, reply in REPLY_TABLE.items():
        if keyword in text:
            print(f"📌 テンプレで返答: {reply}")
            return reply
    return generate_reply_via_local_model(text)

# --- メイン処理 ---
from atproto_client.models.app.bsky.feed.post import ReplyRef
from datetime import datetime, timezone

try:
    from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
    from atproto_client.models.app.bsky.feed.post import ReplyRef
except ImportError:
    StrongRef = None
    ReplyRef = None

def handle_post(record, notification):
    post_uri = getattr(notification, "uri", None)
    post_cid = getattr(notification, "cid", None)

    if StrongRef and ReplyRef and post_uri and post_cid:
        parent_ref = StrongRef(uri=post_uri, cid=post_cid)
        root_ref = getattr(getattr(record, "reply", None), "root", parent_ref)
        reply_ref = ReplyRef(parent=parent_ref, root=root_ref)
        return reply_ref, post_uri

    return None, post_uri

def run_reply_bot():
    try:
        client = Client()
        client.login(HANDLE, APP_PASSWORD)
        print("✅ ログイン成功！")
    except Exception as e:
        print(f"❌ ログインに失敗しました: {e}")
        return

    self_did = client.me.did
    replied = load_replied()
    replied_texts = load_replied_texts()  # ← ここで辞書型で読み込み

    print(f"📘 replied の型: {type(replied)} / 件数: {len(replied)}")

# --- 🧹 replied（URLのセット）を整理 ---
original_replied_count = len(replied)
replied = {uri for uri in replied if isinstance(uri, str) and uri.startswith("http")}

removed_count = original_replied_count - len(replied)
if removed_count > 0:
    print(f"🧹 無効なデータを {removed_count} 件削除しました（replied）")
else:
    print("✅ replied は問題ありませんでした")

# --- 🧹 replied_texts（辞書）を整理 ---
if isinstance(replied_texts, dict):
    if None in replied_texts:
        del replied_texts[None]
        print("🧹 replied_texts から None キーを削除しました")
    else:
        print("✅ replied_texts に None キーは存在しませんでした")
else:
    print("⚠️ replied_texts が辞書ではありません。初期化します")
    replied_texts = {}

# --- ⛑️ 空じゃなければ保存・アップロード ---
if replied:
    save_replied(replied)
    print("💾 replied を保存しました")
    try:
        upload_to_gist(REPLIED_GIST_FILENAME, GIST_ID, GIST_TOKEN)
        print("☁️ Gist にアップロードしました")
    except Exception as e:
        print(f"❌ Gist アップロード失敗: {e}")
else:
    print("⚠️ replied が空なので Gist に保存しません")

    save_replied(replied)
    save_replied_texts(replied_texts)

    # 確実にファイルが書き込まれたか確認（例：os.path.exists とかでもOK）
    if os.path.exists(REPLIED_GIST_FILENAME):
        upload_to_gist(REPLIED_GIST_FILENAME, GIST_ID, GIST_TOKEN)
    else:
        print("⚠️ REPLIED_GIST_FILENAME の保存に失敗した可能性あり、Gistへのアップロード中止")

    try:
        notifications = client.app.bsky.notification.list_notifications(params={"limit": 25}).notifications
    except Exception as e:
        print(f"❌ 通知の取得に失敗しました: {e}")
        return

    print(f"🔔 通知総数: {len(notifications)} 件")

    MAX_REPLIES = 5
    REPLY_INTERVAL = 5
    reply_count = 0

    for notification in notifications:
        notification_uri = getattr(notification, "uri", None) or getattr(notification, "reasonSubject", None)
        if notification_uri:
            notification_uri = str(notification_uri).strip()
        else:
            record = getattr(notification, "record", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                continue
            text = getattr(record, "text", "")
            author_handle = getattr(author, "handle", "")
            notification_uri = f"{author_handle}:{text}"
            print(f"⚠️ notification_uri が取得できなかったので、仮キーで対応 → {notification_uri}")

        print(f"📌 チェック中 notification_uri: {notification_uri}")
        print(f"📂 保存済み replied: {replied}")

        if reply_count >= MAX_REPLIES:
            print(f"⏹️ 最大返信数（{MAX_REPLIES}）に達したので終了します")
            break

        record = getattr(notification, "record", None)
        author = getattr(notification, "author", None)

        if not record or not hasattr(record, "text"):
            continue

        text = getattr(record, "text", None)
        if f"@{HANDLE}" not in text and (not hasattr(record, "reply") or not record.reply):
            continue

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

        import hashlib

        def hash_text(text):
            return hashlib.sha256(text.encode("utf-8")).hexdigest()

        check_key = f"{author_did}:{hash_text(text)}"

        if notification_uri in replied:
            print(f"⏭️ すでに replied 済み → {notification_uri}")
            print(f"📂 現在の保存件数: {len(replied)} / 最新5件: {list(replied)[-5:]}")
            continue

        if not text:
            print(f"⚠️ テキストが空 → @{author_handle}")
            continue

        reply_ref, post_uri = handle_post(record, notification)
        print("🔗 reply_ref:", reply_ref)
        print("🧾 post_uri:", post_uri)

        reply_text = get_reply(text)
        print("🤖 生成された返信:", reply_text)

        if not reply_text:
            print("⚠️ 返信テキストが生成されていません")
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

            now = datetime.now(timezone.utc)
            replied.add(notification_uri)
            save_replied(replied)
            replied_texts[check_key] = now
            save_replied_texts(replied_texts)

            print(f"✅ @{author_handle} に返信完了！ → {notification_uri}")
            print(f"💾 URI保存成功 → 合計: {len(replied)} 件")
            print(f"📁 最新URI一覧: {list(replied)[-5:]}")

            reply_count += 1
            time.sleep(REPLY_INTERVAL)

        except Exception as e:
            print("⚠️ 投稿失敗:", e)
            traceback.print_exc()
            
if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()