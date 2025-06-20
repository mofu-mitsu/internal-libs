# dm_checker.py
from atproto import Client
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# ------------------------------
# カスタマイズポイント
# -------------------
CHAR_NAMES = {
    "@mirinchuuu.bsky.social": "みりんてゃ",
    "@mofumitsukoubou.bsky": "みつき"
}
DM_NOTIFICATION_SUBJECTS = {
    "@mirinchuuu.bsky.social": "みりんてゃにDM来たんだけど…めっちゃウザいんですけど♡",
    "@mofumitsukoubou.bsky": "みつき、DM来たぜ！さっさとチェックしろよ～😎"
}
DM_NOTIFICATION_BODIES = {
    "@mirinchuuu.bsky.social": """
ねえ、@{account}に@{sender}からDM来てるんだけど。マジ何これ？💖
内容: {content}
みりんてゃ、こんなん完全スルー案件なんだけど？🙀
ブルスカでチェックしてよね～！！
""",
    "@mofumitsukoubou.bsky": """
よお、みつき！@{account}に@{sender}からDM来たぜ！😄
内容: {content}
ほら、さっさとブルスクでチェックしろよ～。まぁ、みつきならマイペースでいいけどな！😜
        """
}
DM_NOTIFICATION_HTML = {
    "@mirinchuuu.bsky.social": """
<html>
  <body style='font-family: courier new, sans-serif; background-color: #fff3f6; color: #880e4f; padding: 20px;'>
    <h1 style='color: #ff6f91;'>💖 みりんてゃからのDM通知 💌</h1>
    <p>ねえ、@{sender}からDM来てたよ！何これ？😽</p>
    <blockquote style='border-left: 3px solid #ff6f91; padding-left: 10px;'>
      {content}
    </blockquote>
    <p>…てか、みりん、こんなんスルーしたい気分なんだけど？🙀 <a href='https://bsky.app/' style='color: #ff6f91;'>ブルスク</a>で確認してよね～💖</p>
  </body>
</html>
""",
    "@mofumitsukoubou.bsky": """
<html>
    <body style='font-family: courier, sans-serif; background-color: #1e1e2e; color: #ffffff; padding: 20px;'>
    <h1 style='color: #7dd3fc;'>🚖 みつき、DM着いたぜ！ 😎🚖</h1>
    <p>よお、@{sender}からDM来てたよ！何の用だろ？😄</p>
    <blockquote style='border-left: 3px solid #7dd3fc; padding-left: 10px;'>
      {content}
    </blockquote>
    <p>ほら、<a href='https://bsky.app/' style='color: #7dd3fc;'>ブルスク</a>でチェックしろよ～。まぁ、みつきならのんびりいいけどな！😜</p>
    </body>
</html>
"""
}
# ------------------------------

# 前回のチェック時刻を保存するファイル
LAST_CHECK_FILES = {
    "@mirinchuuu.bsky.social": "チェック_みりん.json",
    "@mofumitsukoubou.bsky": "チェック_みつき.json"
}

def get_new_dms(handle, app_password):
    login_handle = handle.lstrip("@")
    print(f"Logging in with handle: {login_handle}, app_password: {'*' * len(app_password)}")
    try:
        client = Client()
        client.login(login_handle, app_password)
        # 認証状態のデバッグ
        print(f"🔍 Client state: {json.dumps(vars(client), indent=2, default=str)}")
        # セッションディスパッチャーからトークン取得
        access_token = None
        if hasattr(client, '_session_dispatcher'):
            session_dispatcher = client._session_dispatcher
            try:
                session_data = getattr(session_dispatcher, '_session', None)
                if session_data:
                    # 全属性をログ
                    session_attrs = {k: getattr(session_data, k) for k in dir(session_data) if not k.startswith('_')}
                    print(f"🔍 Session attributes: {json.dumps(session_attrs, indent=2, default=str)}")
                    # トークン候補を試行
                    for key in ['accessJwt', 'refreshJwt', 'access_jwt', 'jwt', 'accessToken', 'token']:
                        access_token = getattr(session_data, key, None)
                        if access_token:
                            print(f"🔍 Access token: {len(access_token) * characters}")
                            break
                    if not access_token:
                        print(f"🔍 No token found in known attributes")
            except Exception as e:
                print(f"🔍 SessionDispatcher error: {str(e)}")
        if not access_token:
            raise AttributeError("No access token available in Client or SessionDispatcher")
        # 通知APIで全応答確認
        notifications = client.app.bsky.notification.list_notifications().notifications
        print(f"🔍 Available bsky methods: {dir(client.app.bsky)}")
        print(f"🔍 Full notification response: {json.dumps(notifications, indent=2, default=str)}")
        new_dms = []
        last_check = load_last_check(f"@{login_handle}")

        for notif in notifications:
            print(f"Not🔍 Notification dict: {dkeyjson.dumps(notif.__dict__dict__, indent=2, default=str)}")
            print(f"🔍 Record dict: {dkeyjson.dumps(notif.record.__dict__dict__if hasattr(notif notif hasattr, 'record') else {}, indent=2, default=str)}")
            record_type = getattr(notif_record, "$type", "") if hasattr(notif, 'record') else ""
            record_text = contentgetattr(notif_record.content, "text", "") if hasattr(notif, 'record') else ""
            indexed_at = notif.__dict__.get("indexedAt", "")
            print(f"🔍 record type: {record_type}, content: {record_text}, indexed_at: {indexed_at}")
            if record_type == "app.bsky.chat.message" and indexed_at and indexed_at > last_check:
                new_dms.append({
                    "sender": notif.author.handle,
                    "content": record_text,
                    "time": indexed_at,
                    "account": f"@{login_handle}"
                })

        # チャットAPIをライブラリ経由で試行
        try:
            conversations = client.app.bsky.chat.getConversations({'limit': 50})
            print(f"🔍 Chat API (getConversations) response: {json.dumps(conversations, indent=2, default=str)}")
            for convo in conversations.get('conversations', []):
                convo_id = convo.get('id')
                messages_response = client.app.bsky.chat.getMessages({'conversationId': convo_id, 'limit': 50})
                print(f"🔍 Chat API (getMessages) response: {json.dumps(messages_response, indent=2, default=str)}")
                messages = messages_response.get('messages', [])
                for message in messages:
                    message_type = message.get("$type", "")
                    message_text = message.get("content", {}).get("text", "")
                    message_time = message.get("createdAt", "")
                    sender_handle = message.get("sender", {}).get("handle", "")
                    print(f"🔍 message type: {message_type}, content: {message_text}, time: {message_time}, sender: {sender_handle}")
                    if message_type == "app.bsky.chat.message" and message_time and message_time > last_check:
                        new_dms.append({
                            "sender": sender_handle,
                            "content": message_text,
                            "time": message_time,
                            "account": f"@{login_handle}"
                        })
        except Exception as e:
            print(f"🔍 Chat API (library) error: {str(e)}")

        # フォールバック: HTTPでチャットAPI
        headers = {"Authorization": f"Bearer {access_token}"}
        chat_response = requests.get("https://bsky.social/xrpc/app.bsky.chat.getConversations?limit=50", headers=headers)
        print(f"🔍 Chat API (HTTP) response - Status: {chat_response.status_code}, Body: {json.dumps(chat_response.json(), indent=2)}")
        if chat_response.status_code == 200:
            conversations = chat_response.json().get("conversations", [])
            for convo in conversations:
                convo_id = convo.get("id")
                messages_response = requests.get(
                    f"https://bsky.social/xrpc/app.bsky.chat.getMessages?conversationId={convo_id}&limit=50",
                    headers=headers
                )
                print(f"🔍 Chat API (HTTP getMessages) response - Status: {messages_response.status_code}, Body: {json.dumps(messages_response.json(), indent=2)}")
                if messages_response.status_code == 200:
                    messages = messages_response.json().get("messages", [])
                    for message in messages:
                        message_type = message.get("$type", "")
                        message_text = message.get("content", {}).get("text", "")
                        message_time = message.get("createdAt", "")
                        sender_handle = message.get("sender", {}).get("handle", "")
                        print(f"🔍 message type: {message_type}, content: {message_text}, time: {message_time}, sender: {sender_handle}")
                        if message_type == "app.bsky.chat.message" and message_time and message_time > last_check:
                            new_dms.append({
                                "sender": sender_handle,
                                "content": message_text,
                                "time": message_time,
                                "account": f"@{login_handle}"
                            })

        if notifications or new_dms:
            first_time = (notifications[0].__dict__.get("indexedAt", "") if notifications else
                         new_dms[0]["time"]) if notifications or new_dms else ""
            if first_time:
                save_last_check(f"@{login_handle}", first_time)
        
        return new_dms
    except Exception as e:
        print(f"Error for {login_handle}: {str(e)}")
        return []

def load_last_check(handle):
    try:
        with open(LAST_CHECK_FILES[handle], "r") as f:
            return json.load(f).get("last_check", "1970-01-01T00:00:00Z")
    except FileNotFoundError:
        return "1970-01-01T00:00:00Z"

def save_last_check(handle, timestamp):
    with open(LAST_CHECK_FILES[handle], "w") as f:
        json.dump({"last_check": timestamp}, f)

def send_dm_notification(account, dm_sender, dm_content):
    sender = os.getenv("EMAIL_SENDER")
    receiver = "mitsuki.momoka@i.softbank.jp"
    password = os.getenv("EMAIL_PASSWORD")

    char_name = CHAR_NAMES.get(account, "誰か")
    subject = DM_NOTIFICATION_SUBJECTS.get(account, "DM来たよ！")
    text_body = DM_NOTIFICATION_BODIES.get(account, "DM来た！内容: {content}").format(
        account=account, sender=dm_sender, content=dm_content
    )
    html_body = DM_NOTIFICATION_HTML_BODIES.get(account, "<p>DM来た！内容: {content}</p>").format(
        account=account, sender=dm_sender, content=dm_content
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    text_part = MIMEText(text_body, "plain")
    html_part = MIMEText(html_body, "html")
    msg.attach(text_part)
    msg.attach(html_part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

def main():
    accounts = [
        {
            "handle": os.getenv("HANDLE").lstrip("@"),
            "app_password": os.getenv("APP_PASSWORD")
        },
        {
            "handle": os.getenv("HANDLE_MITSUKI").lstrip("@"),
            "app_password": os.getenv("APP_PASSWORD_MITSUKI")
        }
    ]
    total_dms = 0

    for acc in accounts:
        print(f"Checking DMs for: @{acc['handle']}, app_password: {'*' * len(acc['app_password'])}")
        new_dms = get_new_dms(acc["handle"], acc["app_password"])
        if new_dms:
            for dm in new_dms:
                send_dm_notification(dm["account"], dm["sender"], dm["content"])
            total_dms += len(new_dms)

    if total_dms > 0:
        print(f"{total_dms}件のDMを通知したぜ！")
    else:
        print("新着DMなし！メール送信スキップ！")
        send_dm_notification("test@test.com", "TestSender", "デバッグ: DM検出なし（エラー再確認用）")

if __name__ == "__main__":
    main()