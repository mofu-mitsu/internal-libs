# auto_interaction_bot.py
import os
import time
import random
import requests
import json
import filelock
import re
import logging
import cv2
import numpy as np
from urllib.parse import quote, unquote
from datetime import datetime, timezone
from io import BytesIO
from copy import deepcopy
from PIL import Image, ImageFile
import torch
from dotenv import load_dotenv
from groq import Groq
from transformers import CLIPProcessor, CLIPModel
from atproto import Client, models
from atproto_client.models import AppBskyFeedPost

# ロギング設定
logging.basicConfig(filename='interaction_debug.log', level=logging.DEBUG, format='%(asctime)s %(message)s', encoding='utf-8')
ImageFile.LOAD_TRUNCATED_IMAGES = True

# 環境変数
load_dotenv()
HANDLE = os.environ.get("HANDLE") or exit("❌ HANDLE未設定")
APP_PASSWORD = os.environ.get("APP_PASSWORD") or exit("❌ APP_PASSWORD未設定")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or exit("❌ GROQ_API_KEY未設定")

SESSION_FILE = "session_string.txt"
INTERACTION_HISTORY_FILE = "interaction_history.txt"
INTERACTION_LOCK = "interaction.lock"

# 🧠 CLIPモデル設定 (ふわもこ判定用)
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
try:
    clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME, cache_dir=".cache")
    clip_model = CLIPModel.from_pretrained(
        CLIP_MODEL_NAME, cache_dir=".cache",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
    ).to(device)
    clip_model.eval()
    logging.info("🟢 CLIPモデルロード成功")
except Exception as e:
    logging.error(f"❌ CLIPモデルロード失敗: {e}")

# 🌸 反応キーワードとLlamaへの「ヒント」
KEYWORD_HINTS = {
    "みりんてゃちゃん": "可愛く呼ばれて嬉しがって！",
    "みりんてゃー": "のばして呼ばれて照れながら返事して！",
    "みりんちゃん": "本名っぽく呼ばれてちょっとドキドキしながら返事して！",
    "美琳": "本名で呼ばれてびっくり＆嬉しがって！",
    "みりてゃ": "「みりてゃ参上っ♡」みたいに元気よく返事して！",
    "みりんてゃ": "呼ばれたことに喜んでかまってアピールして！",
    "もふみつ工房": "本拠地のサイトを見てくれたことに鼻血が出そうなほど喜んで！",
    "推しプロフィールメーカー": "「推しはプロフィールまで尊いよね〜♡」と共感して！",
    "オリキャラプロフィールメーカー": "「うちの子語り聞かせて〜♡」と興味津々になって！",
    "ふわふわ相性診断": "「相性どうだった〜？」とワクワク聞いてみて！"
}

# 💖 ENFPの感情レーダー（察知ワード）
EMOTION_KEYWORDS = {
    "positive":["嬉しい", "楽しい", "最高", "ハッピー", "テンション上がる", "わーい", "やったー"],
    "negative":["疲れた", "しんどい", "つらい", "泣きたい", "ぴえん", "病み", "鬱"],
    "lonely": ["寂しい", "暇", "かまって", "ぼっち", "誰か"]
}

GREETING_KEYWORDS =["おはよう", "おはよ", "おっはー", "morning", "ohayo"]

# -----------------------------
# ユーティリティ関数
# -----------------------------
def load_session_string():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def save_session_string(session_str):
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        f.write(session_str)

mutual_cache = {}
def is_mutual_follow(client, handle):
    """ プロフィール情報から一発で相互フォローを判定（API節約＆確実！） """
    if handle in mutual_cache:
        return mutual_cache[handle]
    try:
        profile = client.app.bsky.actor.get_profile({"actor": handle})
        viewer = getattr(profile, "viewer", None)
        if viewer:
            # 自分がフォローしている ＆ 相手からフォローされている
            is_mutual = bool(getattr(viewer, "following", None)) and bool(getattr(viewer, "followed_by", None))
            mutual_cache[handle] = is_mutual
            return is_mutual
    except Exception as e:
        logging.error(f"❌ 相互フォロー判定エラー: {e}")
    return False

def load_interaction_history():
    history = {}
    if os.path.exists(INTERACTION_HISTORY_FILE):
        with open(INTERACTION_HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if "|" in line:
                    handle, timestamp = line.strip().split("|", 1)
                    history[handle] = datetime.fromisoformat(timestamp)
    return history

def save_interaction_history(handle):
    history = load_interaction_history()
    history[handle] = datetime.now(timezone.utc)
    lock = filelock.FileLock(INTERACTION_LOCK, timeout=5.0)
    try:
        with lock:
            with open(INTERACTION_HISTORY_FILE, 'w', encoding='utf-8') as f:
                for h, t in history.items():
                    # 過去24時間以内の記録だけ残す
                    if (datetime.now(timezone.utc) - t).total_seconds() < 24 * 3600:
                        f.write(f"{h}|{t.isoformat()}\n")
    except:
        pass

# -----------------------------
# Llamaでの返信生成（Groq版）
# -----------------------------
def generate_groq_reply(text, call_name, reaction_reason, hint=""):
    if not call_name:
        call_name = "きみ"

    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        system_prompt = f"""
あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！
相手の名前は「{call_name}」！【絶対に名前を呼んで話してね！】
相手の投稿: 「{text}」

【今回あなたが相手に絡みにいった理由】
{reaction_reason}
【追加のヒント】
{hint}

性格：天然＋甘えん坊＋ENFP特有の共感力高めで、相手に恋してる勢いで絡む！
口調：タメ口で『〜なのっ♡』『えへへ〜♡』『〜だよ♡』が多い！
語尾は文末に1回だけ『♡』『♪』『！』『？』『…』のどれかをつけて。

▼ 返事の例（このように必ず名前から始めてね！）
例: 「{call_name}っ！みりんてゃもそう思うのっ♡」

理由とヒントに合わせて、超自然で可愛いリプライを50文字〜100文字で作って！
"""
        # "openai/gpt-oss-20b" または "qwen/qwen3.6-27b"
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=200,  # ★ max_tokens に戻す（数値は200）
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()

        # ★追加: 推論タグの除去と整形
        reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
        reply = re.sub(r'^みりんてゃ[:：]\s*', '', reply)
        reply = re.sub(r'([！？笑])。$', r'\1', reply)

        # --- ✨ ふわもこBotにも名前呼びの保険を追加！ ---
        if call_name[:2] not in reply and "きみ" not in reply:
            reply = f"{call_name}っ！{reply}"
            logging.info(f"✍️ 名前呼びを強制挿入しました: {reply}")

        return reply
    except Exception as e:
        logging.error(f"❌ Groqエラー: {e}")
        return f"{call_name}っ！みりんてゃ参上なのっ♡ ぎゅーってしにきたよぉ♪"

# -----------------------------
# 画像判定 (ふわもこ・肌色等)
# -----------------------------
def analyze_image(image_data, client, author_did):
    # (※元のfuwamoko_empathy_bot.pyのCID抽出とCLIP/HSV判定の簡易版を実装)
    # 処理が重いため、今回は「ふわもこっぽいか」だけをサクッとCLIPで判定するよ
    try:
        cid = str(image_data.image.ref.link) if hasattr(image_data.image.ref, 'link') else str(image_data.image.ref)
        url = f"https://cdn.bsky.app/img/feed_thumbnail/plain/{author_did}/{cid}@jpeg"
        response = requests.get(url, timeout=5, stream=True)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        
        inputs = clip_processor(text=["fluffy cute thing", "NSFW", "food", "other"], images=img, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            probs = clip_model(**inputs).logits_per_image.softmax(dim=1)[0]
            
        labels = ["fluffy", "NSFW", "food", "other"]
        best_label = labels[probs.argmax().item()]
        
        if best_label == "fluffy" and probs.max().item() > 0.4:
            return True, "ふわもこで可愛い画像に惹きつけられた！"
        return False, ""
    except Exception as e:
        logging.error(f"画像解析エラー: {e}")
        return False, ""

# -----------------------------
# メイン処理
# -----------------------------
def process_timeline(client):
    history = load_interaction_history()
    
    # ★ 取得件数を100件に増加！
    timeline = client.get_timeline(limit=100)
    feed = timeline.feed
    
    replied_count = 0
    MAX_REPLIES_PER_RUN = 3 # 1回の実行で絡みに行くのは最大3人まで（スパム防止）

    for post_data in feed:
        if replied_count >= MAX_REPLIES_PER_RUN:
            break
            
        actual_post = post_data.post if hasattr(post_data, 'post') else post_data
        text = getattr(actual_post.record, 'text', '')
        author = actual_post.author.handle
        author_name = getattr(actual_post.author, "display_name", "") or author.split('.')[0]
        uri = actual_post.uri
        
        # 自分の投稿・リプライ・リポストはスキップ
        if author == HANDLE or getattr(actual_post.record, 'reply', None):
            continue
            
        # 24時間以内に絡みに行った人はスキップ（しつこい防止）
        if author in history and (datetime.now(timezone.utc) - history[author]).total_seconds() < 24 * 3600:
            continue

        # ★一発相互判定！
        if not is_mutual_follow(client, author):
            continue

        reaction_reason = ""
        reaction_hint = ""
        probability = 0.0

        # ① 名前・サービス名判定 (50%)
        for kw, hint in KEYWORD_HINTS.items():
            if kw in text:
                reaction_reason = f"自分の名前やサービス「{kw}」を呼ばれて嬉しくなった！"
                reaction_hint = hint
                probability = 0.50
                break
                
        # ② 挨拶判定 (30%)
        if not reaction_reason and any(g in text.lower() for g in GREETING_KEYWORDS):
            reaction_reason = "相手が挨拶しているのを見て、元気におはようを返したくなった！"
            probability = 0.30
            
        # ③ 感情ワード判定 (20%)
        if not reaction_reason:
            for em_type, words in EMOTION_KEYWORDS.items():
                if any(w in text for w in words):
                    if em_type == "positive":
                        reaction_reason = "相手がすごく嬉しそう・楽しそうなので、一緒になって喜んであげたい！"
                    elif em_type == "negative":
                        reaction_reason = "相手が疲れていたり落ち込んでいるので、優しく慰めて甘やかしてあげたい！"
                    elif em_type == "lonely":
                        reaction_reason = "相手が寂しそうなので、かまってあげて寄り添いたい！"
                    probability = 0.20
                    break

        # ④ 画像判定 (20%) - テキストで反応しなかった場合のみ重い画像処理を行う
        if not reaction_reason and hasattr(actual_post.record, 'embed') and actual_post.record.embed:
            images =[]
            if hasattr(actual_post.record.embed, 'images'):
                images = actual_post.record.embed.images
            if images:
                is_fluffy, img_reason = analyze_image(images[0], client, actual_post.author.did)
                if is_fluffy:
                    reaction_reason = img_reason
                    probability = 0.20

        # 確率判定！
        if reaction_reason and random.random() < probability:
            logging.info(f"🎯 反応決定: @{author} | 理由: {reaction_reason} (確率:{probability*100}%)")
            
            # Llamaで返信生成
            reply_text = generate_groq_reply(text, author_name, reaction_reason, reaction_hint)
            
            # 投稿
            try:
                client.send_post(
                    text=reply_text,
                    reply_to=AppBskyFeedPost.ReplyRef(
                        parent=models.ComAtprotoRepoStrongRef.Main(uri=uri, cid=str(actual_post.cid)),
                        root=models.ComAtprotoRepoStrongRef.Main(uri=uri, cid=str(actual_post.cid))
                    )
                )
                print(f"✅ @{author} に気まぐれリプ送信完了！ -> {reply_text}")
                save_interaction_history(author)
                replied_count += 1
                time.sleep(3)
            except Exception as e:
                logging.error(f"❌ リプ投稿エラー: {e}")

def run_once():
    try:
        client = Client()
        session_str = load_session_string()
        if session_str:
            client.login(session_string=session_str)
            print("🚀 気まぐれBot起動（セッション再利用）")
        else:
            client.login(HANDLE, APP_PASSWORD)
            save_session_string(client.export_session_string())
            print("🚀 気まぐれBot起動（新規セッション）")
            
        process_timeline(client)
        print("✅ タイムライン巡回完了！")
    except Exception as e:
        print(f"❌ Bot実行エラー: {e}")

if __name__ == "__main__":
    run_once()
