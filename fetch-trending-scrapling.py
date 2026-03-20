#!/usr/bin/env python3
"""
GitHub Trending 抓取脚本 - Scrapling 版本
使用 Scrapling 优化 HTML 解析，带 fallback 到 BeautifulSoup
支持 AI 自动生成项目描述
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from scrapling.fetchers import Fetcher

# OpenAI 客户端（用于自动生成描述）
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("⚠️ openai 未安装，自动生成描述功能禁用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_description_with_ai(repo):
    """使用 AI 自动生成项目描述"""
    if not HAS_OPENAI:
        return None
    
    # 检查 API Key（优先环境变量，其次从 ~/.openclaw/.env.openai 读取）
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        # 从 OpenClaw 环境文件读取
        env_file = os.path.expanduser('~/.openclaw/workspace/.env.openai')
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith('OPENAI_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        break
    if not api_key:
        logger.warning("⚠️ OPENAI_API_KEY 未设置，跳过自动生成")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""请为以下 GitHub 项目生成中文描述：

项目名：{repo['name']}
原始描述：{repo['description']}
语言：{repo['language']}
今日新增：+{repo['stars_today']} stars

请严格按照以下 JSON 格式输出（不要添加任何其他内容）：
{{
  "overview": "一句话项目概述（50字以内）",
  "scenario": "具体用户场景和痛点（80字以内）",
  "solution": "核心解决方案（60字以内）"
}}

要求：
1. overview：简洁概括项目是什么
2. scenario：描述具体的使用场景和用户痛点
3. solution：列出核心功能或技术方案"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个技术文档撰写专家，擅长用简洁的中文描述开源项目。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        # 尝试解析 JSON
        # 去除可能的 markdown 代码块标记
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        
        desc = json.loads(content)
        
        logger.info(f"✅ AI 生成描述成功: {repo['name']}")
        return desc
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ AI 生成失败: {e}")
        return None


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
        'opendataloader-project/opendataloader-pdf': {
            'overview': 'opendataloader-pdf是一个用于处理PDF文件的开源项目，旨在为AI提供可用数据。',
            'scenario': '用户在处理大量PDF文档时常面临数据提取困难，影响信息获取和分析效率。',
            'solution': '该项目自动化PDF可访问性，提供高效的PDF解析功能，便于生成AI可用的数据。'
        },
        'mobile-dev-inc/Maestro': {
            'overview': 'Maestro 是一个简化移动和网页端的端到端自动化测试工具。',
            'scenario': '开发者在进行移动和网页应用测试时，常面临复杂的自动化流程，耗时且易出错，影响开发效率。',
            'solution': '通过简洁的脚本和强大的框架，Maestro 提供易用的自动化测试功能，支持快速集成和高效执行。'
        },
        'louis-e/arnis': {
            'overview': '一个开源项目，用于在Minecraft中生成高细节的真实世界地点。',
            'scenario': '玩家希望在Minecraft中重现真实世界的地点，以增加游戏的沉浸感和探索乐趣，但现有工具无法满足高细节需求。',
            'solution': '该项目利用Rust语言生成高精度的真实地理位置，并将其转换为Minecraft可用的地图数据。'
        },
        'unslothai/unsloth': {
            'overview': '一个统一的网页用户界面，用于本地训练和运行开源模型，如Qwen、DeepSeek、gpt-oss和Gemma。',
            'scenario': '用户希望在本地环境中轻松训练和运行多个开源AI模型，但面对复杂的设置和操作流程感到困扰。',
            'solution': '提供统一的Web界面，简化模型训练和运行的流程，支持多种开源模型，提升用户体验。'
        },
        'newton-physics/newton': {
            'overview': 'newton 是一个开源的物理仿真引擎，利用 NVIDIA Warp 加速，专为机器人和仿真研究者设计。',
            'scenario': '机器人开发者和仿真研究人员需要高效的物理仿真工具，以便在真实环境中测试算法和设计，传统的仿真引擎往往性能不足，难以满足需求。',
            'solution': 'newton 提供 GPU 加速的物理模拟，支持复杂的物理交互，为用户提供高效、逼真的仿真体验。'
        },
        'shadps4-emu/shadPS4': {
            'overview': 'shadPS4是一个用于Windows、Linux和macOS的PlayStation 4模拟器，采用C++编写。',
            'scenario': '游戏玩家希望在不同操作系统上体验PS4游戏，但缺乏兼容的平台，导致无法享受游戏乐趣。',
            'solution': '提供高效的PS4游戏模拟，让玩家能够在多种操作系统上运行和体验PS4游戏。'
        },
        'langchain-ai/open-swe': {
            'overview': 'open-swe 是一个开源的异步编码助手，旨在提高编程效率。',
            'scenario': '开发者在编写代码时常遇到效率低下和重复劳动的问题，尤其在处理异步任务时更为明显。',
            'solution': '该项目提供了异步编程的智能支持，简化了代码编写过程，并自动处理复杂的异步逻辑。'
        },
        'codecrafters-io/build-your-own-x': {
            'overview': '通过从零开始重建您最喜欢的技术，掌握编程技能。',
            'scenario': '许多开发者希望深入理解技术原理，但缺乏实践机会。通过重建经典项目，他们能够提高编程能力，解决技术盲区。',
            'solution': '提供一系列项目指南，用户可以逐步实现各种技术，涵盖编程语言、框架和工具的核心概念。'
        },
        'langchain-ai/deepagents': {
            'overview': '深度智能体框架，基于LangChain和LangGraph构建。',
            'scenario': '用户需要处理复杂的任务时，常常面临子任务管理和资源调配的挑战。此项目旨在提供一种高效的方式来组织和执行这些任务。',
            'solution': '提供规划工具、文件系统后端和生成子智能体的能力，支持复杂的智能任务处理。'
        },
        'jarrodwatts/claude-hud': {
            'overview': 'Claude Code 插件，用于显示上下文使用情况、活动工具、运行代理和待办进度。',
            'scenario': '开发人员在使用 Claude Code 时，需要实时了解当前上下文、工具和进度，以便更高效地完成任务，但往往难以获得这些信息。',
            'solution': '该插件通过可视化界面提供实时信息，帮助用户快速掌握工作状态和进度，提升工作效率。'
        },
        'cloudflare/workerd': {
            'overview': 'workerd 是一个支持 JavaScript 和 WebAssembly 的运行时，驱动着 Cloudflare Workers。 ',
            'scenario': '开发者需要在边缘计算平台上快速部署无服务器应用，但常常面临性能和兼容性问题。使用 workerd，可以轻松创建高效的应用，解决延迟和资源限制的挑战。',
            'solution': 'workerd 提供高性能的 JavaScript 和 WebAssembly 运行时，支持轻松的 API 集成，优化了边缘计算的执行效率。'
        },
        '666ghj/MiroFish': {
            'overview': 'MiroFish 是一个简洁通用的群体智能引擎，能够进行各类预测。',
            'scenario': '用户可以在数据分析、市场预测等领域应用 MiroFish，提升决策准确性和效率，解决传统模型灵活性不足的问题。',
            'solution': 'MiroFish 采用先进的群体智能算法，支持多种数据输入，实时生成高精度预测结果。'
        },
        'thedotmack/claude-mem': {
            'overview': 'Claude-mem 是一个 Claude 代码插件，自动记录编码过程中的所有操作，并利用 AI 压缩信息。',
            'scenario': '开发者在编码时常常需要回顾之前的操作和上下文，手动记录信息既繁琐又容易遗漏，影响工作效率。',
            'solution': '该插件自动捕捉编码过程，使用 Claude 的 agent-sdk 压缩信息，并将相关上下文注入未来会话，提升编码效率。'
        },
        'Crosstalk-Solutions/project-nomad': {
            'overview': 'Project N.O.M.A.D 是一款自给自足的离线生存计算机，集成了重要工具、知识和人工智能。',
            'scenario': '用户在偏远地区或灾后环境中，可能面临缺乏信息和资源的问题，无法获取必要的生存知识和工具。',
            'solution': '该项目提供离线访问的生存工具和知识库，以及AI助手，确保用户随时随地获取关键信息。'
        },
        'obra/superpowers': {
            'overview': '一个有效的代理技能框架和软件开发方法论。',
            'scenario': '开发团队在项目管理中常面临技能分配不均和效率低下的问题，影响项目进度和质量。',
            'solution': '提供系统化的技能框架，优化团队协作和任务分配，提高软件开发效率。'
        },
        'abhigyanpatwari/GitNexus': {
            'overview': 'GitNexus 是一款零服务器的代码智能引擎，完全在浏览器中运行，帮助用户创建知识图谱。',
            'scenario': '用户可以将 GitHub 仓库或 ZIP 文件导入 GitNexus，适用于开发者在代码探索中快速获取项目结构和依赖关系，提升工作效率。',
            'solution': '通过交互式知识图谱和内置的 Graph RAG Agent，GitNexus 让代码分析和理解变得更加简单直观。'
        },
        'lightpanda-io/browser': {
            'overview': 'Lightpanda 是一款专为人工智能和自动化设计的无头浏览器。',
            'scenario': '开发者在进行网页抓取、自动化测试或数据分析时，常面临浏览器交互复杂、效率低下的问题。',
            'solution': 'Lightpanda 提供高性能的无头浏览功能，支持自动化操作，简化网页处理流程，提升效率。'
        },
        'volcengine/OpenViking': {
            'overview': 'OpenViking是一个开源的上下文数据库，专为AI代理（如openclaw）设计。',
            'scenario': '在复杂的AI应用中，代理需要高效管理上下文信息，包括记忆、资源和技能，传统方式难以满足动态和层次化的需求。',
            'solution': 'OpenViking通过文件系统范式统一管理上下文，支持层次化上下文传递与自我演化，提升AI代理的智能化水平。'
        },
        'shareAI-lab/learn-claude-code': {
            'overview': '一个基于 TypeScript 的轻量级 Claude Code 风格代理，旨在简化 Bash 脚本编写。',
            'scenario': '开发者在编写 Bash 脚本时常面临语法复杂和功能限制的问题，本项目提供了类似 Claude 的智能助手，帮助用户快速生成脚本。',
            'solution': '通过智能代码生成和自动补全功能，提升 Bash 脚本编写效率，减少错误率。'
        },
        '666ghj/MiroFish': {
            'overview': 'MiroFish是一个简洁通用的群体智能引擎，能够进行各种预测。',
            'scenario': '用户可以在金融、气候、交通等领域利用该引擎进行数据预测，帮助决策，但传统方法往往复杂、效率低下。',
            'solution': 'MiroFish通过先进的群体智能算法，提供快速、准确的预测，支持多种应用场景。'
        },
        'thedotmack/claude-mem': {
            'overview': 'Claude-mem 是一个 Claude 代码插件，自动捕捉编码过程中的操作并优化上下文。',
            'scenario': '开发者在编码时常常需要回忆之前的工作，但上下文信息容易遗忘，影响效率。该插件帮助用户自动记录和恢复这些信息。',
            'solution': '通过 Claude 的 agent-sdk，自动捕捉和压缩编码过程中的关键信息，并在未来会话中注入相关上下文。'
        },
        'Crosstalk-Solutions/project-nomad': {
            'overview': 'Project N.O.M.A.D 是一款离线生存计算机，集成必要工具、知识和人工智能，随时随地为用户提供支持。',
            'scenario': '在偏远地区或自然灾害中，用户可能缺乏信息和资源，无法获取生存所需的知识和工具，面临生存困境。',
            'solution': '该项目提供离线访问的生存工具和知识库，并结合人工智能帮助用户获取实时信息和应对策略。'
        },
        'obra/superpowers': {
            'overview': 'superpowers是一个有效的技能框架和软件开发方法论，旨在提升开发效率。',
            'scenario': '开发者在项目管理中常面临技能不足、协作不畅和效率低下的问题，导致项目进展缓慢。',
            'solution': '提供系统化的技能提升框架和方法论，帮助开发团队高效协作，提升软件开发质量与速度。'
        },
        'abhigyanpatwari/GitNexus': {
            'overview': 'GitNexus 是一款零服务器的代码智能引擎，可以在浏览器中创建知识图谱。',
            'scenario': '用户只需将 GitHub 仓库或 ZIP 文件导入，便能轻松探索代码，解决传统工具无法快速获取代码结构和关系的问题。',
            'solution': 'GitNexus 通过在浏览器中生成互动知识图谱，并内置 Graph RAG Agent，实现高效的代码分析和探索。'
        },
        'lightpanda-io/browser': {
            'overview': 'Lightpanda是一个为AI和自动化设计的无头浏览器。',
            'scenario': '开发者在进行网页自动化测试、数据抓取时，常常需要一个轻量级且高效的浏览器。传统浏览器占用资源大，操作繁琐，影响开发效率。',
            'solution': 'Lightpanda提供高效的无头浏览功能，支持快速页面加载和自动化操作，极大提升开发者的工作效率。'
        },
        'volcengine/OpenViking': {
            'overview': 'OpenViking是一个开源上下文数据库，专为AI代理（如openclaw）设计。',
            'scenario': '在复杂的AI应用中，代理需要有效管理上下文信息（如记忆、资源和技能），以便适应不同场景并提供精准服务。现有解决方案往往难以满足这一需求。',
            'solution': 'OpenViking通过文件系统范式统一管理上下文，实现层级上下文交付和自我演化，简化了AI代理的信息管理。'
        },
        'shareAI-lab/learn-claude-code': {
            'overview': 'learn-claude-code是一个基于TypeScript构建的轻量级智能助手，灵感来源于Claude Code。',
            'scenario': '用户在开发过程中常常需要快速获取代码示例和建议，现有工具往往复杂或不够直观，影响开发效率。',
            'solution': '该项目通过简化的命令行界面，提供智能代码建议和示例，帮助开发者快速解决问题。'
        },
        'lightpanda-io/browser': {
            'overview': 'Lightpanda是一个为AI和自动化设计的无头浏览器，使用Zig语言构建。',
            'scenario': '开发者需要在无界面的环境中进行网页抓取、自动化测试或数据提取，但现有工具效率低下或不支持特定需求。',
            'solution': 'Lightpanda提供高效的无头浏览功能，支持快速网页渲染和数据处理，适合自动化任务和AI应用。'
        },
        'Crosstalk-Solutions/project-nomad': {
            'overview': 'Project N.O.M.A.D 是一款自给自足的离线生存计算机，包含关键工具和知识。',
            'scenario': '在偏远地区或灾难情况下，用户可能缺乏信息和资源。此项目帮助用户随时获取生存知识和工具，提升应对能力。',
            'solution': '该项目集成了知识库、实用工具和人工智能，确保用户在任何时间、任何地点都能获得重要信息和支持。'
        },
        'volcengine/OpenViking': {
            'overview': 'OpenViking是一个专为AI代理设计的开源上下文数据库，提供统一的上下文管理。',
            'scenario': '在AI代理（如openclaw）中，管理上下文（记忆、资源和技能）往往复杂且碎片化，影响代理的性能和适应能力。',
            'solution': 'OpenViking采用文件系统范式，实现分层上下文传递和自我演化，简化上下文管理。'
        },
        'shareAI-lab/learn-claude-code': {
            'overview': '一个基于 TypeScript 的轻量级 Claude Code 类代理，从零开始构建，简单易用。',
            'scenario': '开发者在编写 Bash 脚本时常遇到复杂的代码逻辑，难以快速实现自动化任务。该项目旨在简化这一过程，为用户提供智能化的代码辅助。',
            'solution': '通过使用 TypeScript 开发的智能代理，提供代码自动生成和建议，提升 Bash 脚本编写的效率和准确性。'
        },
        'shanraisshan/claude-code-best-practice': {
            'overview': '这是一个旨在提升代码编写最佳实践的开源项目。',
            'scenario': '开发者在编写代码时常常缺乏规范，导致代码质量参差不齐，难以维护和协作。该项目帮助开发者学习和应用最佳实践。',
            'solution': '提供一系列代码示例和指导，帮助开发者掌握高效、可维护的编码技巧。'
        },
        'obra/superpowers': {
            'overview': 'superpowers 是一个代理技能框架和软件开发方法论，旨在提升开发效率。',
            'scenario': '开发者在项目管理和技能提升过程中常常面临方法不明确、效率低下的问题，导致进度延误和资源浪费。',
            'solution': '提供一套系统化的开发方法和技能框架，帮助团队优化工作流程，提升项目执行力和协作效率。'
        },
        'p-e-w/heretic': {
            'overview': 'heretic 是一个针对语言模型的全自动审查内容移除工具。',
            'scenario': '在使用语言模型时，用户常常遇到审查导致的信息缺失，影响模型的表现和应用。heretic 旨在解决这一问题，帮助用户获取更完整的信息。',
            'solution': '该项目通过先进的算法自动检测并去除审查内容，提升语言模型的输出质量和准确性。'
        },
        '666ghj/MiroFish': {
            'overview': 'MiroFish是一个简单而通用的群体智能引擎，能够进行各种预测。',
            'scenario': '在数据分析、市场预测和智能决策中，用户常常面临复杂的数据模式和不确定性，MiroFish可以帮助用户从数据中提取有价值的洞察。',
            'solution': '通过群体智能算法，MiroFish实现高效的预测功能，适用于多种领域，支持自定义模型和数据输入。'
        },
        # 2026-03-16 新增项目
        'Crosstalk-Solutions/project-nomad': {
            'overview': '离线生存计算项目。内置关键工具、知识库和 AI 能力，确保在任何时间、任何地点都能获取信息和做出决策。',
            'scenario': '网络不可用或受限的场景：户外探险、应急响应、远程工作、隐私敏感环境。需要离线访问关键工具和知识，但现有方案依赖云端服务。',
            'solution': '自包含架构 + 离线 AI 模型 + 本地知识库 + 多工具集成 + 低功耗优化。'
        },
        'shareAI-lab/learn-claude-code': {
            'overview': 'Claude Code 学习项目。从零到一构建一个迷你版 Claude Code Agent，完整实现核心功能。',
            'scenario': '开发者想理解 Claude Code 的工作原理、学习 Agent 架构设计、掌握 AI 编程助手的实现方法。',
            'solution': '渐进式教程 + 完整代码示例 + 架构解析 + 实战练习。'
        },
        'shanraisshan/claude-code-best-practice': {
            'overview': 'Claude Code 最佳实践集合。提供项目上下文模板、问题解决格式、开发方法论。',
            'scenario': '想让 Claude Code 更好地理解项目、生成更符合规范的代码、遵循统一的开发流程。',
            'solution': 'Markdown 上下文模板 + 问题-解决方案格式 + 代码规范 + 工作流指南。'
        },
        'obra/superpowers': {
            'overview': '实用的 Agent 技能框架和软件开发方法论。提供可复用的技能模式和最佳实践。',
            'scenario': 'AI Agent 开发者需要一套成熟的技能框架，避免从零设计、提高开发效率、保证质量。',
            'solution': '模块化技能设计 + 标准化接口 + 测试框架 + 部署指南。'
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
    """保存数据到 JSON 文件，    自动为缺失描述的项目生成描述
    """
    # 获取当前日期
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    # 创建 data 目录
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # 获取现有描述
    descriptions = get_descriptions()
    
    # 检查并生成缺失的描述
    logger.info("🔍 检查项目描述完整性...")
    new_descriptions = {}
    
    for repo in repos:
        full_name = repo['full_name']
        if full_name not in descriptions:
            logger.info(f"⚠️ 缺失描述: {full_name}")
            
            # 尝试使用 AI 生成
            logger.info(f"🤖 正在使用 AI 生成描述: {full_name}")
            ai_desc = generate_description_with_ai(repo)
            
            if ai_desc:
                new_descriptions[full_name] = ai_desc
                descriptions[full_name] = ai_desc
                logger.info(f"✅ 已生成: {full_name}")
            else:
                # 使用默认模板
                logger.warning(f"⚠️ AI 生成失败，使用默认模板: {full_name}")
                descriptions[full_name] = {
                    'overview': repo.get('description', '暂无描述'),
                    'scenario': '当前面临的具体痛点：用户需要解决什么问题，遇到什么困难。',
                    'solution': '从以下几个方面提供解决方案：1) 核心功能实现 2) 性能优化 3) 易用性改进。'
                }
    
    # 如果有新生成的描述，更新描述字典文件
    if new_descriptions:
        logger.info(f"📝 更新描述字典，新增 {len(new_descriptions)} 个项目")
        # 将新描述保存到文件中（追加到 get_descriptions 函数）
        update_descriptions_file(new_descriptions)
    
    # 准备数据
    data = {
        'date': date_str,
        'repos': repos,
        'descriptions': descriptions
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


def update_descriptions_file(new_descriptions):
    """将新生成的描述追加到描述文件"""
    script_file = Path(__file__)
    
    # 读取当前脚本内容
    with open(script_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到 get_descriptions 函数的 return 语句
    # 在第一个项目之前插入新描述
    lines = content.split('\n')
    insert_index = None
    
    for i, line in enumerate(lines):
        if 'def get_descriptions():' in line:
            # 找到函数后的第一个 return {
            for j in range(i, min(i + 20, len(lines))):
                if 'return {' in lines[j]:
                    insert_index = j + 1
                    break
            break
    
    if insert_index is None:
        logger.error("❌ 无法找到插入位置")
        return
    
    # 生成新描述的代码
    new_lines = []
    for full_name, desc in new_descriptions.items():
        new_lines.append(f"        '{full_name}': {{")
        new_lines.append(f"            'overview': '{desc['overview']}',")
        new_lines.append(f"            'scenario': '{desc['scenario']}',")
        new_lines.append(f"            'solution': '{desc['solution']}'")
        new_lines.append("        },")
    
    # 插入新描述
    for i, line in enumerate(new_lines):
        lines.insert(insert_index + i, line)
    
    # 写回文件
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    logger.info(f"✅ 已将 {len(new_descriptions)} 个描述写入脚本文件")


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
