FROM python:3.10-slim

# 依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ作成
WORKDIR /app

# ファイルコピー
COPY . .

# Python依存関係のインストール
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 実行コマンド（reply_bot.py がメインファイル想定）
CMD ["python", "reply_bot.py"]