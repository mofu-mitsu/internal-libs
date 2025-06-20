# dm_checker.py
from atproto import Client
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from datetime import datetime
import dotenv

# .env読み込み
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path=dotenv_path)
print(f"🔍 Loaded .env: {dict(os.environ).keys()}")
print(f"🔍 ENV values: EMAIL_SENDER={os.getenv('EMAIL_SENDER')}, EMAIL_RECEIVER={os.getenv('EMAIL_RECEIVER')}, DEBUG={os.getenv('DEBUG')}")

# ------------------------------
# ★ カスタマイズポイント
# ------------------------------
CHAR_NAMES = {
    "@mirinchuuu.bsky.social": "みりんてゃ",
    "@mofumitsukoubou.bsky.social": "みつき",
    "@debug.test": "デバッグ君"
}
DM_NOTIFICATION_SUBJECTS = {
    "@mirinchuuu.bsky.social": "みりんてゃにDM来たんだけど…めっちゃウザいんですけど♡",
    "@mofumitsukoubou.bsky.social": "みつき、DM来たぜ！さっさとチェックしろよ～😎",
    "@debug.test": "デバッグ通知だよ！チェックしてね！"
}
DM_NOTIFICATION_BODIES = {
    "@mirinchuuu.bsky.social": """
ねえ、@{account}に@{sender}からDM来てるんだけど。マジ何これ？💭
内容: {content}
みりんてゃ、こんなん完全スルー案件なんだけど？ᐢ⩌⌯⩌ᐢ ブルスカで確認してよね～♡
""",
    "@mofumitsukoubou.bsky.social": """
よお、みつき！@{account}に@{sender}からDM来たぜ！😎
内容: {content}
ほら、さっさとブルスカでチェックしろよ～。まぁ、みつきならのんびりでもいいけどな！😜
""",
    "@debug.test": """
デバッグ通知だよ！@{account}でエラー確認！
内容: {content}
みつき、ログ見て直してね～！
"""
}
DM_NOTIFICATION_HTML_BODIES = {
    "@mirinchuuu.bsky.social": """
<html>
  <body style="font-family: 'Arial', sans-serif; background-color: #fce4ec; color: #880e4f; padding: 20px;">
    <h1 style="color: #ff69b4;">💌 みりんてゃからの地雷風通知 💌</h1>
    <p>ねえ、@{sender}からDM来てるんだけど、マジ何これ？💭</p>
    <blockquote style="border-left: 3px solid #ff69b4; padding-left: 10px;">
      {content}
    </blockquote>
    <p>…てか、みりんてゃ、こんなんスルーしたい気分なんだけど？ᐢ⩌⌯⩌ᐢ <a href="https://bsky.app/" style="color: #ff69b4;">ブルスカ</a>で確認してよね～♡</p>
  </body>
</html>
""",
    "@mofumitsukoubou.bsky.social": """
<html>
  <body style="font-family: 'Arial', sans-serif; background-color: #1e1e1e; color: #ffffff; padding: 20px;">
    <h1 style="color: #00b7eb;">🚀 みつき、DM着信だぜ！by Grok 🚀</h1>
    <p>よお、@{sender}からDM来たぞ！何の用だろ？😎</p>
    <blockquote style="border-left: 3px solid #00b7eb; padding-left: 10px;">
      {content}
    </blockquote>
    <p>ほら, <a href="https://bsky.app/" style="color: #00b7eb;">ブルスカ</a>でチェックしろよ～。まぁ、みつきならマイペースでいいけどな！😜</p>
  </body>
</html>
""",
    "@debug.test": """
<html>
  <body style="font-family: 'Arial', sans-serif; background-color: #f0f0f0; color: #333; padding: 20px;">
    <h1 style="color: #666;">🛠 デバッグ通知 🛠</h1>
    <p>@{sender}からのデバッグ情報だよ！</p>
    <blockquote style="border-left: 3px solid #666; padding-left: 10px;">
      {content}
    </blockquote>
    <p>みつき、ログ確認してね～！</p>
  </body>
</html>
"""
}
# ------------------------------

# 前回のチェック時刻を保存するファイル
LAST_CHECK_FILES = {
    "@mirinchuuu.bsky.social": "last_check_mirin.json",
    "@mofumitsukoubou.bsky.social": "last_check_mitsuki.json",
    "@debug.test": "last_check_debug.json"
}

# デバッグモード
DEBUG = True
print(f"🔍 DEBUG mode: {DEBUG}")

def debug_log(message):
    if DEBUG:
        print(f"🔍 [DEBUG] {datetime.now().isoformat()}: {message}")

def get_new_dms(handle, app_password):
    login_handle = handle.lstrip("@")
    debug_log(f"Logging in with handle: {login_handle}, app_password: {'*' * len(app_password)}")
    try:
        client = Client()
        client.login(login_handle, app_password)
        debug_log(f"Client state: {json.dumps(vars(client), indent=2, default=str)}")
        # トークン取得
        access_token = None
        if hasattr(client, '_session_dispatcher'):
            session_dispatcher = client._session_dispatcher
            try:
                session_data = getattr(session_dispatcher, '_session', None)
                if session_data:
                    session_attrs = {k: str(getattr(session_data, k)) for k in dir(session_data) if not k.startswith('__')}
                    debug_log(f"Session attributes: {json.dumps(session_attrs, indent=2, default=str)}")
                    for key in ['accessJwt', 'refreshJwt', 'access_jwt', 'jwt', 'accessToken', 'token', 'access', 'refresh', 'accessJwtToken', 'refreshJwtToken']:
                        access_token = getattr(session_data, key, None)
                        if access_token:
                            debug_log(f"Access token found: {'*' * len(access_token)}")
                            break
                    if not access_token and isinstance(session_data, dict):
                        debug_log(f"Session as dict: {json.dumps(session_data, indent=2, default=str)}")
                        access_token = session_data.get('accessJwt') or session_data.get('refreshJwt')
                        if access_token:
                            debug_log(f"Access token found in dict: {'*' * len(access_token)}")
                    if not access_token:
                        debug_log("No token found in known attributes or dict")
            except Exception as e:
                debug_log(f"SessionDispatcher error: {str(e)}")
        if not access_token:
            raise AttributeError("No access token available in Client or SessionDispatcher")
        # 通知API
        notifications = client.app.bsky.notification.list_notifications().notifications
        debug_log(f"Available bsky methods: {dir(client.app.bsky)}")
        debug_log(f"Full notification response: {json.dumps([n.__dict__ for n in notifications], indent=2, default=str)}")
        new_dms = []
        last_check = load_last_check(f"@{login_handle}")

        for notif in notifications:
            debug_log(f"Notification dict: {json.dumps(notif.__dict__, indent=2, default=str)}")
            debug_log(f"Record dict: {json.dumps(notif.record.__dict__ if hasattr(notif, 'record') else {}, indent=2, default=str)}")
            record_type = getattr(notif.record, "$type", "") if hasattr(notif, 'record') else ""
            record_text = getattr(notif.record, "text", "") if hasattr(notif, 'record') else ""
            indexed_at = notif.__dict__.get("indexedAt", "")
            debug_log(f"record type: {record_type}, content: {record_text}, indexed_at: {indexed_at}")
            if record_type == "app.bsky.chat.message" and indexed_at and indexed_at > last_check:
                new_dms.append({
                    "sender": notif.author.handle,
                    "content": record_text,
                    "time": indexed_at,
                    "account": f"@{login_handle}"
                })

        # チャットAPI
        try:
            conversations = client.app.bsky.chat.get_conversations({'limit': 50})
            debug_log(f"Chat API (get_conversations) response: {json.dumps(conversations.__dict__, indent=2, default=str)}")
            for convo in conversations.conversations:
                convo_id = convo.id
                messages_response = client.app.bsky.chat.get_messages({'conversation_id': convo_id, 'limit': 50})
                debug_log(f"Chat API (get_messages) response: {json.dumps(messages_response.__dict__, indent=2, default=str)}")
                messages = messages_response.messages
                for message in messages:
                    message_type = message.__dict__.get("$type", "")
                    message_text = message.content.get("text", "") if hasattr(message, 'content') else ""
                    message_time = message.__dict__.get("created_at", "")
                    sender_handle = message.sender.handle if hasattr(message, 'sender') else ""
                    debug_log(f"message type: {message_type}, content: {message_text}, time: {message_time}, sender: {sender_handle}")
                    if message_type == "app.bsky.chat.message" and message_time and message_time > last_check:
                        new_dms.append({
                            "sender": sender_handle,
                            "content": message_text,
                            "time": message_time,
                            "account": f"@{login_handle}"
                        })
        except Exception as e:
            debug_log(f"Chat API (library) error: {str(e)}")

        # HTTPフォールバック
        headers = {"Authorization": f"Bearer {access_token}"}
        for endpoint in [
            "com.atproto.chat.getConversations",
            "chat.bsky.app.getConversations",
            "app.bsky.convo.getConvos"
        ]:
            chat_response = requests.get(f"https://bsky.social/xrpc/{endpoint}?limit=50", headers=headers)
            debug_log(f"Chat API (HTTP {endpoint}) response - Status: {chat_response.status_code}, Body: {json.dumps(chat_response.json() if chat_response.status_code == 200 else chat_response.text, indent=2)}")
            if chat_response.status_code == 200:
                conversations = chat_response.json().get("conversations", [])
                for convo in conversations:
                    convo_id = convo.get("id")
                    messages_endpoint = endpoint.replace("getConversations", "getMessages").replace("getConvos", "getMessages")
                    messages_response = requests.get(
                        f"https://bsky.social/xrpc/{messages_endpoint}?conversation_id={convo_id}&limit=50",
                        headers=headers
                    )
                    debug_log(f"Chat API (HTTP getMessages {messages_endpoint}) response - Status: {messages_response.status_code}, Body: {json.dumps(messages_response.json() if messages_response.status_code == 200 else messages_response.text, indent=2)}")
                    if messages_response.status_code == 200:
                        messages = messages_response.json().get("messages", [])
                        for message in messages:
                            message_type = message.get("$type", "")
                            message_text = message.get("content", {}).get("text", "")
                            message_time = message.get("createdAt", "")
                            sender_handle = message.get("sender", {}).get("handle", "")
                            debug_log(f"message type: {message_type}, content: {message_text}, time: {message_time}, sender: {sender_handle}")
                            if message_type == "app.bsky.chat.message" and message_time and message_time > last_check:
                                new_dms.append({
                                    "sender": sender_handle,
                                    "content": message_text,
                                    "time": message_time,
                                    "account": f"@{login_handle}"
                                })

        # first_time処理
        first_time = None
        if notifications:
            first_time = notifications[0].__dict__.get("indexedAt", "")
        elif new_dms:
            first_time = new_dms[0]["time"]

        if first_time:
            save_last_check(f"@{login_handle}", first_time)
        
        return new_dms
    except Exception as e:
        debug_log(f"Error for {login_handle}: {str(e)}")
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
    receiver = os.getenv("EMAIL_RECEIVER", "mitsuki.momoka@i.softbank.jp")
    password = os.getenv("EMAIL_PASSWORD")

    debug_log(f"Preparing notification: sender={sender}, receiver={receiver}, account={account}")
    if not sender or not receiver:
        debug_log(f"✋ メール送信スキップ: sender or receiver が未設定！ sender={sender}, receiver={receiver}")
        return

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

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            debug_log(f"Sent notification to {receiver} for {account}")
    except Exception as e:
        debug_log(f"SMTP error: {str(e)}")

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
        debug_log(f"Checking DMs for: @{acc['handle']}, app_password: {'*' * len(acc['app_password'])}")
        new_dms = get_new_dms(acc["handle"], acc["app_password"])
        if new_dms:
            for dm in new_dms:
                send_dm_notification(dm["account"], dm["sender"], dm["content"])
            total_dms += len(new_dms)

    if total_dms > 0:
        print(f"{total_dms}件のDMを通知したぜ！")
    else:
        print("新着DMなし！メール送信スキップ！")
        send_dm_notification("@debug.test", "TestSender", f"デバッグ: DM検出なし（エラー再確認用） {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()