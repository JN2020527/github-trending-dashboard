#!/bin/bash
# GitHub Trending Dashboard 推送通知脚本

# 读取最新数据
DATA_FILE="$HOME/github-trending-dashboard/data/latest.json"

if [ ! -f "$DATA_FILE" ]; then
    echo "❌ 数据文件不存在"
    exit 1
fi

# 提取日期
DATE=$(cat "$DATA_FILE" | python3 -c "import sys, json; print(json.load(sys.stdin)['date'])")

# 提取项目数量
REPO_COUNT=$(cat "$DATA_FILE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['repos']))")

# 提取 Top 3 项目
TOP3=$(cat "$DATA_FILE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, repo in enumerate(data['repos'][:3], 1):
    name = repo['name']
    stars = repo['stars_today']
    print(f'{i}. {name} (+{stars} ⭐)')
")

# 构建消息
MESSAGE="📊 **GitHub Trending Dashboard 已更新**

📅 日期：${DATE}
🔥 热门项目：${REPO_COUNT} 个

Top 3 今日热门：
${TOP3}

🌐 Dashboard: https://jn2020527.github.io/github-trending-dashboard/"

# 发送到 Discord
echo "📤 发送通知到 Discord..."
openclaw message send --channel discord --target "channel:1480614916930146366" --message "$MESSAGE"

if [ $? -eq 0 ]; then
    echo "✅ 通知发送成功"
else
    echo "❌ 通知发送失败"
fi
