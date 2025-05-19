import os
import json
import requests
import traceback
from atproto import Client, models
from dotenv import load_dotenv

# --- 環境変数読み込み ---
load_dotenv()
HANDLE = os.environ["HANDLE"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
HF_API_TOKEN = os.environ["HF_API_TOKEN"]
REPLIED_JSON_URL = os.environ["REPLIED_JSON_URL"]
GIST_TOKEN = os.environ["GIST_TOKEN"]

client = Client()
client.login(HANDLE, APP_PASSWORD)

HF_API_URL = "https://api-inference.huggingface.co/"  # ← 共通URL！

HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "model": "elyza/ELYZA-japanese-stablelm-instruct-alpha",  # ← モデル名ここ！
    "inputs": "ユーザー: ○○○\nみりんてゃ:",
    "parameters": {
        "max_new_tokens": 100,
        "temperature": 0.8,
        "top_p": 0.9,
        "do_sample": True
    }
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
def save_replied(replied_set):
    gist_id = REPLIED_JSON_URL.split("/")[4]
    filename = "replied.json"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "files": {
            filename: {
                "content": json.dumps(list(replied_set), indent=2, ensure_ascii=False)
            }
        }
    }
    try:
        res = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=data)
        if res.status_code == 200:
            print("💾 Gistに保存完了")
        else:
            print("⚠️ Gist保存失敗:", res.status_code, res.text)
    except Exception as e:
        print("⚠️ Gist保存エラー:", e)

# --- AIで返す ---
def generate_reply_via_api(user_input):
    prompt = f"ユーザー: {user_input}\nみりんてゃ（甘えん坊で地雷系ENFPっぽい）:"
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 100,
            "temperature": 0.8,
            "top_p": 0.9,
            "do_sample": True
        }
    }
    try:
        print("📡 AIに問い合わせ中...")
        response = requests.post(HF_API_URL, headers=HEADERS, json=data, timeout=20)
        print("🤖 AIレスポンス:", response.status_code, response.text)
        if response.status_code == 200:
            generated = response.json()[0]["generated_text"]
            if "みりんてゃ" in generated:
                return generated.split("みりんてゃ")[-1].strip()
            return generated
        else:
            return "え〜ん……AIとおしゃべりできないみたい（泣）"
    except Exception:
        print("⚠️ AIレスポンスエラー:")
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
from atproto_client.models import AppBskyFeedPost

def handle_post(record):
    reply_ref = getattr(record, "reply", None)
    post_uri = getattr(record, "uri", None)
    return reply_ref, post_uri
    
def run_reply_bot():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    print("✅ ログイン成功！")

    self_did = client.me.did
    replied = load_replied()

    notifications = client.app.bsky.notification.list_notifications(params={"limit": 25}).notifications
    print(f"🔔 通知総数: {len(notifications)} 件")

    for notification in notifications:
        record = getattr(notification, "record", None)
        author = getattr(notification, "author", None)

        if not record or not hasattr(record, "reply") or not record.reply:
            continue  # 返信じゃない投稿はスキップ

        print(f"\n📦 record内容: {record}")
        print(f"📎 record.__class__: {type(record)}")

        if not author:
            print("⚠️ author情報なし（notificationに含まれない）、スキップ")
            continue

        author_handle = getattr(author, "handle", None)
        author_did = getattr(author, "did", None)

        print(f"👤 from: @{author_handle} / did: {author_did}")

        if not author_handle or not author_did:
            print("⚠️ handle or didがない、スキップ")
            continue

        if author_did == self_did or author_handle == HANDLE:
            print("🛑 自分自身の投稿なのでスキップ")
            continue

        reply_ref, post_uri = handle_post(record)
        print("🔗 reply_ref:", reply_ref)
        print("🧾 post_uri:", post_uri)

        if post_uri is None or post_uri in replied:
            print("⏭️ すでに返信済み、または処理不要な投稿")
            continue

        text = getattr(record, "text", None)
        print("💬 受信メッセージ:", text)

        if not text:
            print("⚠️ テキストが空、スキップ")
            continue

        reply_text = get_reply(text)
        print("🤖 生成された返信:", reply_text)

        if not reply_text:
            print("⚠️ 返信テキストが生成されていません")
            continue

        from datetime import datetime, timezone
    try:
        client.app.bsky.feed.post.create(
            record=AppBskyFeedPost(
                text=reply_text,
                created_at=datetime.now(timezone.utc).isoformat(),
                reply=reply_ref
            ),
            repo=client.me.did
        )
        replied.add(post_uri)
            save_replied(replied)
            print(f"✅ @{author_handle} に返信完了！")
        except Exception as e:
            print("⚠️ 投稿失敗:", e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()