import os
import json
import requests
import traceback
from atproto import Client, models
from dotenv import load_dotenv
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from datetime import datetime, timezone, timedelta  # ← これも最初の import 群のとこに追加！
import time

REPLIED_TEXTS_FILE = "replied_texts.json"  # 追加で新しい保存ファイル

def load_replied_texts():
    if os.path.exists(REPLIED_TEXTS_FILE):
        try:
            with open(REPLIED_TEXTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # ISO形式の文字列を datetime に変換して返す
                return {k: datetime.fromisoformat(v) for k, v in data.items()}
        except Exception as e:
            print(f"⚠️ replied_texts.json の読み込みエラー: {e}")
            return {}
    else:
        print("📂 replied_texts.json が存在しないので新規作成します")
        return {}

def save_replied_texts(data):
    try:
        with open(REPLIED_TEXTS_FILE, "w", encoding="utf-8") as f:
            # datetime を ISO形式の文字列にして保存
            json.dump({k: v.isoformat() for k, v in data.items()}, f, ensure_ascii=False, indent=2)
        print(f"💾 replied_texts.json に保存しました（件数: {len(data)}）")
    except Exception as e:
        print(f"⚠️ replied_texts.json の保存中にエラーが発生しました: {e}")

# --- 環境変数読み込み ---
load_dotenv()
HANDLE = os.environ["HANDLE"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
HF_API_TOKEN = os.environ["HF_API_TOKEN"]
REPLIED_JSON_URL = os.environ["REPLIED_JSON_URL"]
GIST_TOKEN = os.environ["GIST_TOKEN"]

REPLIED_FILE = "replied.json"  # 返信済み通知のURIを保存するファイル

def load_replied():
    if os.path.exists(REPLIED_FILE):
        try:
            with open(REPLIED_FILE, "r", encoding="utf-8") as f:
                data = set(json.load(f))
                print(f"✅ replied.json を読み込みました（件数: {len(data)}）")
                return data
        except Exception as e:
            print(f"⚠️ replied.json の読み込み中にエラーが発生しました: {e}")
            return set()
    else:
        print("📂 replied.json が存在しないので新規作成します")
        return set()

def save_replied(replied_set):
    try:
        with open(REPLIED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(replied_set), f, ensure_ascii=False, indent=2)
        print(f"💾 replied.json に保存しました（件数: {len(replied_set)}）")
    except Exception as e:
        print(f"⚠️ replied.json の保存中にエラーが発生しました: {e}")

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
    try:
        res = requests.get(REPLIED_JSON_URL)
        if res.status_code == 200:
            return set(json.loads(res.text))
        else:
            print("⚠️ Gist読み込み失敗:", res.status_code)
    except Exception as e:
        print("⚠️ Gist読み込みエラー:", e)
    return set()

# --- Gistに保存 ---
def generate_reply_via_api(user_input):
    prompt = f"ユーザー: {user_input}\nみりんてゃ（甘えん坊で地雷系ENFPっぽい）:"
    HF_API_URL = "https://api-inference.huggingface.co/models/rinna/japanese-gpt2-small"
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 100,
            "temperature": 0.8,
            "top_p": 0.95,
            "do_sample": True
        },
        "options": {
            "wait_for_model": True
        }
    }

    try:
        print(f"📤 {datetime.now().isoformat()} ｜APIへリクエスト送信中…")
        response = requests.post(HF_API_URL, headers=headers, json=data)
        print(f"🌐 ステータスコード: {response.status_code}")
        print(f"📦 レスポンス内容: {response.text}")

        response.raise_for_status()  # ← ここでエラーがあれば例外に
        result = response.json()
        return result

    except requests.exceptions.RequestException as e:
        print(f"⚠️ API通信エラー: {e}")
        return {"error": str(e)}

    try:
        print("📡 AIに問い合わせ中...")
        response = requests.post(HF_API_URL, headers=headers, json=data, timeout=20)
        print("🤖 AIレスポンス:", response.status_code, response.text)

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and "generated_text" in result[0]:
                generated = result[0]["generated_text"]
            else:
                print("⚠️ 予期しない応答形式:", result)
                return "えへへっ、ちょっとだけ迷子になっちゃった〜"

            if "みりんてゃ" in generated:
                return generated.split("みりんてゃ")[-1].strip()
            return generated.strip()
        else:
            print(f"⚠️ Status Code: {response.status_code}, Text: {response.text}")
            return "ふふっ、返信がうまくできなかったけど、気持ちは伝わったよ〜！"

    except Exception as e:
        print("⚠️ AIレスポンスエラー:", e)
        traceback.print_exc()
        return "え〜ん……みりんてゃ迷子になっちゃった〜"
        
# --- テンプレ or AI返し ---
def get_reply(text):
    for keyword, reply in REPLY_TABLE.items():
        if keyword in text:
            print(f"📌 テンプレで返答: {reply}")
            return reply
    return generate_reply_via_api(text)

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

    # replyがない場合はStrongRefから組み立て（失敗してもNone）
    if StrongRef and ReplyRef and post_uri and post_cid:
        parent_ref = StrongRef(uri=post_uri, cid=post_cid)
        reply_ref = ReplyRef(parent=parent_ref, root=parent_ref)
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
    replied_texts = load_replied_texts()  # ← ここが追加！
    print(f"📘 replied の型: {type(replied)} / 件数: {len(replied)}")

    # 🧹 ゴミデータの除去
    for garbage in ["replied", None, "None"]:
        if garbage in replied:
            replied.remove(garbage)
            print(f"🧹 ゴミデータ '{garbage}' を削除しました")

    save_replied(replied)
    upload_to_gist(REPLIED_FILE, GIST_ID, TOKEN)  # ←これ超大事！

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
            print("⚠️ author情報なし（notificationに含まれない）、スキップ")
            continue

        author_handle = getattr(author, "handle", None)
        author_did = getattr(author, "did", None)

        print(f"\n👤 from: @{author_handle} / did: {author_did}")
        print(f"💬 受信メッセージ: {text}")
        print(f"🔗 チェック対象 notification_uri: {notification_uri}")

        # 自分自身には返信しない
        if author_did == self_did or author_handle == HANDLE:
            print("🛑 スキップ理由：自分自身の投稿")
            continue

        check_key = f"{author_did}:{text}"

        # 🔁 12時間以内の重複チェック（追加部分！）
        last_replied_time = replied_texts.get(check_key)
        if last_replied_time:
            elapsed = datetime.now(timezone.utc) - last_replied_time
            if elapsed < timedelta(hours=12):
                print(f"⏭️ スキップ理由：12時間以内に同じユーザー・同じ内容に返信済み（{elapsed} 経過）")
                continue

        if notification_uri in replied:
            print(f"⏭️ スキップ理由：すでに replied 済み → {notification_uri}")
            continue

        if not text:
            print(f"⚠️ スキップ理由：テキストが空 → @{author_handle}")
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

            replied_texts[check_key] = now  # ← 追加！
            save_replied_texts(replied_texts)  # ← 追加！

            print(f"✅ @{author_handle} に返信完了！ → {notification_uri}")

            reply_count += 1
            time.sleep(REPLY_INTERVAL)

        except Exception as e:
            print("⚠️ 投稿失敗:", e)
            traceback.print_exc()

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()