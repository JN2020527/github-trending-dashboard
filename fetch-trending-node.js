#!/usr/bin/env node

/**
 * GitHub Trending 浏览器自动化数据抓取
 * 需要在 OpenClaw agent 环境中运行
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DASHBOARD_DIR = path.join(process.env.HOME, 'github-trending-dashboard');
const DATA_DIR = path.join(DASHBOARD_DIR, 'data');
const DATE = new Date().toISOString().split('T')[0];
const TRENDING_FILE = path.join(DATA_DIR, `${DATE}.json`);
const DATES_FILE = path.join(DATA_DIR, 'dates.json');

console.log('🔥 GitHub Trending 浏览器自动化抓取');
console.log(`📅 日期: ${DATE}\n`);

// 确保数据目录存在
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// 使用 OpenClaw 命令行工具启动浏览器并获取数据
async function fetchTrendingData() {
  return new Promise((resolve, reject) => {
    console.log('🌐 正在访问 GitHub Trending...');
    
    // 这里使用简单的 HTTP 请求（因为 browser 工具需要在 OpenClaw 上下文中）
    // 实际运行时，OpenClaw agent 会使用 browser 工具
    
    const options = {
      hostname: 'github.com',
      path: '/trending',
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        console.log('✅ 成功获取页面数据');
        resolve(data);
      });
    });

    req.on('error', (e) => {
      console.error('❌ 请求失败:', e.message);
      reject(e);
    });

    req.end();
  });
}

// 解析 HTML 提取 trending 仓库信息
function parseTrendingRepos(html) {
  const repos = [];
  
  // 简单的正则匹配（实际应该用更健壮的解析器）
  const articleRegex = /<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>([\s\S]*?)<\/article>/gi;
  const repoRegex = /href="\/([^"]+)"[^>]*>\s*<span[^>]*class="[^"]*text-normal[^"]*"[^>]*>([^<]+)<\/span>\s*([^<]+)<\/a>/i;
  const descRegex = /<p[^>]*class="[^"]*col-9[^"]*"[^>]*>([\s\S]*?)<\/p>/i;
  const langRegex = /<span[^>]*itemprop="programmingLanguage"[^>]*>([^<]+)<\/span>/i;
  const starsRegex = /href="\/[^"]+\/stargazers"[^>]*>\s*<svg[^>]*>[\s\S]*?<\/svg>\s*([\d,]+)/i;
  const starsTodayRegex = /([\d,]+)\s*stars?\s*today/i;
  
  let match;
  let rank = 1;
  
  while ((match = articleRegex.exec(html)) !== null && rank <= 8) {
    const article = match[1];
    
    try {
      // 提取仓库名称
      const repoMatch = article.match(/href="\/([^"]+)"/);
      if (!repoMatch) continue;
      
      const fullName = repoMatch[1];
      const [owner, name] = fullName.split('/');
      
      // 提取描述
      const descMatch = article.match(descRegex);
      const description = descMatch ? descMatch[1].trim() : '';
      
      // 提取语言
      const langMatch = article.match(langRegex);
      const language = langMatch ? langMatch[1].trim() : 'Unknown';
      
      // 提取总 star 数
      const starsMatch = article.match(starsRegex);
      const totalStars = starsMatch ? starsMatch[1].trim() : '0';
      
      // 提取今日 star 数
      const todayMatch = article.match(starsTodayRegex);
      const starsToday = todayMatch ? todayMatch[1].trim() : '0';
      
      repos.push({
        rank: rank++,
        name: `${owner} / ${name}`,
        full_name: fullName,
        url: `https://github.com/${fullName}`,
        description,
        language,
        total_stars: totalStars,
        stars_today: starsToday
      });
      
    } catch (e) {
      console.error(`⚠️  解析第 ${rank} 个仓库失败:`, e.message);
    }
  }
  
  return repos;
}

// 生成增强描述（使用 Gemini 或其他 AI）
function generateDescriptions(repos) {
  const descriptions = {};
  
  repos.forEach(repo => {
    // 简单的描述生成（实际可以使用 AI 增强）
    descriptions[repo.full_name] = {
      overview: repo.description || '暂无描述',
      scenario: '适用于需要此功能的开发者和团队',
      solution: '提供完整的解决方案和实现方式'
    };
  });
  
  return descriptions;
}

// 更新 dates.json
function updateDatesFile() {
  let dates = [];
  
  if (fs.existsSync(DATES_FILE)) {
    const content = fs.readFileSync(DATES_FILE, 'utf8');
    const data = JSON.parse(content);
    dates = data.dates || [];
  }
  
  // 将今天日期添加到开头（如果不存在）
  if (!dates.includes(DATE)) {
    dates.unshift(DATE);
    // 只保留最近 30 天的数据
    dates = dates.slice(0, 30);
  }
  
  fs.writeFileSync(DATES_FILE, JSON.stringify({ dates }, null, 2));
  console.log('✅ 已更新 dates.json');
}

// 主函数
async function main() {
  try {
    // 获取数据
    const html = await fetchTrendingData();
    
    // 解析数据
    const repos = parseTrendingRepos(html);
    console.log(`📊 成功解析 ${repos.length} 个 trending 仓库`);
    
    if (repos.length === 0) {
      throw new Error('未能解析到任何仓库数据');
    }
    
    // 生成描述
    const descriptions = generateDescriptions(repos);
    
    // 构建最终数据
    const data = {
      date: DATE,
      repos: repos,
      descriptions: descriptions
    };
    
    // 保存数据
    fs.writeFileSync(TRENDING_FILE, JSON.stringify(data, null, 2));
    console.log(`✅ 已保存数据到: ${TRENDING_FILE}`);
    
    // 更新 dates.json
    updateDatesFile();
    
    // 推送到 GitHub
    console.log('\n🚀 推送到 GitHub...');
    process.chdir(DASHBOARD_DIR);
    
    execSync('git add data/', { stdio: 'inherit' });
    execSync(`git commit -m "feat: 更新 GitHub Trending 数据 - ${DATE}"`, { stdio: 'inherit' });
    execSync('git pull --rebase origin main', { stdio: 'inherit' });
    execSync('git push origin main', { stdio: 'inherit' });
    
    console.log('\n✅ 完成！Dashboard 已更新');
    console.log(`🌐 访问: https://jn2020527.github.io/github-trending-dashboard/`);
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    process.exit(1);
  }
}

main();
