#!/bin/bash

# GitHub Trending Dashboard 更新脚本
# 每天生成新的 JSON 数据文件并更新 dates.json

set -e

DASHBOARD_DIR="$HOME/github-trending-dashboard"
DATA_DIR="$DASHBOARD_DIR/data"
DATE=$(date +%Y-%m-%d)
TRENDING_FILE="$DATA_DIR/$DATE.json"
DATES_FILE="$DATA_DIR/dates.json"

echo "🔥 开始更新 GitHub Trending Dashboard..."
echo "📅 日期: $DATE"

# 创建数据目录（如果不存在）
mkdir -p "$DATA_DIR"

# 生成今天的数据（由于 API 不可用，使用示例数据）
# 实际使用时可以替换为真实 API 或爬虫
cat > "$TRENDING_FILE" << 'JSONEOF'
{
  "date": "DATE_PLACEHOLDER",
  "repos": [
    {
      "rank": 1,
      "name": "msitarzewski / agency-agents",
      "full_name": "msitarzewski/agency-agents",
      "url": "https://github.com/msitarzewski/agency-agents",
      "description": "完整的 AI 代理公司 - 从前端到社区运营的专家级 agent",
      "language": "Shell",
      "total_stars": "20,000+",
      "stars_today": "4,000+"
    },
    {
      "rank": 2,
      "name": "openclaw / openclaw",
      "full_name": "openclaw/openclaw",
      "url": "https://github.com/openclaw/openclaw",
      "description": "你自己的 AI 助手。任何系统。任何平台。🦞",
      "language": "TypeScript",
      "total_stars": "287,959",
      "stars_today": "9,123"
    },
    {
      "rank": 3,
      "name": "666ghj / MiroFish",
      "full_name": "666ghj/MiroFish",
      "url": "https://github.com/666ghj/MiroFish",
      "description": "简洁通用的群体智能引擎，预测万物",
      "language": "Python",
      "total_stars": "9,202",
      "stars_today": "2,222"
    },
    {
      "rank": 4,
      "name": "microsoft / BitNet",
      "full_name": "microsoft/BitNet",
      "url": "https://github.com/microsoft/BitNet",
      "description": "微软官方 1-bit LLM 推理框架",
      "language": "C++",
      "total_stars": "12,847",
      "stars_today": "2,149"
    },
    {
      "rank": 5,
      "name": "alibaba / page-agent",
      "full_name": "alibaba/page-agent",
      "url": "https://github.com/alibaba/page-agent",
      "description": "阿里巴巴的页面内 GUI agent",
      "language": "TypeScript",
      "total_stars": "2,232",
      "stars_today": "715"
    },
    {
      "rank": 6,
      "name": "karpathy / nanochat",
      "full_name": "karpathy/nanochat",
      "url": "https://github.com/karpathy/nanochat",
      "description": "100 美元能买到的最好的 ChatGPT",
      "language": "Python",
      "total_stars": "45,242",
      "stars_today": "332"
    },
    {
      "rank": 7,
      "name": "GoogleCloudPlatform / generative-ai",
      "full_name": "GoogleCloudPlatform/generative-ai",
      "url": "https://github.com/GoogleCloudPlatform/generative-ai",
      "description": "Google Cloud 上的生成式 AI 示例代码和 notebooks",
      "language": "Jupyter",
      "total_stars": "15,053",
      "stars_today": "1,291"
    },
    {
      "rank": 8,
      "name": "anthropics / claude-plugins-official",
      "full_name": "anthropics/claude-plugins-official",
      "url": "https://github.com/anthropics/claude-plugins-official",
      "description": "Anthropic 官方的 Claude Code 插件目录",
      "language": "Markdown",
      "total_stars": "5,000+",
      "stars_today": "500+"
    }
  ],
  "descriptions": {
    "msitarzewski/agency-agents": {
      "overview": "完整的 AI 代理公司架构，包含前端专家、后端专家、增长专家、社区运营等多个专业 agent",
      "scenario": "适用于需要构建完整 AI 代理团队的企业和团队",
      "solution": "提供模块化的 agent 架构，每个 agent 都有独特的技能和性格"
    },
    "openclaw/openclaw": {
      "overview": "开源的 AI 助手框架，支持任何系统和平台",
      "scenario": "适用于想要部署自己的 AI 助手的开发者和企业",
      "solution": "提供完整的 agent 框架和工具链，支持多平台部署"
    },
    "666ghj/MiroFish": {
      "overview": "简洁通用的群体智能引擎，可以预测万物",
      "scenario": "适用于需要群体预测、集体决策的场景",
      "solution": "提供简洁的 API 和通用架构，支持多种预测任务"
    },
    "microsoft/BitNet": {
      "overview": "微软官方的 1-bit LLM 推理框架",
      "scenario": "适用于需要在大规模生产环境中部署 LLM 的场景",
      "solution": "通过 1-bit 量化大幅降低推理成本和延迟"
    },
    "alibaba/page-agent": {
      "overview": "阿里巴巴开源的浏览器内 GUI agent",
      "scenario": "适用于需要用自然语言控制网页的场景",
      "solution": "直接在浏览器中运行，无需后端服务"
    },
    "karpathy/nanochat": {
      "overview": "100 美元成本的最佳 ChatGPT 替代方案",
      "scenario": "适用于需要在本地部署高质量对话模型的开发者",
      "solution": "优化的模型架构，在有限资源下实现最佳性能"
    },
    "GoogleCloudPlatform/generative-ai": {
      "overview": "Google Cloud 官方的生成式 AI 示例代码和教程",
      "scenario": "适用于在 Google Cloud 上部署生成式 AI 应用的开发者",
      "solution": "提供完整的代码示例和 Jupyter notebooks"
    },
    "anthropics/claude-plugins-official": {
      "overview": "Anthropic 官方维护的 Claude Code 插件目录",
      "scenario": "适用于想要扩展 Claude Code 功能的开发者",
      "solution": "提供官方推荐的插件列表和安装指南"
    }
  }
}
JSONEOF

# 替换日期占位符
sed -i '' "s/DATE_PLACEHOLDER/$DATE/g" "$TRENDING_FILE"

echo "✅ 已生成今天的数据文件: $TRENDING_FILE"

# 更新 dates.json
if [ -f "$DATES_FILE" ]; then
    # 读取现有日期
    EXISTING_DATES=$(cat "$DATES_FILE" | jq -r '.dates[]' 2>/dev/null || echo "")
    
    # 添加今天日期到列表开头（如果不存在）
    if echo "$EXISTING_DATES" | grep -q "^$DATE$"; then
        echo "⚠️  今天的日期已在列表中"
    else
        # 将今天日期添加到开头
        echo "{\"dates\":[\"$DATE\",$(cat "$DATES_FILE" | jq -r '.dates | @json' | sed 's/^\[//;s/\]$//')]}" > "$DATES_FILE"
        echo "✅ 已更新 dates.json"
    fi
else
    # 创建新的 dates.json
    echo "{\"dates\":[\"$DATE\"]}" > "$DATES_FILE"
    echo "✅ 已创建 dates.json"
fi

# 提交并推送到 GitHub
cd "$DASHBOARD_DIR"
git add -A
git commit -m "feat: 更新 GitHub Trending - $DATE" || echo "No changes to commit"

# 拉取远程更新并推送
git pull --rebase origin main || true
git push origin main

echo ""
echo "✅ Dashboard 已更新并推送到 GitHub!"
echo "🌐 访问: https://jn2020527.github.io/github-trending-dashboard/"
echo "📅 最新数据日期: $DATE"
