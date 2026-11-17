# eCommerce-Skills Plus (电商技能工具箱增强版)

> **中英双语 / Bilingual README** (中文在前，English follows below)

---

## 🇨🇳 中文说明

### 项目介绍
**eCommerce-Skills Plus** 是针对跨平台跨境电商（Amazon、Shopify、TikTok Shop、Walmart、Temu 等）卖家的 AI Agent 技能与量化分析工具箱增强版。提供开箱即用的利润测算、供应链瓶颈诊断、商品评价真实性排查、品牌舆情监控、跟卖侵权检测及出海拓展决策支持。

---

### 功能与实质改进点

本项目针对原开源项目进行了 5 项实质性核心重构与功能扩充（逐条对应 [CHANGES.md](./CHANGES.md)）：

1. **修复利润计算核心数学公式与 CLI 崩溃（Math & CLI Bug Fixes）**
   - **保本价格公式修正**：原算法将平台佣金按原价当作固定支出计入保本价分子，导致保本价虚高；现已修正为随降价动态比例扣除佣金（`min_price = fixed_costs / (1 - referral_rate - ad_rate)`）。
   - **目标定价模型修正**：补全退货货损折旧成本估算（`return_rate * product_cost * 0.5`），解决目标利润定价被低估的问题。
   - **CLI 命令行健壮性**：全面消除原脚本传入 `--demo`、`--zh`、`--help` 触发 `JSONDecodeError` 崩溃的问题，支持标准参数解析与开箱演示。
   - **排版修复**：修复状态行多重勾选图标（`✅ ✅ Healthy`）的排版异常。

2. **消除跨平台代码纯复制粘贴，建立各平台专属财务与供应链模型（Multi-Platform Custom Models）**
   - **Shopify DTC 模型**：剥离原搬抄 Amazon 的 FBA 逻辑，引入 3PL 仓配打包费、Stripe/Shopify Payments 网关手续费（2.9% + $0.30）、SaaS 订阅分摊与独立站 CAC 获客成本核算；供应链增加 3PL 周转与 DTC 现金流监控。
   - **TikTok Shop 模型**：适配 TikTok Shop 佣金结构、达人分销带货佣金率（Affiliate Commission）、FBT（Fulfilled by TikTok）与短视频爆品冲量易断货快反供应链模型。
   - **Walmart Marketplace 模型**：适配 Walmart 类目佣金梯度表、WFS 配送费用标准及 SQEP 入库合规处置策略。

3. **补齐正统中文电商场景、重构机翻乱码词库与优化中文 NLP 分析（Chinese Localization & NLP Enhancement）**
   - **机翻乱码修复**：彻底清理原代码中由自动化脚本造成的荒谬词汇（如把“好评返现”翻为 `"Positive ReviewCashback"`，把“时尚”翻为 `"Timeyet"`，输出 `"Total mention and"` 等），全面替换为正统地道的中文电商术语。
   - **违规与舆情词库扩充**：为评价检测补齐“好评返现”、“刷单”、“加微信”、“返红包”等高频刷评特征词；为品牌舆情扩充常见客诉与侵权词。
   - **中文字符级 N-gram 相似度切词**：针对中文无空格特性，为文本相似度检测新增 CJK 滑动切分，解决水军刷单模板识别失效的问题。

4. **增强数据接口稳定性：超时控制、指数退避重试与限流保护（Network Stability & Rate Limiting）**
   - **真实接口解析**：补齐 Google News RSS、DuckDuckGo API 及 Reddit 公开接口的解析逻辑。
   - **高可用与风控防御**：内置网络超时控制（Connect 2.0s / Read 5.0s）、指数退避重试（带随机抖动 Jitter）、Token Bucket 请求频控限流与优雅降级回退，彻底告别上游网络假死与反爬封禁。

5. **扩充平台覆盖：新增 Temu 全托管/半托管跨境核算技能（Temu Platform Expansion）**
   - **新增 Temu 专属技能**：新增 `profit-margin-calculator-temu` 技能及 Python 计算内核。
   - **核价模型构建**：全托管模式支持出厂采购价、国内集运头程、贴标包材、违规罚款预留及售后“仅退款”损耗率测算；半托管模式支持海外仓履约与尾程派送。
   - **生态联动**：同步更新 `cross-border-ecommerce/SKILL.md`，将 Temu 全托管与半托管履约模型纳入跨境拓展战略全景。

---

### 快速开始

#### 1. 环境依赖
本项目仅依赖 Python 3.8+ 标准库（`urllib`、`json`、`re`、`math`、`datetime` 等），无需安装任何笨重的第三方包，开箱即用。

```bash
# 验证 Python 版本
python3 --version
```

#### 2. 核心模块运行与自测

##### (1) 多平台利润核算（支持中英双语、开箱演示）
```bash
# Amazon 利润分析
python3 profit-margin-calculator/profit-margin-calculator-amazon/scripts/calculator.py --demo
python3 profit-margin-calculator/profit-margin-calculator-amazon/scripts/calculator.py --demo --zh

# Shopify DTC 独立站利润分析
python3 profit-margin-calculator/profit-margin-calculator-shopify/scripts/calculator.py --demo --zh

# TikTok Shop 利润分析
python3 profit-margin-calculator/profit-margin-calculator-tiktok/scripts/calculator.py --demo --zh

# Walmart Marketplace 利润分析
python3 profit-margin-calculator/profit-margin-calculator-walmart/scripts/calculator.py --demo --zh

# 新增：Temu 全托管与半托管供货核算
python3 profit-margin-calculator/profit-margin-calculator-temu/scripts/calculator.py --demo --zh
```

##### (2) 供应链瓶颈与营运资金诊断
```bash
# 诊断 Amazon 供应链（库存周转、Cash-to-Cash 周期）
python3 supply-chain-optimization/supply-chain-optimization-amazon/scripts/calculator.py --demo --zh

# 诊断 Shopify 供应链
python3 supply-chain-optimization/supply-chain-optimization-shopify/scripts/calculator.py --demo --zh
```

##### (3) 品牌舆情监控与弹性网络采集
```bash
# 运行品牌舆情监控分析
python3 brand-monitoring/scripts/monitor.py --demo --zh

# 运行网络声量检索（支持超时重试与限流熔断）
python3 brand-monitoring/scripts/scrapers.py "Anker" --zh
```

##### (4) 商品评价真实性排查（反刷单/防返现）
```bash
python3 review-checker/amazon-review-checker/scripts/analyzer.py --demo --zh
```

##### (5) 品牌保护与防跟卖维权
```bash
python3 brand-protection/brand-protection-amazon/scripts/detector.py --demo --zh
```

#### 3. 作为 AI Agent 技能安装
支持 Claude Code、Cursor、Windsurf、OpenClaw 等符合 Skills 规范的 AI 助手：
```bash
# 安装整个技能工具箱
npx skills add nexscope-ai/eCommerce-Skills -g

# 安装单个平台技能（以 Temu 为例）
npx skills add nexscope-ai/eCommerce-Skills --skill profit-margin-calculator-temu -g
```

---

### 来源与致谢
本项目基于 eCommerce-Skills（附原仓库链接 https://github.com/nexscope-ai/eCommerce-Skills）二次开发，原项目由 nexscope-ai 以 MIT 许可证开源。特别致谢原团队建立的基础框架与架构思路。

---

### 许可证
本项目沿用 MIT 许可证，全文见根目录 [LICENSE](./LICENSE)。

---
---

## 🇬🇧 English Description

### Overview
**eCommerce-Skills Plus** is an enhanced open-source collection of AI agent skills and quantitative decision tools designed for cross-border e-commerce sellers on Amazon, Shopify, TikTok Shop, Walmart, and Temu. It delivers ready-to-run profit margin calculators, supply chain bottleneck diagnosis, review authenticity analysis, brand sentiment monitoring, anti-hijacking protection, and international expansion guidance.

---

### Key Features & Substantive Improvements

This repository implements 5 major substantive improvements over the original project (aligned with [CHANGES.md](./CHANGES.md)):

1. **Core Math & CLI Bug Fixes in Profit & Supply Chain Calculators**
   - **Break-Even Formula Correction**: Fixed the break-even pricing calculation by dynamically accounting for variable referral rates (`min_price = fixed_costs / (1 - referral_rate - ad_rate)`), avoiding artificial price inflation.
   - **Target Pricing Accuracy**: Included product return damage loss (`return_rate * product_cost * 0.5`) in the target margin model.
   - **Robust CLI Handling**: Fixed `JSONDecodeError` crashes triggered by arguments like `--demo`, `--zh`, and `--help`. Implemented clean argument parsing for out-of-the-box evaluation.
   - **Layout Polish**: Removed redundant status badges (`✅ ✅ Healthy`).

2. **Dedicated Multi-Platform Financial & Logistics Models**
   - **Shopify DTC Model**: Replaced copy-pasted FBA logic with true DTC unit economics: 3PL fulfillment & storage, payment gateway transaction fees (2.9% + $0.30), SaaS plan amortizations, and CAC customer acquisition analytics.
   - **TikTok Shop Model**: Modeled TikTok Shop category commissions (5-8%), creator affiliate commissions (10-15%), FBT fulfillment fees, and agile viral restock buffers.
   - **Walmart Marketplace Model**: Adapted WFS tiered fulfillment fees, category commission schedules, and SQEP inbound compliance rules.

3. **Authentic Chinese Localization, Terminology Cleaning & NLP Segmentation**
   - **Clean Terminology**: Cleaned up mangled machine translations (e.g., replaced `"Positive ReviewCashback"` with authentic e-commerce terms, eliminated broken phrases like `"Total mention and"`).
   - **Expanded Chinese Violation Dictionaries**: Added authentic keywords for incentivized reviews ("好评返现", "五星好评", "刷单", "返红包") and brand reputation monitoring.
   - **CJK Bi-gram/Tri-gram Tokenization**: Added sliding n-gram segmentation for non-spaced Chinese text in review similarity detection, restoring accurate spam detection for Asian languages.

4. **Network Interface Resilience: Timeout, Exponential Backoff, & Rate Limiting**
   - **Functional Scrapers**: Implemented working parsers for Google News RSS, DuckDuckGo JSON, and Reddit public feeds.
   - **High Availability**: Built-in network timeout controls (Connect 2.0s / Read 5.0s), exponential backoff retries with random jitter, rate limiting (Token Bucket), and graceful fallback to prevent process hangs or anti-scraping bans.

5. **Platform Expansion: Added Temu Full-Managed & Semi-Managed Calculator**
   - **New Temu Skill**: Introduced `profit-margin-calculator-temu` skill documentation and Python execution engine.
   - **Temu Financial Modeling**: Modeled Full-Managed (procurement FOB, domestic consolidated shipping, packaging, compliance penalty reserves, and "refund-only" return loss) and Semi-Managed overseas fulfillment.
   - **Ecosystem Integration**: Updated `cross-border-ecommerce/SKILL.md` to integrate Temu logistics comparisons into global cross-border strategy.

---

### Quick Start

#### 1. Prerequisites
Requires Python 3.8+. Standard library only—no external third-party dependencies required.

```bash
python3 --version
```

#### 2. Running Core Modules

##### (1) Profit Margin Calculators
```bash
# Amazon Profit Analysis
python3 profit-margin-calculator/profit-margin-calculator-amazon/scripts/calculator.py --demo

# Shopify DTC Unit Economics
python3 profit-margin-calculator/profit-margin-calculator-shopify/scripts/calculator.py --demo

# TikTok Shop Economics
python3 profit-margin-calculator/profit-margin-calculator-tiktok/scripts/calculator.py --demo

# Walmart Marketplace Economics
python3 profit-margin-calculator/profit-margin-calculator-walmart/scripts/calculator.py --demo

# Temu Cross-Border Pricing (Full & Semi-Managed)
python3 profit-margin-calculator/profit-margin-calculator-temu/scripts/calculator.py --demo --zh
```

##### (2) Supply Chain & Working Capital Optimization
```bash
# Amazon FBA & Cash-to-Cash Cycle
python3 supply-chain-optimization/supply-chain-optimization-amazon/scripts/calculator.py --demo

# Shopify 3PL & DTC Working Capital
python3 supply-chain-optimization/supply-chain-optimization-shopify/scripts/calculator.py --demo
```

##### (3) Brand Monitoring & Resilient Scraping
```bash
# Brand Social Sentiment Monitoring
python3 brand-monitoring/scripts/monitor.py --demo

# Resilient Brand Scraper (with rate limiting & jitter retry)
python3 brand-monitoring/scripts/scrapers.py "Anker"
```

##### (4) Review Authenticity & Fraud Detection
```bash
python3 review-checker/amazon-review-checker/scripts/analyzer.py --demo
```

##### (5) Brand Protection & Anti-Hijacking
```bash
python3 brand-protection/brand-protection-amazon/scripts/detector.py --demo
```

#### 3. Installing as AI Agent Skills
Compatible with Claude Code, Cursor, Windsurf, OpenClaw, and any agent supporting the Skills standard:
```bash
# Install entire skill suite
npx skills add nexscope-ai/eCommerce-Skills -g

# Install specific skill (e.g. Temu calculator)
npx skills add nexscope-ai/eCommerce-Skills --skill profit-margin-calculator-temu -g
```

---

### Source & Acknowledgments
本项目基于 eCommerce-Skills（附原仓库链接 https://github.com/nexscope-ai/eCommerce-Skills）二次开发，原项目由 nexscope-ai 以 MIT 许可证开源。  
*This project is a secondary development based on eCommerce-Skills (original repository: https://github.com/nexscope-ai/eCommerce-Skills), originally open-sourced under the MIT License by nexscope-ai.*

---

### License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for the full license text.
