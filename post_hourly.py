from atproto import Client
import os
from dotenv import load_dotenv
from datetime import datetime
import random
from pathlib import Path
import unicodedata

# .env 読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# 各時間帯の投稿メッセージ
HOUR_MESSAGES = {
    'morning': [
        "おはようのちゅ〜〜〜♡ #地雷女",
        "おはようのちゅ〜〜〜〜♡ #地雷女ですけど何か",
        "眠いけどがんばる…あたしえらい！ #自画自賛",
        """朝からかわいいって思ってくれたらうれしいな♡ 
        #自撮りあげちゃおうかな""",
        """朝のテンションってだいたい壊れてるよね〜♡ 
        #病みかわ""",
        "ふにゃ…おきたかも…？でも脳はまだ寝てる…",
        "起きたはいいけど…なにもしたくない日ってあるよね？",
        "今日も『かわいい』って言われたい人生だった♡",
        """おはよ♡今日はなんて呼ばれたい気分？ 
        #名前呼び選手権""",
    ],
    'afternoon': [
        "ひとりぼっちは慣れてるはずだったのに。 #病みかわ",
        "おなかすいた…だれかご飯連れてって？ #構って",
        "ねぇ、みんな何してるの？ ひとりだけど、ひとりじゃないフリしてる♡",
        """どっか遠くに行きたいな〜 
        #逃避行 #連れてって""",
        "LINE未読100件より、誰にも通知が来ないのがいちばんつらいよね♡",
        """ランチ誘ってくれたら秒で行くのに〜♡ 
        #構って #寂しがり屋""",
    ],
    'evening': [
        "夕焼けが綺麗だと、泣きたくなる。 #メンヘラ",
        "だれか構ってくれるまで、ずっと黙ってるもん（ﾁﾗｯﾁﾗｯ",
        "きいてきいて〜！みりんてゃ今日もかわいいの！（って言ってほしい）",
        "今日も一日がんばったね？ #自分を甘やかす",
        "オレンジ色の空を見ると、ちょっとだけ泣きたくなるよね♡",
        "夕方の風って、なんかさみしい。なんでだろうね♡",
        "帰り道、手をつなぐ相手がいないの、ばれちゃったかな？",
        "今日も『だいじょうぶ』って言いながら崩れてるよ♡",
    ],
    'night': [
        """さみしい夜に、おやすみのちゅ〜♡ 
        #夜のポエム""",
        "…え？まだ寝ないで？ もうちょっとだけ一緒にいよ？",
        """本音は、誰にも届かないって知ってる 
        #ひとりごと""",
        """夜は誰かに甘えたくなるよね？ 
        #夜のつぶやき""",
        """寝ても寝ても眠いのに、夜になると目が冴えるのなんで？ 
        #地雷系""",
        """かわいくなりたいのは、誰かの一番になりたいから 
        #共感したらRT #夜の独り言""",
        "♡おやすみのちゅーしてくれないと寝れないよぉ…^ᴗ.ᴗ^♡",
        """強がるのに疲れた夜は、誰かに見つけてほしい 
        #わかってほしい #さみしい夜に""",
        "こわい夢見た…ぎゅーってしてくれなきゃ寝れないの…",
        "誰かの特別になりたいって、欲張りかな？ #わかって",
        "『おやすみ』って言ってくれる人がほしいだけなのに。",
        "みりんがかわいいって言ってくれたら、今日も頑張れたのに♡",
        "夜になると『会いたい』が止まらない…♡",
        """好きって言われるたびに、嘘じゃないか確かめたくなるの 
        #病みかわ""",
        "消えたいんじゃなくて、ちょっとだけ休みたいだけなんだよ♡",
        """寝るの？でもちょっとだけ、もう少し話そ…？ 
#さみしんぼ""",
        """今日も生きててえらかった！でも…ひとりだと意味ないのかな 
#夜の情緒""",
        "だれもいないTLって…静かでこわいよね…",
        """いま、起きてるのって…運命？
それとも寂しさのせい？ 
#深夜テンション""",
        "おやすみ世界…みりてゃはまだ夢の中です…Zzz",
        "ぐーすか…（夢の中でもかわいくしてるの）",
    ],
}

# 現在の時間帯を判定（JST対応）
def get_time_period():
    hour = datetime.utcnow().hour + 9
    if 5 <= hour < 11:
        return "morning"
    elif 11 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 23:
        return "evening"
    else:
        return "night"

# テキスト正規化（全角などの統一）
def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# facets生成（UTF-8バイト位置でハッシュタグ対応）
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []

    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        byte_start = text_bytes.find(tag_bytes)

        if byte_start != -1:
            facets.append({
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_start + len(tag_bytes)
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#tag",
                    "tag": tag.lstrip("#")
                }]
            })

    return facets

# --- 実行 ---
def post_hourly_message():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    period = get_time_period()
    raw_message = random.choice(HOUR_MESSAGES[period])
    message = normalize_text(raw_message)

    hashtags = [word for word in message.split() if word.startswith("#")]
    facets = generate_facets_from_text(message, hashtags)

    client.send_post(
        text=message,
        facets=facets if facets else None,
    )

    print(f"[{period}] 投稿したよ: {message}")

# エントリーポイント
if __name__ == "__main__":
    post_hourly_message()