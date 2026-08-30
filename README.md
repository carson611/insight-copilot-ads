# Insight Copilot for Ads

面向产品经理 / 运营 / 投放同学的**电商广告投放周复盘 Copilot**：上传广告投放明细（CSV / XLSX），系统自动完成指标计算、异常识别、维度归因、图表证据和周报生成。

> 定位：不是通用聊天问答，而是把「数据接入 → 指标计算 → 问题识别 → 图表证据 → AI 组织表达 → 风险提示」沉淀为一条可复用的投放复盘工作流。

## 核心能力

- **数据接入**：内置样例数据 / CSV、XLSX 上传 / 字段映射确认（支持中文业务字段名自动推荐）
- **指标体系**：16 个派生指标（CTR、CVR、ROI、CPC、CPA、CPM、单订单成本、客单价、贡献占比等），绑定字段字典与指标口径
- **自然语言问答**：18 类问题意图识别，覆盖转化下降、渠道 ROI、成本效率、贡献占比、预算分配、周报等高频复盘问题
- **图表证据链**：系统按问题意图生成图表计划并基于真实数据渲染，LLM 只解释证据、不伪造图表
- **RAG 知识增强**：72 张电商广告分析知识卡（指标口径、诊断框架、图表规则、风险边界）
- **AI 周报**：一键生成投放周报，可选 DeepSeek 润色，未配置 Key 时自动回退规则诊断

## 技术架构

| 层 | 职责 | 实现 |
|---|---|---|
| 规则层 | 指标计算、异常排序、规则诊断 | pandas |
| 图表层 | 图表计划生成与校验、真实图表渲染 | chart_planner.py + Plotly |
| 知识层 | 本地知识卡检索增强 | rag.py + knowledge_base/*.md |
| 表达层 | 回答与周报文字组织（可选） | DeepSeek Chat Completions API |

关键设计：**图表和指标全部由系统计算渲染，LLM 只负责组织语言**，从机制上约束幻觉。

## 快速开始（本地）

```bash
# 1. Python 3.12 建议
python -m venv .venv
.\.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 DeepSeek Key（可选，不配也能用规则诊断）
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
# 编辑 .streamlit/secrets.toml，填入 DEEPSEEK_API_KEY

# 4. 启动
streamlit run app.py
```

浏览器打开 http://127.0.0.1:8501。

## 部署到 Streamlit Community Cloud（免费）

1. 把本仓库推送到 GitHub（Public）。
2. 打开 https://share.streamlit.io 或 https://streamlit.io/cloud，用 GitHub 账号登录。
3. 点击 **New app** → 选择本仓库 → Branch `main` → Main file `app.py` → **Deploy**。
4. 部署完成后进入 **Settings → Secrets**，粘贴：
   ```toml
   DEEPSEEK_API_KEY = "sk-..."
   DEEPSEEK_MODEL = "deepseek-v4-flash"
   DEEPSEEK_BASE_URL = "https://api.deepseek.com"
   ```
5. 打开生成的公开链接即可使用。

> 免费额度限制：应用闲置约 1-3 天后进入休眠，再次访问会自动唤醒；单应用每月约有基础运行时长额度。

## 目录结构

```
.
├── app.py                  # Streamlit 主程序（页面 / 指标计算 / 诊断 / LLM 调用）
├── chart_planner.py        # 图表证据计划器（意图 → 图表计划 → 校验）
├── rag.py                  # RAG 检索模块（知识卡加载 / 打分 / 召回）
├── knowledge_base/         # 电商广告分析知识库（72 张知识卡）
├── evaluation/             # RAG 评估用例
├── outputs/                # 样例数据、字段/指标字典、项目文档
└── .streamlit/             # Streamlit 配置与密钥模板
```

## 样例数据说明

- `outputs/ecommerce_growth_sample.csv`：3,360 行、28 天模拟广告投放明细（预埋「本周转化率下降、抖音为主要拖累、搜索广告 ROI 最差」等可复现现象）
- `outputs/ecommerce_growth_user_upload_test.csv`：模拟用户上传文件，使用中文业务字段名，用于验证字段映射流程
- 数据均为**模拟数据**，不包含任何真实业务数据或用户隐私

## 版本迭代

- v1.0 定位 / PRD / 原型 / MVP Demo
- v1.1-v1.3 上传入口、字段映射、垂直定位收敛
- v2.x 接入 DeepSeek、RAG 知识库、意图识别、图表证据链
- v3.0-v3.1 指标系统建设（CPC / CPA / CVR / 贡献占比）

详细迭代说明见 `outputs/Insight-Copilot-for-Ads-产品总览与交接文档.md`。

## 免责声明

本项目为个人作品，用于求职展示与产品验证。所有指标计算基于样例数据，结论仅作为分析框架参考，不构成真实业务决策依据。
