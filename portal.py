from atproto import Client
import random
import os
from dotenv import load_dotenv
from pathlib import Path
import unicodedata
import re
import requests
from bs4 import BeautifulSoup
import io
from PIL import Image

# 環境変数読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# GASから送られてきたデータ（ストーリー更新時のみ存在）
STORY_TITLE = os.getenv('STORY_TITLE')
STORY_CHARS = os.getenv('STORY_CHARS')
STORY_TAG = os.getenv('STORY_TAG')

# ==========================================
# みりんてゃのポータル紹介メッセージ（ランダム用）
# ==========================================
PORTAL_MESSAGES =[
    # トップページ
    "とりの丘学園の公式ポータルサイトだよっ♡\n300人以上の生徒のプロフィールや、学園の秘密がたっぷり詰まってるの！遊びに来てね🐾\nhttps://mofu-mitsu.github.io/Torinooka_portal/ #とりの丘学園",
    
    # 生徒名簿（応援）
    "学園の生徒名簿はこちらっ！\nみんなの推しは見つかったかな？プロフから『応援する』ボタンでエールを送ってね♡\nもちろん、みりんてゃ（H2-2）への投票も待ってるよ🐾\nhttps://mofu-mitsu.github.io/Torinooka_portal/chara.html #とりの丘学園",
    
    "みんな、今月の人気ランキングはチェックした？👑\n推しキャラの順位を上げるには、名簿から毎日『応援する』を押すのがコツだよっ！\nhttps://mofu-mitsu.github.io/Torinooka_portal/chara.html #とりの丘学園",
    
    # 学校生活
    "とりの丘学園には『水兵部』や『航空部』みたいな変わった部活もあるんだよ！⚓✈️\nみんなはどの部活やシェアハウスが気になる？\nhttps://mofu-mitsu.github.io/Torinooka_portal/life.html #とりの丘学園",
    
    # コンテンツ（ミニゲーム）
    "ひまー？そんな時は『とりの丘ミニゲーム集』で遊んでみてっ！\nいちごメロンパン争奪戦や、のりおみくんのシャッター回避ゲーム…みりんてゃとのソリティア対決もあるよ♡\nhttps://mofu-mitsu.github.io/Torinooka_portal/games.html #とりの丘学園",
    
    # 掲示板
    "学園の自由掲示板だよっ！\nストーリーの感想とか、推しキャラへの愛を自由に叫んでね♡ みりんてゃもこっそり見てるかも…？🐾\nhttps://mofu-mitsu.github.io/Torinooka_portal/bulletin.html #とりの丘学園",
    
    # お手紙
    "生徒のみんなに匿名でお手紙が送れるポストがあるよっ💌\n質問や応援メッセージを送ったら、お返事がもらえるかも！？\nhttps://mofu-mitsu.github.io/Torinooka_portal/letters.html #とりの丘学園",
    
    # ストーリー
    "学園で起きた色んな事件や、みんなの日常の記録が読めちゃう『ストーリー』ページだよっ📖\nタグ検索もできるから、気になる話をチェックしてみてね♡\nhttps://mofu-mitsu.github.io/Torinooka_portal/story.html #とりの丘学園"
]

# --- OGP (リンクカード) 生成関数 ---
def generate_embed_from_url(client, url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find("meta", property="og:title") or soup.find("title")
        description = soup.find("meta", property="og:description")
        image = soup.find("meta", property="og:image")

        title = (title["content"] if title and "content" in title.attrs else title.string) if title else "とりの丘学園 ポータル"
        description = description["content"] if description else "300人以上のキャラが織りなす学園生活♡"
        image_url = image["content"] if image else None

        thumb_blob = None
        if image_url:
            try:
                img_res = requests.get(image_url, timeout=10)
                if img_res.status_code == 200:
                    # 容量削減のためリサイズ
                    img = Image.open(io.BytesIO(img_res.content))
                    img.thumbnail((800, 800), Image.LANCZOS)
                    buffer = io.BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG", quality=85)
                    thumb_blob = client.com.atproto.repo.upload_blob(buffer.getvalue()).blob
            except:
                pass

        external = {"uri": url, "title": title[:300], "description": description[:300]}
        if thumb_blob:
            external["thumb"] = thumb_blob
        return {"$type": "app.bsky.embed.external", "external": external}
    except:
        return None

# --- Facets (リンクやハッシュタグの青色化) ---
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets =[]
    
    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(tag_bytes)},
                "features":[{"$type": "app.bsky.richtext.facet#tag", "tag": tag.lstrip("#")}]
            })
            
    url_pattern = r'(https?://[^\s]+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        url_bytes = url.encode("utf-8")
        start = text_bytes.find(url_bytes)
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(url_bytes)},
                "features":[{"$type": "app.bsky.richtext.facet#link", "uri": url}]
            })
    return facets

def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# ==========================================
# ★ メイン実行処理
# ==========================================
def main():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    message = ""

    # GASからストーリー更新の合図が来ている場合（即時投稿）
    if STORY_TITLE:
        tag_str = f"#{STORY_TAG}" if STORY_TAG else ""
        message = f"🐾 新しい物語が学園史に刻まれたよっ！\n\n『{STORY_TITLE}』\n登場キャラ：{STORY_CHARS}\n\nポータルサイトで読んでみてね♡\nhttps://mofu-mitsu.github.io/Torinooka_portal/story.html\n#とりの丘学園 {tag_str}"
    else:
        # 定期実行の場合はランダムにポータルを紹介
        message = random.choice(PORTAL_MESSAGES)

    message = normalize_text(message)

    # URLがあればOGPカードを生成
    embed = None
    url_match = re.search(r'(https?://[^\s]+)', message)
    if url_match:
        embed = generate_embed_from_url(client, url_match.group(0))

    hashtags =[word for word in message.split() if word.startswith("#")]
    facets = generate_facets_from_text(message, hashtags)

    # Blueskyへ投稿！
    client.send_post(text=message, facets=facets if facets else None, embed=embed)
    print("🐾 ポスト完了だよっ！")

if __name__ == "__main__":
    main()
