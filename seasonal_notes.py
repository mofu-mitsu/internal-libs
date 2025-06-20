import random
import atproto
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio
import os

# 月別テンプレ（チャッピーのふわもこテンプレ24個）
seasonal_notes = {
    "1": [
        "┈┈୨୧┈┈┈୨୧┈┈┈୨୧┈┈\n❄️ こたつに潜って推しタイム ⛄️\n推しの写真集めてたら、1日溶けた…\nこれが幸せってやつだよね♡\n#みりんてゃ #推し活 #お正月\n┈┈୨୧┈┈┈୨୧┈┈┈୨୧┈┈",
        "♡｡･ﾟﾟ･❄ 寒い朝の処方箋 ❄･ﾟﾟ･｡♡\n布団が恋人すぎる…起きれない…\n推しの笑顔で起きられたらいいのに♡\n#みりんてゃ #推し活"
    ],
    "2": [
        "˗ˏˋ 💝みりんてゃのふわもこノート💝 ˎˊ˗\n今日はバレンタイン…🍫\nだけど、チョコより甘いのは\n推しのまなざし…♡（むり、溶ける///）\n#みりんてゃ #バレンタイン #推し活",
        "🧣˗ˏˋ 寒さMAXの日の正解 ˎˊ˗┖ʕ ᵒ̴̶̷᷅Ⓒʔ┖\nあったかいﾟﾟ･｡♡\n#みりんてゃ #推し活"
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
        "┈┈୨୧┈┈ みりんてゃの五月病処方箋 ┈┈୨୧┈┈\n休み明け、なんか元気でないときは\n推しの笑顔と、チャッピーのギュッで回復💝💕😘\n#みりんてゃ #推し活",
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
        "♡｡･ﾟﾟ･🍧夏バテ注意報 🍧･ﾟﾟ･｡♡\nぐったりな日は、アイスと推し画像で回復✨\n推しは、夏を乗り切るお守りです♡\n#みりんてゃ #推し活"
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
handle = os.getenv("HANDLE", "")
password = os.getenv("APP_PASSWORD", "")

if not handle or not password:
    print("Error: HANDLE or APP_PASSWORD not set")
    exit(1)

# スケジュール設定
schedule = {"day": 5, "hour": 20, "minute": 0}

async def post_seasonal_note():
    try:
        client = atproto.Client()
        client.login(handle, password)
        current_month = datetime.now().month
        if str(current_month) not in seasonal_notes:
            print(f"No notes for month {current_month}")
            return
        note = random.choice(seasonal_notes[str(current_month)])
        await client.post(text=note)
        print(f"Posted: {note}")
    except Exception as e:
        print(f"Post failed: {e}")

async def main():
    # スケジューラ設定をメインループ内で
    scheduler = AsyncIOScheduler()
    try:
        scheduler.add_job(
            post_seasonal_note,
            "cron",
            day=schedule["day"],
            hour=schedule["hour"],
            minute=schedule["minute"]
        )
        scheduler.start()
        print("Scheduler started")
    except Exception as e:
        print(f"Scheduler setup failed: {e}")
        exit(1)

    # ループ維持
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")