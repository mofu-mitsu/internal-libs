import requests

# API設定
APP_ID = "1055088369869282145"
AFFILIATE_ID = "3d94ea21.0d257908.3d94ea22.0ed11c6e"
API_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"

# パラメータ
params = {
    "applicationId": APP_ID,
    "keyword": "推し活グッズ",
    "hits": 10,  # 取得件数
    "format": "json"
}

# APIリクエスト
response = requests.get(API_URL, params=params)
data = response.json()

# 結果確認
if data["Items"]:
    item = data["Items"][0]["Item"]
    product_url = item["itemUrl"]
    affiliate_link = f"https://hb.afl.rakuten.co.jp/hgc/{AFFILIATE_ID}/?pc={product_url}"
    print(f"商品名: {item['itemName']}")
    print(f"リンク: {affiliate_link}")
else:
    print("商品が見つかりませんでした…")

# みりんてゃ風返信（仮）
keyword = "推し活捗るやつ！"
if "推し活" in keyword:
    reply = f"神アクスタケース、これ使ってる人多いっぽ！→ {affiliate_link}"
    print(reply)