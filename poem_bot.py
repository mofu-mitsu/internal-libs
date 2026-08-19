# poem_bot.py
import os
import random
import re
import json
import logging
import unicodedata
from datetime import datetime, timezone
from atproto import Client
from groq import Groq
from dotenv import load_dotenv
from text_limits import limit_graphemes

# 環境変数
load_dotenv()
HANDLE = os.environ.get("HANDLE")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# ------------------------------
# ★ Facets生成と文字正規化
# ------------------------------
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []
    
    # ハッシュタグの処理
    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append({
                "index": {
                    "byteStart": start,
                    "byteEnd": start + len(tag_bytes)
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#tag",
                    "tag": tag.lstrip("#")
                }]
            })
            
    # URL facets
    url_pattern = r'(https?://[^\s]+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        start = text_bytes.find(url.encode("utf-8"))
        if start != -1:
            facets.append({
                "index": {
                    "byteStart": start,
                    "byteEnd": start + len(url.encode("utf-8"))
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url
                }]
            })

    return facets

def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# ------------------------------
# ★ ポエム作成機能
# ------------------------------
def get_timeline_vibes(client):
    """ TLからみんなの「空気感」を読み取るよ """
    timeline = client.get_timeline(limit=30).feed
    all_text = ""
    for post_data in timeline:
        text = getattr(post_data.post.record, 'text', '')
        if len(text) > 5 and post_data.post.author.handle != HANDLE:
            all_text += text + "\n---\n"
    return all_text

def generate_mirin_poem_content(tl_content):
    """ Llamaにポエムの『中身だけ』を作ってもらうよ """
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = """
あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子。
あなたは今、大好きなフォロワーさんたちのタイムライン（TL）を眺めて、みんなの想いを受け取りました。

【TLの空気感】
{tl_content}

この空気感を元に、みんなの心に寄り添う「ポエム（詩）」を1つ書いて。
性格：感受性が豊か、ちょっと情緒不安定でポエミー、愛が重め。

【ルール】
・ポエムの『本文だけ』を出力して。
・140文字以内。TLの内容を具体的に説明するのではなく、その「感情」や「季節感」をすくい取って詩的に表現して。
・性格：感受性豊か、情緒不安定、愛が重め。
・口調：あざと可愛いタメ口（〜なのっ♡、〜だよぉ♪）。
"""
        response = groq_client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[{"role": "system", "content": system_prompt.format(tl_content=tl_content[:2000])}],
            max_tokens=150,
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Groqエラー: {e}")
        return "みんなの想い、ふわふわ届いたよ♡\nみりんてゃは、ずっとキミの味方なのっ♡"

def run_poem_bot():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    
    print("📜 TLの空気感を読み取り中...")
    vibes = get_timeline_vibes(client)
    
    print("✍️ ポエムを執筆中...")
    poem_body = generate_mirin_poem_content(vibes)
    
    # ------------------------------
    # ★ タイトルとタグをスクリプト側で合体！
    # ------------------------------
    title = "🎀 みりんてゃの、たそがれポエム 🎀"
    hashtag = "#みりんてゃポエム"
    
    # 全部まとめて正規化
    full_text = normalize_text(f"{title}\n\n{poem_body}\n\n{hashtag}")
    full_text = limit_graphemes(full_text)
    
    # Facets生成（タグを青くする）
    facets = generate_facets_from_text(full_text, [hashtag])
    
    print(f"📤 投稿します:\n{full_text}")
    client.send_post(text=full_text, facets=facets if facets else None)
    print("✅ 投稿完了！完璧なフォーマットだよ♡")

if __name__ == "__main__":
    run_poem_bot()
