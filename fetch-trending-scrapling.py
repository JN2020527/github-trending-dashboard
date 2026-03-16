#!/usr/bin/env python3
"""
GitHub Trending 抓取脚本 - Scrapling 版本
使用 Scrapling 优化 HTML 解析，带 fallback 到 BeautifulSoup
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from scrapling.fetchers import Fetcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_with_scrapling():
    """使用 Scrapling 抓取 GitHub Trending"""
    logger.info("🚀 使用 Scrapling Fetcher 抓取...")
    
    try:
        page = Fetcher.get('https://github.com/trending')
        
        # 检查 HTTP 状态码
        if page.status != 200:
            raise Exception(f"HTTP {page.status}: 请求失败")
        repos = []
        
        # 使用自适应选择器
        articles = page.css('article.Box-row', adaptive=True)[:8]
        
        for i, article in enumerate(articles):
            try:
                # 提取仓库路径
                h2_links = article.css('h2 a', adaptive=True)
                if not h2_links:
                    logger.warning(f"Repo {i+1}: 无法找到 h2 a 元素")
                    continue
                
                h2_link = h2_links[0]
                repo_path = h2_link.attrib.get('href', '').strip('/')
                repo_name = repo_path.replace('/', ' / ')
                
                # 提取描述
                desc_elems = article.css('p.col-9', adaptive=True)
                description = desc_elems[0].get_all_text(strip=True) if desc_elems else ''
                
                # 提取语言
                lang_elems = article.css('[itemprop="programmingLanguage"]', adaptive=True)
                language = lang_elems[0].get_all_text(strip=True) if lang_elems else 'Unknown'
                
                # 提取总 star 数
                stars_elems = article.css('a[href$="/stargazers"]', adaptive=True)
                total_stars = stars_elems[0].get_all_text(strip=True) if stars_elems else '0'
                
                # 提取今日新增 star
                stars_today_elems = article.css('span.d-inline-block.float-sm-right', adaptive=True)
                stars_today = '0'
                if stars_today_elems:
                    stars_today_text = stars_today_elems[0].get_all_text(strip=True)
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
                
                logger.debug(f"✅ Repo {i+1}: {repo_name}")
                
            except Exception as e:
                logger.error(f"❌ 解析 repo {i+1} 失败: {e}")
                continue
        
        logger.info(f"✅ Scrapling 抓取成功: {len(repos)} 个仓库")
        return repos
        
    except Exception as e:
        logger.error(f"❌ Scrapling 抓取失败: {e}")
        raise


def fetch_with_beautifulsoup():
    """Fallback: 使用 BeautifulSoup 抓取（旧逻辑）"""
    logger.info("🔄 使用 BeautifulSoup Fallback...")
    
    url = "https://github.com/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    repos = []
    
    articles = soup.select('article.Box-row')[:8]
    
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
            logger.error(f"❌ 解析 repo {i+1} 失败: {e}")
            continue
    
    logger.info(f"✅ BeautifulSoup 抓取成功: {len(repos)} 个仓库")
    return repos


def fetch_github_trending():
    """主函数：带 fallback 逻辑"""
    try:
        # 优先使用 Scrapling
        return fetch_with_scrapling()
    except Exception as e:
        logger.warning(f"⚠️ Scrapling 失败，降级到 BeautifulSoup: {e}")
        try:
            # Fallback 到 BeautifulSoup
            return fetch_with_beautifulsoup()
        except Exception as e2:
            logger.error(f"❌ BeautifulSoup 也失败了: {e2}")
            raise


def get_descriptions():
    """项目描述数据库"""
    return {
        # 2026-03-16 新增项目
        'Crosstalk-Solutions/project-nomad': {
            'overview': '离线生存计算项目。内置关键工具、知识库和 AI 能力，确保在任何时间、任何地点都能获取信息和做出决策。',
            'scenario': '网络不可用或受限的场景：户外探险、应急响应、远程工作、隐私敏感环境。需要离线访问关键工具和知识，但现有方案依赖云端服务。',
            'solution': '自包含架构 + 离线 AI 模型 + 本地知识库 + 多工具集成 + 低功耗优化。'
        },
        # 2026-03-15 新增项目
        'volcengine/OpenViking': {
            'overview': '专为 AI Agent 设计的开源上下文数据库。通过文件系统范式统一管理 Agent 需要的上下文（记忆、资源、技能），支持分层上下文交付和自我进化。',
            'scenario': 'AI Agent 开发者面临上下文管理混乱：记忆散落各处、资源难以组织、技能无法复用。需要一个系统化的解决方案。',
            'solution': '文件系统式组织结构 + 分层上下文管理 + 自我进化机制 + 开放标准接口。'
        },
        'anthropics/claude-plugins-official': {
            'overview': 'Anthropic 官方维护的高质量 Claude Code 插件目录。精选插件经过严格筛选和测试。',
            'scenario': 'Claude Code 用户想扩展功能，但不知道哪些插件可靠、安全、好用。官方市场缺乏统一入口。',
            'solution': '官方背书 + 质量保证 + 分类索引 + 安装指南 + 持续更新。'
        },
        'dimensionalOS/dimos': {
            'overview': '物理空间的 Agent 操作系统。用自然语言控制人形机器人、四足机器人、无人机等硬件平台，构建多 Agent 系统。',
            'scenario': '硬件开发者想用 AI 控制物理设备，但面临复杂 SDK、硬件兼容性、多设备协调等难题。',
            'solution': '自然语言编程 + 多硬件抽象层 + 多 Agent 协调 + 实时传感器集成。'
        },
        'p-e-w/heretic': {
            'overview': '全自动语言模型审查移除工具。针对模型内置的审查机制进行自动化处理。',
            'scenario': '研究人员需要无审查限制的模型用于学术研究、安全测试，但现有模型都有内置限制。',
            'solution': '自动化审查检测 + 精准移除算法 + 模型完整性保持 + 开源可审计。'
        },
        'langflow-ai/openrag': {
            'overview': '一体化 RAG 平台。基于 Langflow、Docling、Opensearch 构建，提供开箱即用的检索增强生成解决方案。',
            'scenario': '企业想快速部署 RAG 系统，但不想从零搭建各个组件：文档处理、向量检索、生成模型集成。',
            'solution': '一站式安装 + 可视化流程设计 + 多数据源支持 + 生产级部署。'
        },
        'lightpanda-io/browser': {
            'overview': '专为 AI 和自动化设计的无头浏览器。用 Zig 语言编写，高性能、低资源占用。',
            'scenario': 'AI Agent 需要浏览网页，但现有无头浏览器（Puppeteer、Playwright）资源消耗大、启动慢。',
            'solution': 'Zig 原生实现 + 极致性能优化 + 标准 CDP 协议 + AI 友好接口。'
        },
        'fishaudio/fish-speech': {
            'overview': 'SOTA 级开源文本转语音（TTS）系统。高质量、低延迟、多语言支持。',
            'scenario': '开发者需要高质量 TTS 能力，但商业服务昂贵、开源方案质量差、延迟高。',
            'solution': 'SOTA 模型架构 + 多语言训练 + 实时推理优化 + 开源可定制。'
        },
        # 历史项目
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
        },
        'openclaw/openclaw': {
            'overview': '你自己的 AI 助手。任何系统、任何平台。开源、可扩展、支持多模型。',
            'scenario': '需要一个私密、可控的 AI 助手，不想依赖商业服务。',
            'solution': '模块化架构，支持 Claude/GPT/GLM 等多种模型，可自定义 Agent 技能。'
        },
        'karpathy/nanochat': {
            'overview': '100 美元能买到的最好的 ChatGPT。极简、高效、本地运行。',
            'scenario': '想在本地低成本运行一个 ChatGPT 级别的对话系统。',
            'solution': '优化的模型推理，在消费级硬件上实现高性能对话。'
        },
        'alirezarezvani/claude-skills': {
            'overview': '169 个生产级 Claude Code 技能插件，覆盖工程、营销、产品、合规等领域。',
            'scenario': '想扩展 Claude Code 的能力，需要现成的技能插件。',
            'solution': '即装即用的技能库，通过 /plugin marketplace 安装。'
        },
        'Raphire/Win11Debloat': {
            'overview': '轻量级 PowerShell 脚本，移除 Windows 预装应用、禁用遥测、自定义系统。',
            'scenario': '新装的 Windows 有太多预装软件和广告，想清理干净。',
            'solution': '一键脚本，支持 Windows 10 和 11，可自定义清理选项。'
        }
    }


def get_available_dates():
    """获取可用的日期列表"""
    data_dir = Path('data')
    if not data_dir.exists():
        return []
    
    dates = []
    for f in data_dir.iterdir():
        if f.suffix == '.json' and f.stem != 'latest' and f.stem != 'dates':
            date_str = f.stem
            if len(date_str) == 10 and date_str.count('-') == 2:
                dates.append(date_str)
    
    return sorted(dates, reverse=True)


def save_data(repos):
    """保存数据到 JSON 文件"""
    # 获取当前日期
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    # 创建 data 目录
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # 准备数据
    data = {
        'date': date_str,
        'repos': repos,
        'descriptions': get_descriptions()
    }
    
    # 保存到日期文件
    date_file = data_dir / f'{date_str}.json'
    with open(date_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"📝 已保存 {date_file}")
    
    # 更新 latest.json
    latest_file = data_dir / 'latest.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"📝 已更新 data/latest.json")
    
    # 获取可用日期列表
    available_dates = get_available_dates()
    
    # 生成日期列表文件
    dates_file = data_dir / 'dates.json'
    with open(dates_file, 'w', encoding='utf-8') as f:
        json.dump({'dates': available_dates}, f, ensure_ascii=False, indent=2)
    logger.info(f"📝 已更新 data/dates.json ({len(available_dates)} 个日期)")


def git_commit_and_push():
    """Git 提交并推送"""
    import subprocess
    
    try:
        # 检查是否有变更
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not result.stdout.strip():
            logger.info("✅ 没有需要提交的变更")
            return
        
        # 添加变更
        subprocess.run(['git', 'add', 'data/'], check=True, capture_output=True)
        logger.info("📦 已添加 data/ 到暂存区")
        
        # 获取日期
        date = datetime.now().strftime('%Y-%m-%d')
        
        # 提交
        subprocess.run(['git', 'commit', '-m', f'feat: 更新 GitHub Trending 数据 - {date}'], check=True, capture_output=True)
        logger.info(f"✅ 已提交变更: {date}")
        
        # 拉取最新代码
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], check=True, capture_output=True)
        logger.info("🔄 已拉取最新代码")
        
        # 推送
        subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
        logger.info("🚀 已推送到 GitHub")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Git 操作失败: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 未知错误: {e}")
        raise


def main():
    logger.info("🔍 开始抓取 GitHub Trending...")
    
    try:
        repos = fetch_github_trending()
        logger.info(f"✅ 成功抓取 {len(repos)} 个仓库")
        
        save_data(repos)
        
        git_commit_and_push()
        
        logger.info("✨ 完成！")
        
    except Exception as e:
        logger.error(f"❌ 严重错误: {e}")
        raise


if __name__ == '__main__':
    main()
