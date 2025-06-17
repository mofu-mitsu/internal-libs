from atproto import Client
import json
import os

# BlueSkyログイン
client = Client()
client.login(os.getenv("BSKY_USERNAME"), os.getenv("BSKY_PASSWORD"))

# 前回のチェック時刻を保存するファイル
LAST_CHECK_FILE = "last_check.json"

def get_new_dms():
    notifications = client.app.bsky.notification.list_notifications()
    new_dms = []
    last_check = load_last_check()

    for notif in notifications:
        if notif.record_type == "chat.message" and notif.created_at > last_check:
            new_dms.append({
                "sender": notif.author.handle,
                "content": notif.record.text,
                "time": notif.created_at
            })

    # 最新のチェック時刻を保存
    if notifications:
        save_last_check(notifications[0].created_at)
    
    return new_dms

def load_last_check():
    try:
        with open(LAST_CHECK_FILE, "r") as f:
            return json.load(f).get("last_check", "1970-01-01T00:00:00Z")
    except FileNotFoundError:
        return "1970-01-01T00:00:00Z"

def save_last_check(timestamp):
    with open(LAST_CHECK_FILE, "w") as f:
        json.dump({"last_check": timestamp}, f)

def main():
    new_dms = get_new_dms()
    if new_dms:
        for dm in new_dms:
            send_dm_notification(dm["sender"], dm["content"])
    else:
        print("新着DMなし！メール送信スキップ！")

if __name__ == "__main__":
    main()
