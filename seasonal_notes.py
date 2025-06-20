import random
import atproto
from datetime import datetime
import os
import asyncio
import re

# ハッシュタグとURLのfacets生成
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []
    # ハッシュタグのfacets
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
    # URLのfacets
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

# 季節テンプレ（全12か月、24個）
seasonal_notes = {
    "1": [
        "┈┈୨୧┈┈┈୨୧┈┈┈୨୧┈┈\n❄️ こたつに潜って推しタイム ⛄️\n推しの写真集めてたら、1日溶けた…\nこれが幸せってやつだよね♡\n#みりんてゃ #推し活 #お正月\n┈┈୨୧┈┈┈୨୧┈┈┈୨୧┈┈",
        "♡｡･ﾟﾟ･❄ 寒い朝の処方箋 ❄･ﾟﾟ･｡♡\n布団が恋人すぎる…起きれない…\n推しの笑顔で起きられたらいいのに♡\n#みりんてゃ #推し活"
    ],
    "2": [
        "˗ˏˋ 💝みりんてゃのふわもこノート💝 ˎˊ˗\n今日はバレンタイン…🍫\nだけど、チョコより甘いのは\n推しのまなざし…♡（むり、溶ける///）\n#みりんてゃ #バレンタイン #推し活",
        "🧣˗ˏˋ 寒さMAXの日の正解 ˎˊ˗🧸\nあったかい飲み物＋毛布＋推しの動画＝最強\n冬を乗りきる、ふわもこ三銃士♡\n#みりんてゃ #推し活"
    ],
    "3": [
        "┈┈🌸卒業ノート by みりんてゃ🌸┈┈\n卒業ってちょっと泣けるよね…\nでも、推しがそばにいるから寂しくないよ♡\n#みりんてゃ #春ポエム",
        "˗ˏˋ 🤧花粉症と推し尊 🤧 ˎˊ˗\n花粉で泣いてるのか、推しで泣いてるのか…\nもうどっちでもいいや、って日あるよねw\n#みりんてゃ #ふわもこ苦悩"
    ],
    "4": [
        "♡🌸新生活ノート🌸♡\n環境の変化でドキドキしてるキミへ\n深呼吸して、推しの声を思い出して？♡\n#みりんてゃ #入学 #推し活",
        "˗ˏˋ 桜と推し ˎˊ˗🌸\n花びらの中に推しがいる気がして\nふと、立ち止まっちゃう春なんだ…\n#みりんてゃ #桜ポエム"
    ],
    "5": [
        "┈┈୨୧┈┈ みりんてゃの五月病処方箋 ┈┈୨୧┈┈\nおやすみ明け、心がどんよりする時あるよね…\nそんな時は、推しにギュッてされる妄想で、ちょっとずつ回復しよ♡\n#みりんてゃ #ふわもこ #五月病",
        "˗ˏˋ 🌿初夏のお部屋活🌿 ˎˊ˗\n気持ちいい風、でも今日は引きこもりDay\n推し鑑賞会って、永遠に終わらなくて良くない？\n#みりんてゃ #ふわもこ"
    ],
    "6": [
        "♡☔梅雨だるノート☔♡\n雨の日は…気分も重たくなりがち…\nでもね、しっとり妄想モードは捗るのだ♡\n#みりんてゃ #梅雨",
        "˗ˏˋ 湿気と情緒のバトル ˎˊ˗💭\nじめじめした日は、推しの声と深呼吸\nそれだけでちょっとラクになれるから♡\n#みりんてゃ #推し活"
    ],
    "7": [
        "┈┈୨୧┈┈ 熱中症注意報 ┈┈୨୧┈┈\n推しに会うためにも、水分補給わすれずに♡\n倒れたら推しに心配されちゃうぞ〜？\n#みりんてゃ #夏バテ",
        "˗ˏˋ 🐬夏は推しと生きのびる ˎˊ˗\n推しのうちわ持って、アイス食べて\n無理しない夏を過ごそうね♡\n#みりんてゃ #夏ポエム"
    ],
    "8": [
        "🎆˗ˏˋ 夏夜ノート ˎˊ˗🎇\n花火見ながら、推しとデートしてる妄想中…\n現実じゃなくても、それが幸せ♡\n#みりんてゃ #夏 #妄想デート",
        "┈┈୨୧ 推し脳内、冷凍保存中 ❄️୨୧┈┈\nぐったりな日は、アイスと推し画像で回復✨\nむり…推し尊すぎて脳がとける…ʷʷʷ\n#みりんてゃ #推し活"
    ],
    "9": [
        "🍂˗ˏˋ 秋風と推し ˎˊ˗🍁\n夜風に吹かれながら、推しの声を思い出す…\nセンチな夜も悪くないかも♡\n#みりんてゃ #秋ポエム",
        "┈┈୨୧┈┈ 秋のはじまりノート ┈┈୨୧┈┈\n秋って、どこか寂しくなるけど\nそれすらも美しく感じるのは…推しのせい？♡\n#みりんてゃ #秋"
    ],
    "10": [
        "˗ˏˋ 🎃推しにTrick or Treat🎃 ˎˊ˗\nハロウィンは、推しの仮装妄想が止まらない！\n妄想コスプレ大会、開幕♡\n#みりんてゃ #ハロウィン",
        "♡🧸衣替えノート🧣♡\n寒くなってきたね〜\nふわもこパーカー着て、ぬくぬく推し活しよ？\n#みりんてゃ #推し活"
    ],
    "11": [
        "🍁˗ˏˋ 落ち葉と推し ˎˊ˗🍂\nカサカサ音を聞くたびに、\n推しのこと思い出すの、なんでだろう…♡\n#みりんてゃ #秋",
        "♡｡･ﾟﾟ･⛄体調管理ノート⛄･ﾟﾟ･｡♡\n寒暖差つらい日は、推しの声で温まって？\n心もふわもこに包んでね♡\n#みりんてゃ #ふわもこケア"
    ],
    "12": [
        "🎄˗ˏˋ キラキライルミ妄想 ˎˊ˗✨\n街が光ると、推しが一緒に歩いてる気がする…\nそんな妄想で今日も頑張れた♡\n#みりんてゃ #クリスマス",
        "♡❄️年末ノート❄️♡\n今年もよく頑張ったね！\n推しと過ごす妄想年越しで、心リセットしよ♡\n#みりんてゃ #年末ケア"
    ]
}

# 環境変数から認証情報取得
handle = os.getenv("HANDLE")
password = os.getenv("APP_PASSWORD")

if not handle or not password:
    print("環境変数（HANDLE, APP_PASSWORD）が設定されてないよ")
    exit(1)

async def post_note():
    try:
        client = atproto.Client()
        client.login(handle, password)  # 同期関数
        current_month = str(datetime.now().month)
        if current_month not in seasonal_notes:
            print(f"テンプレが未設定の月: {current_month}")
            return
        note = random.choice(seasonal_notes[current_month])
        # ハッシュタグを抽出
        hashtags = re.findall(r'#\w+', note)
        facets = generate_facets_from_text(note, hashtags)
        client.post(text=note, facets=facets)  # 同期関数、facets追加
        print("✅ 投稿完了:", note)
    except Exception as e:
        print(f"投稿失敗: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(post_note())