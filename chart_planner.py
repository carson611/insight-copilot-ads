from __future__ import annotations

from typing import Any

import pandas as pd


ALLOWED_RENDERERS = {
    "metric_trend",
    "weekly_metric",
    "dimension_rank",
    "drag",
    "budget_matrix",
    "core_metrics",
}

INTENT_DIMENSION_LABELS = {
    "dimension_product_category": ("product_category", "商品品类"),
    "dimension_ad_type": ("ad_type", "广告类型"),
    "dimension_campaign_type": ("campaign_type", "活动类型"),
}


def _chart(renderer: str, title: str, **kwargs: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {"renderer": renderer, "title": title}
    for key, value in kwargs.items():
        if value is not None:
            spec[key] = value
    return spec


def _section(title: str, layout: str, charts: list[dict[str, Any]], note: str | None = None) -> dict[str, Any]:
    section: dict[str, Any] = {"title": title, "layout": layout, "charts": charts}
    if note:
        section["note"] = note
    return section


def _has_previous_period(df: pd.DataFrame) -> bool:
    return "week_label" in df.columns and df["week_label"].dropna().nunique() >= 2


def _dimension_available(df: pd.DataFrame, dimension: str) -> bool:
    return dimension in df.columns


def _cost_efficiency_metric(question: str) -> tuple[str, str]:
    normalized = question.lower()
    if "cpm" in normalized or "千次曝光" in question:
        return "cpm", "CPM"
    if "cpa" in normalized or "获客成本" in question or "注册成本" in question or "单注册成本" in question:
        return "cpa", "获客成本"
    if "单订单成本" in question or "订单成本" in question or "成交成本" in question:
        return "cost_per_order", "单订单成本"
    return "cpc", "CPC"


def _contribution_metric(question: str) -> tuple[str, str]:
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


def build_chart_plan(question: str, intent: str, df: pd.DataFrame, current_label: str | None = None) -> dict[str, Any]:
    sections: list[dict[str, Any]]

    if intent in {"click_quality", "signup_quality"}:
        metric = "ctr" if intent == "click_quality" else "signup_rate"
        metric_label = "CTR" if metric == "ctr" else "注册转化率"
        sections = [
            _section(
                f"{metric_label}趋势",
                "split",
                [
                    _chart("metric_trend", f"{metric_label}趋势图", source="analysis", metric=metric, metric_label=metric_label),
                    _chart("weekly_metric", f"近四周{metric_label}趋势图", source="current", metric=metric, metric_label=metric_label),
                ],
            ),
            _section(
                f"渠道{metric_label}",
                "single",
                [_chart("dimension_rank", f"渠道{metric_label}排行", source="current", dimension="channel", metric=metric, metric_label=metric_label, ascending=True)],
            ),
            _section(
                "渠道 ROI",
                "single",
                [_chart("dimension_rank", "渠道 ROI 排名", source="current", dimension="channel", metric="roi", metric_label="ROI", ascending=True)],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent == "click_conversion":
        sections = [
            _section(
                "CVR趋势",
                "split",
                [
                    _chart("metric_trend", "CVR趋势图", source="analysis", metric="cvr", metric_label="CVR / 点击到订单转化率"),
                    _chart("weekly_metric", "近四周CVR趋势图", source="current", metric="cvr", metric_label="CVR / 点击到订单转化率"),
                ],
            ),
            _section(
                "渠道CVR",
                "single",
                [_chart("dimension_rank", "渠道CVR排行", source="current", dimension="channel", metric="cvr", metric_label="CVR / 点击到订单转化率", ascending=True)],
            ),
            _section(
                "渠道 ROI",
                "single",
                [_chart("dimension_rank", "渠道 ROI 排名", source="current", dimension="channel", metric="roi", metric_label="ROI", ascending=True)],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent in {"conversion", "drag"}:
        sections = [
            _section(
                "转化趋势",
                "split",
                [
                    _chart("metric_trend", "下单转化率趋势图", source="analysis", metric="order_rate", metric_label="下单转化率"),
                    _chart("weekly_metric", "近四周转化趋势图", source="current", metric="order_rate", metric_label="下单转化率"),
                ],
            ),
            _section(
                "渠道拖累",
                "single",
                [_chart("drag", "渠道拖累图", source="analysis", dimension="channel")],
            ),
            _section(
                "渠道 ROI",
                "single",
                [_chart("dimension_rank", "渠道 ROI 排名", source="current", dimension="channel", metric="roi", metric_label="ROI", ascending=True)],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent in {"roi", "budget"}:
        sections = [
            _section(
                "渠道 ROI",
                "single",
                [_chart("dimension_rank", "渠道 ROI 排名", source="current", dimension="channel", metric="roi", metric_label="ROI", ascending=True)],
            ),
            _section(
                "成本收益矩阵",
                "single",
                [_chart("budget_matrix", "成本收益矩阵", source="current")],
            ),
            _section(
                "趋势证据",
                "single",
                [_chart("weekly_metric", "ROI 多周趋势图", source="current", metric="roi", metric_label="ROI")],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent == "cost_efficiency":
        metric, metric_label = _cost_efficiency_metric(question)
        sections = [
            _section(
                f"{metric_label}趋势",
                "split",
                [
                    _chart("metric_trend", f"{metric_label}趋势图", source="analysis", metric=metric, metric_label=metric_label),
                    _chart("weekly_metric", f"近四周{metric_label}趋势图", source="current", metric=metric, metric_label=metric_label),
                ],
            ),
            _section(
                f"渠道{metric_label}",
                "single",
                [_chart("dimension_rank", f"渠道{metric_label}排行", source="current", dimension="channel", metric=metric, metric_label=metric_label, ascending=False)],
            ),
            _section(
                "成本收益矩阵",
                "single",
                [_chart("budget_matrix", "成本收益矩阵", source="current")],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent == "contribution":
        metric, metric_label = _contribution_metric(question)
        sections = [
            _section(
                f"{metric_label}趋势",
                "split",
                [
                    _chart("weekly_metric", f"近四周{metric_label}趋势图", source="current", metric=metric, metric_label=metric_label),
                    _chart("dimension_rank", f"渠道{metric_label}排行", source="current", dimension="channel", metric=metric, metric_label=metric_label, ascending=False),
                ],
            ),
            _section(
                "成本收益矩阵",
                "single",
                [_chart("budget_matrix", "成本收益矩阵", source="current")],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent in {"cost", "revenue"}:
        metric = "cost" if intent == "cost" else "revenue"
        metric_label = "广告消耗" if metric == "cost" else "GMV"
        sections = [
            _section(
                f"{metric_label}趋势",
                "split",
                [
                    _chart("metric_trend", f"{metric_label}趋势图", source="analysis", metric=metric, metric_label=metric_label),
                    _chart("weekly_metric", f"近四周{metric_label}趋势图", source="current", metric=metric, metric_label=metric_label),
                ],
            ),
            _section(
                f"渠道{metric_label}",
                "single",
                [_chart("dimension_rank", f"渠道{metric_label}排行", source="current", dimension="channel", metric=metric, metric_label=metric_label, ascending=False)],
            ),
            _section(
                "渠道 ROI",
                "single",
                [_chart("dimension_rank", "渠道 ROI 排名", source="current", dimension="channel", metric="roi", metric_label="ROI", ascending=True)],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    elif intent in {"boundary", "field_mapping"}:
        sections = [
            _section(
                "数据口径",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
            _section(
                "渠道结构",
                "split",
                [
                    _chart("dimension_rank", "渠道 GMV 排行", source="current", dimension="channel", metric="revenue", metric_label="GMV", ascending=False),
                    _chart("dimension_rank", "渠道广告消耗排行", source="current", dimension="channel", metric="cost", metric_label="广告消耗", ascending=False),
                ],
            ),
        ]

    elif intent in INTENT_DIMENSION_LABELS:
        dimension, dimension_label = INTENT_DIMENSION_LABELS[intent]
        rank_metric = "roi" if intent in {"dimension_ad_type", "dimension_campaign_type"} else "revenue"
        rank_metric_label = "ROI" if rank_metric == "roi" else "GMV"
        sections = [
            _section(
                f"{dimension_label}拖累",
                "single",
                [_chart("drag", f"{dimension_label}拖累图", source="analysis", dimension=dimension)],
            ),
            _section(
                f"{dimension_label}排行",
                "single",
                [
                    _chart(
                        "dimension_rank",
                        f"{dimension_label}{rank_metric_label}排行",
                        source="current",
                        dimension=dimension,
                        metric=rank_metric,
                        metric_label=rank_metric_label,
                        ascending=rank_metric == "roi",
                    )
                ],
            ),
            _section(
                "趋势证据",
                "single",
                [_chart("weekly_metric", "下单转化率趋势图", source="current", metric="order_rate", metric_label="下单转化率")],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    else:
        sections = [
            _section(
                "综合趋势",
                "split",
                [
                    _chart("weekly_metric", "GMV 多周趋势图", source="current", metric="revenue", metric_label="GMV"),
                    _chart("weekly_metric", "ROI 多周趋势图", source="current", metric="roi", metric_label="ROI"),
                ],
            ),
            _section(
                "渠道拖累",
                "single",
                [_chart("drag", "渠道拖累图", source="analysis", dimension="channel")],
            ),
            _section(
                "渠道 ROI",
                "single",
                [_chart("dimension_rank", "渠道 ROI 排名", source="current", dimension="channel", metric="roi", metric_label="ROI", ascending=True)],
            ),
            _section(
                "核心指标",
                "table",
                [_chart("core_metrics", "核心指标对比表", source="current")],
            ),
        ]

    return {
        "intent": intent,
        "question": question,
        "current_label": current_label,
        "has_previous_period": _has_previous_period(df),
        "sections": sections,
    }


def validate_chart_plan(plan: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    if not isinstance(plan, dict):
        return build_chart_plan("", "weekly", df)

    sections: list[dict[str, Any]] = []
    for section in plan.get("sections", []):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title", "")).strip()
        layout = str(section.get("layout", "single")).strip() or "single"
        charts: list[dict[str, Any]] = []
        for chart in section.get("charts", []):
            if not isinstance(chart, dict):
                continue
            renderer = chart.get("renderer")
            if renderer not in ALLOWED_RENDERERS:
                continue
            cleaned = {"renderer": renderer, "title": str(chart.get("title", "")).strip()}
            for key in ("source", "metric", "metric_label", "dimension", "ascending"):
                if key in chart:
                    cleaned[key] = chart[key]
            if renderer in {"metric_trend", "weekly_metric", "dimension_rank", "drag"}:
                if not cleaned.get("title"):
                    continue
            if renderer in {"dimension_rank", "drag"} and cleaned.get("dimension") not in df.columns:
                continue
            charts.append(cleaned)
        if charts:
            sections.append({"title": title, "layout": layout, "charts": charts})

    if not sections:
        return build_chart_plan(str(plan.get("question", "")), str(plan.get("intent", "weekly")), df, plan.get("current_label"))

    return {
        "intent": plan.get("intent", "weekly"),
        "question": plan.get("question", ""),
        "current_label": plan.get("current_label"),
        "has_previous_period": _has_previous_period(df),
        "sections": sections,
    }


def chart_plan_summary(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in plan.get("sections", []):
        if not isinstance(section, dict):
            continue
        title = section.get("title", "")
        chart_titles = [str(chart.get("title", "")).strip() for chart in section.get("charts", []) if isinstance(chart, dict)]
        chart_titles = [title for title in chart_titles if title]
        if chart_titles:
            lines.append(f"{title}: {'、'.join(chart_titles)}")
    return "\n".join(lines) if lines else "未生成图表计划。"
