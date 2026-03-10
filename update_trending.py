#!/usr/bin/env python3
"""
GitHub Trending 抓取脚本
每天自动抓取 trending 数据并生成 HTML 页面
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

def fetch_github_trending():
    """抓取 GitHub Trending 页面"""
    url = "https://github.com/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    repos = []
    
    articles = soup.select('article.Box-row')[:8]  # 取前 8 个
    
    for i, article in enumerate(articles):
        try:
            # 获取仓库信息
            h2 = article.select_one('h2 a')
            if not h2:
                continue
                
            repo_path = h2.get('href', '').strip('/')
            repo_name = repo_path.replace('/', ' / ')
            
            # 获取描述
            desc_elem = article.select_one('p.col-9')
            description = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # 获取语言
            lang_elem = article.select_one('[itemprop="programmingLanguage"]')
            language = lang_elem.get_text(strip=True) if lang_elem else 'Unknown'
            
            # 获取总 star 数
            stars_elem = article.select_one('a[href$="/stargazers"]')
            total_stars = stars_elem.get_text(strip=True) if stars_elem else '0'
            
            # 获取今日新增 star
            stars_today_elem = article.select_one('span.d-inline-block.float-sm-right')
            stars_today = '0'
            if stars_today_elem:
                stars_today_text = stars_today_elem.get_text(strip=True)
                # 提取数字
                stars_today = ''.join(filter(str.isdigit, stars_today_text)) or '0'
            
            repos.append({
                'rank': i + 1,
                'name': repo_name,
                'full_name': repo_path,
                'url': f'https://github.com/{repo_path}',
                'description': description,
                'language': language,
                'total_stars': total_stars,
                'stars_today': stars_today
            })
            
        except Exception as e:
            print(f"Error parsing repo {i+1}: {e}")
            continue
    
    return repos

def generate_descriptions():
    """项目描述数据库（可扩展）"""
    return {
        'msitarzewski/agency-agents': {
            'overview': '61 个专业 AI Agent 的开源集合，覆盖工程、设计、营销、产品等 9 大领域。每个 Agent 都有独立人格、专属工作流、代码示例和成功指标。',
            'scenario': '适合需要专业 AI 协作的开发者和团队。当你发现通用提示词太泛、无法产出专业交付物时，可以召唤对应领域的专家 Agent。',
            'solution': '深度专业化的 Agent 设计：Frontend Developer 懂 React 性能优化，Reddit Community Builder 懂社区运营礼仪，每个 Agent 都有真实项目验证过的工作流。'
        },
        '666ghj/MiroFish': {
            'overview': '基于多智能体技术的 AI 预测引擎。上传种子材料（新闻、报告、小说），自动构建平行数字世界，成千上万智能体在其中交互演化。',
            'scenario': '决策者需要零风险试错环境：政策推演、公关策略、舆情预测。普通用户也可以推演小说结局或探索脑洞。',
            'solution': 'GraphRAG 构建知识图谱 → 生成独立人格智能体 → 双平台并行模拟 → ReportAgent 生成可交互的预测报告。'
        },
        'GoogleCloudPlatform/generative-ai': {
            'overview': 'Google Cloud 生成式 AI 官方示例仓库。包含 notebooks、代码示例、示例应用，演示如何在 Vertex AI 上使用 Gemini 等模型。',
            'scenario': '开发者想快速上手 Google Cloud 的生成式 AI 能力，但不知道从哪里开始。需要从入门到进阶的完整学习路径。',
            'solution': '按场景分类的示例库：Gemini 入门、RAG/Grounding、图像生成 (Imagen)、语音 (Chirp)、搜索 (Vertex AI Search)。'
        },
        'pbakaus/impeccable': {
            'overview': '让 AI 摆脱"模板感"的设计语言系统。7 个专业参考文件 + 17 个命令 + 精选反模式清单。',
            'scenario': 'AI 生成的前端设计总是千篇一律：Inter 字体、紫色渐变、卡片嵌套卡片。你需要 AI 懂真正的设计原则。',
            'solution': '覆盖排版、色彩、空间、动效、交互、响应式、UX 文案 7 大领域。命令如 /audit 审查质量、/polish 打磨细节。'
        },
        '666ghj/BettaFish': {
            'overview': '多 Agent 舆情分析系统"微舆"。用户用自然语言提问，4 类 Agent 协作分析国内外 30+ 社媒平台，自动生成深度报告。',
            'scenario': '品牌方需要了解舆情风向、分析用户反馈、追踪热点事件。传统方式要人工收集多个平台数据，效率低下。',
            'solution': 'QueryAgent 广度搜索 + MediaAgent 多模态理解 + InsightAgent 私有数据挖掘 + ReportAgent 报告生成。'
        },
        'NousResearch/hermes-agent': {
            'overview': '自我进化的 AI Agent。内置完整学习循环：从经验创建技能、使用中改进技能、主动持久化记忆、搜索历史对话。',
            'scenario': '你需要一个真正"认识你"的 Agent。不是每次对话都从零开始，而是能记住你的偏好、习惯、项目，越用越顺手。',
            'solution': 'Honcho 方言式用户建模 + Agent 自主创建技能 + FTS5 跨会话搜索 + 定时任务调度。'
        },
        'alibaba/page-agent': {
            'overview': '阿里巴巴开源的页内 GUI Agent。纯 JavaScript 实现，用自然语言控制网页界面，无需浏览器插件、Python 或无头浏览器。',
            'scenario': 'SaaS 产品想加 AI Copilot 功能，但不想重写后端。ERP/CRM 系统有复杂表单，用户希望能一句话完成操作。',
            'solution': '文本化 DOM 操作，无需截图/OCR/多模态 LLM。一行代码集成，支持任意 OpenAI 兼容 API。'
        },
        'teng-lin/notebooklm-py': {
            'overview': 'Google NotebookLM 非官方 Python API。提供编程式访问能力，解锁 Web UI 没有暴露的功能。',
            'scenario': '你想批量处理 NotebookLM 资源、自动生成播客/视频/测验、导出结构化数据，但官方界面只能手动操作。',
            'solution': '完整 Python API + CLI + Claude Code 技能。支持批量导入源、生成音频/视频/幻灯片/思维导图、多格式导出。'
        }
    }

def generate_html(repos, date_str):
    """生成 HTML 页面"""
    descriptions = generate_descriptions()
    
    html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Trending Today</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: oklch(97% 0.005 260);
            --bg-card: oklch(100% 0 0);
            --fg-primary: oklch(20% 0.02 260);
            --fg-secondary: oklch(40% 0.02 260);
            --fg-muted: oklch(55% 0.02 260);
            --accent: oklch(50% 0.2 25);
            --rank-gold: oklch(75% 0.15 85);
            --rank-silver: oklch(70% 0.01 260);
            --rank-bronze: oklch(65% 0.12 50);
            --border: oklch(90% 0.01 260);
            --positive: oklch(50% 0.18 145);
            --section-label: oklch(50% 0.15 25);
            --space-xs: 4px; --space-sm: 8px; --space-md: 16px;
            --space-lg: 24px; --space-xl: 40px; --space-2xl: 64px;
            --font-display: 'Space Grotesk', sans-serif;
            --font-body: 'DM Sans', sans-serif;
            --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
            --duration-fast: 150ms; --duration-normal: 300ms;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: var(--font-body);
            background: var(--bg-base);
            color: var(--fg-primary);
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        .container {
            position: relative;
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--space-xl) var(--space-lg);
        }
        .header {
            text-align: center;
            margin-bottom: var(--space-2xl);
            animation: fadeIn var(--duration-normal) var(--ease-out);
        }
        .header-label {
            display: inline-flex;
            align-items: center;
            gap: var(--space-sm);
            font-size: 12px;
            font-weight: 500;
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: var(--space-md);
        }
        .header-label::before, .header-label::after {
            content: '';
            width: 32px;
            height: 1px;
            background: var(--border);
        }
        .header h1 {
            font-family: var(--font-display);
            font-size: clamp(32px, 7vw, 48px);
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: var(--space-sm);
            color: var(--fg-primary);
        }
        .header-date { font-size: 14px; color: var(--fg-muted); }
        .repo-list {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-md);
        }
        .repo-card {
            position: relative;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: var(--space-md);
            transition: transform var(--duration-fast) var(--ease-out),
                        border-color var(--duration-fast) var(--ease-out),
                        box-shadow var(--duration-fast) var(--ease-out);
            animation: slideIn var(--duration-normal) var(--ease-out) backwards;
            display: flex;
            flex-direction: column;
        }
        .repo-card:nth-child(1) { animation-delay: 50ms; }
        .repo-card:nth-child(2) { animation-delay: 100ms; }
        .repo-card:nth-child(3) { animation-delay: 150ms; }
        .repo-card:nth-child(4) { animation-delay: 200ms; }
        .repo-card:nth-child(5) { animation-delay: 250ms; }
        .repo-card:nth-child(6) { animation-delay: 300ms; }
        .repo-card:nth-child(7) { animation-delay: 350ms; }
        .repo-card:nth-child(8) { animation-delay: 400ms; }
        .repo-card:hover {
            transform: translateY(-2px);
            border-color: oklch(80% 0.02 260);
            box-shadow: 0 4px 20px oklch(0% 0 0 / 0.08);
        }
        .repo-card:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
        .repo-card.rank-1 {
            border-left: 4px solid var(--rank-gold);
            background: linear-gradient(135deg, oklch(98% 0.02 85), var(--bg-card));
        }
        .repo-card.rank-2 { border-left: 4px solid var(--rank-silver); }
        .repo-card.rank-3 { border-left: 4px solid var(--rank-bronze); }
        .repo-header {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            margin-bottom: var(--space-sm);
            padding-bottom: var(--space-sm);
            border-bottom: 1px solid var(--border);
        }
        .rank-badge {
            flex-shrink: 0;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-display);
            font-size: 16px;
            font-weight: 700;
            border-radius: 10px;
            background: oklch(94% 0.005 260);
            color: var(--fg-muted);
        }
        .rank-1 .rank-badge {
            background: var(--rank-gold);
            color: oklch(30% 0.02 85);
            box-shadow: 0 2px 8px oklch(75% 0.15 85 / 0.25);
        }
        .rank-2 .rank-badge { background: var(--rank-silver); color: oklch(35% 0.01 260); }
        .rank-3 .rank-badge { background: var(--rank-bronze); color: oklch(30% 0.02 55); }
        .repo-title-group { flex: 1; min-width: 0; }
        .repo-title {
            font-family: var(--font-display);
            font-size: 17px;
            font-weight: 600;
            color: var(--fg-primary);
            text-decoration: none;
            transition: color var(--duration-fast) var(--ease-out);
            word-break: break-word;
            display: block;
        }
        .repo-title:hover { color: var(--accent); }
        .repo-title:focus {
            outline: none;
            text-decoration: underline;
            text-decoration-color: var(--accent);
            text-underline-offset: 3px;
        }
        .repo-meta {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: var(--space-sm);
            font-size: 12px;
            margin-top: 4px;
        }
        .meta-item {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: var(--fg-muted);
        }
        .meta-item.lang { color: var(--fg-secondary); font-weight: 500; }
        .meta-item.lang::before {
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
            opacity: 0.8;
        }
        .stars-today {
            display: inline-flex;
            align-items: center;
            gap: 3px;
            padding: 2px 8px;
            background: oklch(92% 0.08 145);
            color: oklch(40% 0.15 145);
            border-radius: 6px;
            font-weight: 600;
            font-size: 11px;
        }
        .repo-content { display: grid; gap: var(--space-sm); flex: 1; }
        .content-section { display: flex; gap: var(--space-sm); }
        .section-label {
            flex-shrink: 0;
            width: 64px;
            font-size: 10px;
            font-weight: 600;
            color: var(--section-label);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding-top: 2px;
        }
        .section-content {
            flex: 1;
            font-size: 13px;
            color: var(--fg-secondary);
            line-height: 1.6;
        }
        .footer {
            text-align: center;
            margin-top: var(--space-2xl);
            padding-top: var(--space-xl);
            border-top: 1px solid var(--border);
            font-size: 12px;
            color: var(--fg-muted);
        }
        .footer a {
            color: var(--fg-secondary);
            text-decoration: none;
            transition: color var(--duration-fast);
        }
        .footer a:hover { color: var(--accent); }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }
        }
        @media (max-width: 600px) {
            .container { padding: var(--space-lg) var(--space-md); }
            .repo-card { padding: var(--space-md); }
            .content-section { flex-direction: column; gap: var(--space-xs); }
            .section-label { width: auto; }
            .repo-header { flex-wrap: wrap; }
            .repo-list { grid-template-columns: 1fr; }
        }
        @media (max-width: 900px) { .repo-list { grid-template-columns: 1fr; } }
        @media (min-width: 1400px) { .repo-list { grid-template-columns: repeat(3, 1fr); } }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-label">Daily Digest</div>
            <h1>GitHub Trending</h1>
            <p class="header-date">''' + date_str + '''</p>
        </header>
        <main class="repo-list">
'''
    
    for repo in repos:
        rank_class = ''
        if repo['rank'] == 1:
            rank_class = ' rank-1'
        elif repo['rank'] == 2:
            rank_class = ' rank-2'
        elif repo['rank'] == 3:
            rank_class = ' rank-3'
        
        # 获取描述，如果没有则使用默认描述
        desc = descriptions.get(repo['full_name'], {
            'overview': repo['description'] or '暂无描述',
            'scenario': '适用于需要此功能的开发者和团队。',
            'solution': '提供完整的解决方案和实现方式。'
        })
        
        html_template += f'''            <article class="repo-card{rank_class}">
                <div class="repo-header">
                    <span class="rank-badge">{repo['rank']}</span>
                    <div class="repo-title-group">
                        <a href="{repo['url']}" class="repo-title" target="_blank" rel="noopener">
                            {repo['name']}
                        </a>
                        <div class="repo-meta">
                            <span class="meta-item lang">{repo['language']}</span>
                            <span class="meta-item">⭐ {repo['total_stars']}</span>
                            <span class="stars-today">+{repo['stars_today']} 今日</span>
                        </div>
                    </div>
                </div>
                <div class="repo-content">
                    <div class="content-section">
                        <span class="section-label">项目概述</span>
                        <p class="section-content">{desc['overview']}</p>
                    </div>
                    <div class="content-section">
                        <span class="section-label">用户场景</span>
                        <p class="section-content">{desc['scenario']}</p>
                    </div>
                    <div class="content-section">
                        <span class="section-label">解决方案</span>
                        <p class="section-content">{desc['solution']}</p>
                    </div>
                </div>
            </article>
'''
    
    html_template += '''        </main>
        <footer class="footer">
            <p>基于 <a href="https://impeccable.style" target="_blank" rel="noopener">Impeccable</a> 设计原则 · 每日自动更新</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html_template

def main():
    print("🔍 开始抓取 GitHub Trending...")
    
    try:
        repos = fetch_github_trending()
        print(f"✅ 成功抓取 {len(repos)} 个仓库")
        
        # 获取当前日期
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        # 生成 HTML
        html = generate_html(repos, date_str)
        
        # 写入文件
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📝 已生成 index.html ({date_str})")
        
        # 同时保存 JSON 数据供参考
        with open('trending_data.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date': date_str,
                'repos': repos
            }, f, ensure_ascii=False, indent=2)
        
        print("✨ 完成！")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        raise

if __name__ == '__main__':
    main()
