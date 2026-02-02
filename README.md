<p align="center">
  <img src="logo.jpg" alt="u0 logo" width="180" />
</p>

<h1 align="center">u0: 持续金融分析与量化研究平台</h1>

<p align="center">
  <strong>消除金融数据的“盲区” —— 从 T+1 的事后解释，转向 T+0 的持续推断。</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Status-MVP-orange?style=flat-square" alt="Status" />
  <img src="https://img.shields.io/badge/Framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Data-AkShare-blue?style=flat-square" alt="AkShare" />
</p>

---

## 🚩 愿景：解决“信息滞后”

在金融分析领域，传统的基金净值披露存在 **T+1 延迟**。当市场剧烈波动时，投资者处于“盲打”状态：
*   **痛点**：官方净值每晚才公布，盘中只能靠猜。
*   **局限**：市面上的估值工具多为黑盒，缺乏可解释的持仓逻辑与因子暴露分析。

**u0 的存在是为了打破这种滞后。** 我们通过 AI 与因子回归模型，提供**可解释、可追踪、高频更新**的基金盘中实时估值能力。

---

## 🚀 核心功能库

### 📈 1. 实时估值引擎 (Real-time NAV Estimation)
基于历史净值序列与多维市场因子（宽基指数、行业主题）进行滚动回归，分钟级推算基金当前的真实走势。
*   **置信度度量**：不仅给出估值，还给出模型的置信区间。
*   **因子拆解**：自动识别当前的涨跌是由哪个板块（如沪深300、半导体、标普500）驱动。

### 🧪 2. 实验驱动架构 (Labs-First)
项目内置 `labs/` 目录，所有的量化模型和策略构思都需经过严格的实验论证。
*   **从实验到生产**：验证成功的模型会通过标准化接口“毕业”到 `services/` 层。

### 🔍 3. 风格暴露识别
超越静态标签，动态分析基金在“成长/价值”、“大盘/小盘”等维度的实时暴露度。

---

## 📂 项目结构

u0 采用**科研与工程并重**的目录设计方案：

```text
u0/
├── apps/           # 终端应用 (Web UI / 监控大屏)
├── services/       # 稳定服务 (FastAPI 推理接口)
├── core/           # 算法内核 (纯 Python 逻辑，无框架依赖)
├── labs/           # 🧪 实验室 (模型原型、策略复盘、快速验证)
├── data/           # 数据流 (清洗、缓存、AkShare 适配)
└── infra/          # 基建 (Docker, CI/CD, 监控)
```

**研发哲学：** `labs` (探索) → `core` (抽象) → `services` (服务化) → `apps` (产品化)。

---

## 🛠️ 技术栈

| 模块 | 技术选型 |
| :--- | :--- |
| **语言** | Python 3.10+ (类型标注、异步支持) |
| **数据采集** | AkShare (开源金融数据接口库) |
| **核心算法** | Pandas / NumPy / Scikit-learn (回归分析) |
| **后端 API** | FastAPI + Pydantic (高性能异步网关) |
| **存储/缓存** | SQLite / Redis (高效数据中转) |

---

## 🚦 快速开始 (MVP Demo)

直接运行 `labs` 中的原型脚本，体验实时估值逻辑：

```bash
# 1. 克隆并安装依赖
pip install -r requirements.txt

# 2. 运行特定基金(示例: 022485)的盘中估值实验
python labs/fund_nav_rt_022485/main.py
```

**预期输出：**
```json
{
  "timestamp": "2024-05-20 14:30:00",
  "fund_code": "022485",
  "est_nav": 1.412,
  "est_change": "+0.83%",
  "factor_contribution": {
    "CSI300": "0.65%",
    "Sector_Tech": "0.18%"
  },
  "confidence": "High (R²: 0.94)"
}
```
> *注：请在 A 股交易时段运行以获取真实数据反馈。*

---

## 🗺️ 路线图 (Roadmap)

- [x] **v0.1 (Current)**: 单个基金的因子回归估值原型。
- [ ] **v0.2**: 支持 QDII (海外基金) 与跨境资产对冲计算。
- [ ] **v0.3**: 引入长期残差修正模型 (Error Correction Model)。
- [ ] **v1.0**: 面向专业投资者的“量化看板” Web 端正式发布。

---

## 📑 状态说明

> **Warning**
> u0 目前处于 **早期研发阶段 (Early-stage / MVP)**。
> 金融市场具有高度不确定性，本平台提供的所有估值数据仅供科研参考，不构成投资建议。

---

<p align="right">
  Built with Precision by <strong>u0 Team</strong>
</p>
