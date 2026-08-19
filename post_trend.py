# post_trend.py
from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import re
import unicodedata  # ←標準import！
from pytz import timezone
from groq import Groq
import random
import time
# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

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
    "もやもや", "うきうき", "しんみり", "わくわく", "すやすや", "ほんわか",
    "にこにこ", "るんるん", "むにゃむにゃ", "きらきら", "ぴょんぴょん",
    "とろとろ", "はぴはぴ", "くすくす", "ふにゃふにゃ", "ぽよぽよ",
    "ゆめゆめ", "もちもち", "ぷにぷに", "さらさら", "つやつや",
    "ひゅんひゅん", "ころころ", "ぺたんこ", "ふあふあ"
]

# ------------------------------
# ★ NGワードカウントと置換処理
# ------------------------------
def count_ng_words(poem):
    ng_words = [
        "プロフィール", "【", "美魔女", "商品","応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン",
        "政府", "協定", "外交", "経済", "契約", "軍事", "情報", "外相", "更新",
        "選挙", "政治", "投票", "政策", "戦争", "テロ", "犯罪", "逮捕", "死", "殺"
    ]
    return sum(word in poem for word in ng_words)

def clean_poem(poem):
    if poem.count("いつも、") >= 3:
        return "みりんてゃ、ちょっと考えすぎちゃったみたい…お茶でも飲んで仕切り直すね☕️"
    if any(poem.strip().startswith(word) for word in ["作品", "規定", "応募"]):
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
        "プロフィール", "【", "美魔女", "商品", "応募規約",
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
    if len(poem) > 120:
        poem = poem[:117] + "…"

    return poem

def get_trend_word():
    fallback_words = ["ふわふわ", "きらきら", "ドキドキ", "えへへ", "なのっ"]
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://getdaytrends.com/japan/")
        
        # ★ツール解析神待ち★ テーブル完全出現まで待機
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tr td a[href*='/japan/trend/']"))
        )
        time.sleep(2)  # 保険待ち

        trends = []
        # ★ツール解析神セレクタ★ <td><a href="/japan/trend/...">#それスノ</a></td>
        for a in driver.find_elements(By.CSS_SELECTOR, "table tr td a[href*='/japan/trend/']"):
            text = a.text.strip()
            if text.startswith("#") and 3 <= len(text) <= 30:
                trends.append(text)

        driver.quit()

        if len(trends) < 5:
            raise Exception(f"トレンド少なすぎ: {len(trends)}個 → {trends}")

        word = random.choice(trends[:10])
        print(f"✅ ツール解析神トレンドGET: {word} (総数: {len(trends)})")
        return word

    except Exception as e:
        print(f"⚠️ トレンドエラー: {e}")
        return random.choice(fallback_words)
# ------------------------------
# ★ 青ハッシュタグ facets生成
# ------------------------------
def generate_facets(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []
    for tag in hashtags:
        full_tag = f"#{tag.replace('#', '')}"
        tag_bytes = full_tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(tag_bytes)},
                "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag.replace('#', '')}]
            })
    return facets

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
        f"『{trend_word}』が流行ってるの？ {mood}なみりんてゃも気になるな…♡",
        f"「{mood}」な今日、『{trend_word}』見てふわふわしちゃった…きみも一緒に{mood}になろ♡",
        f"えへへ〜♡ 『{trend_word}』が{mood}な香りで包んでくれて…きみとシェアしたいな♪",
        f"{mood}なみりんてゃ、『{trend_word}』にきゅんってなっちゃった…きみも感じてみて？♡"
    ]

    try:
        # ★groq 0.11.0+ 対応（proxies削除）
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
                    model="openai/gpt-oss-120b",
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
# ★ メイン（青タグ対応）
# ------------------------------
def main():
    try:
        client = Client()
        client.login(HANDLE, APP_PASSWORD)

        trend_word = get_trend_word()  # 自動取得
        mood = random.choice(MOOD_LABELS)
        poem = generate_poem(trend_word, mood)

        # トレンドからタグ名抽出（#を除く）
        tag_name = trend_word.replace('#', '').replace(' ', '')

        trend_display = trend_word.replace('#', '')  # #抜き！

        message = (
            f"「{mood}」で『{trend_display}』見つけたのっ。\n"
            f"{poem}\n"
            f"#{tag_name}"  # 最後に#だけ！
        )

        # 正規化
        normalized_text = unicodedata.normalize("NFKC", message)

        # facets生成
        facets = generate_facets(normalized_text, [tag_name])

        # 投稿（facets付きで青タグ！）
        client.send_post(
            text=normalized_text,
            facets=facets if facets else None
        )
        print(f"投稿完了:\n{message}")

    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()