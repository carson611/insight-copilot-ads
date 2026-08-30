# 06 图表选择规则

## KB-CHART-001 转化率下降问题

- 适用问题：转化率为什么下降、下单少、成单掉了。
- 触发词：转化、下单率、下降、下滑、成单、承接。
- 推荐图表：
  1. 下单转化率趋势图：判断是否持续下行。
  2. 渠道转化变化图：定位拖累最大的渠道。
  3. 核心指标对比表：看订单、GMV、ROI 是否同步变化。
  4. 维度拖累图：进一步拆品类、广告类型、活动类型。
- 图表计划示例：
  - chart_type: line, metric: order_rate, dimension: date
  - chart_type: bar, metric: order_rate_change_pp, dimension: channel
  - chart_type: table, metrics: orders/revenue/cost/order_rate/roi
- 风险边界：不要只展示 ROI 图，因为转化问题需要漏斗证据。

## KB-CHART-002 ROI / 投产效率问题

- 适用问题：哪个渠道 ROI 最差、投产比为什么下降、烧钱不赚钱。
- 触发词：ROI、ROAS、投产、回报、不赚钱、低效、浪费。
- 推荐图表：
  1. 渠道 ROI 排名：识别低 ROI 渠道。
  2. 成本收益矩阵：识别高消耗低 ROI 渠道。
  3. ROI 多周趋势：判断是否持续恶化。
  4. 核心指标对比表：看 GMV 和消耗哪一端变化更大。
- 图表计划示例：
  - chart_type: bar, metric: roi, dimension: channel, sort: ascending
  - chart_type: scatter, x: cost, y: roi, size: revenue, dimension: channel
  - chart_type: line, metric: roi, dimension: week_label
- 风险边界：不要只按 ROI 排名给预算建议，需要结合消耗和 GMV 规模。

## KB-CHART-003 成本上涨问题

- 适用问题：广告消耗为什么上涨、成本是不是变贵、预算花在哪里。
- 触发词：成本、消耗、花费、烧钱、预算、变贵。
- 推荐图表：
  1. 广告消耗趋势图：判断成本变化节奏。
  2. 渠道消耗排行：定位消耗集中在哪些渠道。
  3. 成本收益矩阵：判断消耗是否换来回报。
  4. 核心指标对比表：看消耗、GMV、ROI 同步关系。
- 图表计划示例：
  - chart_type: line, metric: cost, dimension: date
  - chart_type: bar, metric: cost, dimension: channel, sort: descending
  - chart_type: scatter, x: cost, y: roi, size: revenue
- 风险边界：没有 CPC/CPM 时，不要生成“点击成本上涨”类确定结论。

## KB-CHART-004 GMV / 收入下降问题

- 适用问题：GMV 为什么下降、收入为什么下降、卖不动了。
- 触发词：GMV、收入、营收、销售额、卖不动、订单少。
- 推荐图表：
  1. GMV 趋势图：判断收入变化方向。
  2. 渠道 GMV 排行：找收入贡献下降渠道。
  3. 核心指标对比表：拆订单量和客单价。
  4. 品类 GMV 透视：判断是否为商品结构问题。
- 图表计划示例：
  - chart_type: line, metric: revenue, dimension: date
  - chart_type: bar, metric: revenue, dimension: channel
  - chart_type: table, metrics: revenue/orders/aov/order_rate/roi
- 风险边界：不能只看 GMV，需要拆订单量和客单价。

## KB-CHART-005 预算分配问题

- 适用问题：哪个渠道值得加预算、哪个渠道该砍、预算怎么分。
- 触发词：加预算、加投、放量、砍预算、预算分配、值得投。
- 推荐图表：
  1. 成本收益矩阵：判断消耗与 ROI 的组合。
  2. 渠道 ROI 排行：识别高效渠道。
  3. 渠道 GMV 排行：判断规模贡献。
  4. 多周 ROI 趋势：验证稳定性。
- 图表计划示例：
  - chart_type: scatter, x: cost, y: roi, size: revenue, dimension: channel
  - chart_type: bar, metric: roi, dimension: channel
  - chart_type: line, metric: roi, dimension: week_label
- 风险边界：不要承诺加预算后效果不变，需要提示边际 ROI 风险。

## KB-CHART-006 周报 / 老板摘要问题

- 适用问题：生成周报、给老板三条结论、业务复盘。
- 触发词：周报、报告、老板、结论、复盘、汇报。
- 推荐图表：
  1. GMV 多周趋势：看经营结果。
  2. ROI 多周趋势：看投放效率。
  3. 渠道拖累图：看异常来源。
  4. 核心指标对比表：支撑整体结论。
- 图表计划示例：
  - chart_type: line, metric: revenue, dimension: week_label
  - chart_type: line, metric: roi, dimension: week_label
  - chart_type: bar, metric: order_rate_change_pp, dimension: channel
  - chart_type: table, metrics: revenue/cost/orders/order_rate/roi
- 风险边界：周报正文只输出文字，真实图表由系统单独渲染。

## KB-CHART-007 点击质量 / CTR 问题

- 适用问题：CTR 下降、点击率异常、曝光有但点击少、素材吸引力变弱。
- 触发词：CTR、点击率、点击少、没人点、素材疲劳、创意。
- 推荐图表：
  1. CTR 趋势图：判断点击意愿是否持续走弱。
  2. 渠道 CTR 排行：识别点击质量最低的渠道。
  3. 核心指标对比表：同步看曝光和点击量变化。
  4. 渠道 ROI 排行：判断点击异常是否传导到投产效率。
- 图表计划示例：
  - chart_type: line, metric: ctr, dimension: date
  - chart_type: bar, metric: ctr, dimension: channel, sort: ascending
  - chart_type: table, metrics: impressions/clicks/ctr/revenue/cost/roi
- 风险边界：没有素材、广告位和停留时长字段时，不能确认 CTR 下降来自素材疲劳。

## KB-CHART-008 注册承接问题

- 适用问题：注册转化率下降、点击后没人注册、留资变少、落地页承接异常。
- 触发词：注册率、注册转化、留资、表单、落地页、点击后没人注册。
- 推荐图表：
  1. 注册转化率趋势图：判断点击到注册链路是否走弱。
  2. 渠道注册转化率排行：识别承接最弱的渠道。
  3. 核心指标对比表：同步看点击量和注册量变化。
  4. 渠道 ROI 排行：判断注册承接是否影响最终投产。
- 图表计划示例：
  - chart_type: line, metric: signup_rate, dimension: date
  - chart_type: bar, metric: signup_rate, dimension: channel, sort: ascending
  - chart_type: table, metrics: clicks/signups/signup_rate/orders/revenue/roi
- 风险边界：没有页面行为、表单错误和跳出率时，不能确认是落地页故障。

## KB-CHART-009 CPC / 成本效率问题

- 适用问题：CPC 为什么上涨、点击成本哪个渠道最高、CPM / 单订单成本异常。
- 触发词：CPC、CPM、CPA、点击成本、千次曝光成本、订单成本、单订单成本。
- 推荐图表：
  1. CPC 趋势图：判断点击成本是否持续抬升。
  2. 渠道 CPC 排行：定位点击成本最高渠道。
  3. 成本收益矩阵：判断高成本是否对应低 ROI。
  4. 核心指标对比表：同步看消耗、点击量、CTR、ROI。
- 图表计划示例：
  - chart_type: line, metric: cpc, dimension: date
  - chart_type: bar, metric: cpc, dimension: channel, sort: descending
  - chart_type: scatter, x: cost, y: roi, size: revenue, dimension: channel
- 风险边界：CPC 只能由成本和点击量计算，不包含真实竞价、出价和竞争环境原因。

## KB-CHART-010 CVR / 点击到订单转化率问题

- 适用问题：CVR 为什么下降、点击后下单为什么变差、点击到订单转化率异常。
- 触发词：CVR、点击到订单转化率、点击转化、点击后下单、成交承接。
- 推荐图表：
  1. CVR 趋势图：判断点击到订单链路是否持续走弱。
  2. 渠道 CVR 排行：识别成交承接最弱的渠道。
  3. 点击-订单漏斗：看点击量和订单量是否同步变化。
  4. 核心指标对比表：同步看 CTR、注册转化率、ROI。
- 图表计划示例：
  - chart_type: line, metric: cvr, dimension: date
  - chart_type: bar, metric: cvr, dimension: channel, sort: ascending
  - chart_type: table, metrics: clicks/orders/cvr/ctr/signup_rate/roi
- 风险边界：CVR 只说明点击到订单的结果，不等于流量质量本身。

## KB-CHART-011 贡献 / 占比问题

- 适用问题：哪个渠道收入贡献最大、哪个渠道消耗占比最高、结构是否变化。
- 触发词：贡献占比、份额、结构、收入贡献、消耗占比、订单贡献、点击贡献。
- 推荐图表：
  1. 贡献占比趋势图：看结构是否随时间变化。
  2. 渠道贡献占比排行：定位当前周期的主要贡献来源。
  3. 成本收益矩阵：判断高占比渠道是否同时高效。
  4. 核心指标对比表：同步看收入、消耗、订单、点击和 ROI。
- 图表计划示例：
  - chart_type: line, metric: revenue_share, dimension: week_label
  - chart_type: bar, metric: revenue_share, dimension: channel, sort: descending
  - chart_type: scatter, x: cost, y: roi, size: revenue, dimension: channel
  - chart_type: table, metrics: revenue/cost/orders/clicks/signups/revenue_share/cost_share
- 风险边界：占比高不等于高效率，要结合 ROI 和规模一起判断。
