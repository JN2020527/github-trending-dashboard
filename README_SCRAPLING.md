# GitHub Trending Dashboard - Scrapling 版本

## 🚀 快速开始

### 1. 安装依赖（首次运行）

```bash
cd ~/github-trending-dashboard

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements-scrapling.txt
```

### 2. 运行脚本

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行抓取
python3 fetch-trending-scrapling.py
```

### 3. 查看结果

```bash
# 查看最新数据
cat data/latest.json | jq .

# 查看今天的数据
cat data/$(date +%Y-%m-%d).json | jq .
```

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `fetch-trending-scrapling.py` | **新脚本** - 使用 Scrapling + Fallback |
| `update_trending.py` | **旧脚本** - 使用 BeautifulSoup（保留作为备份） |
| `requirements-scrapling.txt` | 新脚本的依赖列表 |
| `TEST_REPORT.md` | 测试报告和性能对比 |
| `.venv/` | 虚拟环境目录（约 60MB） |

---

## 🔧 技术特性

### Scrapling 优势
- ✅ **更强的反爬虫能力**: 模拟真实浏览器指纹
- ✅ **自适应选择器**: GitHub 页面结构变化时自动适应
- ✅ **HTTP/2 支持**: 更快的请求速度
- ✅ **智能重试**: 自动处理临时网络错误

### Fallback 机制
- 如果 Scrapling 失败，自动降级到 BeautifulSoup
- 确保数据抓取的稳定性
- 完整的错误日志记录

---

## 🐛 故障排查

### 问题 1: ModuleNotFoundError
**错误**: `ModuleNotFoundError: No module named 'scrapling'`

**解决**:
```bash
source .venv/bin/activate
pip install -r requirements-scrapling.txt
```

### 问题 2: Scrapling 失败
**日志**: `⚠️ Scrapling 失败，降级到 BeautifulSoup`

**说明**: 这是正常的 fallback 机制，不影响数据抓取

**排查**:
1. 检查网络连接
2. 查看 GitHub 是否可访问
3. 检查日志中的详细错误信息

### 问题 3: Playwright 错误
**错误**: `ModuleNotFoundError: No module named 'playwright'`

**解决**:
```bash
source .venv/bin/activate
pip install playwright
playwright install chromium
```

---

## 📊 对比旧脚本

| 指标 | 旧脚本 | 新脚本 |
|------|--------|--------|
| 反爬虫能力 | ❌ 弱 | ✅ 强 |
| 选择器稳定性 | ❌ 一般 | ✅ 高 |
| 错误恢复 | ❌ 无 | ✅ Fallback |
| 依赖复杂度 | ✅ 简单 | ⚠️ 较多 |
| 首次运行 | ✅ 快 | ⚠️ 较慢 |
| 后续运行 | ✅ 快 | ✅ 快 |

---

## 🔄 迁移指南

### 从旧脚本迁移

1. **测试新脚本**（推荐先测试）
   ```bash
   source .venv/bin/activate
   python3 fetch-trending-scrapling.py
   ```

2. **更新 Cron 任务**
   ```bash
   # 编辑 crontab
   crontab -e
   
   # 替换命令
   # 旧: /usr/bin/python3 update_trending.py
   # 新: source .venv/bin/activate && python3 fetch-trending-scrapling.py
   ```

3. **保留旧脚本**
   - 不要删除 `update_trending.py`
   - 作为 fallback 的 fallback

---

## 📝 日志示例

### 成功抓取
```
2026-03-15 13:12:43,850 - INFO - 🔍 开始抓取 GitHub Trending...
2026-03-15 13:12:43,850 - INFO - 🚀 使用 Scrapling Fetcher 抓取...
2026-03-15 13:12:45,244 - INFO - ✅ Scrapling 抓取成功: 8 个仓库
2026-03-15 13:12:45,246 - INFO - ✅ 成功抓取 8 个仓库
```

### Fallback 触发
```
2026-03-15 13:12:43,850 - INFO - 🔍 开始抓取 GitHub Trending...
2026-03-15 13:12:43,850 - INFO - 🚀 使用 Scrapling Fetcher 抓取...
2026-03-15 13:12:44,123 - WARNING - ⚠️ Scrapling 失败，降级到 BeautifulSoup: HTTP 404
2026-03-15 13:12:44,124 - INFO - 🔄 使用 BeautifulSoup Fallback...
2026-03-15 13:12:45,246 - INFO - ✅ BeautifulSoup 抓取成功: 8 个仓库
```

---

## 🎯 推荐用法

### 日常使用
```bash
# 推荐: 使用新脚本
cd ~/github-trending-dashboard
source .venv/bin/activate
python3 fetch-trending-scrapling.py
```

### 紧急情况
```bash
# 如果新脚本持续失败，回退到旧脚本
/usr/bin/python3 update_trending.py
```

---

**维护者**: Elon (CTO)  
**最后更新**: 2026-03-15
