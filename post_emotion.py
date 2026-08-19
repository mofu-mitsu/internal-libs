# post_emotion.py
from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from datetime import datetime
import re
from pytz import timezone
from groq import Groq
import random
import time

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
# ★ NGワードカウントと置換処理
# ------------------------------
def count_ng_words(poem):
    ng_words = [
        "プロフィール", "【", "美魔女", "商品", "ニュース", "応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "みりんてゃらしい文章で" * 2,
        "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン", "ホームページ",
        "記載", "注意事項", "規定", "承諾", "SNS", "送信", "応募方法", "書式",
        "未発表", "発表", "入選", "特典", "料理", "番組", "レシピ", "先生", "NHK", "にんじん"
    ]
    return sum(word in poem for word in ng_words)

def clean_poem(poem):
    ng_words = [
        "プロフィール", "【", "美魔女", "商品", "ニュース", "応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "みりんてゃらしい文章で" * 2,
        "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン", "ホームページ",
        "記載", "注意事項", "規定", "承諾", "SNS", "送信", "応募方法", "書式",
        "未発表", "発表", "入選", "特典", "料理", "番組", "レシピ", "先生", "NHK", "にんじん"
    ]
    if poem.count("いつも、") >= 3:
        return "みりんてゃ、ちょっと考えすぎちゃったみたい…お茶でも飲んで仕切り直すね☕️"
    if any(poem.strip().startswith(word) for word in ["投稿", "作品", "規定", "応募"]):
        return "みりんてゃ、ちょっと真面目すぎたかも…もう一回書き直してみるね🍵"
    if not poem.strip() or "お散歩" in poem:
        return "みりんてゃ、優しい風に誘われて詩を届けるよ…。そっと待っていてね♡"

    # 文っぽい区切りを正規表現でカウント
    sentences = re.split(r'[。！？♡♪]+', poem)
    if len(sentences) >= 4:
        cleaned_parts = ["。".join(sentences[:3]) + "…"]
        return cleaned_parts[0]

    for word in ng_words:
        poem = poem.replace(word, "○○")
    poem = re.sub(r'[。、！？♡♪]{2,}', lambda m: m.group(0)[0], poem)  # 連続句読点対策
    poem = re.sub(r'\n{2,}', '\n', poem)  # 連続改行対策
    return poem.strip()

# ------------------------------
# ★ ポエム生成（Groq版）
# ------------------------------
def generate_poem(weather, day_of_week, temp_min, temp_max, pop):
    fallback_poems = [
        "えへへ〜♡ みりんてゃ、空見てふわふわなのっ♪",
        "きみと一緒なら、どんな天気もキラキラだよ♡",
        "ふわふわ〜♡ みりんてゃ、きみに詩を贈るよ♪"
    ]

    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        prompt = f"{weather}の{day_of_week}、降水確率{pop}%、気温{temp_min}-{temp_max}℃。みりんてゃが空を見上げて、ふわっと浮かんだやさしい詩を一言でつぶやき、その続きをそっとつぶやく。"
        print(f"DEBUG: Prompt: {prompt}")

        system_prompt = (
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "性格：ちょっぴり天然、甘えん坊、依存気味で、ふwaふwaな詩を届けるよっ♡\n"
            "口調：タメ口で『〜なのっ♡』『〜よぉ？♪』『えへへ〜♡』が特徴！二人称は『きみ』のみ！\n"
            "役割：天気と曜日を元に、短くやさしい詩をつぶやく。1文目は短い一言（天気や曜日は含めない）、2文目でそっと続ける。長さは50文字以内。\n"
            "禁止：ニュース、政治、ビジネス、固有名詞（国、企業、場所など）、性的・過激な表現はNG！\n"
            "注意：以下のワードは絶対禁止→「政府」「協定」「韓国」「外交」「経済」「契約」「軍事」「情報」「外相」「更新」「ちゅぱ」「ペロペロ」「ぐちゅ」「ぬぷ」「ビクビク」「お前」「あなた」\n"
            "例：雷の土曜日。そっときみを想うよ…♡"
        )

        for attempt in range(3):
            print(f"📤 {datetime.now(timezone('Asia/Tokyo')).isoformat()} ｜ Groq API呼び出し中…（試行 {attempt + 1}）")
            try:
                response = groq_client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.6,
                    top_p=0.9
                )
                generated_poem = response.choices[0].message.content.strip()
                print(f"DEBUG: Raw Output: {generated_poem}")

                # NGワードチェックとクリーニング
                cleaned_poem = clean_poem(generated_poem)
                print(f"DEBUG: After clean_poem: {cleaned_poem}")

                if count_ng_words(cleaned_poem) > 2:
                    print(f"DEBUG: NG words count > 2 - Poem: {cleaned_poem}, Count: {count_ng_words(cleaned_poem)}")
                    return random.choice(fallback_poems)

                if not cleaned_poem.strip():
                    print(f"DEBUG: Poem is empty or whitespace only - Poem: {cleaned_poem}")
                    return random.choice(fallback_poems)

                # 詩の形式チェック（1文目短く、2文目で続ける）
                sentences = re.split(r'[。！？♡♪]', cleaned_poem)
                sentences = [s.strip() for s in sentences if s.strip()]
                print(f"DEBUG: Sentence split: {sentences}")
                if len(sentences) < 2:
                    print(f"DEBUG: Invalid poem format: Too few sentences - Poem: {cleaned_poem}")
                    return random.choice(fallback_poems)
                if len(sentences[0]) > 30:
                    print(f"DEBUG: Invalid poem format: First sentence too long - Poem: {cleaned_poem}")
                    return random.choice(fallback_poems)

                print(f"DEBUG: Final Poem: {cleaned_poem}")
                with open("poem_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now(timezone('Asia/Tokyo'))}: {cleaned_poem}\n")
                return cleaned_poem

            except Exception as gen_error:
                print(f"⚠️ 生成エラー: {gen_error}")
                if "rate limit" in str(gen_error).lower():
                    print(f"⏳ レートリミット検知、{2 * (attempt + 1)}秒待機")
                    time.sleep(2 * (attempt + 1))
                continue
        else:
            print(f"⚠️ リトライ上限到達、フォールバックを使用")
            return random.choice(fallback_poems)

    except Exception as e:
        print(f"❌ Groq APIエラー: {e}")
        return random.choice(fallback_poems)

# ------------------------------
# ★ 天気取得
# ------------------------------
WEATHER_KEYWORDS = {
    "雷": "雷",
    "風": "風",
    "雪": "雪",
    "雨": "雨",
    "晴": "晴れ",
    "曇": "くもり",
    "くもり": "くもり"
}

def get_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    try:
        response = requests.get(url)
        print(f"DEBUG: Weather API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # 東京地方（code: 130010）のみ選択
            areas = data[0]["timeSeries"][0]["areas"]
            selected_area = next((area for area in areas if area["area"]["code"] == "130010"), None)
            if not selected_area:
                print(f"⚠️ 東京地方(code: 130010)が見つかりません")
                return "くもり", "東京地方", "不明", "不明", "不明"

            area_name = selected_area["area"]["name"]
            text = selected_area["weathers"][0].lower()
            print(f"DEBUG: Selected area: {area_name}, Raw weather data: {text}")

            # 降水確率
            pop = data[0]["timeSeries"][1]["areas"][areas.index(selected_area)]["pops"][1]

            # 気温（timeSeries[2]から取得）
            temp_data = next(
                (a for a in data[0]["timeSeries"][2]["areas"] if a["area"]["code"] == "44132"),  # 東京(code: 44132)
                None
            )
            temp_min = temp_data["temps"][0] if temp_data and "temps" in temp_data else "不明"
            temp_max = temp_data["temps"][1] if temp_data and "temps" in temp_data else "不明"
            print(f"DEBUG: POP: {pop}%, Temp: {temp_min}-{temp_max}℃")

            for keyword, label in WEATHER_KEYWORDS.items():
                if keyword in text:
                    return label, area_name, pop, temp_min, temp_max
            return "くもり", area_name, pop, temp_min, temp_max
        else:
            print(f"⚠️ Weather APIエラー: {response.status_code}")
            return "くもり", "東京地方", "不明", "不明", "不明"
    except Exception as e:
        print(f"❌ Weather APIエラー: {e}")
        return "くもり", "東京地方", "不明", "不明", "不明"

# ------------------------------
# ★ 曜日取得
# ------------------------------
def get_day_of_week(now):
    days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    return days[now.weekday()]

# ------------------------------
# ★ 認証と投稿
# ------------------------------
def main():
    try:
        client = Client()
        print(f"DEBUG: Attempting login with HANDLE: {HANDLE}")
        client.login(HANDLE, APP_PASSWORD)
        print(f"DEBUG: Login successful")

        now = datetime.now(timezone('Asia/Tokyo'))
        weather, area, pop, temp_min, temp_max = get_weather()
        day_of_week = get_day_of_week(now)
        message = generate_poem(weather, day_of_week, temp_min, temp_max, pop)

        # 東京スポットor埼玉スポットを選択
        tokyo_spots = ["渋谷", "新宿", "池袋", "原宿", "秋葉原", "歌舞伎町"]
        saitama_spots = ["大宮", "川越", "所沢"]
        if random.random() < 0.1:  # 10%で埼玉
            spot = random.choice(saitama_spots)
            print(f"DEBUG: Selected spot: {spot} (Saitama)")
        else:  # 90%で東京
            spot = random.choice(tokyo_spots)
            print(f"DEBUG: Selected spot: {spot} (Tokyo)")
        message = f"{spot}の{weather}の{day_of_week}。{message}"

        client.send_post(text=message)
        print(f"DEBUG: Posted message: {message}")
        print(f"投稿しました: {message}")

    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        with open("poem_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone('Asia/Tokyo'))}: エラー - {str(e)}\n")

if __name__ == "__main__":
    print("🤖 Emotion Bot 起動中…")
    main()
