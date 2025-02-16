#!/bin/bash

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# 加载环境变量
set -a
source .env
set +a

# 检查必要的环境变量
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "Error: Required environment variables are not set!"
    echo "Please check your .env file."
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 检查日志目录
mkdir -p logs

# 启动后台进程
echo "Starting options scanner..."
nohup python -m src.daemon > /dev/null 2>&1 &
echo $! > .pid

echo "Options scanner started in background. PID: $(cat .pid)"
echo "Check logs/options_scanner.log for details." 