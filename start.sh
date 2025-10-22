#!/bin/bash

echo "=== 个人健康知识图谱系统 - 第一阶段 ==="
echo ""

# 检查Python版本
echo "检查Python版本..."
python3 --version

# 检查是否安装了依赖
echo ""
echo "安装Python依赖..."
pip3 install -r requirements.txt

# 检查MongoDB
echo ""
echo "检查MongoDB状态..."
if ! command -v mongod &> /dev/null; then
    echo "MongoDB未安装，请先安装MongoDB："
    echo "1. 使用Docker: docker run -d -p 27017:27017 --name mongodb mongo:latest"
    echo "2. 或使用Homebrew: brew install mongodb-community"
    echo "3. 或从官网下载: https://www.mongodb.com/try/download/community"
    echo ""
    echo "安装完成后，请确保MongoDB服务正在运行"
    exit 1
fi

# 检查MongoDB是否运行
if ! pgrep -x "mongod" > /dev/null; then
    echo "MongoDB服务未运行，正在启动..."
    brew services start mongodb/brew/mongodb-community
    sleep 3
fi

echo "MongoDB服务运行正常"

# 检查配置文件
echo ""
echo "检查配置文件..."
if [ ! -f "config.env" ]; then
    echo "配置文件不存在，请先配置config.env文件"
    exit 1
fi

# 检查API Key
if grep -q "your_deepseek_api_key_here" config.env; then
    echo "警告: 请在config.env中配置您的DeepSeek API Key"
    echo "编辑config.env文件，将DEEPSEEK_API_KEY设置为您的实际API Key"
    echo ""
fi

echo ""
echo "启动系统..."
echo "访问地址: http://localhost:8000"
echo "按Ctrl+C停止服务"
echo ""

python3 main.py
