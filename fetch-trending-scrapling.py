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
        'Blaizzy/mlx-vlm': {
            'overview': 'MLX-VLM 是一个用于在 Mac 上进行视觉语言模型推理和微调的 Python 包。',
            'scenario': '用户希望在 Mac 上高效地使用视觉语言模型进行图片与文本的理解与生成，但缺乏合适的工具和支持。',
            'solution': '提供简单易用的接口，支持视觉语言模型的推理与微调，帮助用户快速实现图文任务。'
        },
        'onyx-dot-app/onyx': {
            'overview': 'Onyx是一个开源的AI平台，支持与各种大型语言模型（LLM）进行智能对话。',
            'scenario': '用户在寻找高效的对话AI工具时，常常面临功能不足或不兼容的问题，导致无法充分利用LLM的能力。',
            'solution': 'Onyx提供先进的对话功能，兼容多种LLM，助力用户实现智能对话和更深层次的交互。'
        },
        'Yeachan-Heo/oh-my-codex': {
            'overview': 'OmX是一个开源工具，可以为代码库添加钩子、代理团队和HUD等功能，提升开发效率。',
            'scenario': '开发者在管理代码库时常常需要定制化的功能和工具，来满足团队的特定需求。OmX提供了灵活的扩展能力，帮助开发者解决这一痛点。',
            'solution': '通过添加钩子、管理代理团队和提供HUD，OmX为开发者提供了强大的定制化和协作工具。'
        },
        'siddharthvaddem/openscreen': {
            'overview': 'OpenScreen 是一个开源项目，旨在免费创建精美演示，无需订阅和水印，支持商业使用。',
            'scenario': '用户需要制作高质量的演示，但现有工具往往收费高、带水印或限制使用，影响创作自由。',
            'solution': '提供无水印、高自由度的演示创建工具，完全开源，适合各种商业和个人用途。'
        },
        'telegramdesktop/tdesktop': {
            'overview': 'Telegram Desktop 是一款基于 Telegram 的桌面消息应用，支持多平台使用。',
            'scenario': '用户在工作或学习时希望通过桌面应用方便地发送和接收消息，但手机操作不够便捷，切换应用影响效率。',
            'solution': '提供实时消息同步、群组聊天、文件共享和多平台支持，提升用户沟通效率。'
        },
        'block/goose': {
            'overview': '一个开源、可扩展的 AI 代理，超越代码建议，支持安装、执行、编辑和测试任意 LLM。',
            'scenario': '开发者在编写代码时常常需要实时获取建议和测试功能，这个过程繁琐且耗时。用户希望能够更高效地与 AI 进行互动，提升开发效率。',
            'solution': '提供完整的 AI 代理功能，支持代码的安装、执行、编辑和测试，简化开发流程。'
        },
        'microsoft/agent-framework': {
            'overview': '一个用于构建、协调和部署AI代理及多代理工作流的框架，支持Python和.NET。',
            'scenario': '用户需要管理多个AI代理进行复杂任务时，常面临协调和部署的挑战，导致效率低下和资源浪费。',
            'solution': '提供简洁的API和工具，支持快速构建代理、灵活的工作流管理以及高效的部署方案，提升开发效率。'
        },
        'sherlock-project/sherlock': {
            'overview': 'Sherlock 是一个用于通过用户名在社交网络上查找社交媒体账户的工具。',
            'scenario': '用户希望通过一个用户名找到可能存在的社交媒体账户，但面对众多平台的分散信息，难以高效查找。这时，Sherlock 提供了一种便捷的解决方案。',
            'solution': '该项目支持多种社交媒体平台的账户查找，用户只需输入用户名即可快速获取相关账户信息。'
        },
        'siddharthvaddem/openscreen': {
            'overview': '开源项目 openscreen 提供免费、无水印的精彩演示创建工具，适用于商业用途。',
            'scenario': '用户需要制作高质量演示，但常常面临收费软件的订阅和水印问题，这限制了他们的创作自由。',
            'solution': 'openscreen 提供无水印的演示创建功能，完全免费且开源，支持商业使用，为用户提供灵活的创作选择。'
        },
        'Yeachan-Heo/oh-my-codex': {
            'overview': 'OmX - Oh My codeX 是一个开源的工具，旨在增强代码管理和协作体验。',
            'scenario': '开发者在项目中常常需要与团队协作，面对代码混乱、版本控制困难等问题，影响工作效率与代码质量。',
            'solution': '通过添加钩子、代理团队、HUD等功能，OmX 提供了灵活的代码管理和协作解决方案，提升开发效率。'
        },
        'asgeirtj/system_prompts_leaks': {
            'overview': '该项目提取了多个AI系统的提示信息，包括ChatGPT、Claude、Gemini等，定期更新。',
            'scenario': '用户需要了解不同AI系统的提示内容以优化应用或进行研究，但获取这些信息较为困难，且更新不及时。',
            'solution': '本项目提供了各大AI系统的系统提示提取，用户可以方便地获取和使用这些信息，支持多种AI模型。'
        },
        'sherlock-project/sherlock': {
            'overview': 'Sherlock 是一个用于根据用户名在社交网络上查找账户的开源工具。',
            'scenario': '用户希望找到某个用户名在多个社交平台上的账户，但手动搜索耗时且效率低下，容易遗漏。',
            'solution': 'Sherlock 通过输入用户名自动查询多个社交网络，快速汇总结果，节省时间并提高准确性。'
        },
        'anthropics/claude-code': {
            'overview': 'Claude Code 是一款运行在终端中的智能编码工具，能理解代码库并加速编码过程。',
            'scenario': '开发者常常在重复性任务和复杂代码理解上耗费大量时间，难以专注于核心开发。Claude Code 可以通过自然语言命令简化这些流程。',
            'solution': '该工具执行常规任务、解释复杂代码并处理 git 工作流，提升开发效率。'
        },
        'microsoft/VibeVoice': {
            'overview': 'VibeVoice是一个开源的前沿语音人工智能项目，旨在提升语音交互体验。',
            'scenario': '用户在日常生活中需要更自然的语音助手，现有语音助手常常无法理解复杂指令或上下文，导致用户体验不佳。',
            'solution': 'VibeVoice通过先进的自然语言处理和深度学习技术，实现更智能的语音理解和响应，提供流畅的交互体验。'
        },
        'google-research/timesfm': {
            'overview': 'TimesFM 是由 Google Research 开发的预训练时间序列基础模型，专用于时间序列预测。',
            'scenario': '在金融、气象等领域，用户需要准确预测未来数据，但传统模型往往难以捕捉复杂的时间序列模式，导致预测不准。',
            'solution': 'TimesFM 提供先进的时间序列建模能力，利用深度学习技术提升预测精度，适用于多种时间序列数据的分析与预测。'
        },
        'luongnv89/claude-howto': {
            'overview': '这是一本关于Claude Code的可视化示例指南，涵盖从基础概念到高级代理的内容。',
            'scenario': '开发者在学习Claude Code时，常常缺乏系统的示例和模板，导致理解困难，难以迅速应用。',
            'solution': '提供了易于复制的模板和实例，帮助用户快速掌握Claude Code的使用，提升开发效率。'
        },
        'axios/axios': {
            'overview': 'axios 是一个基于 Promise 的 HTTP 客户端，支持浏览器和 Node.js。',
            'scenario': '在开发 web 应用时，开发者需要发送 HTTP 请求以获取数据，传统的 XMLHttpRequest 使用繁琐，且错误处理不方便，影响开发效率。',
            'solution': 'axios 提供简单易用的 API，支持请求和响应拦截、自动转换 JSON 数据、取消请求和超时设置等功能，极大提升了 HTTP 请求的开发体验。'
        },
        'openai/codex': {
            'overview': '一个轻量级的编码助手，可以在终端中运行，帮助开发者提高效率。',
            'scenario': '开发者在编写代码时常常需要查阅文档或示例，导致效率降低。此工具能够实时提供代码建议，解决了查找信息的痛点。',
            'solution': '通过Rust语言编写，codex 提供智能代码补全和实时示例，提升编程效率，简化开发流程。'
        },
        'f/prompts.chat': {
            'overview': 'f/prompts.chat 是一个开源平台，让用户分享、发现和收藏 ChatGPT 提示。',
            'scenario': '用户在使用 ChatGPT 时常常需要灵感，寻找合适的提示来提高交流效率。社区共享的提示可以帮助用户解决这一痛点。',
            'solution': '提供社区驱动的提示库，用户可以轻松分享和收集提示，同时支持自托管以保障隐私。'
        },
        'anthropics/claude-code': {
            'overview': 'Claude Code 是一款终端中的智能编码工具，帮助开发者提高编码效率。',
            'scenario': '开发者在编写代码时常常面临重复性任务、复杂代码的理解难题和 Git 工作流的管理痛点，影响工作效率。',
            'solution': 'Claude Code 通过自然语言命令执行常规任务、解释复杂代码并管理 Git 工作流，助力快速编码。'
        },
        'google-research/timesfm': {
            'overview': 'TimesFM是由Google Research开发的预训练时间序列基础模型，旨在进行时间序列预测。',
            'scenario': '在金融、气象等领域，企业面临准确预测未来趋势的挑战，传统方法往往难以捕捉复杂的时间序列模式。',
            'solution': 'TimesFM利用深度学习技术，提供高效的时间序列建模，支持多种预测任务，提升预测准确性和效率。'
        },
        'axios/axios': {
            'overview': 'Axios是一个基于Promise的HTTP客户端，适用于浏览器和Node.js。',
            'scenario': '在开发Web应用时，开发者常常需要与服务器进行数据交互，处理请求和响应。传统的XHR请求较为繁琐，容易出错。',
            'solution': 'Axios简化了HTTP请求，支持Promise，提供简洁的API，易于处理响应数据，并自动转换JSON格式。'
        },
        'openai/codex': {
            'overview': 'Codex是一个轻量级的编码助手，能够在终端中运行。',
            'scenario': '开发者在编码时常常需要查找文档和示例，手动搜索耗时且效率低下。Codex可以实时提供代码建议，提升开发效率。',
            'solution': 'Codex通过自然语言处理技术，理解用户意图并生成相应的代码片段，支持多种编程语言，简化了编码过程。'
        },
        'f/prompts.chat': {
            'overview': '一个开源平台，分享、发现和收集社区的 ChatGPT 提示语。',
            'scenario': '用户希望获取高质量的 ChatGPT 提示语以提升聊天效果，但缺乏一个集中获取和分享的渠道，导致信息分散。',
            'solution': '提供社区共享、发现和收藏提示语的功能，支持自我托管，确保隐私与数据安全。'
        },
        'luongnv89/claude-howto': {
            'overview': '这是一个视觉化的示例指南，专注于Claude Code的从基础到高级的应用。',
            'scenario': '开发者在学习Claude Code时常常面临概念抽象和缺乏实践示例的问题，导致上手困难。',
            'solution': '提供易于理解的示例和可直接使用的模板，帮助用户快速掌握Claude Code的应用。'
        },
        'microsoft/VibeVoice': {
            'overview': 'VibeVoice是一个开源的语音AI项目，旨在提升人机交互体验。',
            'scenario': '用户在使用语音助手时，常遇到识别不准确或交互不流畅的问题。VibeVoice可在多种应用场景中提升语音识别的准确性和自然交互。',
            'solution': '通过先进的语音识别技术和自然语言处理，VibeVoice实现高效的语音理解与响应，提供流畅的用户体验。'
        },
        'Yeachan-Heo/oh-my-claudecode': {
            'overview': 'Yeachan-Heo的oh-my-claudecode是一个以团队为中心的多智能体编排工具，专为Claude Code设计。',
            'scenario': '团队在协作开发中常遇到任务分配不均、沟通不畅等问题，导致效率低下和项目进度延误。',
            'solution': '该项目通过多智能体协作，优化任务分配与执行，实现高效的团队协作与项目管理。'
        },
        'shanraisshan/claude-code-best-practice': {
            'overview': '这是一个针对Claude编程的最佳实践示例库，帮助开发者提高代码质量。',
            'scenario': '开发者在使用Claude进行编程时，常常面临代码可读性差和维护困难的问题。该项目提供了实用的示例和最佳实践，帮助用户更好地编写代码。',
            'solution': '项目包含丰富的HTML代码示例和最佳实践指南，旨在提升代码的可读性和可维护性。'
        },
        'NousResearch/hermes-agent': {
            'overview': 'Hermes Agent 是一个与用户共同成长的智能代理，基于 Python 开发。',
            'scenario': '用户在日常工作中需要一个智能助手来自动化任务、提供建议和提高效率，但现有工具无法适应个人需求的变化。',
            'solution': 'Hermes Agent 通过机器学习算法不断优化自身功能，支持个性化定制和任务自动化，提升用户工作效率。'
        },
        'obra/superpowers': {
            'overview': 'superpowers 是一个代理技能框架与软件开发方法论，旨在提升开发效率与协作效果。',
            'scenario': '在软件开发中，团队常面临技能不均、沟通不畅的问题，导致项目进度缓慢和质量下降。开发者需要一种有效的方法来提升自身技能与团队协作。',
            'solution': '通过提供一套系统化的技能框架和开发流程，superpowers 帮助团队更好地识别和应用各自的优势，提高项目执行力。'
        },
        'microsoft/agent-lightning': {
            'overview': '一个高效的训练框架，旨在为AI代理提供支持。',
            'scenario': '开发者在构建AI代理时，常面临训练效率低和资源消耗大的问题，影响项目进度和效果。',
            'solution': '该项目通过优化训练流程和资源管理，提升AI代理的训练效率，降低开发成本。'
        },
        'PaddlePaddle/PaddleOCR': {
            'overview': 'PaddleOCR 是一个强大的轻量级OCR工具包，可将PDF或图像文档转换为结构化数据。',
            'scenario': '用户需要从大量图像或PDF文档中提取文本信息，传统方法效率低且准确性差，影响数据处理。',
            'solution': 'PaddleOCR支持100多种语言，提供高效的OCR识别，简化文档数据提取流程，助力AI应用。'
        },
        'Yeachan-Heo/oh-my-claudecode': {
            'overview': 'Yeachan-Heo的oh-my-claudecode是一个以团队为中心的多智能体编排工具，专为Claude Code设计。',
            'scenario': '在团队协作中，开发者需要高效地管理多个智能体任务，以提高工作效率和协同效果。当前的工具往往无法满足多任务处理的需求，导致沟通不畅和效率低下。',
            'solution': '该项目提供了多智能体的自动编排功能，支持团队协作，优化任务管理，提升开发效率。'
        },
        'microsoft/agent-lightning': {
            'overview': 'Agent-Lightning 是一个用于快速训练 AI 代理的工具，旨在提升开发效率。',
            'scenario': '开发者在构建 AI 代理时常面临训练时间长、配置复杂的问题，导致项目进度缓慢。Agent-Lightning 提供简化的训练流程，帮助开发者高效完成任务。',
            'solution': '该项目利用 Python 构建，提供易于使用的接口和高性能训练框架，支持快速迭代和优化。'
        },
        'PaddlePaddle/PaddleOCR': {
            'overview': 'PaddleOCR 是一个强大的轻量级 OCR 工具包，将PDF或图像文档转化为结构化数据。',
            'scenario': '用户在处理大量文档时，常面临数据提取困难的问题，尤其是多语言文本的识别和转换。PaddleOCR 能有效解决这些痛点。',
            'solution': '支持100+种语言，利用先进的OCR技术，将图像和PDF内容快速转化为可处理的数据，助力AI应用。'
        },
        'luongnv89/claude-howto': {
            'overview': '这是一个关于Claude代码的视觉化示例驱动指南，涵盖从基础概念到高级代理的内容。',
            'scenario': '用户在学习Claude代码时，常面临概念难以理解和缺乏实践示例的问题，导致学习效率低下。',
            'solution': '提供易于理解的示例和可复制的模板，帮助用户快速上手和应用Claude代码。'
        },
        'microsoft/VibeVoice': {
            'overview': 'VibeVoice是一个开源的语音人工智能项目，旨在提供前沿的语音交互技术。',
            'scenario': '用户在需要高效语音识别和自然语言处理的场景中，常常面临现有技术准确率低、响应慢的问题，影响使用体验。',
            'solution': 'VibeVoice通过先进的机器学习算法，提供准确的语音识别、实时语音合成和自然对话能力，提升用户体验。'
        },
        'NousResearch/hermes-agent': {
            'overview': 'Hermes-Agent 是一个可扩展的智能代理，旨在根据用户需求不断成长和优化。',
            'scenario': '用户在处理复杂任务时常常感到力不从心，需求不断变化，传统工具难以适应。这使得用户需要一个灵活且智能的助手来提升效率。',
            'solution': 'Hermes-Agent 提供自适应学习和任务管理功能，能够根据用户的反馈进行优化，帮助用户更高效地完成工作。'
        },
        'OpenBB-finance/OpenBB': {
            'overview': 'OpenBB是一个面向分析师、量化研究者和AI代理的金融数据平台。',
            'scenario': '用户可以在金融分析、投资决策和算法交易中面临数据获取难、分析效率低的问题。',
            'solution': '提供丰富的金融数据接口，支持数据分析和可视化，方便用户进行高效决策。'
        },
        'obra/superpowers': {
            'overview': '一个有效的技能框架和软件开发方法论，旨在提升开发效率。',
            'scenario': '开发团队常面临技能不均、协作不畅的问题，导致项目进展缓慢和质量不高。用户需要一种系统化的方法来提升团队整体能力。',
            'solution': '提供了一套全面的技能框架和方法论，助力团队快速适应变化，提高协作效率。'
        },
        'thedotmack/claude-mem': {
            'overview': 'Claude-mem 是一个 Claude 代码插件，自动记录编码会话中的所有操作，并利用 AI 压缩信息。',
            'scenario': '开发者在编码时常常需要回顾之前的操作和上下文，但手动记录繁琐且容易遗漏，影响工作效率。',
            'solution': '该插件自动捕捉编码过程，利用 Claude 的 agent-sdk 压缩信息，并在未来会话中注入相关上下文，提高编码效率。'
        },
        'hacksider/Deep-Live-Cam': {
            'overview': 'Deep-Live-Cam 是一个基于单张图片实现实时换脸和一键视频深度伪造的 Python 项目。',
            'scenario': '用户可以在视频通话或直播中，通过该工具快速替换自己的面孔，以实现娱乐或隐私保护，但缺乏专业技能的用户往往难以完成此类操作。',
            'solution': '项目提供简单易用的界面，用户只需上传一张图片即可实现实时换脸，支持多种视频格式，降低了深度伪造的技术门槛。'
        },
        'mvanhorn/last30days-skill': {
            'overview': '一个AI代理技能，能够跨越多个平台研究主题并合成总结。',
            'scenario': '用户可能需要快速了解某个话题的全面信息，但在多个平台上查找信息费时费力。此项目为用户提供了一个便捷的解决方案。',
            'solution': '该项目整合了Reddit、X、YouTube等多平台信息，生成有依据的主题总结。'
        },
        'luongnv89/claude-howto': {
            'overview': '这是一本针对Claude Code的视觉化示例指南，涵盖基础概念到高级代理，提供即插即用的模板。',
            'scenario': '开发者在学习和使用Claude Code时，常常面临概念抽象和示例缺乏的问题，导致难以快速上手和实现功能。',
            'solution': '通过详尽的示例和易于复制的模板，帮助用户快速理解和应用Claude Code，提高开发效率。'
        },
        'microsoft/VibeVoice': {
            'overview': 'VibeVoice 是一个开源的语音 AI 项目，旨在为用户提供前沿的语音交互体验。',
            'scenario': '用户在语音助手、智能家居等场景中，常常面临语音识别不准确和交互不流畅的问题，影响使用体验。',
            'solution': 'VibeVoice 采用先进的语音识别技术和自然语言处理算法，提供精准的语音识别和高效的交互能力。'
        },
        'OpenBB-finance/OpenBB': {
            'overview': 'OpenBB 是一个为分析师、量化研究员和 AI 代理提供的金融数据平台。',
            'scenario': '分析师需要实时金融数据进行决策，而量化研究员则希望通过数据分析优化交易策略，现有工具往往数据孤立且难以整合。',
            'solution': 'OpenBB 提供丰富的金融数据接口，支持数据分析、可视化和算法交易，帮助用户高效获取和利用数据。'
        },
        'hacksider/Deep-Live-Cam': {
            'overview': 'Deep-Live-Cam 是一个基于单张图片的实时人脸交换与一键视频深度伪造工具。',
            'scenario': '用户希望在视频中快速实现人脸替换或制作深度伪造内容，但常常面临复杂的操作和技术门槛。',
            'solution': '项目提供简单易用的接口，用户只需上传一张图片即可实现实时人脸交换和深度伪造，极大降低了使用门槛。'
        },
        'pascalorg/editor': {
            'overview': '这是一个基于 TypeScript 的编辑器项目，旨在提供高效的代码编辑体验。',
            'scenario': '开发者需要一个功能强大且易于使用的编辑器，以提高编码效率和完成项目。传统编辑器可能缺乏个性化和智能提示，影响工作流。',
            'solution': '该编辑器支持丰富的插件扩展、智能代码补全和实时预览，帮助开发者提升生产力。'
        },
        'bytedance/deer-flow': {
            'overview': 'Deer-Flow是一个开源的超级代理框架，支持研究、编码和创作。',
            'scenario': '用户可在不同任务场景中使用Deer-Flow，尤其是需要处理复杂任务时，如数据分析和自动化脚本，节省大量时间和精力。',
            'solution': '项目通过沙箱、记忆、工具、技能、子代理和消息网关，处理从几分钟到几小时的多层次任务。'
        },
        'supermemoryai/supermemory': {
            'overview': '超高速、可扩展的记忆引擎与应用，专为AI时代设计的记忆API。',
            'scenario': '在处理大规模数据时，用户常面临存取速度慢、扩展性不足的问题，影响AI应用的性能与效率。',
            'solution': '提供高效的记忆引擎，支持快速数据存取和横向扩展，满足AI应用的需求。'
        },
        'FujiwaraChoki/MoneyPrinterV2': {
            'overview': 'MoneyPrinterV2 是一个自动化线上赚钱的工具，帮助用户轻松获取收入。',
            'scenario': '许多用户在寻找线上赚钱的机会，但常常面临时间和技术能力不足的问题。该项目旨在简化这一过程，让每个人都能参与进来。',
            'solution': '通过自动化脚本和高效算法，MoneyPrinterV2 能够快速生成收入，降低用户的操作难度。'
        },
        'harry0703/MoneyPrinterTurbo': {
            'overview': 'MoneyPrinterTurbo 是一个基于 AI 大模型的一键高清短视频生成工具。',
            'scenario': '用户需要快速制作短视频用于社交媒体或广告，但缺乏视频编辑技能，传统工具复杂且耗时。',
            'solution': '通过简单操作，利用 AI 自动生成高质量短视频，节省时间并降低制作门槛。'
        },
        'Crosstalk-Solutions/project-nomad': {
            'overview': 'Project N.O.M.A.D 是一款自给自足的离线生存计算机，集成了重要工具、知识和人工智能。',
            'scenario': '用户在偏远地区或灾后环境中可能无法获取信息，面临生存挑战，急需可靠的工具和知识以应对突发情况。',
            'solution': '提供离线访问的生存工具、知识库和AI助手，确保用户随时随地获得所需支持。'
        },
        'TauricResearch/TradingAgents': {
            'overview': 'TradingAgents是一个多智能体金融交易框架，基于大语言模型实现。',
            'scenario': '在金融市场中，交易者面临信息不对称和决策复杂性的问题。本项目为交易者提供了一个智能化的交易助手，提高交易效率和决策准确性。',
            'solution': '通过多智能体协作和大语言模型，项目实现了自动化交易策略生成、实时市场分析和风险管理功能。'
        },
        'mvanhorn/last30days-skill': {
            'overview': '一个AI代理技能，能够在Reddit、X、YouTube、HN、Polymarket及网络上研究任何主题，并汇总出有根据的总结。',
            'scenario': '用户在寻找特定主题的信息时，常常面临信息碎片化和可靠性不足的问题，难以获取全面的见解。',
            'solution': '通过整合多个平台的数据，项目提供精准的主题研究和汇总，帮助用户快速了解相关信息。'
        },
        'pascalorg/editor': {
            'overview': '这是一个基于 TypeScript 的在线代码编辑器，提供多种编程语言支持。',
            'scenario': '开发者常常需要一个功能强大的在线编辑器来快速编写和测试代码，但现有工具往往不够灵活或功能有限。',
            'solution': '该编辑器提供实时预览、代码高亮、自动补全等核心功能，提升编码效率和体验。'
        },
        'supermemoryai/supermemory': {
            'overview': 'supermemory 是一个快速可扩展的记忆引擎和应用，专为 AI 时代设计的 Memory API。',
            'scenario': '用户在处理大量数据时，常遇到记忆管理效率低下的问题，影响 AI 应用的性能和响应速度。',
            'solution': '提供高效的记忆存储和检索功能，支持大规模数据处理，优化 AI 任务的执行效率。'
        },
        'harry0703/MoneyPrinterTurbo': {
            'overview': 'MoneyPrinterTurbo 是一个基于 AI 大模型的短视频生成工具，用户可一键生成高清短视频。',
            'scenario': '在社交媒体和内容创作日益增长的背景下，用户常面临视频制作时间长、难度大的问题，急需快速生成吸引眼球的短视频。',
            'solution': '该项目利用先进的 AI 技术，实现一键生成短视频，简化了创作流程，提高了视频制作效率。'
        },
        'mvanhorn/last30days-skill': {
            'overview': '一个AI代理技能，通过多平台研究主题并生成总结。',
            'scenario': '用户希望快速获取某个话题的全面信息，但各个平台信息繁杂且分散，难以整合和理解。',
            'solution': '该项目整合Reddit、YouTube等平台的信息，提供基于事实的主题总结，帮助用户高效获取知识。'
        },
        'FujiwaraChoki/MoneyPrinterV2': {
            'overview': 'MoneyPrinterV2是一个基于Python的自动化在线赚钱工具。',
            'scenario': '许多用户希望通过网络赚取收入，但缺乏有效的工具和方法，导致时间和精力的浪费。',
            'solution': '该项目提供了一系列自动化脚本，帮助用户高效地进行在线赚钱，简化流程，提升收益。'
        },
        'bytedance/deer-flow': {
            'overview': 'Deer-Flow是一个开源的超级代理工具，旨在研究、编码和创建。',
            'scenario': '用户在处理复杂任务时，可能面临时间紧迫、流程繁琐的问题。Deer-Flow通过沙箱和子代理等功能，帮助用户高效完成任务。',
            'solution': '它通过沙箱、记忆、工具和消息网关，支持多层次任务处理，极大提高工作效率。'
        },
        'Crosstalk-Solutions/project-nomad': {
            'overview': 'Project N.O.M.A.D 是一款自给自足的离线生存计算机，集成了关键工具、知识和人工智能。',
            'scenario': '在偏远地区或灾后环境中，用户可能缺乏通信和信息获取手段，面临生存挑战和决策困难。',
            'solution': '该项目提供离线信息、实用工具和AI助手，支持用户随时随地获取生存知识和技能。'
        },
        'vxcontrol/pentagi': {
            'overview': 'pentagi是一个完全自主的人工智能代理系统，专用于执行复杂的渗透测试任务。',
            'scenario': '在网络安全领域，安全专家需要高效识别系统漏洞，传统手动测试耗时且容易遗漏。pentagi帮助他们自动化这一过程，提升效率与准确性。',
            'solution': '该系统利用AI技术，自动执行渗透测试，提供详细报告，快速识别安全漏洞，节省人力成本。'
        },
        'browser-use/browser-use': {
            'overview': '一个帮助AI代理访问和操作网站的工具，简化在线任务自动化。',
            'scenario': '在进行数据采集或测试时，开发者常常需要手动操作网站，耗时且繁琐。此项目旨在解决这一痛点，提升工作效率。',
            'solution': '通过提供简单的API和自动化脚本，使得AI代理能够轻松访问和操作各种网站，实现高效的在线任务自动化。'
        },
        'TauricResearch/TradingAgents': {
            'overview': 'TradingAgents是一个基于多智能体的金融交易框架，结合了大型语言模型技术。',
            'scenario': '用户可以利用该框架在金融市场中实现自动化交易，解决人工交易效率低、情绪影响决策等问题。',
            'solution': '框架支持多智能体协作，集成LLM进行市场分析和策略生成，提升交易决策的智能化与自动化水平。'
        },
        'tinygrad/tinygrad': {
            'overview': 'tinygrad 是一个轻量级的深度学习框架，灵感来自 PyTorch 和 micrograd。',
            'scenario': '适合需要快速原型开发和学习深度学习基本原理的开发者，尤其是对大型框架感到繁重的用户。',
            'solution': '提供简洁的 API 和基础的自动微分功能，轻松实现和训练神经网络。'
        },
        'affaan-m/everything-claude-code': {
            'overview': '一个优化代理性能的系统，支持Claude Code、Codex等工具。',
            'scenario': '开发者在使用Claude Code等工具时，常面临性能瓶颈和资源管理问题，影响开发效率和体验。',
            'solution': '通过技能、直觉、记忆和安全机制，提供高效的性能优化和研究驱动的开发支持。'
        },
        'bytedance/deer-flow': {
            'overview': 'Deer-Flow是一个开源的超级代理工具，支持研究、编码和创作。',
            'scenario': '用户需要处理复杂任务时，常常面临时间紧迫和资源不足的问题，特别是在多任务环境中容易导致效率低下。',
            'solution': '通过沙箱、记忆、工具和子代理等功能，Deer-Flow能够高效管理不同级别的任务，缩短处理时间。'
        },
        'browser-use/browser-use': {
            'overview': '一个帮助AI代理访问网站的工具，简化在线任务自动化。',
            'scenario': '开发者希望利用AI自动化处理网页信息，但面对复杂的网站结构和交互，效率低下，难以实现高效的数据获取和任务执行。',
            'solution': '通过Python库，提供简便的接口，使AI代理能够轻松访问和操作各种网站，提升自动化任务的效率。'
        },
        'tinygrad/tinygrad': {
            'overview': 'tinygrad 是一个轻量级的深度学习框架，灵感来源于 PyTorch 和 Micrograd。',
            'scenario': '对于希望快速实现深度学习模型的开发者，传统框架可能过于复杂，学习曲线陡峭，tinygrad 提供了简洁的接口和易用性。',
            'solution': 'tinygrad 通过简化深度学习的基本构建块，支持自动微分和基本神经网络结构，帮助用户快速构建和训练模型。'
        },
        'TauricResearch/TradingAgents': {
            'overview': 'TradingAgents是一个基于多智能体的金融交易框架，利用大语言模型进行交易决策。',
            'scenario': '在金融市场中，交易者面临复杂的决策环境和信息过载，传统方法难以快速反应和优化策略。用户需要高效、智能的交易工具来提升交易效果。',
            'solution': '该框架结合多智能体系统和大语言模型，实现自主交易策略生成、实时市场分析及风险管理，帮助用户优化交易决策。'
        },
        'vxcontrol/pentagi': {
            'overview': '一个完全自主的人工智能代理系统，能够执行复杂的渗透测试任务。',
            'scenario': '安全团队需要高效地评估系统安全性，传统测试方法耗时且人力成本高，难以快速发现漏洞。',
            'solution': '通过自动化AI代理，快速执行渗透测试，提供详细报告，提升安全测试的效率和准确性。'
        },
        'jamwithai/production-agentic-rag-course': {
            'overview': '这是一个基于Python的生产代理课程，旨在提升人工智能系统的能力。',
            'scenario': '用户在构建智能系统时，面临数据整合和知识检索的挑战，导致效率低下和决策困难。',
            'solution': '该项目提供了一套完整的课程，涵盖数据处理、模型训练及智能检索技术，帮助用户高效构建AI系统。'
        },
        'affaan-m/everything-claude-code': {
            'overview': '一个优化性能的智能代理系统，支持Claude Code等编程助手。',
            'scenario': '开发者在使用智能编程工具时，常面临性能瓶颈和安全隐患，影响开发效率和代码质量。',
            'solution': '通过技能、直觉、记忆和安全机制，提升Claude Code等工具的开发体验和性能。'
        },
        'FujiwaraChoki/MoneyPrinterV2': {
            'overview': 'MoneyPrinterV2 是一个用于自动化在线赚钱过程的 Python 项目。',
            'scenario': '许多用户希望通过互联网获得被动收入，但缺乏有效的工具和策略，导致他们难以实现这一目标。',
            'solution': '该项目提供自动化工具，简化了在线赚钱的步骤，帮助用户更高效地获取收益。'
        },
        'systemd/systemd': {
            'overview': 'systemd 是一个系统和服务管理器，用于Linux操作系统。',
            'scenario': '在Linux系统中，用户常常需要管理服务和启动项，手动配置繁琐且容易出错，影响系统性能和稳定性。',
            'solution': 'systemd 提供统一的服务管理框架，支持并行启动、依赖管理和日志记录，提高系统启动速度和管理效率。'
        },
        'aquasecurity/trivy': {
            'overview': 'Trivy 是一个开源的安全扫描工具，能够检测容器、Kubernetes、代码仓库和云环境中的漏洞和配置错误。',
            'scenario': '开发者在构建和部署应用时，常面临安全漏洞和配置错误的风险，Trivy 可以帮助他们快速识别和修复这些问题。',
            'solution': 'Trivy 提供全面的漏洞检测、错误配置检查、密钥泄露识别和软件物料清单生成，提升应用安全性。'
        },
        'Crosstalk-Solutions/project-nomad': {
            'overview': 'Project N.O.M.A.D 是一款自给自足的离线生存计算机，内置关键工具和知识。',
            'scenario': '在偏远地区或紧急情况下，用户需要随时获取生存知识和工具，传统设备可能无法使用或连接网络。',
            'solution': '该项目提供离线访问的生存指南、实用工具和AI助手，确保用户在任何环境下都能获得支持。'
        },
        'opendataloader-project/opendataloader-pdf': {
            'overview': 'opendataloader-pdf 是一个开源的 PDF 解析器，专为 AI 数据准备而设计。',
            'scenario': '用户在处理大量 PDF 文件时常面临数据提取困难，且缺乏无障碍功能，影响了信息的获取和利用。',
            'solution': '该项目通过自动化 PDF 可访问性，提供高效的数据提取功能，简化用户工作流程。'
        },
        'jarrodwatts/claude-hud': {
            'overview': 'Claude Code 插件，提供实时上下文使用、活跃工具、运行代理及待办进度的可视化信息。',
            'scenario': '开发者在使用 Claude 进行编程时，常常需要清晰地了解当前环境和工具的使用情况，然而缺乏有效的可视化反馈，影响工作效率。',
            'solution': '通过该插件，用户可以实时查看上下文信息、活跃工具和待办事项的进度，提升工作透明度和效率。'
        },
        'protocolbuffers/protobuf': {
            'overview': 'Protocol Buffers是Google开发的数据交换格式，用于高效序列化结构化数据。',
            'scenario': '在分布式系统、微服务架构中，数据传输效率和兼容性是关键痛点。传统的JSON或XML在性能和存储上存在不足。',
            'solution': '通过高效的二进制序列化，Protocol Buffers提供了更小的消息体积和更快的解析速度，同时支持多种编程语言的跨平台使用。'
        },
        'vllm-project/vllm-omni': {
            'overview': 'vllm-omni 是一个高效的多模态模型推理框架，基于 Python 开发。',
            'scenario': '在自然语言处理、计算机视觉等领域，用户需要处理不同模态的数据，现有工具往往效率低下，无法满足实时推理需求。',
            'solution': 'vllm-omni 提供了优化的推理算法和灵活的接口，支持多种模态的高效组合与推理，提升了处理速度和准确性。'
        },
        'FujiwaraChoki/MoneyPrinterV2': {
            'overview': 'MoneyPrinterV2 是一个自动化在线赚钱的工具，基于 Python 开发。',
            'scenario': '用户希望通过网络赚取额外收入，但缺乏有效的方法和工具，常常面临时间和效率的挑战。',
            'solution': '该项目提供了一套自动化流程，简化了在线赚钱的步骤，帮助用户更高效地实现收益。'
        },
        'systemd/systemd': {
            'overview': 'systemd 是一个系统和服务管理器，广泛用于 Linux 操作系统。',
            'scenario': '在现代 Linux 系统中，用户需要高效地管理服务和系统进程。传统的启动方式往往复杂且效率低下，导致系统启动时间长，服务管理困难。',
            'solution': 'systemd 提供并行启动服务、依赖管理和统一的日志系统，显著提升了系统启动速度和服务管理的便利性。'
        },
        'aquasecurity/trivy': {
            'overview': 'Trivy 是一个开源工具，用于扫描容器、Kubernetes、代码库和云环境中的漏洞、错误配置和机密信息。',
            'scenario': '开发者和运维人员在持续集成/持续部署中需要确保应用安全，防止漏洞和配置错误带来的安全风险。',
            'solution': 'Trivy 提供全面的安全扫描功能，能够检测容器和代码中的漏洞、配置错误，以及敏感信息，帮助用户快速识别并修复安全隐患。'
        },
        'protocolbuffers/protobuf': {
            'overview': 'Protocol Buffers是谷歌开发的一种高效数据交换格式。',
            'scenario': '在分布式系统中，数据传输效率至关重要。开发者常面临数据格式不统一、序列化/反序列化慢等问题。',
            'solution': 'Protocol Buffers提供一种语言中立、平台无关的序列化机制，支持高效的数据编码和解码，减少了数据传输的大小和时间。'
        },
        'vllm-project/vllm-omni': {
            'overview': 'vllm-omni是一个用于高效推理的框架，支持多种模态模型。',
            'scenario': '该项目适用于需要处理图像、文本等多种数据类型的应用场景，如自然语言处理、计算机视觉等。用户在进行多模态推理时，常面临性能瓶颈和资源浪费的问题。',
            'solution': 'vllm-omni通过优化模型推理流程，提升计算效率，支持多模态数据整合，帮助用户高效利用资源。'
        },
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
