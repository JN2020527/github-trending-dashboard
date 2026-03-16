#!/bin/bash

# GitHub Trending Dashboard 更新脚本
# 每天抓取数据 + 生成描述 + 推送到 GitHub

set -e

DASHBOARD_DIR="$HOME/github-trending-dashboard"
DATE=$(date +%Y-%m-%d)

echo "🔥 开始更新 GitHub Trending Dashboard..."
echo "📅 日期: $DATE"
cd "$DASHBOARD_DIR"

# 1. 抓取 GitHub Trending 数据
echo "📊 步骤 1/3: 抓取 GitHub Trending 数据..."
source .venv/bin/activate
python fetch-trending-scrapling.py

# 2. 生成缺失的描述
echo "🤖 步骤 2/3: 生成缺失的中文描述..."
if [ -n "$OPENAI_API_KEY" ]; then
    python generate-descriptions.py
else
    echo "⚠️  OPENAI_API_KEY 未设置，跳过描述生成"
fi

# 3. 推送到 GitHub
echo "🚀 步骤 3/3: 推送到 GitHub..."
git add -A
git commit -m "feat: 更新 GitHub Trending - $DATE" || echo "No changes to commit"
git pull --rebase origin main || true
git push origin main

echo ""
echo "✅ Dashboard 已更新并推送到 GitHub!"
echo "🌐 访问: https://jn2020527.github.io/github-trending-dashboard/"
echo "📅 最新数据日期: $DATE"
