# Insight Copilot v3.1 指标与贡献分析增强说明

## 本次升级重点

- 新增 `CVR` / 点击到订单转化率、`CPA` / 获客成本、`GMV 贡献占比`、`广告消耗占比` 等结构类指标。
- 补齐“问法 -> 图表计划 -> 证据图表 -> RAG 知识卡”的一致链路。
- 周报和老板摘要补充了 `CVR`、`CPA`、`GMV 贡献占比`、`广告消耗占比`。

## 主要能力变化

- `click_conversion` 新增：`CVR` 趋势、渠道 `CVR` 排行、点击到订单分析。
- `contribution` 新增：渠道收入贡献、消耗占比、结构趋势分析。
- `cost_efficiency` 扩展：`CPA` 口径与诊断框架。
- `PIVOT` 分析新增：收入/消耗/订单/点击/注册/曝光贡献占比。

## RAG 与知识库

- `rag.py` 新增对 `核心定义` 字段的检索和提示词抽取。
- 知识库新增：
  - `KB-METRIC-012` 到 `KB-METRIC-019`
  - `KB-CONV-005`、`KB-CONV-006`
  - `KB-COST-004`
  - `KB-CHART-010`、`KB-CHART-011`
  - `KB-REPORT-005`
  - `KB-SHARE-001`

## 当前状态

- 代码已做静态收口。
- 本地 Python 执行环境在当前 Codex 权限下被拦，runtime 验证尚未完成。
