# post_trend.py
from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import re
from pytz import timezone
from groq import Groq
import random
import time
from pytrends.request import TrendReq  # Google Trends

# ------------------------------
# 🔐 環境変数
# ------------------------------
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
HANDLE = os.getenv('HANDLE') or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv('APP_PASSWORD') or exit("❌ APP_PASSWORDが設定されていません")
GROQ_API_KEY = os.getenv('GROQ_API_KEY') or exit("❌ GROQ_API_KEYが設定されていません")

print(f"✅ 環境変数読み込み完了: HANDLE={HANDLE[:8]}...")
print(f"🔑 GROQ_API_KEY: {repr(GROQ_API_KEY)[:8]}...")

# ------------------------------
# ★ 気分ラベルリスト（みりんてゃ風）
# ------------------------------
MOOD_LABELS = [
    "ねむねむ", "ふわふわ", "ドキドキ", "ぽかぽか", "えへへ", "きゅんきゅん",
    "もやもや", "うきうき", "しんみり", "わくわく", "すやすや", "ほんわか"
]

# ------------------------------
# ★ NGワードカウントと置換処理
# ------------------------------
def count_ng_words(poem):
    ng_words = [
        "プロフィール", "【", "美魔女", "商品", "ニュース", "応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン",
        "政府", "協定", "韓国", "外交", "経済", "契約", "軍事", "情報", "外相", "更新",
        "選挙", "政治", "投票", "政策", "戦争", "テロ", "犯罪", "逮捕", "死", "殺"
    ]
    return sum(word in poem for word in ng_words)

def clean_poem(poem):
    if poem.count("いつも、") >= 3:
        return "みりんてゃ、ちょっと考えすぎちゃったみたい…お茶でも飲んで仕切り直すね☕️"
    if any(poem.strip().startswith(word) for word in ["投稿", "作品", "規定", "応募", "ニュース"]):
        return "みりんてゃ、ちょっと真面目すぎたかも…もう一回書き直してみるね🍵"
    if not poem.strip():
        return "みりんてゃ、ふわふわな気持ちが言葉にならなくて…そっと待っててね♡"

    # 文っぽい区切りを正規表現でカウント（長めOKなので制限緩め）
    sentences = re.split(r'[。！？♡♪]+', poem)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 6:  # 長すぎたらカット
        cleaned_parts = ["。".join(sentences[:4]) + "…"]
        poem = cleaned_parts[0]

    # NGワード置換
    ng_words = [
        "プロフィール", "【", "美魔女", "商品", "ニュース", "応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン",
        "政府", "協定", "韓国", "外交", "経済", "契約", "軍事", "情報", "外相", "更新",
        "選挙", "政治", "投票", "政策", "戦争", "テロ", "犯罪", "逮捕", "死", "殺"
    ]
    for word in ng_words:
        poem = poem.replace(word, "○○")

    # 連続句読点・改行対策
    poem = re.sub(r'[。、！？♡♪]{2,}', lambda m: m.group(0)[0], poem)
    poem = re.sub(r'\n{2,}', '\n', poem)
    poem = poem.strip()

    # 100文字以内に強制カット（保険）
    if len(poem) > 100:
        poem = poem[:97] + "…"

    return poem

# ------------------------------
# ★ 最終最終兵器：getdaytrendsクラス名対応版（2025年11月最新）
# ------------------------------
def get_trend_word():
    fallback_words = ["ふわふわ", "きらきら", "ドキドキ", "えへへ", "なのっ"]
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://getdaytrends.com/japan/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        trends = []
        
        # ★2025年11月最新クラス名★
        # <a href="/trend/..."><strong>トレンド名</strong></a> の中
        for a in soup.find_all('a', href=lambda h: h and h.startswith('/trend/')):
            strong = a.find('strong')
            if strong:
                text = strong.get_text(strip=True)
                if text and 2 <= len(text) <= 25:
                    trends.append(text)
        
        # それでもダメなら旧クラス名も試す（保険）
        if not trends:
            for div in soup.find_all('div', class_='trend-card'):
                h3 = div.find('h3')
                if h3:
                    text = h3.get_text(strip=True)
                    if text and 2 <= len(text) <= 25:
                        trends.append(text)
        
        if not trends:
            raise Exception("トレンド本当に空っぽ…")
            
        word = random.choice(trends[:10])  # 上位10からランダム
        print(f"✅ getdaytrends日本トレンドGET: {word}")
        return word
        
    except Exception as e:
        print(f"⚠️ 全部ダメ…フォールバック: {e}")
        return random.choice(fallback_words)
# ------------------------------
# ★ 気分ラベル取得
# ------------------------------
def get_mood():
    mood = random.choice(MOOD_LABELS)
    print(f"🎭 今日の気分: {mood}")
    return mood

# ------------------------------
# ★ ポエム生成（Groq Llama + 気分反映）
# ------------------------------
def generate_poem(trend_word, mood):
    fallback_poems = [
        f"「{mood}」で『{trend_word}』見つけたのっ…♡",
        f"えへへ〜♡ 『{trend_word}』って、{mood}な気持ちになるよね♪",
        f"『{trend_word}』が流行ってるの？ {mood}なみりんてゃも気になるな…♡"
    ]

    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        prompt = f"今日の気分は「{mood}」、トレンドワードは『{trend_word}』。みりんてゃがそれを見て、ふわっと浮かんだやさしい反応を短くつぶやく。"

        system_prompt = (
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "性格：天然、甘えん坊、依存気味で、ふわふわな世界観♡\n"
            "口調：タメ口で『〜なのっ♡』『〜よぉ？♪』『えへへ〜♡』が特徴！二人称は『きみ』のみ！\n"
            "役割：今の気分とトレンドワードを絡めて可愛く反応。1文目で両方に触れて、2〜3文でそっと続ける。全体で100文字以内。\n"
            "例：「ねむねむ」な朝に『寒波』って言葉見つけて…きみのぬくもり、恋しいな♡\n"
            "禁止：ニュース、政治、ビジネス、固有名詞（国・企業・人名など）、性的・過激な表現は絶対NG！\n"
            "注意：以下のワードは禁止→「政府」「選挙」「戦争」「死」「殺」「犯罪」「逮捕」「ちゅぱ」「ペロペロ」「お前」「あなた」"
        )

        for attempt in range(3):
            print(f"📤 {datetime.now(timezone('Asia/Tokyo')).isoformat()} ｜ Groq呼び出し中…（試行 {attempt + 1}）")
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=80,
                    temperature=0.7,
                    top_p=0.9
                )
                generated_poem = response.choices[0].message.content.strip()
                print(f"DEBUG: Raw Output: {generated_poem}")

                cleaned_poem = clean_poem(generated_poem)
                print(f"DEBUG: Cleaned: {cleaned_poem}")

                if count_ng_words(cleaned_poem) > 1:
                    print(f"NGワード多すぎ: {count_ng_words(cleaned_poem)}")
                    return random.choice(fallback_poems)

                if len(cleaned_poem) > 100 or len(cleaned_poem) < 10:
                    print(f"長さ不適: {len(cleaned_poem)}文字")
                    return random.choice(fallback_poems)

                # 最低2文あるかチェック
                sentences = re.split(r'[。！？♡♪]', cleaned_poem)
                sentences = [s.strip() for s in sentences if s.strip()]
                if len(sentences) < 2:
                    return random.choice(fallback_poems)

                with open("trend_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now(timezone('Asia/Tokyo'))}: [気分: {mood}] [トレンド: {trend_word}] {cleaned_poem}\n")
                return cleaned_poem

            except Exception as gen_error:
                print(f"⚠️ 生成エラー: {gen_error}")
                if "rate limit" in str(gen_error).lower():
                    wait = 3 * (attempt + 1)
                    print(f"⏳ レートリミット、{wait}秒待機")
                    time.sleep(wait)
                continue
        else:
            print(f"⚠️ リトライ上限、フォールバック")
            return random.choice(fallback_poems)

    except Exception as e:
        print(f"❌ Groqエラー: {e}")
        return random.choice(fallback_poems)

# ------------------------------
# ★ メイン処理
# ------------------------------
def main():
    try:
        client = Client()
        print(f"DEBUG: ログイン試行: {HANDLE}")
        client.login(HANDLE, APP_PASSWORD)
        print(f"DEBUG: ログイン成功")

        trend_word = get_trend_word()
        mood = get_mood()
        poem = generate_poem(trend_word, mood)

        # メッセージ構成：気分＋トレンド＋反応
        message = f"「{mood}」で『{trend_word}』見つけたのっ。{poem}"

        client.send_post(text=message)
        print(f"投稿完了: {message}")

    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        with open("trend_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone('Asia/Tokyo'))}: エラー - {str(e)}\n")

if __name__ == "__main__":
    print("🤖 トレンドBot（気分ラベル付き）起動中…")
    main()