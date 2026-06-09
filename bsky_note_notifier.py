import os
import requests
import xml.etree.ElementTree as ET
import unicodedata
import re
import io
from bs4 import BeautifulSoup
from PIL import Image
from atproto import Client

# 🔑 環境変数から取得（GitHub Secretsに登録してね！）
# 💡 みつきのSecrets（HANDLE, APP_PASSWORD）の名前に完全に合わせました！これでエラーは消えます！
BSKY_HANDLE = os.environ.get("HANDLE")
BSKY_APP_PASSWORD = os.environ.get("APP_PASSWORD")

NOTE_RSS_URL = "https://note.com/mirin_chuuu/rss"

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

        title = (title["content"] if title and "content" in title.attrs else title.string) if title else "みりんてゃの研究日誌"
        description = description["content"] if description else "あたしの研究日誌だよっ♡"
        image_url = image["content"] if image else None

        thumb_blob = None
        if image_url:
            try:
                img_res = requests.get(image_url, timeout=10)
                if img_res.status_code == 200:
                    img = Image.open(io.BytesIO(img_res.content))
                    img.thumbnail((800, 800), Image.LANCZOS)
                    buffer = io.BytesIO()
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(buffer, format="JPEG", quality=85)
                    thumb_blob = client.com.atproto.repo.upload_blob(buffer.getvalue()).blob
            except Exception as e:
                print(f"⚠️ 画像リサイズエラー: {e}")

        external = {"uri": url, "title": title[:300], "description": description[:300]}
        if thumb_blob:
            external["thumb"] = thumb_blob
        return {"$type": "app.bsky.embed.external", "external": external}
    except Exception as e:
        print(f"⚠️ OGP生成エラー: {e}")
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

def main():
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        print("⚠️ ブルスカの認証情報が設定されていません。")
        return

    print("📡 noteのRSSから最新記事をチェック中...")
    try:
        res = requests.get(NOTE_RSS_URL)
        res.raise_for_status()
        
        # XML(RSS)を解析して一番上の記事を取得！
        root = ET.fromstring(res.content)
        latest_item = root.find(".//item")
        
        if not latest_item:
            print("💤 まだ記事が1件も投稿されていません。")
            return
            
        note_url = latest_item.find("link").text
        note_title = latest_item.find("title").text
        print(f"📖 最新記事を発見: {note_title} ({note_url})")
        
    except Exception as e:
        print(f"❌ RSSの取得に失敗しました: {e}")
        return

    print("🦋 Blueskyのタイムラインを確認中...")
    try:
        client = Client()
        client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
        
        # 自分の過去の投稿（最新15件）を取得する
        feed = client.get_author_feed(actor=BSKY_HANDLE, limit=100)
        
        already_posted = False
        for post in feed.feed:
            # 投稿のテキスト情報を取得
            text = getattr(post.post.record, 'text', '')
            # 過去の投稿の中に今回のnoteのURLが含まれているかチェック！
            if note_url in text:
                already_posted = True
                break

        if already_posted:
            print("👍 この記事はすでにブルスカにお知らせ済みだよ！何もしません！")
        else:
            print("✨ 新しい記事だ！ブルスカにお知らせを投稿します！")
            
            # 投稿メッセージを作成
            message = f"新しい研究日誌（note）を公開したよ〜🌸\n\n『{note_title}』\n\nぜひ読んでみてねっ♡\n{note_url}\n#みりんてゃ #note"
            message = unicodedata.normalize("NFKC", message).strip()

            # OGPとFacetsを生成
            embed = generate_embed_from_url(client, note_url)
            hashtags = [word for word in message.split() if word.startswith("#")]
            facets = generate_facets_from_text(message, hashtags)

            # ブルスカへ送信！
            client.send_post(text=message, facets=facets if facets else None, embed=embed)
            print("✅ ブルスカへのお知らせ投稿が完了しました！")
            
    except Exception as e:
        print(f"❌ Bluesky処理エラー: {e}")

if __name__ == "__main__":
    main()
