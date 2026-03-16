#!/bin/bash
# GitHub Trending Dashboard 定时任务脚本

# API Key 从环境变量读取（不要硬编码）
# 设置方式：launchctl setenv OPENAI_API_KEY "your-key"
# 或在 LaunchAgents plist 中配置

export PATH="/opt/homebrew/bin:$PATH"

# 日志文件
LOG_FILE="$HOME/github-trending-dashboard/cron.log"

# 运行更新脚本
{
    echo "========================================"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始更新 GitHub Trending"
    echo "========================================"
    
    cd ~/github-trending-dashboard
    bash update-trending.sh
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 更新完成"
    echo ""
} >> "$LOG_FILE" 2>&1

# 发送 Discord 通知
bash ~/github-trending-dashboard/send-notification.sh >> "$LOG_FILE" 2>&1
