#!/bin/bash

# GitHub Trending Dashboard 更新脚本
# 从 GitHub Trending API 获取数据并更新 dashboard

set -e

DASHBOARD_DIR="$HOME/github-trending-dashboard"
HTML_FILE="$DASHBOARD_DIR/index.html"
DATE=$(date +%Y-%m-%d)

echo "🔥 开始更新 GitHub Trending Dashboard..."
echo "📅 日期: $DATE"

# 使用 GitHub Trending API (via sneat.github.io)
# 或者直接爬取 GitHub Trending 页面
TRENDING_DATA=$(curl -s "https://api.gitterapp.com/repositories?language=&since=daily" 2>/dev/null || echo "[]")

# 如果 API 失败，使用备用方案（直接爬取）
if [ "$TRENDING_DATA" = "[]" ] || [ -z "$TRENDING_DATA" ]; then
    echo "⚠️  API 不可用，使用备用数据..."
    # 备用：使用静态示例数据（实际应该爬取 GitHub）
    cat > "$HTML_FILE" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Trending Today</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 700px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .header p { color: rgba(255,255,255,0.9); font-size: 14px; }
        .repo-card {
            background: white;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 12px;
        }
        .repo-card.gold { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); }
        .repo-card.silver { background: linear-gradient(135deg, #E8E8E8 0%, #C0C0C0 100%); }
        .repo-card.bronze { background: linear-gradient(135deg, #CD7F32 0%, #B8860B 100%); }
        .repo-title {
            font-size: 16px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 6px;
        }
        .repo-card.gold .repo-title,
        .repo-card.silver .repo-title,
        .repo-card.bronze .repo-title { color: white; }
        .repo-desc {
            color: #666;
            font-size: 13px;
            margin-bottom: 10px;
        }
        .repo-card.gold .repo-desc,
        .repo-card.silver .repo-desc,
        .repo-card.bronze .repo-desc { color: rgba(255,255,255,0.9); }
        .repo-stats {
            display: flex;
            gap: 12px;
            font-size: 12px;
            color: #888;
        }
        .repo-card.gold .repo-stats,
        .repo-card.silver .repo-stats,
        .repo-card.bronze .repo-stats { color: rgba(255,255,255,0.85); }
        .stars-today {
            background: #ff4757;
            color: white;
            padding: 2px 6px;
            border-radius: 8px;
            font-weight: 600;
        }
        .repo-card.gold .stars-today,
        .repo-card.silver .stars-today,
        .repo-card.bronze .stars-today { background: rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 GitHub Trending</h1>
            <p id="date">加载中...</p>
        </div>
        <div id="repos"></div>
    </div>
    <script>
        document.getElementById('date').textContent = new Date().toISOString().split('T')[0] + " Today's Top Repositories";
        
        // 使用 GitHub Trending API
        fetch('https://api.gitterapp.com/repositories?language=&since=daily')
            .then(r => r.json())
            .then(data => {
                const repos = data.slice(0, 8);
                const container = document.getElementById('repos');
                repos.forEach((repo, i) => {
                    const card = document.createElement('div');
                    const rank = i + 1;
                    let badge = rank <= 3 ? ['gold', 'silver', 'bronze'][i] : '';
                    const medal = rank === 1 ? '🥇 ' : rank === 2 ? '🥈 ' : rank === 3 ? '🥉 ' : `${rank}. `;
                    
                    card.className = 'repo-card' + (badge ? ' ' + badge : '');
                    card.innerHTML = `
                        <div class="repo-title">${medal}${repo.author}/${repo.name}</div>
                        <div class="repo-desc">${repo.description || 'No description'}</div>
                        <div class="repo-stats">
                            <span>${repo.language || 'Unknown'}</span>
                            <span>⭐ ${repo.stars.toLocaleString()}</span>
                            <span class="stars-today">+${repo.starsSince.toLocaleString()} 🔥</span>
                        </div>
                    `;
                    container.appendChild(card);
                });
            })
            .catch(err => {
                document.getElementById('repos').innerHTML = '<div class="repo-card"><p style="color:#666">数据加载失败，请稍后重试</p></div>';
            });
    </script>
</body>
</html>
HTMLEOF
else
    echo "✅ 成功获取 GitHub Trending 数据"
fi

# 提交并推送到 GitHub
cd "$DASHBOARD_DIR"
git add -A
git commit -m "Update GitHub Trending - $DATE" || echo "No changes to commit"
git push origin main

echo "✅ Dashboard 已更新并推送到 GitHub!"
echo "🌐 访问: https://jn2020527.github.io/github-trending-dashboard/"
