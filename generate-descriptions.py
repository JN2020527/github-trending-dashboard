#!/usr/bin/env python3
"""
GitHub Trending 描述生成脚本 - 本地版
在本地运行，使用 AI 为缺失描述的项目生成中文描述
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 检查 OpenAI 库
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.error("❌ openai 未安装，请运行: pip install openai")
    sys.exit(1)


def load_existing_descriptions():
    """从脚本文件中加载现有描述"""
    script_file = Path(__file__).parent / 'fetch-trending-scrapling.py'
    
    with open(script_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单解析：提取 get_descriptions 函数中的字典
    # 这里我们直接执行 get_descriptions 函数
    import re
    
    # 找到 get_descriptions 函数
    match = re.search(r'def get_descriptions\(\):.*?return \{(.*?)\n\}', content, re.DOTALL)
    if not match:
        logger.error("❌ 无法解析 get_descriptions 函数")
        return {}
    
    # 提取字典内容并执行
    dict_content = match.group(1)
    
    # 简单方式：直接 import 脚本
    import importlib.util
    spec = importlib.util.spec_from_file_location("trending", script_file)
    trending = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trending)
    
    return trending.get_descriptions()


def generate_description_with_ai(repo):
    """使用 AI 生成项目描述"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY 未设置")
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
        
        # 去除可能的 markdown 代码块标记
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join(lines[1:-1])
            if content.startswith('json'):
                content = content[4:].strip()
        
        desc = json.loads(content)
        
        logger.info(f"✅ 生成成功: {repo['name']}")
        return desc
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 解析失败: {e}")
        logger.error(f"   原始内容: {content}")
        return None
    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        return None


def update_script_file(new_descriptions):
    """将新描述写入脚本文件"""
    script_file = Path(__file__).parent / 'fetch-trending-scrapling.py'
    
    with open(script_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    insert_index = None
    
    # 找到插入位置
    for i, line in enumerate(lines):
        if 'def get_descriptions():' in line:
            for j in range(i, min(i + 20, len(lines))):
                if 'return {' in lines[j]:
                    insert_index = j + 1
                    break
            break
    
    if insert_index is None:
        logger.error("❌ 无法找到插入位置")
        return False
    
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
    return True


def main():
    logger.info("🚀 开始生成 GitHub Trending 项目描述...")
    
    # 检查 API Key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ 请设置环境变量: export OPENAI_API_KEY='your-key'")
        sys.exit(1)
    
    # 加载最新数据
    data_file = Path(__file__).parent / 'data' / 'latest.json'
    if not data_file.exists():
        logger.error("❌ 数据文件不存在，请先运行 fetch-trending-scrapling.py")
        sys.exit(1)
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 加载现有描述
    existing_descriptions = load_existing_descriptions()
    logger.info(f"📚 现有描述: {len(existing_descriptions)} 个项目")
    
    # 检测缺失描述的项目
    missing_projects = []
    for repo in data['repos']:
        if repo['full_name'] not in existing_descriptions:
            missing_projects.append(repo)
    
    if not missing_projects:
        logger.info("✅ 所有项目都有描述，无需生成")
        return
    
    logger.info(f"⚠️ 发现 {len(missing_projects)} 个项目缺失描述")
    
    # 生成描述
    new_descriptions = {}
    for i, repo in enumerate(missing_projects, 1):
        logger.info(f"\n[{i}/{len(missing_projects)}] 正在生成: {repo['name']}")
        logger.info(f"   描述: {repo['description'][:60]}...")
        
        desc = generate_description_with_ai(repo)
        if desc:
            new_descriptions[repo['full_name']] = desc
            logger.info(f"   ✅ 概述: {desc['overview']}")
            logger.info(f"   ✅ 场景: {desc['scenario']}")
            logger.info(f"   ✅ 方案: {desc['solution']}")
        else:
            logger.warning(f"   ⚠️ 跳过: {repo['name']}")
    
    if not new_descriptions:
        logger.error("❌ 没有成功生成任何描述")
        sys.exit(1)
    
    # 显示生成结果
    logger.info(f"\n{'='*60}")
    logger.info(f"📝 成功生成 {len(new_descriptions)} 个项目描述")
    logger.info(f"{'='*60}\n")
    
    for full_name, desc in new_descriptions.items():
        logger.info(f"📦 {full_name}")
        logger.info(f"   概述: {desc['overview']}")
        logger.info(f"   场景: {desc['scenario']}")
        logger.info(f"   方案: {desc['solution']}")
        logger.info("")
    
    # 自动保存
    update_script_file(new_descriptions)
    logger.info("✅ 已自动保存到脚本文件")


if __name__ == '__main__':
    main()
