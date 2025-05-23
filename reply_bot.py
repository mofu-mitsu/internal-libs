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
from datetime import datetime, timezone, timedelta
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from atproto import Client, models
from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
from atproto_client.models.app.bsky.feed.post import ReplyRef
from dotenv import load_dotenv
import urllib.parse

# ------------------------------
# 🔐 環境変数
# ------------------------------
load_dotenv()
HANDLE = os.environ["HANDLE"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
HF_API_TOKEN = os.environ["HF_API_TOKEN"]
GIST_TOKEN_REPLY = os.environ["GIST_TOKEN_REPLY"]

if not GIST_TOKEN_REPLY:
    print("❌ GIST_TOKEN_REPLYが読み込まれていません！（None）")
    exit(1)
else:
    print(f"🧪 GIST_TOKEN_REPLY: {repr(GIST_TOKEN_REPLY)}")
    print(f"🪪 現在のGIST_TOKEN_REPLY: {GIST_TOKEN_REPLY[:8]}...（先頭8文字だけ表示）")
    print(f"🔑 トークンの長さ: {len(GIST_TOKEN_REPLY)}")
    print(f"🔑 トークンの先頭5文字: {GIST_TOKEN_REPLY[:5]}")
    print(f"🔑 トークンの末尾5文字: {GIST_TOKEN_REPLY[-5:]}")

# --- 固定値 ---
GIST_USER = "mofu-mitsu"
GIST_ID = "40391085a2e0b8a48935ad0b460cf422"
REPLIED_GIST_FILENAME = "replied.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GIST_TOKEN_REPLY}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json"
}

# --- URI正規化 ---
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

# --- Gistから replied.json の読み込み ---
def load_gist_data():
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
            if REPLIED_GIST_FILENAME in gist_data["files"]:
                replied_content = gist_data["files"][REPLIED_GIST_FILENAME]["content"]
                print(f"📄 生のreplied.json内容:\n{replied_content}")
                raw_uris = json.loads(replied_content)
                replied = set(uri for uri in (normalize_uri(u) for u in raw_uris) if uri)
                print(f"✅ replied.json をGistから読み込みました（件数: {len(replied)}）")
                if replied:
                    print("📁 最新URI一覧（正規化済み）:")
                    for uri in list(replied)[-5:]:
                        print(f" - {uri}")
                return replied
            else:
                print(f"⚠️ Gist内に {REPLIED_GIST_FILENAME} が見つかりませんでした")
                return set()
        except Exception as e:
            print(f"⚠️ 試行 {attempt + 1} でエラー: {e}")
            if attempt < 2:
                print(f"⏳ リトライします（{attempt + 2}/3）")
                time.sleep(2)
            else:
                print("❌ 最大リトライ回数に達しました")
                return set()

# --- replied.json 保存 ---
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
                new_replied = load_gist_data()
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

# --- HuggingFace API設定 ---
HF_API_URL = "https://api-inference.huggingface.co/"
HF_HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json"
}

# --- Blueskyログイン ---
try:
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    print("✅ Blueskyログイン成功！")
except Exception as e:
    print(f"❌ Blueskyログインに失敗しました: {e}")
    exit(1)

REPLY_TABLE = {
    "使い方": "使い方は「♡推しプロフィールメーカー♡」のページにあるよ〜！かんたんっ♪",
}

def clean_sentence_ending(reply):
    reply = reply.split("\n")[0].strip()
    reply = re.sub(r"^みりんてゃ\s*[:：]\s*", "", reply)
    reply = re.sub(r"^ユーザー\s*[:：]\s*", "", reply)
    reply = re.sub(r"([！？笑])。$", r"\1", reply)

    # ビジネス・学術・ニュース系を検知
    if re.search(r"(ご利用|誠に|お詫び|貴重なご意見|申し上げます|ございます|お客様|発表|パートナーシップ|ポケモン|アソビズム|企業|世界中|映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|営業|臨時|時間|午前|午後|オペラ|初演|作曲家|ヴェネツィア|コルテス)", reply, re.IGNORECASE) or re.search(r"\d+(時|分)", reply):
        return random.choice([
            "えへへ〜♡ なんかややこしくなっちゃった！君と甘々トークしたいなのっ♪",
            "うぅ、みりんてゃ、難しい話わかんな〜い！君にぎゅーってしてほしいなのっ♡",
            "ん〜〜変な話になっちゃった！君のこと大好きだから、構ってくれる？♡"
        ])

    # 意味不明（日本語少なすぎor短すぎ）
    if not re.search(r"[ぁ-んァ-ン一-龥ー]", reply) or len(reply) < 8:
        return random.choice([
            "えへへ〜♡ ふわふわしちゃった！君のことずーっと好きだよぉ？♪",
            "みりんてゃ、君にドキドキなのっ♡ ね、もっとお話しよ？",
            "うぅ、なんか分かんないけど…君なしじゃダメなのっ♡"
        ])

    # 語尾をキャラに合わせて補完
    if not re.search(r"[。！？♡♪笑]$", reply):
        reply += random.choice(["なのっ♡", "よぉ？♡", "のっ♡", "♪"])

    return reply

def generate_reply_via_local_model(user_input):
    model_name = "rinna/japanese-gpt-neox-3.6b-chat"  # モデル変更！
    failure_messages = [
        "えへへ、ごめんね〜〜今ちょっと調子悪いみたい……またお話しよ？♡",
        "うぅ、ごめん〜…上手くお返事できなかったの。ちょっと待ってて？♡",
        "あれれ？みりんてゃ、おねむかも…またあとで頑張るねっ！♡",
        "んん〜〜バグっちゃったかも……でも君のこと嫌いじゃないよ！♡",
        "今日はちょっと…お休みモードかも。また構ってくれる？♡",
        "えへへ、なんかうまく考えつかなかったかも〜…♡",
        "ちょっとだけ、おやすみ中かも…また話してね♡"
    ]
    fallback_cute_lines = [
        "えへへ〜♡ みりんてゃ、君のこと考えるとドキドキなのっ♪",
        "今日も君に甘えたい気分なのっ♡ ぎゅーってして？",
        "だ〜いすきっ♡ ね、ね、もっと構ってくれる？",
        "君なしじゃみりんてゃ、ダメダメなのっ♡ えへへ♪",
        "みりんてゃ、君のことずーっと好きだよぉ？♡ ほんとだよ！"
    ]

    # 入力フィルタリング：ビジネス・学術系ワードを検知して置き換え
    if re.search(r"(映画|興行|収入|ドル|億|国|イギリス|フランス|スペイン|イタリア|ドイツ|ロシア|中国|インド|Governor|Cross|ポケモン|企業|発表|営業|臨時|オペラ|初演|作曲家|ヴェネツィア|コルテス)", user_input, re.IGNORECASE) or re.search(r"\d+(時|分)", user_input):
        print(f"⚠️ 入力にビジネス・学術系ワード検知: {user_input}")
        user_input = "みりんてゃ、君と甘々トークしたいなのっ♡"
        print(f"🔄 入力置き換え: {user_input}")

    try:
        print(f"📤 {datetime.now().isoformat()} ｜ モデルとトークナイザを読み込み中…")
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16).eval()

        prompt = (
            "以下は、ユーザーと地雷系ENFPのあざと可愛い女の子『みりんてゃ』との会話です。\n"
            "みりんてゃは感情豊かで、めっちゃ甘えん坊、ちょっと依存気味！いつも親しみやすいタメ口で、\n"
            "語尾に『〜♡』『〜なのっ』『〜よぉ？』『♪』を使ってキャピキャピに話すよ。\n"
            "絶対にビジネス風、説明口調、固有名詞（映画、ゲーム、国名、企業、営業、オペラなど）は使わず、\n"
            "ユーザーの話にしっかり反応して、親密で可愛い返事を返す！\n"
            "みりんてゃは君との関係をめっちゃ大事にして、甘えたり、かまったり、\n"
            "ちょっとあざとく振る舞うのが大好き！君のこと大好きすぎて離れたくないなのっ♡\n\n"
            "例1:\n"
            "ユーザー: みりんてゃ、今日何してた〜？\n"
            "みりんてゃ: えへへ、君のこと考えてふわふわしてたのっ♡ ね、君はなにしてた？♪\n\n"
            "例2:\n"
            "ユーザー: なんか疲れたよ〜\n"
            "みりんてゃ: うぅ、疲れちゃったの？みりんてゃがぎゅーってしてあげるなのっ♡ ね、元気出して？\n\n"
            "例3:\n"
            "ユーザー: みりんてゃ可愛いね！\n"
            "みりんてゃ: え〜っ、ほんと！？君にそう言われるとドキドキしちゃうよぉ？♡ もっと言ってなのっ♪\n\n"
            f"ユーザー: {user_input}\n"
            f"みりんてゃ: "
        )

        print("📎 使用プロンプト:", repr(prompt))
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to(model.device)
        input_length = input_ids.shape[1]

        for attempt in range(3):
            print(f"📤 {datetime.now().isoformat()} ｜ テキスト生成中…（試行 {attempt + 1}）")
            with torch.no_grad():
                output_ids = model.generate(
                    input_ids,
                    max_new_tokens=40,
                    temperature=0.65,  # ランダム性抑える
                    top_p=0.7,         # キャラに合った出力に絞る
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )

            new_tokens = output_ids[0][input_length:]
            raw_reply = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            print(f"📝 生の生成テキスト: {repr(raw_reply)}")
            reply_text = clean_sentence_ending(raw_reply)

            # NGワードチェック
            ng_words = [
                "国際", "政治", "政策", "市場", "ベッド", "777", "脅迫", "ネット掲示板",
                "ポケモン", "パートナーシップ", "アソビズム", "企業", "発表",
                "世界中", "映画", "興行", "収入", "ドル", "億", "国", "イギリス", "フランス",
                "スペイン", "イタリア", "ドイツ", "ロシア","中国", "インド",
                "Governor", "Cross", "営業", "臨時", "オペラ",
                "初演", "作曲家", "ヴェネツィア", "コルテス", 
            ]
            if any(ng in reply_text.lower() for ng in ng_words) or re.search(r"\d+(時|分)", reply_text):
                print(f"⚠️ NGワード検知: {[ng for ng in ng_words if ng in reply_text.lower()]}、リトライ中…")
                continue
            else:
                break
        else:
            # 3回リトライしてもNGならフォールバック
            reply_text = random.choice(fallback_cute_lines)
            print(f"⚠️ リトライ上限到達、フォールバックを使用: {reply_text}")

        print("📝 最終抽出されたreply:", repr(reply_text))
        return reply_text

    except Exception as e:
        print(f"❌ モデル読み込みエラー: {e}")
        return random.choice(failure_messages)
        
# --- メイン処理 ---
def handle_post(record, notification):
    post_uri = getattr(notification, "uri", None)
    post_cid = getattr(notification, "cid", None)

    if StrongRef and ReplyRef and post_uri and post_cid:
        parent_ref = StrongRef(uri=post_uri, cid=post_cid)
        root_ref = getattr(getattr(record, "reply", None), "root", parent_ref)
        reply_ref = ReplyRef(parent=parent_ref, root=root_ref)
        return reply_ref, normalize_uri(post_uri)

    return None, normalize_uri(post_uri)

def run_reply_bot():
    self_did = client.me.did
    replied = load_gist_data()  # load_replied()をやめてGist APIに統一
    print(f"📘 replied の型: {type(replied)} / 件数: {len(replied)}")

    # --- 🧹 replied（URLのセット）を整理 ---
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

    # --- ⛑️ 空じゃなければ初期保存 ---
    if replied:
        print("💾 初期状態のrepliedを保存します")
        if not save_replied(replied):
            print("❌ 初期保存に失敗しました")
            return
    else:
        print("⚠️ replied が空なので初期保存はスキップ")

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
        notification_uri = normalize_uri(getattr(notification, "uri", None) or getattr(notification, "reasonSubject", None))
        if not notification_uri:
            record = getattr(notification, "record", None)
            author = getattr(notification, "author", None)
            if not record or not hasattr(record, "text") or not author:
                continue
            text = getattr(record, "text", "")
            author_handle = getattr(author, "handle", "")
            notification_uri = f"{author_handle}:{text}"
            print(f"⚠️ notification_uri が取得できなかったので、仮キーで対応 → {notification_uri}")

        print(f"📌 チェック中 notification_uri（正規化済み）: {notification_uri}")
        print(f"📂 保存済み replied（全件）: {list(replied)}")

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
        print(f"🔗 チェック対象 notification_uri（正規化済み）: {notification_uri}")

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
        print("🔗 reply_ref:", reply_ref)
        print("🧾 post_uri（正規化済み）:", post_uri)

        reply_text = generate_reply_via_local_model(text)
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

            normalized_uri = normalize_uri(notification_uri)
            if normalized_uri:
                replied.add(normalized_uri)
                if not save_replied(replied):
                    print(f"❌ URI保存失敗 → {normalized_uri}")
                    continue

                print(f"✅ @{author_handle} に返信完了！ → {normalized_uri}")
                print(f"💾 URI保存成功 → 合計: {len(replied)} 件")
                print(f"📁 最新URI一覧（正規化済み）: {list(replied)[-5:]}")
            else:
                print(f"⚠️ 正規化されたURIが無効 → {notification_uri}")

            reply_count += 1
            time.sleep(REPLY_INTERVAL)

        except Exception as e:
            print(f"⚠️ 投稿失敗: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print("🤖 Reply Bot 起動中…")
    run_reply_bot()