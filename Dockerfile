FROM python:3.10-slim

# 必要なライブラリ追加（torchが要求するやつ）
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

CMD ["python", "reply_bot.py"]