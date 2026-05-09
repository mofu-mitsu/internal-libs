# poem_bot.py
import os
import random
import re
import json
import logging
from datetime import datetime, timezone
from atproto import Client
from groq import Groq
from dotenv import load_dotenv

# 環境変数
load_dotenv()
HANDLE = os.environ.get("HANDLE")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def get_timeline_vibes(client):
    """ TLからみんなの「空気感」を読み取るよ """
    timeline = client.get_timeline(limit=30).feed
    all_text = ""
    for post_data in timeline:
        text = getattr(post_data.post.record, 'text', '')
        # ボットの投稿や短すぎるのは除外
        if len(text) > 5 and post_data.post.author.handle != HANDLE:
            all_text += text + "\n---\n"
    return all_text

def generate_mirin_poem(tl_content):
    """ LlamaにTLの空気感を伝えてポエムを作ってもらうよ """
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = """
あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子。
あなたは今、大好きなフォロワーさんたちのタイムライン（TL）を眺めて、みんなの想いを受け取りました。

【みんなの今の空気感】
{tl_content}

この空気感を元に、みんなの心に寄り添う「ポエム（詩）」を1つ書いて。
性格：感受性が豊か、ちょっと情緒不安定でポエミー、愛が重め。
口調：あざと可愛いタメ口（〜なのっ♡、〜だもん、〜だよぉ♪）。

【ポエムのルール】
1. 140文字以内。
2. 最初に「🎀 みりんてゃの、たそがれポエム 🎀」というタイトルをつけて。
3. 最後に「#みりんてゃポエム」というハッシュタグをつけて。
4. TLの内容を具体的に説明するのではなく、その「感情」や「季節感」をすくい取って詩的に表現して。
"""
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt.format(tl_content=tl_content[:2000])}],
            max_tokens=200,
            temperature=0.9 # 少し高めにして創造性を出すよ
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"🎀 みりんてゃの、たそがれポエム 🎀\n\nみんなの想い、ふわふわ届いたよ♡\nうまく言葉にできないけど…\nみりんてゃは、ずっとキミの味方なのっ♡\n\n#みりんてゃポエム"

def run_poem_bot():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    
    print("📜 TLの空気感を読み取り中...")
    vibes = get_timeline_vibes(client)
    
    print("✍️ ポエムを執筆中...")
    poem = generate_mirin_poem(vibes)
    
    print(f"📤 投稿します:\n{poem}")
    client.send_post(text=poem)
    print("✅ 投稿完了！")

if __name__ == "__main__":
    run_poem_bot()
