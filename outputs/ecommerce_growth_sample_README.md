# Insight Copilot v1.2 样例数据说明

生成日期：2026-08-25

## 数据性质

本数据为模拟业务数据，仅用于 Insight Copilot / AI 数据分析 Copilot 个人项目 Demo，不代表真实公司业务，不包含公司真实数据或用户隐私。

## v1.2 升级点

- 覆盖原主样例数据：ecommerce_growth_sample.csv
- 新增商品品类：product_category
- 新增广告类型：ad_type
- 新增活动类型：campaign_type
- 新增用户上传测试文件：ecommerce_growth_user_upload_test.csv

## 时间范围

2026-07-27 至 2026-08-23，共 28 天。

## 核心维度

- date
- week_label
- channel
- device
- region
- product_category
- ad_type
- campaign_type

## 核心指标

- impressions
- clicks
- signups
- orders
- revenue
- cost
- ctr
- signup_rate
- order_rate
- roi
- aov

## 预埋业务现象

1. This Week 整体下单转化率较 Last Week 下降。
2. 抖音渠道是转化率下降的主要贡献来源。
3. 抖音 / 美妆个护 / 直播带货组合下滑更明显。
4. 搜索广告 ROI 最差，适合演示渠道 ROI 分析。

## 文件说明

- ecommerce_growth_sample.csv：v1.2 主样例数据。
- ecommerce_growth_user_upload_test.csv：模拟用户上传文件，字段名故意使用中文业务口径，用于测试字段映射。
- ecommerce_growth_field_dictionary.csv：字段字典。
- ecommerce_growth_metric_dictionary.csv：指标口径。
- ecommerce_growth_validation_summary.csv：本周 vs 上周指标验证。
- ecommerce_growth_channel_analysis.csv：渠道 ROI 和转化率拆解验证。
- ecommerce_growth_scenario_notes.csv：Demo 问题与预期答案。
