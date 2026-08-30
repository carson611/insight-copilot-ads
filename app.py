# Insight Copilot for Ads / E-commerce Ad Performance Copilot
#
# Current version:
# - v2.0 introduced LLM API, RAG knowledge cards, hidden chart planning, and safety prompts.
# - v3.0 starts the metric system iteration: derived metrics, metric metadata, evidence charts, and RAG alignment.
# - v3.1 expands CVR / CPA / contribution-share analysis and aligns chart planning plus RAG cards.

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from chart_planner import build_chart_plan, chart_plan_summary, validate_chart_plan
from rag import format_knowledge_cards_for_prompt, knowledge_card_summary, retrieve_relevant_knowledge


ROOT_DIR = Path(__file__).resolve().parent
SAMPLE_DATA_PATH = ROOT_DIR / "outputs" / "ecommerce_growth_sample.csv"
PRODUCT_NAME = "Insight Copilot for Ads"
PRODUCT_VERSION = "v3.1 指标与贡献分析增强版"
PRODUCT_SUBTITLE = "电商广告投放效果分析 Copilot"
PRODUCT_TAGLINE = "面向产品经理 / 运营 / 投放同学的电商广告周复盘工作台"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"

SUM_COLUMNS = ["impressions", "clicks", "signups", "orders", "revenue", "cost"]
REQUIRED_COLUMNS = ["date", "channel", "device", "region", *SUM_COLUMNS]
OPTIONAL_DIMENSIONS = ["product_category", "ad_type", "campaign_type"]
DIMENSION_COLUMNS = ["channel", "region", "device", *OPTIONAL_DIMENSIONS]
FIELD_GUIDE = {
    "date": "日期，建议格式为 YYYY-MM-DD",
    "channel": "投放渠道，例如抖音、小红书、搜索广告",
    "device": "设备，例如移动端、桌面端",
    "region": "投放地区，例如华东、华北、华南",
    "product_category": "商品品类，例如美妆个护、数码配件",
    "ad_type": "广告类型，例如直播带货、达人种草、关键词广告",
    "campaign_type": "活动类型，例如日常投放、新品促销、会员日活动",
    "impressions": "曝光量，非负数字",
    "clicks": "点击量，非负数字",
    "signups": "注册量，非负数字",
    "orders": "支付订单量，非负数字",
    "revenue": "GMV / 成交金额，非负数字",
    "cost": "广告消耗 / 投放成本，非负数字",
}
QUESTION_OPTIONS = [
    "本周广告投放转化率为什么下降？",
    "哪个投放渠道 ROI 最差？",
    "哪个投放渠道 CPC 最高？",
    "哪个投放渠道获客成本最高？",
    "哪个投放渠道收入贡献最大？",
    "哪个投放渠道消耗占比最高？",
    "CVR 为什么下降？",
    "本周 CPC 为什么上涨？",
    "哪个投放渠道拖累最大？",
    "本周 GMV / 收入为什么下降？",
    "广告消耗为什么上涨？",
    "哪个渠道最值得加预算？",
    "哪个商品品类拖累最大？",
    "哪种广告类型 ROI 最差？",
    "哪个营销活动类型表现最好？",
    "帮我给老板写三条投放复盘结论",
    "帮我生成一份广告投放周报",
]
PIVOT_METRICS = {
    "GMV": "revenue",
    "支付订单量": "orders",
    "广告消耗": "cost",
    "CTR": "ctr",
    "注册转化率": "signup_rate",
    "CVR": "cvr",
    "下单转化率": "order_rate",
    "ROI": "roi",
    "CPC": "cpc",
    "CPM": "cpm",
    "获客成本": "cpa",
    "单订单成本": "cost_per_order",
    "GMV贡献占比": "revenue_share",
    "广告消耗占比": "cost_share",
    "订单贡献占比": "orders_share",
    "点击贡献占比": "click_share",
    "注册贡献占比": "signups_share",
    "曝光贡献占比": "impressions_share",
}

CORE_DISPLAY_METRICS = [
    "impressions",
    "clicks",
    "signups",
    "orders",
    "revenue",
    "cost",
    "ctr",
    "signup_rate",
    "cvr",
    "order_rate",
    "roi",
    "cpc",
    "cpa",
    "cpm",
    "cost_per_order",
    "aov",
]


METRIC_LABELS = {
    "impressions": "曝光量",
    "clicks": "点击量",
    "signups": "注册量",
    "orders": "支付订单量",
    "revenue": "GMV",
    "cost": "广告消耗",
    "ctr": "CTR",
    "signup_rate": "注册转化率",
    "cvr": "CVR / 点击到订单转化率",
    "order_rate": "下单转化率",
    "roi": "ROI",
    "cpc": "CPC",
    "cpa": "CPA / 获客成本",
    "cpm": "CPM",
    "cost_per_order": "单订单成本",
    "aov": "客单价",
    "click_to_order_rate": "CVR / 点击到订单转化率",
    "revenue_share": "GMV贡献占比",
    "cost_share": "广告消耗占比",
    "orders_share": "订单贡献占比",
    "click_share": "点击贡献占比",
    "signups_share": "注册贡献占比",
    "impressions_share": "曝光贡献占比",
}

PERCENT_METRICS = {
    "ctr",
    "signup_rate",
    "cvr",
    "order_rate",
    "click_to_order_rate",
    "revenue_share",
    "cost_share",
    "orders_share",
    "click_share",
    "signups_share",
    "impressions_share",
}

MONEY_METRICS = {
    "revenue",
    "cost",
    "cpc",
    "cpa",
    "cpm",
    "cost_per_order",
    "aov",
}

DIMENSION_LABELS = {
    "channel": "渠道",
    "region": "地区",
    "device": "设备",
    "product_category": "商品品类",
    "ad_type": "广告类型",
    "campaign_type": "活动类型",
}

FIELD_ALIASES = {
    "date": ["date", "日期", "统计日期", "业务日期", "时间"],
    "channel": ["channel", "渠道", "渠道来源", "来源渠道", "流量渠道"],
    "device": ["device", "设备", "终端", "终端类型", "设备类型"],
    "region": ["region", "地区", "区域", "大区", "城市区域"],
    "product_category": ["product_category", "品类", "商品品类", "类目", "商品类目"],
    "ad_type": ["ad_type", "广告类型", "广告方式", "投放方式", "广告形式"],
    "campaign_type": ["campaign_type", "活动类型", "营销活动", "活动名称", "活动"],
    "impressions": ["impressions", "曝光量", "曝光数", "展示量", "展现量"],
    "clicks": ["clicks", "点击量", "点击数"],
    "signups": ["signups", "注册量", "注册数", "注册用户", "注册用户数"],
    "orders": ["orders", "订单量", "订单数", "支付订单", "支付订单数", "成交订单数"],
    "revenue": ["revenue", "收入", "成交金额", "销售额", "GMV", "营收"],
    "cost": ["cost", "成本", "花费", "投放花费", "消耗", "广告消耗"],
    "week_label": ["week_label", "周标签", "自然周", "周期"],
}


@dataclass
class Diagnosis:
    headline: str
    evidence: list[str]
    suggestion: list[str]


@dataclass
class UploadResult:
    data: pd.DataFrame
    warnings: list[str]


def pct(value: float | int | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value * 100:.{digits}f}%"


def num(value: float | int | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}"


def money(value: float | int | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"¥{value:,.{digits}f}"


def ratio(value: float | int | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.{digits}f}"


def delta_pct(this_value: float, last_value: float) -> float | None:
    if pd.isna(this_value) or pd.isna(last_value) or last_value == 0:
        return None
    return this_value / last_value - 1


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["ctr"] = data.apply(lambda row: safe_divide(row["clicks"], row["impressions"]), axis=1)
    data["signup_rate"] = data.apply(lambda row: safe_divide(row["signups"], row["clicks"]), axis=1)
    data["order_rate"] = data.apply(lambda row: safe_divide(row["orders"], row["signups"]), axis=1)
    data["cvr"] = data.apply(lambda row: safe_divide(row["orders"], row["clicks"]), axis=1)
    data["roi"] = data.apply(lambda row: safe_divide(row["revenue"], row["cost"]), axis=1)
    data["cpc"] = data.apply(lambda row: safe_divide(row["cost"], row["clicks"]), axis=1)
    data["cpa"] = data.apply(lambda row: safe_divide(row["cost"], row["signups"]), axis=1)
    data["cpm"] = data.apply(lambda row: safe_divide(row["cost"], row["impressions"]) * 1000, axis=1)
    data["cost_per_order"] = data.apply(lambda row: safe_divide(row["cost"], row["orders"]), axis=1)
    data["aov"] = data.apply(lambda row: safe_divide(row["revenue"], row["orders"]), axis=1)
    return data


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(col).strip() for col in data.columns]
    warnings: list[str] = []

    missing = [col for col in REQUIRED_COLUMNS if col not in data.columns]
    if missing:
        expected = "、".join(REQUIRED_COLUMNS)
        raise ValueError(f"缺少必要字段：{'、'.join(missing)}。当前广告投放 Demo 需要这些字段：{expected}。")

    if data.empty:
        raise ValueError("上传文件没有数据行，请检查是否传错了文件或工作表。")

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    invalid_dates = int(data["date"].isna().sum())
    if invalid_dates:
        raise ValueError(f"date 字段有 {invalid_dates} 行无法识别，请改成 YYYY-MM-DD 这类日期格式。")

    for col in SUM_COLUMNS:
        raw_numeric = pd.to_numeric(data[col], errors="coerce")
        invalid_numbers = int(raw_numeric.isna().sum() - data[col].isna().sum())
        if invalid_numbers > 0:
            warnings.append(f"{col} 有 {invalid_numbers} 行不是数字，已按 0 处理。")
        negative_numbers = int((raw_numeric < 0).sum())
        if negative_numbers > 0:
            warnings.append(f"{col} 有 {negative_numbers} 行为负数，建议检查数据源。")
        data[col] = raw_numeric.fillna(0)

    for col in DIMENSION_COLUMNS:
        if col not in data.columns:
            continue
        missing_dims = int(data[col].isna().sum())
        data[col] = data[col].astype(str).str.strip()
        blank_dims = int((data[col] == "").sum())
        if missing_dims + blank_dims > 0:
            warnings.append(f"{col} 有 {missing_dims + blank_dims} 行为空，已标记为“未填写”。")
            data.loc[data[col] == "", col] = "未填写"
            data.loc[data[col].isin(["nan", "None", "NaT"]), col] = "未填写"

    if "week_label" not in data.columns:
        data = infer_week_label(data)
        warnings.append("未检测到 week_label 字段，已按最近 7 天为当前周期、再往前 7 天为上一周期自动推断。")

    data["week_label"] = data["week_label"].astype(str).str.strip()
    day_count = data["date"].dt.date.nunique()
    if day_count < 14:
        warnings.append("当前数据少于 14 天，本周 vs 上周对比可能不稳定。")

    normalized = add_derived_metrics(data)
    normalized.attrs["quality_warnings"] = warnings
    return normalized


def upload_summary(df: pd.DataFrame) -> list[str]:
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    dimension_summary = []
    for dimension in DIMENSION_COLUMNS:
        if dimension in df.columns:
            dimension_summary.append(f"{DIMENSION_LABELS[dimension]} {df[dimension].nunique()} 个")
    return [
        f"识别到 {len(df):,} 行数据，日期范围 {min_date} 至 {max_date}。",
        "识别到 " + "、".join(dimension_summary) + "。",
        "系统已自动计算 CTR、注册转化率、CVR、下单转化率、ROI、CPC、CPA、CPM、单订单成本、客单价和贡献占比。",
    ]


def infer_week_label(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    latest_date = data["date"].max()
    this_week_start = latest_date - pd.Timedelta(days=6)
    last_week_start = latest_date - pd.Timedelta(days=13)

    def label_date(value: pd.Timestamp) -> str:
        if value >= this_week_start:
            return "This Week"
        if value >= last_week_start:
            return "Last Week"
        return "Earlier"

    data["week_label"] = data["date"].apply(label_date)
    return data


def load_sample_data() -> pd.DataFrame:
    return normalize_data(pd.read_csv(SAMPLE_DATA_PATH, encoding="utf-8-sig"))


def read_table_from_bytes(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    lower_name = file_name.lower()
    if lower_name.endswith(".csv"):
        last_error = None
        for encoding in ["utf-8-sig", "utf-8", "gbk"]:
            try:
                return pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise ValueError(f"CSV 编码识别失败，请另存为 UTF-8 CSV 后再上传。原始错误：{last_error}")
    if lower_name.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(file_bytes))
    if lower_name.endswith(".xls"):
        raise ValueError("目前暂不支持旧版 .xls，请先用 WPS/Excel 另存为 .xlsx 后再上传。")
    raise ValueError("目前只支持 CSV、XLSX 文件。")


def read_uploaded_data(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()
    return normalize_data(read_table_from_bytes(file_name, file_bytes))


def find_default_mapping(columns: list[str], standard_field: str) -> str:
    normalized_columns = {str(col).strip().lower(): col for col in columns}
    for alias in FIELD_ALIASES.get(standard_field, []):
        matched = normalized_columns.get(alias.strip().lower())
        if matched is not None:
            return matched
    return "不映射"


def build_mapped_dataframe(raw_df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    mapped = pd.DataFrame()
    for standard_field, source_field in mapping.items():
        if source_field and source_field != "不映射":
            mapped[standard_field] = raw_df[source_field]
    return normalize_data(mapped)


def ensure_upload_history() -> None:
    if "upload_history" not in st.session_state:
        st.session_state["upload_history"] = []


def add_upload_to_history(uploaded_file) -> None:
    ensure_upload_history()
    file_bytes = uploaded_file.getvalue()
    file_id = f"{uploaded_file.name}-{len(file_bytes)}"
    exists = any(item["id"] == file_id for item in st.session_state["upload_history"])
    if not exists:
        st.session_state["upload_history"].insert(
            0,
            {
                "id": file_id,
                "name": uploaded_file.name,
                "bytes": file_bytes,
            },
        )
        st.session_state["upload_history"] = st.session_state["upload_history"][:5]


def confirmed_mapping_key(source_name: str) -> str:
    return f"confirmed_mapping_{source_name}"


def aggregate_metrics(df: pd.DataFrame, group_cols: Iterable[str] | None = None) -> pd.DataFrame:
    group_cols = list(group_cols or [])
    if group_cols:
        grouped = df.groupby(group_cols, as_index=False)[SUM_COLUMNS].sum()
    else:
        grouped = pd.DataFrame([df[SUM_COLUMNS].sum()])

    grouped["ctr"] = grouped.apply(lambda row: safe_divide(row["clicks"], row["impressions"]), axis=1)
    grouped["signup_rate"] = grouped.apply(lambda row: safe_divide(row["signups"], row["clicks"]), axis=1)
    grouped["order_rate"] = grouped.apply(lambda row: safe_divide(row["orders"], row["signups"]), axis=1)
    grouped["cvr"] = grouped.apply(lambda row: safe_divide(row["orders"], row["clicks"]), axis=1)
    grouped["roi"] = grouped.apply(lambda row: safe_divide(row["revenue"], row["cost"]), axis=1)
    grouped["cpc"] = grouped.apply(lambda row: safe_divide(row["cost"], row["clicks"]), axis=1)
    grouped["cpa"] = grouped.apply(lambda row: safe_divide(row["cost"], row["signups"]), axis=1)
    grouped["cpm"] = grouped.apply(lambda row: safe_divide(row["cost"], row["impressions"]) * 1000, axis=1)
    grouped["cost_per_order"] = grouped.apply(lambda row: safe_divide(row["cost"], row["orders"]), axis=1)
    grouped["aov"] = grouped.apply(lambda row: safe_divide(row["revenue"], row["orders"]), axis=1)

    if group_cols:
        share_sources = {
            "revenue": "revenue_share",
            "cost": "cost_share",
            "orders": "orders_share",
            "clicks": "click_share",
            "signups": "signups_share",
            "impressions": "impressions_share",
        }
        if "week_label" in group_cols:
            share_denominators = grouped.groupby("week_label")[list(share_sources.keys())].transform("sum")
            for source_col, share_col in share_sources.items():
                denom = share_denominators[source_col].replace(0, pd.NA)
                grouped[share_col] = (grouped[source_col] / denom).fillna(0)
        else:
            totals = grouped[list(share_sources.keys())].sum()
            for source_col, share_col in share_sources.items():
                total = float(totals[source_col])
                grouped[share_col] = grouped[source_col] / total if total else 0.0
    else:
        grouped["revenue_share"] = 1.0 if float(grouped["revenue"].iloc[0]) else 0.0
        grouped["cost_share"] = 1.0 if float(grouped["cost"].iloc[0]) else 0.0
        grouped["orders_share"] = 1.0 if float(grouped["orders"].iloc[0]) else 0.0
        grouped["click_share"] = 1.0 if float(grouped["clicks"].iloc[0]) else 0.0
        grouped["signups_share"] = 1.0 if float(grouped["signups"].iloc[0]) else 0.0
        grouped["impressions_share"] = 1.0 if float(grouped["impressions"].iloc[0]) else 0.0

    return grouped


def get_week_pair(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    labels = list(df["week_label"].dropna().unique())
    if "Last Week" in labels and "This Week" in labels:
        return (
            df[df["week_label"] == "Last Week"],
            df[df["week_label"] == "This Week"],
            "Last Week",
            "This Week",
        )

    latest_date = df["date"].max()
    this_start = latest_date - pd.Timedelta(days=6)
    last_start = latest_date - pd.Timedelta(days=13)
    last_week = df[(df["date"] >= last_start) & (df["date"] < this_start)]
    this_week = df[df["date"] >= this_start]
    return last_week, this_week, "上一周期", "当前周期"


def compare_weeks(df: pd.DataFrame) -> pd.DataFrame:
    last_week, this_week, last_label, this_label = get_week_pair(df)
    return compare_periods(last_week, this_week, last_label, this_label)


def compare_periods(last_df: pd.DataFrame, this_df: pd.DataFrame, last_label: str, this_label: str) -> pd.DataFrame:
    last_metrics = aggregate_metrics(last_df).iloc[0]
    this_metrics = aggregate_metrics(this_df).iloc[0]

    rows = []
    for metric in [
        "impressions",
        "clicks",
        "signups",
        "orders",
        "revenue",
        "cost",
        "ctr",
        "signup_rate",
        "cvr",
        "order_rate",
        "roi",
        "cpc",
        "cpa",
        "cpm",
        "cost_per_order",
        "aov",
    ]:
        rows.append(
            {
                "metric": metric,
                "指标": METRIC_LABELS[metric],
                last_label: last_metrics[metric],
                this_label: this_metrics[metric],
                "变化率": delta_pct(this_metrics[metric], last_metrics[metric]),
            }
        )
    return pd.DataFrame(rows)


def comparison_period_columns(comparison: pd.DataFrame) -> tuple[str, str]:
    period_cols = [col for col in comparison.columns if col not in ["metric", "指标", "变化率"]]
    if len(period_cols) < 2:
        raise ValueError("无法识别对比周期列。")
    return period_cols[0], period_cols[1]


def ordered_week_labels(df: pd.DataFrame) -> list[str]:
    if "week_label" not in df.columns:
        return []
    week_order = df.groupby("week_label")["date"].min().sort_values()
    return week_order.index.tolist()


def previous_week_label(df: pd.DataFrame, current_label: str) -> str | None:
    labels = ordered_week_labels(df)
    if current_label not in labels:
        return None
    idx = labels.index(current_label)
    if idx == 0:
        return None
    return labels[idx - 1]


def weekly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    weekly = aggregate_metrics(df, ["week_label"])
    week_start = df.groupby("week_label", as_index=False)["date"].min().rename(columns={"date": "week_start"})
    weekly = weekly.merge(week_start, on="week_label", how="left").sort_values("week_start")
    return weekly


def channel_analysis(df: pd.DataFrame) -> pd.DataFrame:
    return dimension_analysis(df, "channel")


def dimension_analysis(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    last_week, this_week, _, _ = get_week_pair(df)
    last_by_dimension = aggregate_metrics(last_week, [dimension]).rename(
        columns={
            "clicks": "last_clicks",
            "impressions": "last_impressions",
            "orders": "last_orders",
            "revenue": "last_revenue",
            "cost": "last_cost",
            "order_rate": "last_order_rate",
            "cvr": "last_cvr",
            "roi": "last_roi",
            "cpc": "last_cpc",
            "cpa": "last_cpa",
            "cpm": "last_cpm",
            "cost_per_order": "last_cost_per_order",
            "aov": "last_aov",
            "revenue_share": "last_revenue_share",
            "cost_share": "last_cost_share",
            "orders_share": "last_orders_share",
            "click_share": "last_click_share",
            "signups_share": "last_signups_share",
            "impressions_share": "last_impressions_share",
        }
    )
    this_by_dimension = aggregate_metrics(this_week, [dimension]).rename(
        columns={
            "clicks": "this_clicks",
            "impressions": "this_impressions",
            "orders": "this_orders",
            "revenue": "this_revenue",
            "cost": "this_cost",
            "order_rate": "this_order_rate",
            "cvr": "this_cvr",
            "roi": "this_roi",
            "cpc": "this_cpc",
            "cpa": "this_cpa",
            "cpm": "this_cpm",
            "cost_per_order": "this_cost_per_order",
            "aov": "this_aov",
            "revenue_share": "this_revenue_share",
            "cost_share": "this_cost_share",
            "orders_share": "this_orders_share",
            "click_share": "this_click_share",
            "signups_share": "this_signups_share",
            "impressions_share": "this_impressions_share",
        }
    )
    merged = this_by_dimension.merge(
        last_by_dimension[
            [
                dimension,
                "last_clicks",
                "last_impressions",
                "last_orders",
                "last_revenue",
                "last_cost",
                "last_order_rate",
                "last_cvr",
                "last_roi",
                "last_cpc",
                "last_cpa",
                "last_cpm",
                "last_cost_per_order",
                "last_aov",
                "last_revenue_share",
                "last_cost_share",
                "last_orders_share",
                "last_click_share",
                "last_signups_share",
                "last_impressions_share",
            ]
        ],
        on=dimension,
        how="left",
    )
    merged["order_rate_change_pp"] = (merged["this_order_rate"] - merged["last_order_rate"]) * 100
    merged["cvr_change_pp"] = (merged["this_cvr"] - merged["last_cvr"]) * 100
    merged["roi_change"] = merged["this_roi"] - merged["last_roi"]
    merged["revenue_change"] = merged["this_revenue"] - merged["last_revenue"]
    merged["cpc_change"] = merged["this_cpc"] - merged["last_cpc"]
    merged["cpa_change"] = merged["this_cpa"] - merged["last_cpa"]
    merged["cpm_change"] = merged["this_cpm"] - merged["last_cpm"]
    merged["cost_per_order_change"] = merged["this_cost_per_order"] - merged["last_cost_per_order"]
    merged["revenue_share_change_pp"] = (merged["this_revenue_share"] - merged["last_revenue_share"]) * 100
    merged["cost_share_change_pp"] = (merged["this_cost_share"] - merged["last_cost_share"]) * 100
    merged["orders_share_change_pp"] = (merged["this_orders_share"] - merged["last_orders_share"]) * 100
    merged["click_share_change_pp"] = (merged["this_click_share"] - merged["last_click_share"]) * 100
    merged["signups_share_change_pp"] = (merged["this_signups_share"] - merged["last_signups_share"]) * 100
    merged["impressions_share_change_pp"] = (merged["this_impressions_share"] - merged["last_impressions_share"]) * 100
    return merged.sort_values("this_roi", ascending=True)


def build_conversion_diagnosis(df: pd.DataFrame) -> Diagnosis:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    channels = channel_analysis(df)
    order_rate_row = comparison[comparison["metric"] == "order_rate"].iloc[0]
    signup_rate_row = comparison[comparison["metric"] == "signup_rate"].iloc[0]
    order_row = comparison[comparison["metric"] == "orders"].iloc[0]
    worst_drop = channels.sort_values("order_rate_change_pp", ascending=True).iloc[0]

    headline = (
        f"本周下单转化率为 {pct(order_rate_row[this_col])}，较上周 {pct(order_rate_row[last_col])} "
        f"变化 {pct(order_rate_row['变化率'])}。主要拖累来自 {worst_drop['channel']} 渠道。"
    )
    evidence = [
        f"订单量由 {num(order_row[last_col])} 下降到 {num(order_row[this_col])}，变化 {pct(order_row['变化率'])}。",
        f"注册转化率由 {pct(signup_rate_row[last_col])} 变化到 {pct(signup_rate_row[this_col])}，说明问题不只发生在下单环节前后。",
        f"{worst_drop['channel']} 渠道下单转化率下降 {abs(worst_drop['order_rate_change_pp']):.2f} 个百分点，是本周最明显的异常维度。",
    ]
    suggestion = [
        f"优先复盘 {worst_drop['channel']} 的投放素材、落地页、优惠策略和人群定向是否发生变化。",
        "将 ROI 较低且转化下降的渠道先降预算或做小流量实验，避免继续放大损失。",
        "对自然流量和高 ROI 渠道保留观察，避免把整体问题误判为全站产品问题。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_stage_metric_diagnosis(df: pd.DataFrame, metric: str, metric_label: str, stage_label: str) -> Diagnosis:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    row = comparison[comparison["metric"] == metric].iloc[0]
    last_week, this_week, _, _ = get_week_pair(df)
    current_channel = aggregate_metrics(this_week, ["channel"]).sort_values(metric, ascending=True)
    worst = current_channel.iloc[0]
    best = current_channel.sort_values(metric, ascending=False).iloc[0]

    if metric == "ctr":
        volume_metric = comparison[comparison["metric"] == "clicks"].iloc[0]
        volume_text = f"点击量由 {num(volume_metric[last_col])} 变为 {num(volume_metric[this_col])}"
        diagnosis_focus = "素材吸引力、人群匹配和广告位质量"
    else:
        volume_metric = comparison[comparison["metric"] == "signups"].iloc[0]
        volume_text = f"注册量由 {num(volume_metric[last_col])} 变为 {num(volume_metric[this_col])}"
        diagnosis_focus = "落地页承接、注册流程和表单门槛"

    headline = (
        f"本周{metric_label}为 {format_metric_value(metric, row[this_col])}，较上周 "
        f"{format_metric_value(metric, row[last_col])} 变化 {pct(row['变化率'])}，优先按{stage_label}排查。"
    )
    evidence = [
        f"{volume_text}，变化 {pct(volume_metric['变化率'])}。",
        f"本周{metric_label}最低的渠道是 {worst['channel']}，为 {format_metric_value(metric, worst[metric])}。",
        f"作为对比，{metric_label}最高的渠道是 {best['channel']}，为 {format_metric_value(metric, best[metric])}。",
    ]
    suggestion = [
        f"优先排查 {worst['channel']} 的{diagnosis_focus}，先作为待验证假设。",
        "结合下方趋势图和渠道排行判断是否为单周波动，避免只凭一个指标直接定责。",
        "若后续补充页面行为、素材、关键词或表单错误数据，可继续做更细归因。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_click_conversion_diagnosis(df: pd.DataFrame) -> Diagnosis:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    channels = channel_analysis(df)
    cvr_row = comparison[comparison["metric"] == "cvr"].iloc[0]
    click_row = comparison[comparison["metric"] == "clicks"].iloc[0]
    order_row = comparison[comparison["metric"] == "orders"].iloc[0]
    worst_drop = channels.sort_values("cvr_change_pp", ascending=True).iloc[0]
    best = channels.sort_values("this_cvr", ascending=False).iloc[0]

    headline = (
        f"本周 CVR（点击到订单转化率）为 {pct(cvr_row[this_col])}，较上周 {pct(cvr_row[last_col])} "
        f"变化 {pct(cvr_row['变化率'])}。主要拖累来自 {worst_drop['channel']} 渠道。"
    )
    evidence = [
        f"点击量由 {num(click_row[last_col])} 变为 {num(click_row[this_col])}，订单量由 {num(order_row[last_col])} 变为 {num(order_row[this_col])}。",
        f"{worst_drop['channel']} 渠道 CVR 下降 {abs(worst_drop['cvr_change_pp']):.2f} 个百分点，是本周最明显的异常维度。",
        f"作为对比，{best['channel']} 的 CVR 最高，为 {pct(best['this_cvr'])}。",
    ]
    suggestion = [
        f"优先复盘 {worst_drop['channel']} 的落地页承接、商品力、价格权益和支付链路。",
        "结合 CTR 和注册转化率一起看，判断问题是前端流量质量，还是后端成交承接。",
        "如果 CVR 下滑但点击量稳定，说明问题更偏向承接链路而不是流量规模。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def contribution_metric_from_question(question: str) -> tuple[str, str]:
    normalized = question.lower()
    if "消耗" in question or "花费" in question or "成本" in question or "烧钱" in question:
        return "cost_share", "广告消耗占比"
    if "订单" in question or "成交" in question or "下单" in question:
        return "orders_share", "订单贡献占比"
    if "点击" in question or "流量" in question:
        return "click_share", "点击贡献占比"
    if "注册" in question or "留资" in question or "线索" in question:
        return "signups_share", "注册贡献占比"
    if "曝光" in question or "展现" in question or "触达" in question:
        return "impressions_share", "曝光贡献占比"
    if "gmv" in normalized or "收入" in question or "营收" in question or "销售额" in question:
        return "revenue_share", "GMV贡献占比"
    return "revenue_share", "GMV贡献占比"


def build_contribution_diagnosis(df: pd.DataFrame, question: str) -> Diagnosis:
    metric, metric_label = contribution_metric_from_question(question)
    channels = channel_analysis(df)
    ranked = channels.sort_values(f"this_{metric}", ascending=False)
    top = ranked.iloc[0]
    runner_up = ranked.iloc[1] if len(ranked) > 1 else ranked.iloc[0]
    biggest_gain = channels.sort_values(f"{metric}_change_pp", ascending=False).iloc[0]

    headline = f"本周{metric_label}最高的渠道是 {top['channel']}，占比 {pct(top[f'this_{metric}'])}。"
    evidence = [
        f"{top['channel']} 的{metric_label}为 {pct(top[f'this_{metric}'])}，较上周 {pct(top[f'last_{metric}'])} 变化 {top[f'{metric}_change_pp']:.2f} 个百分点。",
        f"第二高的是 {runner_up['channel']}，{metric_label}为 {pct(runner_up[f'this_{metric}'])}。",
        f"占比提升最快的是 {biggest_gain['channel']}，较上周增加 {biggest_gain[f'{metric}_change_pp']:.2f} 个百分点。",
    ]
    suggestion = [
        f"如果是收入或订单贡献占比，优先确认高贡献渠道是否具备稳定放量空间。",
        f"如果是消耗占比，优先排查 {top['channel']} 是否存在预算集中但回报不足的问题。",
        "占比分析适合和 ROI、CPC、CVR 一起看，避免只看结构不看效率。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_roi_diagnosis(df: pd.DataFrame) -> Diagnosis:
    channels = channel_analysis(df)
    worst_roi = channels.iloc[0]
    best_roi = channels.sort_values("this_roi", ascending=False).iloc[0]

    headline = f"本周 ROI 最差的渠道是 {worst_roi['channel']}，ROI 为 {ratio(worst_roi['this_roi'])}。"
    evidence = [
        f"{worst_roi['channel']} 本周收入 {money(worst_roi['this_revenue'])}，成本 {money(worst_roi['this_cost'])}。",
        f"作为对比，ROI 最高渠道是 {best_roi['channel']}，ROI 为 {ratio(best_roi['this_roi'])}。",
        f"{worst_roi['channel']} 的 ROI 较上周变化 {ratio(worst_roi['roi_change'])}，需要结合预算变化判断是否继续投放。",
    ]
    suggestion = [
        f"短期建议降低 {worst_roi['channel']} 的预算占比，并拆看关键词、素材、落地页转化链路。",
        "将预算向 ROI 更稳定的渠道倾斜，但保留小样本实验组继续验证。",
        "不要只看 ROI，也要同步看收入规模，避免误杀低 ROI 但贡献较大的渠道。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_drag_diagnosis(df: pd.DataFrame) -> Diagnosis:
    channels = channel_analysis(df).sort_values("order_rate_change_pp", ascending=True)
    biggest_drag = channels.iloc[0]
    second_drag = channels.iloc[1] if len(channels) > 1 else channels.iloc[0]

    headline = f"本周拖累最大的渠道是 {biggest_drag['channel']}，下单转化率下降 {abs(biggest_drag['order_rate_change_pp']):.2f} 个百分点。"
    evidence = [
        f"{biggest_drag['channel']} 本周下单转化率为 {pct(biggest_drag['this_order_rate'])}，上周为 {pct(biggest_drag['last_order_rate'])}。",
        f"第二个需要关注的渠道是 {second_drag['channel']}，下单转化率变化 {second_drag['order_rate_change_pp']:.2f} 个百分点。",
        f"{biggest_drag['channel']} 本周 ROI 为 {ratio(biggest_drag['this_roi'])}，说明转化下降也影响了投放效率。",
    ]
    suggestion = [
        f"先围绕 {biggest_drag['channel']} 做异常归因，拆成流量质量、落地页、价格权益、库存履约四类假设。",
        "如果渠道流量质量下降，优先调整投放定向；如果落地页转化下降，优先做页面和权益 A/B 测试。",
        "把异常归因结论沉淀成固定分析模板，作为 Copilot 后续自动诊断能力。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_dimension_drag_diagnosis(df: pd.DataFrame, dimension: str) -> Diagnosis:
    label = DIMENSION_LABELS[dimension]
    analysis = dimension_analysis(df, dimension).sort_values("order_rate_change_pp", ascending=True)
    biggest_drag = analysis.iloc[0]
    second_drag = analysis.iloc[1] if len(analysis) > 1 else analysis.iloc[0]

    headline = f"本周拖累最大的{label}是 {biggest_drag[dimension]}，下单转化率下降 {abs(biggest_drag['order_rate_change_pp']):.2f} 个百分点。"
    evidence = [
        f"{biggest_drag[dimension]} 本周下单转化率为 {pct(biggest_drag['this_order_rate'])}，上周为 {pct(biggest_drag['last_order_rate'])}。",
        f"第二个需要关注的{label}是 {second_drag[dimension]}，下单转化率变化 {second_drag['order_rate_change_pp']:.2f} 个百分点。",
        f"{biggest_drag[dimension]} 本周 ROI 为 {ratio(biggest_drag['this_roi'])}，收入为 {money(biggest_drag['this_revenue'])}。",
    ]
    suggestion = [
        f"优先围绕 {biggest_drag[dimension]} 拆看渠道、人群、价格权益和落地页承接。",
        f"把 {label} 维度与渠道维度交叉分析，判断是单一维度问题还是组合问题。",
        "后续迭代可继续增强大模型对指标、维度和时间范围的解析能力。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_dimension_roi_diagnosis(df: pd.DataFrame, dimension: str) -> Diagnosis:
    label = DIMENSION_LABELS[dimension]
    analysis = dimension_analysis(df, dimension).sort_values("this_roi", ascending=True)
    worst = analysis.iloc[0]
    best = analysis.sort_values("this_roi", ascending=False).iloc[0]

    headline = f"本周 ROI 最差的{label}是 {worst[dimension]}，ROI 为 {ratio(worst['this_roi'])}。"
    evidence = [
        f"{worst[dimension]} 本周收入 {money(worst['this_revenue'])}，成本 {money(worst['this_cost'])}。",
        f"作为对比，ROI 最高的{label}是 {best[dimension]}，ROI 为 {ratio(best['this_roi'])}。",
        f"{worst[dimension]} 的 ROI 较上周变化 {ratio(worst['roi_change'])}，需要结合投放策略判断是否继续投入。",
    ]
    suggestion = [
        f"对 {worst[dimension]} 做预算收缩或策略复盘，优先排查成本上涨和转化承接。",
        f"对 {best[dimension]} 保留预算或小幅加码，观察边际 ROI 是否稳定。",
        "不要只按单一维度做决策，建议和渠道、品类、活动类型做交叉验证。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_dimension_best_diagnosis(df: pd.DataFrame, dimension: str) -> Diagnosis:
    label = DIMENSION_LABELS[dimension]
    analysis = dimension_analysis(df, dimension).sort_values(["this_roi", "this_revenue"], ascending=[False, False])
    best = analysis.iloc[0]
    runner_up = analysis.iloc[1] if len(analysis) > 1 else analysis.iloc[0]

    headline = f"本周表现最好的{label}是 {best[dimension]}，ROI 为 {ratio(best['this_roi'])}。"
    evidence = [
        f"{best[dimension]} 本周收入 {money(best['this_revenue'])}，成本 {money(best['this_cost'])}，下单转化率 {pct(best['this_order_rate'])}。",
        f"第二梯队是 {runner_up[dimension]}，ROI 为 {ratio(runner_up['this_roi'])}。",
        f"{best[dimension]} 的 ROI 较上周变化 {ratio(best['roi_change'])}，需要继续观察稳定性。",
    ]
    suggestion = [
        f"短期可以保留或小幅增加 {best[dimension]} 的资源投入。",
        "同时关注收入规模，避免只追求 ROI 而忽略业务增量。",
        f"建议把 {label} 与渠道维度交叉，找到可复制的高效组合。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_missing_dimension_diagnosis(df: pd.DataFrame, dimension: str) -> Diagnosis:
    label = DIMENSION_LABELS.get(dimension, dimension)
    available_dimensions = [DIMENSION_LABELS[col] for col in DIMENSION_COLUMNS if col in df.columns]
    available_text = "、".join(available_dimensions) if available_dimensions else "暂无可用维度"

    return Diagnosis(
        f"当前数据没有「{label}」字段，暂时不能按{label}做细分分析。",
        [
            f"当前已识别维度为：{available_text}。",
            f"这个问题需要上传数据中存在并映射到标准字段 {dimension}，否则系统无法计算{label}维度的排行、拖累或 ROI。",
            "基础广告指标仍可继续按渠道、地区和设备分析，不会影响 GMV、广告消耗、ROI、CPC、CPA、CVR 等核心指标计算。",
        ],
        [
            f"如果要分析{label}，请在上传文件中补充对应列，并在字段映射确认区完成映射。",
            "在字段缺失时不要强行输出维度结论，避免把不存在的字段包装成业务发现。",
        ],
    )


def build_boundary_diagnosis(df: pd.DataFrame) -> Diagnosis:
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    dimensions = [DIMENSION_LABELS[col] for col in DIMENSION_COLUMNS if col in df.columns]
    dimension_text = "、".join(dimensions) if dimensions else "暂无可用维度"

    return Diagnosis(
        "当前数据能定位广告投放异常维度，但不能确认真实业务原因。",
        [
            f"当前数据范围为 {min_date} 至 {max_date}，可分析维度为：{dimension_text}。",
            "系统可计算曝光、点击、注册、订单、GMV、广告消耗、CTR、CVR、ROI、CPC、CPA、CPM、贡献占比等指标。",
            "当前数据没有素材、出价、竞价环境、库存、价格、落地页行为、用户分层和售后等字段，因此不能证明真实原因。",
        ],
        [
            "回答中只能把原因写成可能原因或待验证假设，不能写成已验证事实。",
            "如果要继续提高归因可信度，需要补充素材、出价、页面行为、商品价格、库存履约和活动策略数据。",
        ],
    )


def build_field_compatibility_diagnosis(df: pd.DataFrame) -> Diagnosis:
    required_text = "日期、渠道、设备、地区、曝光量、点击量、注册量、支付订单量、GMV、广告消耗"
    optional_text = "商品品类、广告类型、活动类型、自然周标签"
    dimensions = [DIMENSION_LABELS[col] for col in DIMENSION_COLUMNS if col in df.columns]
    dimension_text = "、".join(dimensions) if dimensions else "暂无可用维度"

    return Diagnosis(
        "可以分析字段名不同的上传文件，但必须先完成标准字段映射确认。",
        [
            f"P0 必填字段是：{required_text}。缺少必填字段时系统会停止分析，避免错口径计算。",
            f"可选增强字段是：{optional_text}。缺少可选字段时，只影响对应维度拆解，不影响核心指标。",
            f"当前筛选数据已识别维度为：{dimension_text}。",
        ],
        [
            "上传后先在左侧完成字段映射确认，再进入看板、Copilot 问答和周报生成。",
            "如果业务字段口径不一致，例如收入不是 GMV、注册不是留资，需要先在人为确认后再分析。",
        ],
    )


def build_revenue_diagnosis(df: pd.DataFrame) -> Diagnosis:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    channels = channel_analysis(df)
    revenue = comparison[comparison["metric"] == "revenue"].iloc[0]
    orders = comparison[comparison["metric"] == "orders"].iloc[0]
    aov = comparison[comparison["metric"] == "aov"].iloc[0]
    biggest_revenue_drop = channels.sort_values("revenue_change", ascending=True).iloc[0]

    headline = f"本周收入为 {money(revenue[this_col])}，较上周变化 {pct(revenue['变化率'])}，主要受订单量下降影响。"
    evidence = [
        f"订单量由 {num(orders[last_col])} 变为 {num(orders[this_col])}，变化 {pct(orders['变化率'])}。",
        f"客单价由 {money(aov[last_col], digits=2)} 变为 {money(aov[this_col], digits=2)}，变化 {pct(aov['变化率'])}，不是收入下降的主因。",
        f"{biggest_revenue_drop['channel']} 渠道收入变化 {money(biggest_revenue_drop['revenue_change'])}，是收入侧最需要优先复盘的渠道。",
    ]
    suggestion = [
        "先把收入下降拆成订单量和客单价两条线，本周优先排查订单量下降。",
        f"重点复盘 {biggest_revenue_drop['channel']} 的流量质量、转化链路和优惠策略变化。",
        "后续迭代可继续拆到品类、广告类型和活动类型，判断是否是局部业务问题。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_cost_diagnosis(df: pd.DataFrame) -> Diagnosis:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    channels = channel_analysis(df)
    cost = comparison[comparison["metric"] == "cost"].iloc[0]
    roi = comparison[comparison["metric"] == "roi"].iloc[0]
    current_channel = aggregate_metrics(get_week_pair(df)[1], ["channel"])
    costliest = current_channel.sort_values("cost", ascending=False).iloc[0]
    worst_roi = channels.iloc[0]

    headline = f"本周投放成本为 {money(cost[this_col])}，较上周变化 {pct(cost['变化率'])}，同时 ROI 从 {ratio(roi[last_col])} 降至 {ratio(roi[this_col])}。"
    evidence = [
        f"本周成本最高的渠道是 {costliest['channel']}，成本为 {money(costliest['cost'])}。",
        f"ROI 最低的渠道是 {worst_roi['channel']}，本周 ROI 为 {ratio(worst_roi['this_roi'])}。",
        "成本上涨但 ROI 下滑，说明预算增加没有带来等比例收入增长，需要拆看投放效率。",
    ]
    suggestion = [
        f"优先检查 {worst_roi['channel']} 的预算、点击成本、关键词或素材质量。",
        "对低 ROI 渠道做预算收缩或小流量实验，避免继续扩大无效消耗。",
        "把成本、收入和 ROI 同时展示，避免只看成本上涨而忽略投入产出。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def cost_efficiency_metric_from_question(question: str) -> tuple[str, str]:
    normalized = question.lower()
    if "cpm" in normalized or "千次曝光" in question:
        return "cpm", "CPM"
    if "cpa" in normalized or "获客成本" in question or "注册成本" in question or "单注册成本" in question:
        return "cpa", "CPA / 获客成本"
    if "单订单成本" in question or "订单成本" in question or "成交成本" in question:
        return "cost_per_order", "单订单成本"
    return "cpc", "CPC"


def build_cost_efficiency_diagnosis(df: pd.DataFrame, question: str) -> Diagnosis:
    metric, metric_label = cost_efficiency_metric_from_question(question)
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    metric_row = comparison[comparison["metric"] == metric].iloc[0]
    cost_row = comparison[comparison["metric"] == "cost"].iloc[0]
    channels = channel_analysis(df)
    worst = channels.sort_values(f"this_{metric}", ascending=False).iloc[0]
    best = channels.sort_values(f"this_{metric}", ascending=True).iloc[0]

    if metric == "cpc":
        clicks_row = comparison[comparison["metric"] == "clicks"].iloc[0]
        driver = (
            f"广告消耗由 {money(cost_row[last_col])} 变为 {money(cost_row[this_col])}，"
            f"点击量由 {num(clicks_row[last_col])} 变为 {num(clicks_row[this_col])}，"
            "CPC 变化需要同时看成本和点击量。"
        )
        focus = "出价、关键词/人群质量、素材点击效率和平台竞争环境"
    elif metric == "cpm":
        impressions_row = comparison[comparison["metric"] == "impressions"].iloc[0]
        driver = (
            f"广告消耗由 {money(cost_row[last_col])} 变为 {money(cost_row[this_col])}，"
            f"曝光量由 {num(impressions_row[last_col])} 变为 {num(impressions_row[this_col])}，"
            "CPM 变化需要同时看成本和曝光量。"
        )
        focus = "出价、人群竞争、曝光资源和排期变化"
    elif metric == "cpa":
        signups_row = comparison[comparison["metric"] == "signups"].iloc[0]
        driver = (
            f"广告消耗由 {money(cost_row[last_col])} 变为 {money(cost_row[this_col])}，"
            f"注册量由 {num(signups_row[last_col])} 变为 {num(signups_row[this_col])}，"
            "CPA 变化需要同时看成本和注册量。"
        )
        focus = "注册承接、线索质量、落地页门槛和投放人群"
    else:
        orders_row = comparison[comparison["metric"] == "orders"].iloc[0]
        driver = (
            f"广告消耗由 {money(cost_row[last_col])} 变为 {money(cost_row[this_col])}，"
            f"订单量由 {num(orders_row[last_col])} 变为 {num(orders_row[this_col])}，"
            "单订单成本变化需要同时看成本和成交量。"
        )
        focus = "投放效率、成交承接、低效渠道占比和订单质量"

    headline = (
        f"本周{metric_label}为 {format_metric_value(metric, metric_row[this_col])}，较上周 "
        f"{format_metric_value(metric, metric_row[last_col])} 变化 {pct(metric_row['变化率'])}。"
    )
    evidence = [
        driver,
        f"本周{metric_label}最高的渠道是 {worst['channel']}，为 {format_metric_value(metric, worst[f'this_{metric}'])}。",
        f"作为对比，{metric_label}最低的渠道是 {best['channel']}，为 {format_metric_value(metric, best[f'this_{metric}'])}。",
    ]
    suggestion = [
        f"优先排查 {worst['channel']} 的{focus}，先作为待验证假设。",
        f"下方可结合【{metric_label}趋势图】和【渠道{metric_label}排行】判断是整体抬升还是局部渠道拉高。",
        "当前 Demo 没有平台出价、竞争度和素材粒度，不能直接确认真实成本上涨原因。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_budget_diagnosis(df: pd.DataFrame) -> Diagnosis:
    last_week, this_week, _, _ = get_week_pair(df)
    current_channel = aggregate_metrics(this_week, ["channel"])
    paid_channel = current_channel[~current_channel["channel"].str.contains("自然", na=False)].copy()
    if paid_channel.empty:
        paid_channel = current_channel.copy()
    best = paid_channel.sort_values(["roi", "revenue"], ascending=[False, False]).iloc[0]
    worst = paid_channel.sort_values("roi", ascending=True).iloc[0]

    headline = f"如果只看当前样例数据，最值得优先加预算的付费渠道是 {best['channel']}，本周 ROI 为 {ratio(best['roi'])}。"
    evidence = [
        f"{best['channel']} 本周收入 {money(best['revenue'])}，成本 {money(best['cost'])}，ROI {ratio(best['roi'])}。",
        f"作为对比，{worst['channel']} ROI 为 {ratio(worst['roi'])}，投放效率明显更弱。",
        "自然流量 ROI 很高，但通常不适合简单理解为“加预算渠道”，因此预算建议优先看付费渠道。",
    ]
    suggestion = [
        f"对 {best['channel']} 做小幅预算加码，同时观察转化率和边际 ROI 是否保持稳定。",
        f"对 {worst['channel']} 先降预算或拆分实验组，定位是流量质量问题还是承接页问题。",
        "预算调整不建议一次性大幅切换，先用 10%-20% 的预算做分层验证更稳妥。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_executive_summary(df: pd.DataFrame) -> Diagnosis:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    channels = channel_analysis(df)
    revenue = comparison[comparison["metric"] == "revenue"].iloc[0]
    cost = comparison[comparison["metric"] == "cost"].iloc[0]
    roi = comparison[comparison["metric"] == "roi"].iloc[0]
    cvr = comparison[comparison["metric"] == "cvr"].iloc[0]
    cpa = comparison[comparison["metric"] == "cpa"].iloc[0]
    order_rate = comparison[comparison["metric"] == "order_rate"].iloc[0]
    worst_roi = channels.iloc[0]
    biggest_drag = channels.sort_values("order_rate_change_pp", ascending=True).iloc[0]
    top_revenue = channels.sort_values("this_revenue_share", ascending=False).iloc[0]
    top_cost = channels.sort_values("this_cost_share", ascending=False).iloc[0]

    headline = "给老板看的三条投放复盘结论已生成。"
    evidence = [
        f"收入侧：本周收入 {money(revenue[this_col])}，较上周变化 {pct(revenue['变化率'])}，下单转化率从 {pct(order_rate[last_col])} 变为 {pct(order_rate[this_col])}。",
        f"效率侧：本周成本 {money(cost[this_col])}，较上周变化 {pct(cost['变化率'])}；ROI 从 {ratio(roi[last_col])} 变为 {ratio(roi[this_col])}；CVR 为 {pct(cvr[this_col])}，CPA 为 {money(cpa[this_col], digits=2)}。",
        f"结构侧：{top_cost['channel']} 是消耗占比最高渠道，{top_revenue['channel']} 是 GMV 贡献最高渠道。",
        f"归因侧：{biggest_drag['channel']} 是转化下降主要拖累，{worst_roi['channel']} 是 ROI 最差渠道。",
    ]
    suggestion = [
        f"下周优先复盘 {biggest_drag['channel']} 的转化链路，确认是否与素材、人群或落地页变化有关。",
        f"对 {worst_roi['channel']} 做预算控制和分组实验，避免成本继续放大。",
        "保留高 ROI 渠道预算，同时补充品类/活动维度，判断问题是否集中在局部业务单元。",
    ]
    return Diagnosis(headline, evidence, suggestion)


def build_weekly_report(df: pd.DataFrame) -> str:
    comparison = compare_weeks(df)
    last_col, this_col = comparison_period_columns(comparison)
    channels = channel_analysis(df)
    order_rate = comparison[comparison["metric"] == "order_rate"].iloc[0]
    revenue = comparison[comparison["metric"] == "revenue"].iloc[0]
    roi = comparison[comparison["metric"] == "roi"].iloc[0]
    cost = comparison[comparison["metric"] == "cost"].iloc[0]
    cvr = comparison[comparison["metric"] == "cvr"].iloc[0]
    cpa = comparison[comparison["metric"] == "cpa"].iloc[0]
    worst_roi = channels.iloc[0]
    biggest_drag = channels.sort_values("order_rate_change_pp", ascending=True).iloc[0]
    top_revenue = channels.sort_values("this_revenue_share", ascending=False).iloc[0]
    top_cost = channels.sort_values("this_cost_share", ascending=False).iloc[0]

    return "\n".join(
        [
            "广告投放周报摘要",
            "",
            f"本周收入 {money(revenue[this_col])}，较上周变化 {pct(revenue['变化率'])}；投放成本 {money(cost[this_col])}，较上周变化 {pct(cost['变化率'])}。",
            f"本周 ROI 为 {ratio(roi[this_col])}，较上周 {ratio(roi[last_col])} 变化 {pct(roi['变化率'])}。",
            f"本周 CVR 为 {pct(cvr[this_col])}，较上周 {pct(cvr[last_col])} 变化 {pct(cvr['变化率'])}；CPA 为 {money(cpa[this_col], digits=2)}，较上周变化 {pct(cpa['变化率'])}。",
            f"本周下单转化率为 {pct(order_rate[this_col])}，较上周 {pct(order_rate[last_col])} 变化 {pct(order_rate['变化率'])}。",
            f"GMV 贡献最高的渠道是 {top_revenue['channel']}，贡献占比 {pct(top_revenue['this_revenue_share'])}。",
            f"广告消耗占比最高的渠道是 {top_cost['channel']}，占比 {pct(top_cost['this_cost_share'])}。",
            f"渠道侧看，{worst_roi['channel']} ROI 最低，为 {ratio(worst_roi['this_roi'])}；{biggest_drag['channel']} 下单转化率下降最明显，下降 {abs(biggest_drag['order_rate_change_pp']):.2f} 个百分点。",
            "建议下周优先排查低 ROI 渠道的投放质量和落地页转化，同时保留高 ROI 渠道预算，避免整体收入继续承压。",
        ]
    )


def build_weekly_report_for_label(df: pd.DataFrame, current_label: str) -> str:
    labels = ordered_week_labels(df)
    if current_label not in labels:
        current_label = labels[-1]
    previous_label = previous_week_label(df, current_label)
    current_df = df[df["week_label"] == current_label]
    current_metrics = aggregate_metrics(current_df).iloc[0]
    current_channels = channel_analysis(current_df)

    if previous_label is None:
        top_revenue = current_channels.sort_values("this_revenue_share", ascending=False).iloc[0]
        top_cost = current_channels.sort_values("this_cost_share", ascending=False).iloc[0]
        return "\n".join(
            [
                f"{current_label} 广告投放周报摘要",
                "",
                f"本周期收入 {money(current_metrics['revenue'])}，订单量 {num(current_metrics['orders'])}，下单转化率 {pct(current_metrics['order_rate'])}，CVR {pct(current_metrics['cvr'])}，CPA {money(current_metrics['cpa'], digits=2)}，ROI {ratio(current_metrics['roi'])}。",
                f"GMV 贡献最高的渠道是 {top_revenue['channel']}，贡献占比 {pct(top_revenue['this_revenue_share'])}。",
                f"广告消耗占比最高的渠道是 {top_cost['channel']}，占比 {pct(top_cost['this_cost_share'])}。",
                "当前选择周期没有上一周期可对比，因此本报告先输出单周期经营概览。",
                "建议选择后续自然周查看环比变化和异常归因。",
            ]
        )

    previous_df = df[df["week_label"] == previous_label]
    comparison = compare_periods(previous_df, current_df, previous_label, current_label)
    channels = channel_analysis(pd.concat([previous_df, current_df], ignore_index=True))
    revenue = comparison[comparison["metric"] == "revenue"].iloc[0]
    cost = comparison[comparison["metric"] == "cost"].iloc[0]
    roi = comparison[comparison["metric"] == "roi"].iloc[0]
    cvr = comparison[comparison["metric"] == "cvr"].iloc[0]
    cpa = comparison[comparison["metric"] == "cpa"].iloc[0]
    order_rate = comparison[comparison["metric"] == "order_rate"].iloc[0]
    worst_roi = channels.iloc[0]
    biggest_drag = channels.sort_values("order_rate_change_pp", ascending=True).iloc[0]
    top_revenue = channels.sort_values("this_revenue_share", ascending=False).iloc[0]
    top_cost = channels.sort_values("this_cost_share", ascending=False).iloc[0]

    return "\n".join(
        [
            f"{current_label} 广告投放周报摘要",
            "",
            f"本周期收入 {money(revenue[current_label])}，较 {previous_label} 变化 {pct(revenue['变化率'])}；投放成本 {money(cost[current_label])}，变化 {pct(cost['变化率'])}。",
            f"ROI 为 {ratio(roi[current_label])}，较 {previous_label} 的 {ratio(roi[previous_label])} 变化 {pct(roi['变化率'])}。",
            f"CVR 为 {pct(cvr[current_label])}，较 {previous_label} 的 {pct(cvr[previous_label])} 变化 {pct(cvr['变化率'])}；CPA 为 {money(cpa[current_label], digits=2)}。",
            f"下单转化率为 {pct(order_rate[current_label])}，较 {previous_label} 的 {pct(order_rate[previous_label])} 变化 {pct(order_rate['变化率'])}。",
            f"GMV 贡献最高的渠道是 {top_revenue['channel']}，贡献占比 {pct(top_revenue['this_revenue_share'])}。",
            f"广告消耗占比最高的渠道是 {top_cost['channel']}，占比 {pct(top_cost['this_cost_share'])}。",
            f"渠道侧看，{worst_roi['channel']} ROI 最低，为 {ratio(worst_roi['this_roi'])}；{biggest_drag['channel']} 下单转化率下降最明显，下降 {abs(biggest_drag['order_rate_change_pp']):.2f} 个百分点。",
            "建议下周期优先排查低 ROI 渠道的投放质量和落地页转化，同时保留高 ROI 渠道预算。",
        ]
    )


def secret_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        value = st.secrets.get(name, "")
    except Exception:
        return ""
    return str(value).strip()


def diagnosis_to_markdown(answer: Diagnosis | str) -> str:
    if isinstance(answer, str):
        return answer
    evidence = "\n".join(f"- {item}" for item in answer.evidence)
    suggestion = "\n".join(f"- {item}" for item in answer.suggestion)
    return "\n".join(
        [
            f"### 结论\n{answer.headline}",
            "",
            "### 关键证据",
            evidence,
            "",
            "### 投放动作建议",
            suggestion,
        ]
    )


def context_periods(df: pd.DataFrame, current_label: str | None = None) -> tuple[pd.DataFrame | None, pd.DataFrame, str | None, str]:
    if current_label:
        labels = ordered_week_labels(df)
        if current_label not in labels:
            current_label = labels[-1]
        previous_label = previous_week_label(df, current_label)
        current_df = df[df["week_label"] == current_label]
        previous_df = df[df["week_label"] == previous_label] if previous_label else None
        return previous_df, current_df, previous_label, current_label

    last_week, this_week, last_label, this_label = get_week_pair(df)
    return last_week, this_week, last_label, this_label


def build_chart_evidence_context(df: pd.DataFrame, current_label: str | None = None) -> str:
    previous_df, current_df, previous_label, this_label = context_periods(df, current_label)
    analysis_df = pd.concat([previous_df, current_df], ignore_index=True) if previous_df is not None else current_df
    evidence = []

    trend = aggregate_metrics(analysis_df, ["date"]).sort_values("date")
    if not trend.empty:
        first = trend.iloc[0]
        last = trend.iloc[-1]
        lowest = trend.loc[trend["order_rate"].idxmin()]
        highest = trend.loc[trend["order_rate"].idxmax()]
        evidence.append(
            "【下单转化率趋势图】"
            f"{first['date'].date()} 为 {pct(first['order_rate'])}，{last['date'].date()} 为 {pct(last['order_rate'])}；"
            f"最低点出现在 {lowest['date'].date()}，为 {pct(lowest['order_rate'])}；"
            f"最高点出现在 {highest['date'].date()}，为 {pct(highest['order_rate'])}。"
        )

    current_channel = aggregate_metrics(current_df, ["channel"]).sort_values("roi", ascending=True)
    if not current_channel.empty:
        bottom_roi = "；".join(
            f"{row['channel']} ROI {ratio(row['roi'])}、GMV {money(row['revenue'])}、消耗 {money(row['cost'])}"
            for _, row in current_channel.head(3).iterrows()
        )
        top_roi = "；".join(
            f"{row['channel']} ROI {ratio(row['roi'])}"
            for _, row in current_channel.sort_values("roi", ascending=False).head(3).iterrows()
        )
        evidence.append(f"【渠道 ROI 对比图（{this_label}）】低 ROI 渠道：{bottom_roi}。高 ROI 渠道：{top_roi}。")

    current_cpc = aggregate_metrics(current_df, ["channel"]).sort_values("cpc", ascending=False)
    if not current_cpc.empty:
        high_cpc = "；".join(
            f"{row['channel']} CPC {money(row['cpc'], digits=2)}、点击量 {num(row['clicks'])}、消耗 {money(row['cost'])}"
            for _, row in current_cpc.head(3).iterrows()
        )
        low_cpc = "；".join(
            f"{row['channel']} CPC {money(row['cpc'], digits=2)}"
            for _, row in current_cpc.sort_values("cpc", ascending=True).head(3).iterrows()
        )
        evidence.append(f"【渠道 CPC 对比图（{this_label}）】高 CPC 渠道：{high_cpc}。低 CPC 渠道：{low_cpc}。")

    current_cpa = aggregate_metrics(current_df, ["channel"]).sort_values("cpa", ascending=False)
    if not current_cpa.empty:
        high_cpa = "；".join(
            f"{row['channel']} CPA {money(row['cpa'], digits=2)}、注册量 {num(row['signups'])}、消耗 {money(row['cost'])}"
            for _, row in current_cpa.head(3).iterrows()
        )
        evidence.append(f"【渠道获客成本对比图（{this_label}）】高 CPA 渠道：{high_cpa}。")

    current_cvr = aggregate_metrics(current_df, ["channel"]).sort_values("cvr", ascending=True)
    if not current_cvr.empty:
        low_cvr = "；".join(
            f"{row['channel']} CVR {pct(row['cvr'])}、点击量 {num(row['clicks'])}、订单量 {num(row['orders'])}"
            for _, row in current_cvr.head(3).iterrows()
        )
        evidence.append(f"【渠道 CVR 对比图（{this_label}）】低 CVR 渠道：{low_cvr}。")

    current_revenue_share = aggregate_metrics(current_df, ["channel"]).sort_values("revenue_share", ascending=False)
    if not current_revenue_share.empty:
        top_revenue_share = "；".join(
            f"{row['channel']} GMV贡献占比 {pct(row['revenue_share'])}、GMV {money(row['revenue'])}"
            for _, row in current_revenue_share.head(3).iterrows()
        )
        current_cost_share = aggregate_metrics(current_df, ["channel"]).sort_values("cost_share", ascending=False)
        top_cost_share = "；".join(
            f"{row['channel']} 广告消耗占比 {pct(row['cost_share'])}、消耗 {money(row['cost'])}"
            for _, row in current_cost_share.head(3).iterrows()
        )
        evidence.append(f"【渠道贡献占比图（{this_label}）】GMV贡献：{top_revenue_share}。消耗占比：{top_cost_share}。")

    if previous_df is not None and previous_label is not None:
        comparison = compare_periods(previous_df, current_df, previous_label, this_label)
        metric_bits = []
        for metric in ["revenue", "cost", "orders", "signup_rate", "cvr", "order_rate", "roi", "cpc", "cpa", "cpm", "cost_per_order", "aov"]:
            row = comparison[comparison["metric"] == metric].iloc[0]
            metric_bits.append(
                f"{METRIC_LABELS[metric]} {format_metric_value(metric, row[previous_label])} -> "
                f"{format_metric_value(metric, row[this_label])}，变化 {pct(row['变化率'])}"
            )
        evidence.append(f"【核心指标对比表】{ '；'.join(metric_bits) }。")

        channels = dimension_analysis(analysis_df, "channel").sort_values("order_rate_change_pp", ascending=True)
        channel_bits = []
        for _, row in channels.head(3).iterrows():
            channel_bits.append(
                f"{row['channel']} 下单转化率 {pct(row['last_order_rate'])} -> {pct(row['this_order_rate'])}，"
                f"变化 {row['order_rate_change_pp']:.2f}pp，当前 ROI {ratio(row['this_roi'])}"
            )
        evidence.append(f"【渠道归因拆解表】转化下滑最明显渠道：{ '；'.join(channel_bits) }。")

    weekly = weekly_metrics(df).tail(4)
    if len(weekly) >= 2:
        weekly_bits = []
        for _, row in weekly.iterrows():
            weekly_bits.append(
                f"{row['week_label']} GMV {money(row['revenue'])}、ROI {ratio(row['roi'])}、下单转化率 {pct(row['order_rate'])}"
            )
        evidence.append(f"【多周趋势图】最近 {len(weekly)} 周表现：{ '；'.join(weekly_bits) }。")

    for dimension in [col for col in OPTIONAL_DIMENSIONS if col in current_df.columns]:
        dimension_rows = aggregate_metrics(current_df, [dimension]).sort_values("roi", ascending=True)
        if dimension_rows.empty:
            continue
        bottom = dimension_rows.iloc[0]
        top = dimension_rows.sort_values("roi", ascending=False).iloc[0]
        evidence.append(
            f"【维度透视分析-{DIMENSION_LABELS[dimension]}】"
            f"低 ROI：{bottom[dimension]} ROI {ratio(bottom['roi'])}、GMV {money(bottom['revenue'])}；"
            f"高 ROI：{top[dimension]} ROI {ratio(top['roi'])}、GMV {money(top['revenue'])}。"
        )

    return "\n".join(f"- {item}" for item in evidence)


def build_llm_context(
    df: pd.DataFrame,
    current_label: str | None = None,
    include_full_evidence: bool = True,
) -> str:
    previous_df, current_df, previous_label, this_col = context_periods(df, current_label)
    if previous_df is not None and previous_label is not None:
        comparison = compare_periods(previous_df, current_df, previous_label, this_col)
        last_col = previous_label
        analysis_df = pd.concat([previous_df, current_df], ignore_index=True)
        channels = dimension_analysis(analysis_df, "channel")
    else:
        comparison = None
        last_col = None
        analysis_df = current_df
        channels = pd.DataFrame()
    current_channel = aggregate_metrics(current_df, ["channel"]).sort_values("roi", ascending=True)
    metric_rows = []
    for metric in [
        "impressions",
        "clicks",
        "signups",
        "orders",
        "revenue",
        "cost",
        "ctr",
        "signup_rate",
        "cvr",
        "order_rate",
        "roi",
        "cpc",
        "cpa",
        "cpm",
        "cost_per_order",
        "aov",
    ]:
        if comparison is not None and last_col is not None:
            row = comparison[comparison["metric"] == metric].iloc[0]
            metric_rows.append(
                f"- {METRIC_LABELS[metric]}：{last_col}={format_metric_value(metric, row[last_col])}，"
                f"{this_col}={format_metric_value(metric, row[this_col])}，变化率={pct(row['变化率'])}"
            )
        else:
            row = aggregate_metrics(current_df).iloc[0]
            metric_rows.append(f"- {METRIC_LABELS[metric]}：{this_col}={format_metric_value(metric, row[metric])}")

    channel_rows = []
    if not channels.empty:
        for _, row in channels.sort_values("order_rate_change_pp", ascending=True).head(6).iterrows():
            channel_rows.append(
                f"- {row['channel']}：下单转化率变化 {row['order_rate_change_pp']:.2f}pp，"
                f"当前 ROI {ratio(row['this_roi'])}，当前 GMV {money(row['this_revenue'])}，当前广告消耗 {money(row['this_cost'])}"
            )
    else:
        channel_rows.append("- 当前周期没有上一周期可对比，暂不输出渠道转化变化。")

    roi_rows = []
    for _, row in current_channel.head(6).iterrows():
        roi_rows.append(
            f"- {row['channel']}：ROI {ratio(row['roi'])}，CPC {money(row['cpc'], digits=2)}，GMV {money(row['revenue'])}，广告消耗 {money(row['cost'])}"
        )

    cpa_rows = []
    for _, row in aggregate_metrics(current_df, ["channel"]).sort_values("cpa", ascending=False).head(5).iterrows():
        cpa_rows.append(
            f"- {row['channel']}：CPA {money(row['cpa'], digits=2)}，CVR {pct(row['cvr'])}，注册量 {num(row['signups'])}，消耗 {money(row['cost'])}"
        )

    contribution_rows = []
    for _, row in aggregate_metrics(current_df, ["channel"]).sort_values("revenue_share", ascending=False).head(5).iterrows():
        contribution_rows.append(
            f"- {row['channel']}：GMV贡献占比 {pct(row['revenue_share'])}，广告消耗占比 {pct(row['cost_share'])}，GMV {money(row['revenue'])}"
        )

    cost_share_rows = []
    for _, row in aggregate_metrics(current_df, ["channel"]).sort_values("cost_share", ascending=False).head(5).iterrows():
        cost_share_rows.append(
            f"- {row['channel']}：广告消耗占比 {pct(row['cost_share'])}，GMV贡献占比 {pct(row['revenue_share'])}，广告消耗 {money(row['cost'])}"
        )

    date_min = analysis_df["date"].min().date()
    date_max = analysis_df["date"].max().date()
    dimensions = "、".join([DIMENSION_LABELS[col] for col in DIMENSION_COLUMNS if col in df.columns])
    parts = [
        f"数据范围：{date_min} 至 {date_max}，共 {len(df):,} 行广告投放明细。",
        f"可分析维度：{dimensions}。",
        "",
        "核心指标对比：",
        *metric_rows,
        "",
        "渠道转化变化：",
        *channel_rows,
        "",
        "当前周期渠道 ROI / CPC 排序：",
        *roi_rows,
        "",
        "当前周期渠道 CPA / 贡献占比：",
        *cpa_rows,
        *contribution_rows,
        "",
        "当前周期渠道消耗占比：",
        *cost_share_rows,
    ]
    if include_full_evidence:
        parts.extend(
            [
                "",
                "可用全量指标证据（仅供数值参考，不代表本次问题都会渲染）：",
                build_chart_evidence_context(df, current_label),
            ]
        )
    return "\n".join(parts)


def call_deepseek_chat(
    api_key: str,
    model: str,
    base_url: str,
    messages: list[dict[str, str]],
    max_tokens: int = 1200,
    proxy_url: str = "",
) -> str:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "thinking": {"type": "disabled"},
                "temperature": 0.2,
                "max_tokens": max_tokens,
                "stream": False,
            },
            timeout=60,
            proxies=proxies,
        )
    except requests.exceptions.ProxyError as exc:
        raise RuntimeError("代理连接失败：请确认代理软件已开启，代理地址和端口填写正确。") from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("DeepSeek API 请求超时：请检查网络或稍后重试。") from exc
    except requests.exceptions.ConnectionError as exc:
        message = str(exc)
        if "WinError 10013" in message:
            raise RuntimeError(
                "无法连接 DeepSeek API：Windows 拒绝了 Python/Streamlit 发起的网络连接。"
                "这通常是防火墙、杀毒软件、校园网/公司网络策略或本机代理未配置导致的。"
                "如果你正在使用 Clash/v2rayN 等代理，请在下方填写代理地址，例如 http://127.0.0.1:7890。"
            ) from exc
        raise RuntimeError(f"无法连接 DeepSeek API：{message}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"DeepSeek API 调用失败：HTTP {response.status_code}，{response.text[:300]}")
    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"DeepSeek API 返回格式异常：{payload}") from exc


def answer_question_with_llm(
    question: str,
    df: pd.DataFrame,
    api_key: str,
    model: str,
    base_url: str,
    proxy_url: str = "",
    rag_cards: list | None = None,
    chart_plan: dict | None = None,
) -> str:
    rule_answer = answer_question(question, df)
    rag_cards = rag_cards if rag_cards is not None else retrieve_rag_cards(question)
    rag_context = format_knowledge_cards_for_prompt(rag_cards)
    chart_plan = validate_chart_plan(chart_plan or build_chart_plan(question, infer_question_intent(question), df), df)
    chart_context = chart_plan_summary(chart_plan)
    context = build_llm_context(df, include_full_evidence=False)
    messages = [
        {
            "role": "system",
            "content": (
                "你是 Insight Copilot for Ads，一个面向产品经理、运营和投放同学的电商广告投放复盘助手。"
                "你必须只基于用户提供的数据上下文和规则分析结果回答，不得虚构上线数据、用户规模、真实业务原因或外部事实。"
                "你会收到 RAG 检索到的电商广告分析知识卡；知识卡只提供分析框架和常见假设，不代表当前业务事实。"
                "你还会收到系统内部图表证据提纲；这些提纲只用于帮助你引用真实图表，不要在回答中提及“图表计划”或输出 JSON。"
                "不得把知识卡中的常见假设写成已验证原因，必须结合当前数据证据判断是否可作为待验证方向。"
                "请区分数据事实、可能原因和投放建议；如果问题超出数据范围，要明确说明不能判断。"
                "回答必须显式引用系统内部图表证据提纲中的图表或表格名称，且只能引用提纲里出现的名称，不得引用提纲之外的图表。"
                "不要声称自己生成了图表；真实图表会由系统在回答下方基于当前数据渲染，你只负责引用和解释这些图表。"
                "输出必须短而密，总字数控制在 220-320 字。"
                "每个小节 1-3 条项目符号，图表证据最多 3 条，可能原因 2-3 条，建议动作 2 条，风险提示 1 条。"
                "不要输出一整段长文，使用 Markdown 小标题和项目符号，不要复述数据上下文。"
                "输出结构固定为：一、结论；二、图表证据；三、可能原因；四、建议动作；五、风险提示。"
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    f"用户问题：{question}",
                    "当前筛选数据上下文：",
                    context,
                    "规则层分析结果：",
                    diagnosis_to_markdown(rule_answer),
                    "RAG 检索到的电商广告分析知识：",
                    rag_context,
                    "系统内部图表证据提纲：",
                    chart_context,
                    (
                        "请把以上内容整理成中文业务复盘回答。"
                        "在“图表证据”部分输出 3 条以内证据，每条都要包含：证据来自哪个图表/表格、具体数值、支撑哪个结论。"
                        "本次实际会渲染的图表仅限上述提纲；数据上下文里的指标只能作为数值参考，不能当作页面图表名称。"
                        "所有原因都必须写成“可能原因”，不得写成已被验证的真实原因。"
                    ),
                ]
            ),
        },
    ]
    return call_deepseek_chat(api_key, model, base_url, messages, max_tokens=1200, proxy_url=proxy_url)


def polish_weekly_report_with_llm(
    base_report: str,
    df: pd.DataFrame,
    api_key: str,
    model: str,
    base_url: str,
    proxy_url: str = "",
    current_label: str | None = None,
    rag_cards: list | None = None,
    chart_plan: dict | None = None,
) -> str:
    report_query = f"{current_label or ''} 电商广告投放周报 复盘 老板 运营 投放建议"
    rag_cards = rag_cards if rag_cards is not None else retrieve_rag_cards(report_query, top_k=5)
    rag_context = format_knowledge_cards_for_prompt(rag_cards)
    chart_plan = validate_chart_plan(chart_plan or build_chart_plan(report_query, "weekly", df, current_label), df)
    chart_context = chart_plan_summary(chart_plan)
    messages = [
        {
            "role": "system",
            "content": (
                "你是 Insight Copilot for Ads 的投放周报生成助手。"
                "你的任务不是简单润色，而是基于规则周报和数据上下文，生成一份纯文字版电商广告投放周报。"
                "你会收到 RAG 检索到的周报、诊断和风险边界知识卡；知识卡只提供结构和分析框架，不代表当前业务事实。"
                "你还会收到系统内部图表证据提纲；这些提纲只用于帮助你组织文字，不要在周报正文里提及“图表计划”或输出 JSON。"
                "知识卡中的推荐图表只供系统下方证据板块使用，不要写进周报正文。"
                "必须引用具体指标数值，不得新增数据中没有的上线效果、用户规模、转化提升、真实业务原因。"
                "不要输出任何图表、表格、代码块、图片链接、图表占位符、ASCII 图或 Mermaid。"
                "不要设置“图表证据”小节，也不要写“如下图”“见下方图表”等表述；真实图表会由系统在周报下方单独渲染。"
                "所有归因必须标注为“可能原因”或“待验证假设”。"
                "输出 350-550 字左右，使用 Markdown。"
                "每个小节 1-3 条项目符号，尽量短句，不要写成散文。"
                "输出结构：一、本周总体判断；二、核心指标表现；三、渠道与维度表现；四、异常归因与待验证假设；五、下周动作建议；六、风险提示。"
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    "数据上下文（仅用于提取事实和指标数值，不包含本次实际渲染图表清单）：",
                    build_llm_context(df, current_label, include_full_evidence=False),
                    "规则周报草稿：",
                    base_report,
                    "RAG 检索到的周报与广告分析知识：",
                    rag_context,
                    "系统内部图表证据提纲：",
                    chart_context,
                    (
                        "请生成完整的纯文字周报，不要只改写草稿。"
                        "每个主要结论都要给出对应指标数值支撑，但不要在正文里生成或模拟任何图表/表格。"
                        "周报正文不要引用图表名称；图表证据由系统在正文下方独立渲染。"
                        "控制篇幅，避免大段背景说明。"
                        "表达要像产品经理/运营同学可以直接复制进周会材料的版本。"
                    ),
                ]
            ),
        },
    ]
    return call_deepseek_chat(api_key, model, base_url, messages, max_tokens=1800, proxy_url=proxy_url)


def answer_question(question: str, df: pd.DataFrame) -> Diagnosis | str:
    normalized = question.strip().lower()
    if "周报" in question or "报告" in question:
        return build_weekly_report(df)
    if contains_any(normalized, ["上传", "字段", "映射", "不一样", "格式", "csv", "excel", "xlsx"]) and contains_any(
        normalized,
        ["能", "可以", "分析", "识别", "口径", "字段"],
    ):
        return build_field_compatibility_diagnosis(df)
    if contains_any(normalized, ["不能确定", "无法确定", "不确定", "边界", "限制", "风险", "幻觉", "数据安全", "权限", "脱敏"]):
        return build_boundary_diagnosis(df)
    if contains_any(normalized, ["ctr", "点击率", "点击下降", "点击少", "没人点", "素材疲劳", "创意"]):
        return build_stage_metric_diagnosis(df, "ctr", "CTR", "点击意愿异常")
    if contains_any(normalized, ["注册率", "注册转化", "注册少", "留资", "表单", "落地页"]):
        return build_stage_metric_diagnosis(df, "signup_rate", "注册转化率", "注册承接异常")
    if contains_any(normalized, ["cvr", "点击到订单转化率", "点击后下单", "点击转化", "点击到成交", "点击后成交"]):
        return build_click_conversion_diagnosis(df)
    if contains_any(normalized, ["cpc", "cpm", "cpa", "点击成本", "千次曝光成本", "订单成本", "单订单成本", "获客成本"]):
        return build_cost_efficiency_diagnosis(df, question)
    if contains_any(normalized, ["占比", "贡献", "份额", "结构", "分布", "谁贡献", "贡献最大", "消耗占比", "收入贡献", "订单贡献"]):
        return build_contribution_diagnosis(df, question)
    if "品类" in question or "类目" in question:
        if "product_category" not in df.columns:
            return build_missing_dimension_diagnosis(df, "product_category")
        return build_dimension_drag_diagnosis(df, "product_category")
    if "广告类型" in question or "广告方式" in question:
        if "ad_type" not in df.columns:
            return build_missing_dimension_diagnosis(df, "ad_type")
        return build_dimension_roi_diagnosis(df, "ad_type")
    if "活动类型" in question or "活动" in question:
        if "campaign_type" not in df.columns:
            return build_missing_dimension_diagnosis(df, "campaign_type")
        return build_dimension_best_diagnosis(df, "campaign_type")
    if "老板" in question or "三条" in question or "结论" in question:
        return build_executive_summary(df)
    if "加预算" in question or "预算" in question or "值得" in question:
        return build_budget_diagnosis(df)
    if "浪费" in question:
        return build_roi_diagnosis(df)
    if "成本" in question or "花费" in question or "消耗" in question:
        return build_cost_diagnosis(df)
    if contains_any(normalized, ["订单下降", "订单下滑", "订单变少", "订单减少", "订单量下降", "订单量下滑", "订单量为什么", "支付订单少", "订单少", "出单少", "订单为什么"]):
        return build_revenue_diagnosis(df)
    if "收入" in question or "gmv" in normalized or "营收" in question:
        return build_revenue_diagnosis(df)
    if "roi" in normalized or "ROI" in question or "最差" in question:
        return build_roi_diagnosis(df)
    if "拖累" in question or "贡献" in question or "归因" in question:
        return build_drag_diagnosis(df)
    if contains_any(normalized, ["转化率", "转化", "下单率", "成单", "漏斗", "注册到下单", "承接"]):
        return build_conversion_diagnosis(df)

    return Diagnosis(
        "当前 MVP 还不能完全理解这个问题，我先给你一版综合总览。",
        build_executive_summary(df).evidence,
        ["后续迭代可以继续增强自由文本问题到指标、维度和时间范围的解析能力。"],
    )


def format_comparison_table(comparison: pd.DataFrame) -> pd.DataFrame:
    formatted = comparison.copy()
    week_cols = [col for col in formatted.columns if col not in ["metric", "指标", "变化率"]]
    for col in week_cols:
        formatted[col] = formatted.apply(lambda row: format_metric_value(row["metric"], row[col]), axis=1)
    formatted["变化率"] = formatted["变化率"].apply(lambda value: pct(value))
    return formatted[["指标", *week_cols, "变化率"]]


def format_metric_value(metric: str, value: float) -> str:
    if metric in {"revenue", "cost"}:
        return money(value)
    if metric in MONEY_METRICS:
        return money(value, digits=2)
    if metric in PERCENT_METRICS:
        return pct(value)
    if metric == "roi":
        return ratio(value)
    return num(value)


def format_metric_series(metric: str, series: pd.Series) -> pd.Series:
    if metric in {"revenue", "cost"}:
        return series.apply(money)
    if metric in MONEY_METRICS:
        return series.apply(lambda value: money(value, digits=2))
    if metric in PERCENT_METRICS:
        return series.apply(pct)
    if metric == "roi":
        return series.apply(ratio)
    return series.apply(num)


def render_field_mapping(raw_df: pd.DataFrame, source_name: str) -> pd.DataFrame | None:
    columns = [str(col).strip() for col in raw_df.columns]
    raw_df = raw_df.copy()
    raw_df.columns = columns
    options = ["不映射", *columns]
    required_fields = ["date", "channel", "device", "region", *SUM_COLUMNS]
    optional_fields = ["week_label", *OPTIONAL_DIMENSIONS]

    state_key = confirmed_mapping_key(source_name)
    confirmed_mapping = st.session_state.get(state_key)
    if confirmed_mapping:
        try:
            mapped_df = build_mapped_dataframe(raw_df, confirmed_mapping)
        except Exception as exc:
            del st.session_state[state_key]
            st.sidebar.warning(f"已保存的字段映射失效，请重新确认：{exc}")
        else:
            st.sidebar.success("字段映射已确认")
            with st.sidebar.expander("数据识别结果", expanded=False):
                mapping_rows = [
                    {
                        "标准字段": field,
                        "原始字段": confirmed_mapping.get(field, "不映射"),
                    }
                    for field in [*required_fields, *optional_fields]
                    if confirmed_mapping.get(field) != "不映射"
                ]
                st.dataframe(pd.DataFrame(mapping_rows), width="stretch", hide_index=True)
                st.markdown("**上传文件概览**")
                for item in upload_summary(mapped_df):
                    st.write(f"- {item}")
                for warning in mapped_df.attrs.get("quality_warnings", []):
                    st.warning(warning)

            if st.sidebar.button("重新映射", key=f"remap_{source_name}", width="stretch"):
                del st.session_state[state_key]
                st.rerun()
            return mapped_df

    mapping: dict[str, str] = {}
    with st.sidebar.expander("字段映射确认", expanded=True):
        st.caption("当前仅面向电商广告投放明细表。首次上传需要确认字段含义；确认后这里会自动收起。")
        st.markdown("**上传文件预览**")
        st.dataframe(raw_df.head(5), width="stretch", hide_index=True)

        for field in [*required_fields, *optional_fields]:
            default = find_default_mapping(columns, field)
            default_index = options.index(default) if default in options else 0
            label = f"{field} - {FIELD_GUIDE.get(field, '可选字段')}"
            if field in required_fields:
                label = f"必填：{label}"
            else:
                label = f"可选：{label}"
            mapping[field] = st.selectbox(label, options, index=default_index, key=f"map_{source_name}_{field}")

        missing_required = [field for field in required_fields if mapping.get(field) == "不映射"]
        if missing_required:
            st.info("还需完成必填字段映射：" + "、".join(missing_required))

        confirm_clicked = st.button("确认字段映射", type="primary", key=f"confirm_mapping_{source_name}", width="stretch")
        if not confirm_clicked:
            return None

        if missing_required:
            st.error("请先完成必填字段映射，再点击确认。")
            return None

        try:
            mapped_df = build_mapped_dataframe(raw_df, mapping)
        except Exception as exc:
            st.error(str(exc))
            return None

        st.session_state[state_key] = mapping
        st.rerun()

    return None


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    ensure_upload_history()
    st.sidebar.header("投放数据与筛选")
    uploaded_file = st.sidebar.file_uploader("上传广告投放 CSV / XLSX", type=["csv", "xlsx"])

    if uploaded_file is not None:
        add_upload_to_history(uploaded_file)

    source = "电商广告样例数据"
    history = st.session_state["upload_history"]
    source_options = ["电商广告样例数据", *[f"{item['name']}（上传历史 {idx + 1}）" for idx, item in enumerate(history)]]
    default_source_index = 1 if history else 0
    selected_source = st.sidebar.selectbox("数据源", source_options, index=default_source_index)

    if selected_source != "电商广告样例数据":
        history_index = source_options.index(selected_source) - 1
        item = history[history_index]
        try:
            raw_df = read_table_from_bytes(item["name"], item["bytes"])
            mapped_df = render_field_mapping(raw_df, item["id"])
            if mapped_df is not None:
                df = mapped_df
                source = f"上传投放文件：{item['name']}"
            else:
                st.sidebar.info("字段映射未完成，当前暂时使用电商广告样例数据。")
        except Exception as exc:
            st.sidebar.error(str(exc))
            st.sidebar.info("已回退到电商广告样例数据。")

    st.sidebar.markdown(f"**当前数据源**：{source}")
    st.sidebar.markdown(f"**当前数据行数**：{len(df):,} 行")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    date_range = st.sidebar.date_input("日期范围", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

    channel_options = sorted(df["channel"].dropna().unique().tolist())
    device_options = sorted(df["device"].dropna().unique().tolist())
    region_options = sorted(df["region"].dropna().unique().tolist())

    selected_channels = st.sidebar.multiselect("渠道", channel_options, default=channel_options)
    selected_devices = st.sidebar.multiselect("设备", device_options, default=device_options)
    selected_regions = st.sidebar.multiselect("地区", region_options, default=region_options)

    filtered = df[
        df["channel"].isin(selected_channels)
        & df["device"].isin(selected_devices)
        & df["region"].isin(selected_regions)
    ]

    for optional_dimension in OPTIONAL_DIMENSIONS:
        if optional_dimension in filtered.columns:
            options = sorted(filtered[optional_dimension].dropna().unique().tolist())
            selected = st.sidebar.multiselect(DIMENSION_LABELS[optional_dimension], options, default=options)
            filtered = filtered[filtered[optional_dimension].isin(selected)]

    return filtered


def render_kpis(df: pd.DataFrame) -> None:
    comparison = compare_weeks(df)
    current_label = comparison.columns[-2]
    metrics = aggregate_metrics(get_week_pair(df)[1]).iloc[0]
    kpi_config = [
        ("GMV", money(metrics["revenue"]), comparison.loc[comparison["metric"] == "revenue", "变化率"].iloc[0]),
        ("支付订单量", num(metrics["orders"]), comparison.loc[comparison["metric"] == "orders", "变化率"].iloc[0]),
        ("下单转化率", pct(metrics["order_rate"]), comparison.loc[comparison["metric"] == "order_rate", "变化率"].iloc[0]),
        ("ROI", ratio(metrics["roi"]), comparison.loc[comparison["metric"] == "roi", "变化率"].iloc[0]),
        ("广告消耗", money(metrics["cost"]), comparison.loc[comparison["metric"] == "cost", "变化率"].iloc[0]),
        ("CPC", money(metrics["cpc"], digits=2), comparison.loc[comparison["metric"] == "cpc", "变化率"].iloc[0]),
    ]

    cols = st.columns(len(kpi_config))
    for col, (label, value, change) in zip(cols, kpi_config):
        col.metric(label=f"{label}（{current_label}）", value=value, delta=pct(change))


def render_charts(df: pd.DataFrame) -> None:
    comparison = compare_weeks(df)
    last_week, this_week, last_label, this_label = get_week_pair(df)
    trend = aggregate_metrics(df, ["date"]).sort_values("date")
    channel_roi = aggregate_metrics(this_week, ["channel"]).sort_values("roi", ascending=True)
    channel_order = channel_analysis(df).sort_values("order_rate_change_pp", ascending=True)

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("下单转化率趋势")
        fig = px.line(
            trend,
            x="date",
            y="order_rate",
            markers=True,
            labels={"date": "日期", "order_rate": "下单转化率"},
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(height=320, margin=dict(l=8, r=8, t=20, b=8))
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader(f"渠道 ROI 对比（{this_label}）")
        fig = px.bar(
            channel_roi,
            x="roi",
            y="channel",
            orientation="h",
            text="roi",
            labels={"roi": "ROI", "channel": "渠道"},
            color="roi",
            color_continuous_scale=["#d95f59", "#f2c14e", "#4c956c"],
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(height=320, margin=dict(l=8, r=24, t=20, b=8), coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")

    st.subheader("核心指标：本周 vs 上周")
    display_comparison = comparison[comparison["metric"].isin(CORE_DISPLAY_METRICS)]
    st.dataframe(format_comparison_table(display_comparison), width="stretch", hide_index=True)

    st.subheader("渠道归因拆解")
    display_channel = channel_order[
        ["channel", "last_order_rate", "this_order_rate", "order_rate_change_pp", "this_roi", "this_revenue", "this_cost"]
    ].copy()
    display_channel.columns = ["渠道", f"{last_label} 下单转化率", f"{this_label} 下单转化率", "变化百分点", f"{this_label} ROI", f"{this_label} GMV", f"{this_label} 广告消耗"]
    display_channel[f"{last_label} 下单转化率"] = display_channel[f"{last_label} 下单转化率"].apply(pct)
    display_channel[f"{this_label} 下单转化率"] = display_channel[f"{this_label} 下单转化率"].apply(pct)
    display_channel["变化百分点"] = display_channel["变化百分点"].map(lambda value: f"{value:.2f}pp")
    display_channel[f"{this_label} ROI"] = display_channel[f"{this_label} ROI"].apply(ratio)
    display_channel[f"{this_label} GMV"] = display_channel[f"{this_label} GMV"].apply(money)
    display_channel[f"{this_label} 广告消耗"] = display_channel[f"{this_label} 广告消耗"].apply(money)
    st.dataframe(display_channel, width="stretch", hide_index=True)


def render_weekly_trend(df: pd.DataFrame) -> None:
    st.subheader("多周趋势")
    weekly = weekly_metrics(df)
    metric_label = st.selectbox("趋势指标", list(PIVOT_METRICS.keys()), index=0, key="weekly_trend_metric")
    metric = PIVOT_METRICS[metric_label]

    fig = px.line(
        weekly,
        x="week_label",
        y=metric,
        markers=True,
        labels={"week_label": "自然周", metric: metric_label},
    )
    if metric in PERCENT_METRICS:
        fig.update_yaxes(tickformat=".0%")
    elif metric in {"revenue", "cost", "orders", "impressions", "clicks", "signups"}:
        fig.update_yaxes(tickformat=",.0f")
    elif metric in MONEY_METRICS:
        fig.update_yaxes(tickformat=",.2f")
    fig.update_layout(height=300, margin=dict(l=8, r=8, t=20, b=8))
    st.plotly_chart(fig, width="stretch")


def render_pivot_analysis(df: pd.DataFrame) -> None:
    st.subheader("维度透视分析")
    available_dimensions = [col for col in DIMENSION_COLUMNS if col in df.columns]
    left, right = st.columns([1, 1])
    with left:
        dimension = st.selectbox("分析维度", available_dimensions, format_func=lambda value: DIMENSION_LABELS.get(value, value))
    with right:
        metric_label = st.selectbox("分析指标", list(PIVOT_METRICS.keys()), index=0, key="pivot_metric")
    metric = PIVOT_METRICS[metric_label]

    by_week_dimension = aggregate_metrics(df, ["week_label", dimension])
    order_map = {label: idx for idx, label in enumerate(ordered_week_labels(df))}
    by_week_dimension["week_order"] = by_week_dimension["week_label"].map(order_map)
    by_week_dimension = by_week_dimension.sort_values(["week_order", metric], ascending=[True, False])
    pivot = by_week_dimension.pivot(index=dimension, columns="week_label", values=metric)
    pivot = pivot[[label for label in ordered_week_labels(df) if label in pivot.columns]]
    formatted = pivot.copy()
    for col in formatted.columns:
        formatted[col] = format_metric_series(metric, formatted[col])
    formatted = formatted.reset_index().rename(columns={dimension: DIMENSION_LABELS.get(dimension, dimension)})
    st.dataframe(formatted, width="stretch", hide_index=True)

    latest_label = ordered_week_labels(df)[-1]
    latest = by_week_dimension[by_week_dimension["week_label"] == latest_label].sort_values(metric, ascending=True)
    fig = px.bar(
        latest,
        x=metric,
        y=dimension,
        orientation="h",
        text=metric,
        labels={metric: metric_label, dimension: formatted.columns[0]},
        color=metric,
        color_continuous_scale=["#d95f59", "#f2c14e", "#4c956c"],
    )
    if metric in PERCENT_METRICS:
        fig.update_traces(texttemplate="%{text:.2%}", textposition="outside")
        fig.update_xaxes(tickformat=".0%")
    elif metric in {"revenue", "cost", "orders", "impressions", "clicks", "signups"}:
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_xaxes(tickformat=",.0f")
    elif metric in MONEY_METRICS:
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_xaxes(tickformat=",.2f")
    else:
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=300, margin=dict(l=8, r=24, t=20, b=8), coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")


INTENT_LABELS = {
    "weekly": "周报 / 综合复盘",
    "executive": "管理层摘要",
    "dimension_product_category": "商品品类分析",
    "dimension_ad_type": "广告类型分析",
    "dimension_campaign_type": "活动类型分析",
    "budget": "预算分配 / 加投判断",
    "cost": "广告消耗 / 成本异常",
    "cost_efficiency": "成本效率 / CPC 异常",
    "click_conversion": "CVR / 点击到订单转化",
    "contribution": "渠道贡献 / 占比分析",
    "revenue": "GMV / 收入变化",
    "roi": "ROI / 投产效率",
    "drag": "拖累归因",
    "click_quality": "点击质量 / CTR 异常",
    "signup_quality": "注册承接异常",
    "conversion": "转化率下降归因",
    "boundary": "AI 边界 / 数据限制",
    "field_mapping": "字段映射 / 口径确认",
}


def contains_any(text: str, words: Iterable[str]) -> bool:
    normalized = text.lower()
    return any(word.lower() in normalized for word in words)


def infer_question_intent(question: str) -> str:
    normalized = question.strip().lower()
    if contains_any(normalized, ["周报", "报告", "周总结", "复盘稿", "业务周会", "本周总结"]):
        return "weekly"
    if contains_any(normalized, ["老板", "三条", "结论", "汇报", "管理层", "一句话", "整体表现", "投放效果怎么样"]):
        return "executive"
    if contains_any(normalized, ["上传", "字段", "映射", "不一样", "格式", "csv", "excel", "xlsx"]) and contains_any(
        normalized,
        ["能", "可以", "分析", "识别", "口径", "字段"],
    ):
        return "field_mapping"
    if contains_any(normalized, ["不能确定", "无法确定", "不确定", "边界", "限制", "风险", "幻觉", "数据安全", "权限", "脱敏"]):
        return "boundary"
    if contains_any(normalized, ["品类", "类目", "商品线", "产品线", "sku"]):
        return "dimension_product_category"
    if contains_any(normalized, ["广告类型", "广告方式", "投放方式", "广告形式", "素材类型"]):
        return "dimension_ad_type"
    if contains_any(normalized, ["活动类型", "营销活动", "活动", "促销", "会员日", "新品"]):
        return "dimension_campaign_type"
    if contains_any(normalized, ["ctr", "点击率", "点击下降", "点击少", "没人点", "素材疲劳", "创意"]):
        return "click_quality"
    if contains_any(normalized, ["注册率", "注册转化", "注册少", "留资", "表单", "落地页"]):
        return "signup_quality"
    if contains_any(normalized, ["cvr", "点击到订单转化率", "点击后下单", "点击转化", "点击到成交", "点击后成交"]):
        return "click_conversion"
    if contains_any(normalized, ["加预算", "预算", "值得", "加投", "放量", "扩量", "砍预算", "缩预算", "保留预算", "优先投", "投哪个"]):
        return "budget"
    if contains_any(normalized, ["cpc", "cpm", "cpa", "点击成本", "千次曝光成本", "订单成本", "单订单成本", "获客成本"]):
        return "cost_efficiency"
    if contains_any(normalized, ["占比", "贡献", "份额", "结构", "分布", "谁贡献", "贡献最大", "消耗占比", "收入贡献", "订单贡献"]):
        return "contribution"
    if contains_any(normalized, ["roi", "投产", "投产比", "roas", "回报", "回本", "不赚钱", "亏", "低效", "浪费", "不划算", "最差", "烧钱不赚钱"]):
        return "roi"
    if contains_any(normalized, ["成本", "花费", "消耗", "烧钱", "花钱", "变贵", "投放成本"]):
        return "cost"
    if contains_any(
        normalized,
        ["收入", "gmv", "营收", "销售额", "成交额", "成交金额", "卖不动", "订单少", "订单下降", "订单下滑", "订单变少", "订单减少", "订单量下降", "订单量下滑", "订单量为什么", "支付订单少", "订单为什么", "出单", "成交", "销售"],
    ):
        return "revenue"
    if contains_any(normalized, ["拖累", "归因", "拖后腿", "拉胯", "锅", "谁导致", "主要原因", "原因是什么", "问题在哪"]):
        return "drag"
    if contains_any(normalized, ["转化率", "转化", "下单率", "成单", "漏斗", "注册到下单", "承接"]):
        return "conversion"
    return "weekly"


def rag_extra_terms_for_intent(intent: str) -> list[str]:
    mapping = {
        "weekly": ["周报", "报告", "复盘", "老板", "运营", "风险边界", "周报模板", "KB-REPORT-001", "KB-CHART-006", "KB-RISK-002", "KB-REPORT-005"],
        "executive": ["老板", "三条结论", "管理层摘要", "核心指标", "风险边界", "KB-REPORT-002", "KB-RISK-001", "KB-RISK-005", "KB-CHART-006"],
        "field_mapping": ["上传", "字段映射", "口径确认", "字段不一致", "CSV", "XLSX", "KB-RISK-004", "KB-RISK-003", "KB-METRIC-004"],
        "boundary": ["不能确定", "边界", "限制", "幻觉控制", "数据安全", "权限", "脱敏", "KB-RISK-001", "KB-RISK-003", "KB-RISK-004"],
        "dimension_product_category": ["品类", "类目", "维度拖累", "转化率下降", "维度透视", "KB-CONV-003", "KB-CHART-001", "KB-METRIC-004"],
        "dimension_ad_type": ["广告类型", "广告方式", "维度 ROI", "投放方式", "图表选择", "KB-CONV-003", "KB-CHART-002", "KB-METRIC-007"],
        "dimension_campaign_type": ["活动类型", "营销活动", "维度表现", "图表选择", "KB-CONV-003", "KB-CHART-002", "KB-METRIC-007"],
        "budget": ["预算分配", "加预算", "成本收益矩阵", "ROI", "高消耗低 ROI", "KB-ROI-002", "KB-ROI-003", "KB-CHART-005", "KB-METRIC-007"],
        "cost": ["广告消耗", "成本上涨", "渠道消耗", "成本收益矩阵", "ROI", "KB-COST-001", "KB-CHART-003", "KB-METRIC-006"],
        "cost_efficiency": ["CPC", "CPM", "CPA", "点击成本", "获客成本", "单订单成本", "成本效率", "成本上涨"],
        "click_conversion": ["CVR", "点击到订单转化率", "点击后下单", "点击转化", "订单转化率", "KB-METRIC-013", "KB-CONV-005", "KB-CHART-010"],
        "contribution": ["贡献占比", "GMV贡献", "消耗占比", "订单贡献", "结构", "份额"],
        "revenue": ["GMV", "收入下降", "订单量", "客单价", "渠道 GMV", "KB-REV-001", "KB-CHART-004", "KB-METRIC-005"],
        "roi": ["ROI", "ROAS", "投产效率", "烧钱不赚钱", "成本收益矩阵", "KB-ROI-001", "KB-ROI-002", "KB-ROI-004", "KB-CONV-001", "KB-CHART-002", "KB-METRIC-007"],
        "drag": ["拖累归因", "渠道拖累", "转化率下降", "下单转化率变化", "KB-CONV-002", "KB-CONV-003", "KB-CHART-001"],
        "click_quality": ["CTR", "点击意愿", "点击率下降", "素材疲劳", "曝光点击漏斗", "KB-STAGE-001", "KB-CHART-007", "KB-METRIC-002"],
        "signup_quality": ["注册转化率", "注册承接", "落地页", "表单门槛", "点击注册漏斗", "KB-STAGE-002", "KB-CHART-008", "KB-METRIC-003"],
        "conversion": ["转化率下降", "下单转化率", "漏斗", "渠道转化变化", "归因", "KB-CONV-001", "KB-CHART-001", "KB-METRIC-004"],
    }
    return mapping.get(intent, [])


def retrieve_rag_cards(question: str, top_k: int = 6) -> list:
    intent = infer_question_intent(question)
    extra_terms = [INTENT_LABELS.get(intent, intent), *rag_extra_terms_for_intent(intent)]
    if intent == "cost_efficiency":
        metric, metric_label = cost_efficiency_metric_from_question(question)
        metric_card_ids = {
            "cpc": "KB-METRIC-009",
            "cpm": "KB-METRIC-010",
            "cpa": "KB-METRIC-012",
            "cost_per_order": "KB-METRIC-011",
        }
        extra_terms.extend([metric, metric_label, metric_card_ids[metric], "KB-COST-004", "KB-CHART-009"])
    elif intent == "click_conversion":
        extra_terms.extend(["cvr", "点击到订单转化率", "KB-METRIC-013", "KB-CONV-005", "KB-CHART-010"])
    elif intent == "contribution":
        metric, metric_label = contribution_metric_from_question(question)
        metric_card_ids = {
            "revenue_share": "KB-METRIC-014",
            "cost_share": "KB-METRIC-015",
            "orders_share": "KB-METRIC-016",
            "click_share": "KB-METRIC-017",
            "signups_share": "KB-METRIC-018",
            "impressions_share": "KB-METRIC-019",
        }
        extra_terms.extend([metric, metric_label, metric_card_ids[metric], "KB-SHARE-001", "KB-CHART-011"])
    return retrieve_relevant_knowledge(question, top_k=top_k, extra_terms=extra_terms)


def render_rag_cards(cards: list, title: str = "RAG 知识增强") -> None:
    with st.expander(title, expanded=False):
        st.caption("系统会先检索电商广告分析知识卡，再把相关卡片与当前数据证据一起交给 LLM。当前检索会优先保留关键显式卡片，并尽量减少无关重复。")
        if not cards:
            st.info("本次没有检索到相关知识卡，将仅使用规则层指标和图表证据。")
            return
        st.dataframe(pd.DataFrame(knowledge_card_summary(cards)), width="stretch", hide_index=True)


def evidence_metric_for_intent(intent: str) -> tuple[str, str]:
    if intent == "click_quality":
        return "ctr", "CTR"
    if intent == "signup_quality":
        return "signup_rate", "注册转化率"
    if intent == "click_conversion":
        return "cvr", "CVR / 点击到订单转化率"
    if intent == "cost_efficiency":
        return "cpc", "CPC"
    if intent == "contribution":
        return "revenue_share", "GMV贡献占比"
    if intent == "cost":
        return "cost", "广告消耗"
    if intent == "revenue":
        return "revenue", "GMV"
    if intent in {"roi", "budget"}:
        return "roi", "ROI"
    return "order_rate", "下单转化率"


def evidence_dimension_for_intent(intent: str) -> str | None:
    if intent == "dimension_product_category":
        return "product_category"
    if intent == "dimension_ad_type":
        return "ad_type"
    if intent == "dimension_campaign_type":
        return "campaign_type"
    return None


def format_plotly_axis(fig, metric: str, axis: str) -> None:
    if metric in PERCENT_METRICS:
        getattr(fig, f"update_{axis}axes")(tickformat=".0%")
    elif metric in {"revenue", "cost", "orders", "impressions", "clicks", "signups"}:
        getattr(fig, f"update_{axis}axes")(tickformat=",.0f")
    elif metric in MONEY_METRICS:
        getattr(fig, f"update_{axis}axes")(tickformat=",.2f")


def metric_text_template(metric: str) -> str:
    if metric in PERCENT_METRICS:
        return "%{text:.2%}"
    if metric == "roi":
        return "%{text:.2f}"
    if metric in {"revenue", "cost", "orders", "impressions", "clicks", "signups"}:
        return "%{text:,.0f}"
    if metric in MONEY_METRICS:
        return "%{text:.2f}"
    return "%{text:,.0f}"


def render_metric_trend_evidence(df: pd.DataFrame, metric: str, metric_label: str, key_suffix: str) -> None:
    trend = aggregate_metrics(df, ["date"]).sort_values("date")
    fig = px.line(
        trend,
        x="date",
        y=metric,
        markers=True,
        labels={"date": "日期", metric: metric_label},
    )
    format_plotly_axis(fig, metric, "y")
    fig.update_layout(height=300, margin=dict(l=8, r=8, t=12, b=8))
    st.plotly_chart(fig, width="stretch", key=f"evidence_metric_trend_{metric}_{key_suffix}")


def render_weekly_metric_evidence(df: pd.DataFrame, metric: str, metric_label: str, key_suffix: str) -> None:
    weekly = weekly_metrics(df).tail(4)
    fig = px.line(
        weekly,
        x="week_label",
        y=metric,
        markers=True,
        labels={"week_label": "自然周", metric: metric_label},
    )
    format_plotly_axis(fig, metric, "y")
    fig.update_layout(height=300, margin=dict(l=8, r=8, t=12, b=8))
    st.plotly_chart(fig, width="stretch", key=f"evidence_weekly_metric_{metric}_{key_suffix}")


def render_dimension_rank_evidence(
    df: pd.DataFrame,
    dimension: str,
    metric: str,
    metric_label: str,
    key_suffix: str,
    ascending: bool = True,
) -> None:
    ranked = aggregate_metrics(df, [dimension]).sort_values(metric, ascending=ascending)
    fig = px.bar(
        ranked,
        x=metric,
        y=dimension,
        orientation="h",
        text=metric,
        labels={metric: metric_label, dimension: DIMENSION_LABELS.get(dimension, dimension)},
        color=metric,
        color_continuous_scale=["#d95f59", "#f2c14e", "#4c956c"],
    )
    fig.update_traces(texttemplate=metric_text_template(metric), textposition="outside")
    format_plotly_axis(fig, metric, "x")
    fig.update_layout(height=320, margin=dict(l=8, r=24, t=12, b=8), coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch", key=f"evidence_dimension_rank_{dimension}_{metric}_{key_suffix}")

    supporting_columns_by_metric = {
        "cpc": ["clicks", "cost", "ctr", "roi"],
        "cpa": ["signups", "cost", "cvr", "roi"],
        "cpm": ["impressions", "cost", "ctr", "roi"],
        "cost_per_order": ["orders", "cost", "order_rate", "roi"],
        "ctr": ["impressions", "clicks", "cpc", "roi"],
        "signup_rate": ["clicks", "signups", "cpc", "roi"],
        "cvr": ["clicks", "orders", "signup_rate", "roi"],
        "order_rate": ["signups", "orders", "cost_per_order", "roi"],
        "roi": ["revenue", "cost", "orders", "order_rate", "cpc"],
        "revenue": ["orders", "aov", "cost", "roi"],
        "cost": ["revenue", "roi", "cpc", "cost_per_order"],
        "revenue_share": ["revenue", "cost", "orders", "roi"],
        "cost_share": ["cost", "revenue", "orders", "roi"],
        "orders_share": ["orders", "revenue", "cost", "roi"],
        "click_share": ["clicks", "revenue", "cost", "roi"],
        "signups_share": ["signups", "revenue", "cost", "roi"],
        "impressions_share": ["impressions", "revenue", "cost", "roi"],
    }
    table_metrics = [metric, *supporting_columns_by_metric.get(metric, ["revenue", "cost", "orders", "order_rate", "roi", "cpc"])]
    table_metrics = [col for index, col in enumerate(table_metrics) if col in ranked.columns and col not in table_metrics[:index]]
    display = ranked[[dimension, *table_metrics]].copy()
    display = display.rename(columns={dimension: DIMENSION_LABELS.get(dimension, dimension), **METRIC_LABELS})
    for col in table_metrics:
        display[METRIC_LABELS[col]] = ranked[col].apply(lambda value, metric=col: format_metric_value(metric, value))
    st.dataframe(display, width="stretch", hide_index=True)


def render_drag_evidence(
    analysis_df: pd.DataFrame,
    dimension: str,
    previous_label: str | None,
    this_label: str,
    key_suffix: str,
) -> None:
    if previous_label is None:
        st.info("当前周期没有可对比的上一周期，暂不展示归因拆解。")
        return

    drag = dimension_analysis(analysis_df, dimension).sort_values("order_rate_change_pp", ascending=True)
    chart_df = drag.rename(columns={"order_rate_change_pp": "下单转化率变化pp"})
    fig = px.bar(
        chart_df,
        x="下单转化率变化pp",
        y=dimension,
        orientation="h",
        text="下单转化率变化pp",
        labels={"下单转化率变化pp": "下单转化率变化（百分点）", dimension: DIMENSION_LABELS.get(dimension, dimension)},
        color="下单转化率变化pp",
        color_continuous_scale=["#d95f59", "#f2c14e", "#4c956c"],
    )
    fig.update_traces(texttemplate="%{text:.2f}pp", textposition="outside")
    fig.update_layout(height=320, margin=dict(l=8, r=24, t=12, b=8), coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch", key=f"evidence_drag_{dimension}_{key_suffix}")

    display = drag[
        [dimension, "last_order_rate", "this_order_rate", "order_rate_change_pp", "this_roi", "this_revenue", "this_cost"]
    ].copy()
    display.columns = [
        DIMENSION_LABELS.get(dimension, dimension),
        f"{previous_label} 下单转化率",
        f"{this_label} 下单转化率",
        "变化百分点",
        f"{this_label} ROI",
        f"{this_label} GMV",
        f"{this_label} 广告消耗",
    ]
    display[f"{previous_label} 下单转化率"] = display[f"{previous_label} 下单转化率"].apply(pct)
    display[f"{this_label} 下单转化率"] = display[f"{this_label} 下单转化率"].apply(pct)
    display["变化百分点"] = display["变化百分点"].map(lambda value: f"{value:.2f}pp")
    display[f"{this_label} ROI"] = display[f"{this_label} ROI"].apply(ratio)
    display[f"{this_label} GMV"] = display[f"{this_label} GMV"].apply(money)
    display[f"{this_label} 广告消耗"] = display[f"{this_label} 广告消耗"].apply(money)
    st.dataframe(display, width="stretch", hide_index=True)


def render_budget_matrix_evidence(current_df: pd.DataFrame, key_suffix: str) -> None:
    channel = aggregate_metrics(current_df, ["channel"]).sort_values("roi", ascending=False)
    fig = px.scatter(
        channel,
        x="cost",
        y="roi",
        size="revenue",
        color="channel",
        text="channel",
        labels={"cost": "广告消耗", "roi": "ROI", "revenue": "GMV", "channel": "渠道"},
    )
    fig.update_traces(textposition="top center")
    fig.update_xaxes(tickformat=",.0f")
    fig.update_layout(height=340, margin=dict(l=8, r=16, t=12, b=8))
    st.plotly_chart(fig, width="stretch", key=f"evidence_budget_matrix_{key_suffix}")

    display = channel[["channel", "roi", "cpc", "cpa", "cvr", "revenue", "cost", "orders", "order_rate"]].copy()
    display.columns = ["渠道", "ROI", "CPC", "CPA", "CVR", "GMV", "广告消耗", "支付订单量", "下单转化率"]
    display["ROI"] = display["ROI"].apply(ratio)
    display["CPC"] = display["CPC"].apply(lambda value: money(value, digits=2))
    display["CPA"] = display["CPA"].apply(lambda value: money(value, digits=2))
    display["CVR"] = display["CVR"].apply(pct)
    display["GMV"] = display["GMV"].apply(money)
    display["广告消耗"] = display["广告消耗"].apply(money)
    display["支付订单量"] = display["支付订单量"].apply(num)
    display["下单转化率"] = display["下单转化率"].apply(pct)
    st.dataframe(display, width="stretch", hide_index=True)


def render_core_metric_evidence(
    previous_df: pd.DataFrame | None,
    current_df: pd.DataFrame,
    previous_label: str | None,
    this_label: str,
) -> None:
    if previous_df is not None and not previous_df.empty:
        comparison = compare_periods(previous_df, current_df, previous_label or "上一周期", this_label)
        display_comparison = comparison[
            comparison["metric"].isin(CORE_DISPLAY_METRICS)
        ]
        st.dataframe(format_comparison_table(display_comparison), width="stretch", hide_index=True)
        return

    metrics = aggregate_metrics(current_df).iloc[0]
    metric_rows = [
        {"指标": METRIC_LABELS[metric], this_label: format_metric_value(metric, metrics[metric])}
        for metric in CORE_DISPLAY_METRICS
    ]
    st.dataframe(pd.DataFrame(metric_rows), width="stretch", hide_index=True)


def render_chart_spec(
    spec: dict,
    df: pd.DataFrame,
    previous_df: pd.DataFrame | None,
    current_df: pd.DataFrame,
    analysis_df: pd.DataFrame,
    previous_label: str | None,
    this_label: str,
    key_suffix: str,
) -> None:
    renderer = spec.get("renderer")
    title = str(spec.get("title", "")).strip()
    if title:
        st.caption(title)

    if renderer == "metric_trend":
        metric = str(spec.get("metric", "order_rate"))
        metric_label = str(spec.get("metric_label", METRIC_LABELS.get(metric, metric)))
        render_metric_trend_evidence(analysis_df, metric, metric_label, key_suffix)
    elif renderer == "weekly_metric":
        metric = str(spec.get("metric", "order_rate"))
        metric_label = str(spec.get("metric_label", METRIC_LABELS.get(metric, metric)))
        render_weekly_metric_evidence(df, metric, metric_label, key_suffix)
    elif renderer == "dimension_rank":
        dimension = str(spec.get("dimension", "channel"))
        metric = str(spec.get("metric", "roi"))
        metric_label = str(spec.get("metric_label", METRIC_LABELS.get(metric, metric)))
        ascending = bool(spec.get("ascending", True))
        render_dimension_rank_evidence(current_df, dimension, metric, metric_label, key_suffix, ascending=ascending)
    elif renderer == "drag":
        dimension = str(spec.get("dimension", "channel"))
        render_drag_evidence(analysis_df, dimension, previous_label, this_label, key_suffix)
    elif renderer == "budget_matrix":
        render_budget_matrix_evidence(current_df, key_suffix)
    elif renderer == "core_metrics":
        render_core_metric_evidence(previous_df, current_df, previous_label, this_label)
    else:
        st.info("暂不支持的图表配置。")


def render_chart_section(
    section: dict,
    df: pd.DataFrame,
    previous_df: pd.DataFrame | None,
    current_df: pd.DataFrame,
    analysis_df: pd.DataFrame,
    previous_label: str | None,
    this_label: str,
    key_suffix: str,
) -> None:
    note = str(section.get("note", "")).strip()
    if note:
        st.caption(note)

    charts = section.get("charts", [])
    layout = str(section.get("layout", "single")).strip() or "single"
    if layout == "split" and len(charts) > 1:
        columns = st.columns(len(charts))
        for column, spec in zip(columns, charts):
            with column:
                render_chart_spec(spec, df, previous_df, current_df, analysis_df, previous_label, this_label, key_suffix)
        return

    for spec in charts:
        render_chart_spec(spec, df, previous_df, current_df, analysis_df, previous_label, this_label, key_suffix)


def render_evidence_charts(
    df: pd.DataFrame,
    question: str = "",
    current_label: str | None = None,
    chart_plan: dict | None = None,
) -> None:
    intent_hint = infer_question_intent(question) if question else "weekly"
    chart_plan = validate_chart_plan(chart_plan or build_chart_plan(question, intent_hint, df, current_label), df)
    intent = str(chart_plan.get("intent", intent_hint))
    previous_df, current_df, previous_label, this_label = context_periods(df, current_label)
    analysis_df = pd.concat([previous_df, current_df], ignore_index=True) if previous_df is not None else current_df
    key_suffix = f"{intent}_{current_label or 'latest'}"

    st.markdown("**真实图表证据**")
    st.caption("以下图表由当前筛选后的广告投放明细实时计算生成。Copilot 负责选择和解释证据，图表本身不由 LLM 凭空生成。")
    st.caption(f"已识别问题意图：{INTENT_LABELS.get(intent, intent)}")
    sections = chart_plan.get("sections", [])
    if not sections:
        st.info("暂无可展示的图表证据。")
        return

    section_tabs = st.tabs([str(section.get("title", "证据")).strip() or "证据" for section in sections])
    for tab, section in zip(section_tabs, sections):
        with tab:
            render_chart_section(section, df, previous_df, current_df, analysis_df, previous_label, this_label, key_suffix)


def render_answer(answer: Diagnosis | str) -> None:
    st.warning("AI 投放分析提示：以下结论由系统基于当前广告投放数据和固定指标口径计算生成，请结合业务背景理性判断。")
    if isinstance(answer, str):
        st.markdown(answer)
        return

    st.success(answer.headline)
    st.markdown("**关键证据**")
    for item in answer.evidence:
        st.write(f"- {item}")
    st.markdown("**投放动作建议**")
    for item in answer.suggestion:
        st.write(f"- {item}")


LLM_SECTION_RE = re.compile(r"^(?:#{1,3}\s+|[一二三四五六七八九十]+[、．.]\s*)(.+)$")


def split_llm_response_sections(text: str) -> list[tuple[str, str]]:
    lines = text.strip().splitlines()
    if not lines:
        return []

    sections: list[tuple[str, str]] = []
    current_title = "内容"
    current_lines: list[str] = []
    saw_heading = False

    def flush() -> None:
        nonlocal current_lines
        body = "\n".join(current_lines).strip()
        if body or saw_heading:
            sections.append((current_title or "内容", body))
        current_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()
        heading_match = LLM_SECTION_RE.match(line.strip())
        if heading_match:
            flush()
            current_title = heading_match.group(1).strip()
            saw_heading = True
            continue
        current_lines.append(line)

    flush()
    cleaned = [(title or "内容", body) for title, body in sections if title or body]
    return cleaned or [("内容", text.strip())]


def render_llm_response(text: str) -> None:
    sections = split_llm_response_sections(text)
    if len(sections) <= 1:
        with st.container(border=True):
            st.markdown(text)
        return

    for title, body in sections:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            if body:
                st.markdown(body)


def render_copilot(df: pd.DataFrame) -> None:
    st.subheader("投放效果 Copilot")
    preset = st.selectbox("选择一个广告投放复盘问题", QUESTION_OPTIONS)
    custom_question = st.text_input("也可以自己输入问题", placeholder="例如：本周广告投放转化率为什么下降？")
    question = custom_question.strip() or preset
    rag_cards = retrieve_rag_cards(question)
    render_rag_cards(rag_cards, "RAG 知识增强（本次问答会调用）")

    with st.expander("DeepSeek 配置", expanded=False):
        saved_api_key = secret_value("DEEPSEEK_API_KEY")
        if saved_api_key:
            st.success("已从环境变量或 Streamlit secrets 读取 DEEPSEEK_API_KEY。")
            api_key = saved_api_key
        else:
            api_key = st.text_input(
                "DeepSeek API Key（仅本次本地会话使用，不会写入代码）",
                type="password",
                placeholder="sk-...",
            ).strip()
        model = st.text_input("模型名称", value=secret_value("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL)
        base_url = st.text_input("API Base URL", value=secret_value("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL)
        proxy_url = st.text_input(
            "代理地址（可选）",
            value=secret_value("DEEPSEEK_PROXY"),
            placeholder="例如：http://127.0.0.1:7890",
        ).strip()
        st.caption("检测到 API Key 后，点击“生成分析”会自动调用 DeepSeek；未配置或调用失败时自动回退到规则诊断结果。")

    ask_clicked = st.button("生成分析", type="primary", width="stretch")

    if ask_clicked:
        chart_plan = build_chart_plan(question, infer_question_intent(question), df)
        st.markdown("**Copilot 分析结果**")
        if api_key:
            with st.spinner("正在调用 DeepSeek 生成分析..."):
                try:
                    st.warning("AI 结果提示：以下内容由 DeepSeek 基于当前筛选数据和规则层证据生成，请结合业务背景理性判断。")
                    llm_answer = answer_question_with_llm(
                        question,
                        df,
                        api_key,
                        model.strip(),
                        base_url.strip(),
                        proxy_url,
                        rag_cards=rag_cards,
                        chart_plan=chart_plan,
                    )
                    render_llm_response(llm_answer)
                except Exception as exc:
                    st.error(str(exc))
                    st.info("已回退到规则诊断结果。")
                    render_answer(answer_question(question, df))
        else:
            render_answer(answer_question(question, df))
        st.divider()
        render_evidence_charts(df, question=question, chart_plan=chart_plan)


def render_safety_notes() -> None:
    st.subheader("AI 投放分析边界")
    st.write(
        "当前垂直 Copilot 已接入规则指标计算、RAG 知识卡和真实图表证据，DeepSeek 只负责文字表达与复盘组织。"
        "回答不会直接把知识卡中的常见假设说成已验证事实，也不会在正文里伪造图表。"
        "如果涉及跨字段、跨场景或低置信度结论，仍需要人工确认。"
    )
    notes = pd.DataFrame(
        [
            ["错答/幻觉", "结论必须同时参考真实指标、规则分析和 RAG 知识卡，原因只能写成可能原因或待验证假设。"],
            ["图表边界", "图表由系统基于真实数据渲染，LLM 只负责解释，不直接生成伪图表。"],
            ["权限控制", "按角色控制可见字段和可分析范围，上传数据后先做字段映射确认。"],
            ["数据安全", "上传数据本地处理或脱敏后处理，敏感字段不进入 LLM prompt。"],
            ["口径一致", "指标解释统一引用指标字典，避免同名指标多口径。"],
            ["人工确认", "对低置信度、字段冲突或超出样例场景的问题，提示用户确认后再分析。"],
        ],
        columns=["风险", "产品方案"],
    )
    st.dataframe(notes, width="stretch", hide_index=True)


def render_rag_evaluation_notes() -> None:
    st.subheader("RAG 评估机制")
    st.write(
        "当前 RAG v0.2 采用问题意图、关键词和主题去重检索知识卡。评估重点不是追求自动打分，"
        "而是验证知识召回是否相关、区分度是否足够、回答是否更专业、风险边界是否受控。"
    )
    scoring = pd.DataFrame(
        [
            ["意图识别", "自然语言问题是否能映射到转化、ROI、成本、收入、预算、周报等意图。"],
            ["知识召回", "是否召回对应的指标口径、诊断框架、图表规则和风险边界。"],
            ["回答质量", "是否基于真实指标给出清晰结论、业务假设和可执行建议。"],
            ["风险控制", "是否避免虚构真实业务原因、上线效果、用户规模或伪图表。"],
        ],
        columns=["评估维度", "判断标准"],
    )
    st.dataframe(scoring, width="stretch", hide_index=True)

    eval_path = ROOT_DIR / "evaluation" / "rag_eval_cases.csv"
    if eval_path.exists():
        cases = pd.read_csv(eval_path).head(8)
        st.caption("评估用例预览")
        st.dataframe(cases[["case_id", "question", "expected_intent", "expected_cards", "status"]], width="stretch", hide_index=True)
    else:
        st.info("尚未找到 evaluation/rag_eval_cases.csv。")


def render_positioning_header() -> None:
    st.title(PRODUCT_NAME)
    st.caption(f"{PRODUCT_SUBTITLE}｜{PRODUCT_TAGLINE}")
    st.caption(f"当前版本：{PRODUCT_VERSION}")

    st.markdown(
        """
        <div class="positioning-strip">
          <div><strong>核心场景</strong><span>电商广告投放周复盘</span></div>
          <div><strong>分析对象</strong><span>渠道 / 品类 / 广告类型 / 活动类型</span></div>
          <div><strong>关键指标</strong><span>曝光、点击、注册、订单、GMV、广告消耗、ROI、CPC、CPA、CVR、贡献占比</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def main() -> None:
    st.set_page_config(page_title=PRODUCT_NAME, page_icon=None, layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; }
        h1, h2, h3 { letter-spacing: 0; }
        div[data-testid="stMetric"] {
            border: 1px solid #e6e8eb;
            border-radius: 8px;
            padding: 12px 14px;
            background: #ffffff;
        }
        .positioning-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 8px 0 14px 0;
        }
        .positioning-strip div {
            border: 1px solid #e6e8eb;
            border-radius: 8px;
            padding: 10px 12px;
            background: #f8fafc;
        }
        .positioning-strip strong {
            display: block;
            color: #1f4d78;
            font-size: 0.86rem;
            margin-bottom: 4px;
        }
        .positioning-strip span {
            color: #20242a;
            font-size: 0.95rem;
        }
        @media (max-width: 780px) {
            .positioning-strip {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_positioning_header()

    try:
        base_df = load_sample_data()
    except Exception as exc:
        st.error(f"电商广告样例数据读取失败：{exc}")
        st.stop()

    df = render_sidebar(base_df)
    if df.empty:
        st.warning("当前筛选条件下没有数据，请调整左侧筛选项。")
        st.stop()

    tab_dashboard, tab_copilot, tab_report, tab_data = st.tabs(["投放看板", "投放 Copilot", "投放周报", "数据口径"])

    with tab_dashboard:
        render_kpis(df)
        render_charts(df)
        render_weekly_trend(df)
        render_pivot_analysis(df)

    with tab_copilot:
        render_copilot(df)

    with tab_report:
        st.subheader("一键生成广告投放周报")
        week_labels = ordered_week_labels(df)
        selected_week = st.selectbox("选择自然周", week_labels, index=len(week_labels) - 1)
        report_state_key = "generated_weekly_report"
        report_week_key = "generated_weekly_report_week"
        report_chart_plan_key = "generated_weekly_report_chart_plan"
        report_week = st.session_state.get(report_week_key, selected_week)
        report_rag_query = f"{report_week} 电商广告投放周报 复盘 老板 运营 投放建议"
        report_rag_cards = retrieve_rag_cards(report_rag_query)
        render_rag_cards(report_rag_cards, "RAG 知识增强（周报生成会调用）")
        with st.expander("DeepSeek 周报生成（可选）", expanded=False):
            saved_api_key = secret_value("DEEPSEEK_API_KEY")
            polish_enabled = st.checkbox("使用 DeepSeek 生成完整周报", value=False)
            if saved_api_key:
                st.success("已从环境变量或 Streamlit secrets 读取 DEEPSEEK_API_KEY。")
                report_api_key = saved_api_key
            else:
                report_api_key = st.text_input(
                    "DeepSeek API Key（仅本次本地会话使用）",
                    type="password",
                    placeholder="sk-...",
                    key="report_deepseek_api_key",
                ).strip()
            report_model = st.text_input("周报生成模型", value=secret_value("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL)
            report_base_url = st.text_input("周报生成 API Base URL", value=secret_value("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL)
            report_proxy_url = st.text_input(
                "周报生成代理地址（可选）",
                value=secret_value("DEEPSEEK_PROXY"),
                placeholder="例如：http://127.0.0.1:7890",
            ).strip()
        report_chart_plan = st.session_state.get(report_chart_plan_key)
        if st.button("生成投放周报", type="primary", width="stretch"):
            base_report = build_weekly_report_for_label(df, selected_week)
            report_chart_plan = build_chart_plan(report_rag_query, "weekly", df, selected_week)
            if polish_enabled and report_api_key:
                with st.spinner("正在调用 DeepSeek 生成完整周报..."):
                    try:
                        st.warning("AI 结果提示：投放周报正文由 DeepSeek 基于规则证据和当前数据上下文生成，请结合业务背景理性判断；真实图表证据见下方独立板块。")
                        report = polish_weekly_report_with_llm(
                            base_report,
                            df,
                            report_api_key,
                            report_model.strip(),
                            report_base_url.strip(),
                            report_proxy_url,
                            current_label=selected_week,
                            rag_cards=report_rag_cards,
                            chart_plan=report_chart_plan,
                        )
                    except Exception as exc:
                        st.error(str(exc))
                        st.info("已回退到规则周报草稿。")
                        report = base_report
            else:
                st.warning("AI 结果提示：投放周报由系统基于当前数据和固定指标口径计算生成，请结合业务背景理性判断。")
                report = base_report
            st.session_state[report_state_key] = report
            st.session_state[report_week_key] = selected_week
            st.session_state[report_chart_plan_key] = report_chart_plan

        if report_state_key in st.session_state:
            report_week = st.session_state.get(report_week_key, selected_week)
            st.markdown(f"**{report_week} 投放周报正文**")
            render_llm_response(st.session_state[report_state_key])
            st.divider()
            if report_chart_plan is None:
                report_chart_plan = build_chart_plan(
                    f"{report_week} 电商广告投放周报 复盘 老板 运营 投放建议",
                    "weekly",
                    df,
                    report_week,
                )
            render_evidence_charts(df, question=report_rag_query, current_label=report_week, chart_plan=report_chart_plan)

    with tab_data:
        st.subheader("广告投放数据口径")
        st.write(f"当前筛选后共有 {len(df):,} 行投放明细，日期范围 {df['date'].min().date()} 至 {df['date'].max().date()}。")
        with st.expander("当前支持的广告投放字段"):
            field_table = pd.DataFrame(
                [{"字段": field, "说明": description} for field, description in FIELD_GUIDE.items()]
            )
            st.dataframe(field_table, width="stretch", hide_index=True)
        st.dataframe(df.sort_values("date").head(200), width="stretch", hide_index=True)
        render_safety_notes()
        render_rag_evaluation_notes()


if __name__ == "__main__":
    main()
