from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base"
GENERIC_KEYWORDS = {
    "渠道",
    "地区",
    "设备",
    "本周",
    "当前",
    "问题",
    "指标",
    "建议",
    "动作",
    "原因",
    "归因",
    "分析",
    "图表",
    "数据",
    "复盘",
    "结论",
    "风险边界",
}
CARD_ID_RE = re.compile(r"\bKB-[A-Z]+-\d{3}\b", flags=re.IGNORECASE)


@dataclass(frozen=True)
class KnowledgeCard:
    card_id: str
    title: str
    source: str
    content: str
    keywords: tuple[str, ...]
    score: int = 0


FIELD_NAMES = ["适用问题", "触发词", "核心指标", "推荐图表", "回答要求", "风险边界"]
FIELD_NAMES += ["核心定义", "分析路径", "常见假设", "推荐结构"]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def split_terms(value: str) -> list[str]:
    parts = re.split(r"[、,，;；/|]", value)
    return [part.strip().strip("。.") for part in parts if part.strip().strip("。.")]


def truncate_text(value: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 1)].rstrip("，,；;、 ") + "…"


def extract_field(content: str, field_name: str) -> str:
    start_pattern = re.compile(rf"^\s*-\s*{re.escape(field_name)}[：:]\s*(.*)$")
    next_field_pattern = re.compile(r"^\s*-\s*[^：:\n]+[：:]\s*")
    collected: list[str] = []
    capturing = False

    for line in content.splitlines():
        if not capturing:
            match = start_pattern.match(line)
            if match:
                capturing = True
                if match.group(1).strip():
                    collected.append(match.group(1).strip())
            continue

        if line.startswith("## "):
            break
        if next_field_pattern.match(line):
            break
        stripped = line.strip()
        if stripped:
            collected.append(stripped)

    return " ".join(collected).strip()


def extract_keywords(title: str, content: str) -> tuple[str, ...]:
    keywords: list[str] = []
    keywords.extend(split_terms(title))
    for field_name in FIELD_NAMES:
        keywords.extend(split_terms(extract_field(content, field_name)))

    cleaned = []
    seen = set()
    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword or keyword in seen or normalize_text(keyword) in GENERIC_KEYWORDS:
            continue
        seen.add(keyword)
        cleaned.append(keyword)
    return tuple(cleaned)


def card_group(card_id: str) -> str:
    parts = card_id.split("-")
    if len(parts) >= 2:
        return "-".join(parts[:2])
    return card_id


def explicit_card_ids(query: str, extra_terms: Iterable[str] = ()) -> list[str]:
    raw_text = " ".join([query, *[str(term) for term in extra_terms]])
    card_ids: list[str] = []
    seen: set[str] = set()
    for match in CARD_ID_RE.findall(raw_text):
        card_id = match.upper()
        if card_id in seen:
            continue
        seen.add(card_id)
        card_ids.append(card_id)
    return card_ids


def split_cards_from_markdown(path: Path) -> list[KnowledgeCard]:
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^##\s+(KB-[^\n]+)$", text, flags=re.MULTILINE))
    cards: list[KnowledgeCard] = []
    for index, heading in enumerate(headings):
        heading_text = heading.group(1).strip()
        next_start = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end() : next_start].strip()
        parts = heading_text.split(maxsplit=1)
        card_id = parts[0]
        title = parts[1] if len(parts) > 1 else card_id
        content = f"## {heading_text}\n\n{body}".strip()
        cards.append(
            KnowledgeCard(
                card_id=card_id,
                title=title,
                source=path.name,
                content=content,
                keywords=extract_keywords(title, content),
            )
        )
    return cards


@lru_cache(maxsize=1)
def load_knowledge_cards() -> tuple[KnowledgeCard, ...]:
    if not KNOWLEDGE_BASE_DIR.exists():
        return tuple()

    cards: list[KnowledgeCard] = []
    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        cards.extend(split_cards_from_markdown(path))
    return tuple(cards)


def score_card(card: KnowledgeCard, query: str, extra_terms: Iterable[str] = ()) -> int:
    normalized_query = normalize_text(query)
    expanded_query = normalized_query + normalize_text(" ".join(extra_terms))
    score = 0

    if normalize_text(card.title) in expanded_query:
        score += 12
    if normalize_text(card.card_id) in expanded_query:
        score += 12

    for keyword in card.keywords:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue
        if normalized_keyword in normalized_query:
            score += 8 if len(normalized_keyword) >= 3 else 4
        elif normalized_keyword in expanded_query:
            score += 4

    # A small title/content fallback helps natural language queries that do not
    # exactly match trigger words but contain important English metrics.
    for token in re.findall(r"[a-zA-Z]{2,}|[0-9]+", query):
        token = token.lower()
        if token in card.title.lower():
            score += 4
        if token and token in card.content.lower():
            score += 1

    return score


def retrieve_relevant_knowledge(query: str, top_k: int = 5, extra_terms: Iterable[str] = ()) -> list[KnowledgeCard]:
    extra_terms = tuple(extra_terms)
    requested_card_ids = explicit_card_ids(query, extra_terms)
    scored_cards = []
    all_cards = load_knowledge_cards()
    for card in all_cards:
        score = score_card(card, query, extra_terms)
        if score > 0:
            scored_cards.append(
                KnowledgeCard(
                    card_id=card.card_id,
                    title=card.title,
                    source=card.source,
                    content=card.content,
                    keywords=card.keywords,
                    score=score,
                )
            )

    scored_cards.sort(key=lambda card: (card.score, card.card_id), reverse=True)

    selected: list[KnowledgeCard] = []
    selected_ids: set[str] = set()

    cards_by_id = {card.card_id.upper(): card for card in all_cards}
    scored_by_id = {card.card_id.upper(): card for card in scored_cards}
    for card_id in requested_card_ids:
        card = scored_by_id.get(card_id)
        if card is None and card_id in cards_by_id:
            raw_card = cards_by_id[card_id]
            card = KnowledgeCard(
                card_id=raw_card.card_id,
                title=raw_card.title,
                source=raw_card.source,
                content=raw_card.content,
                keywords=raw_card.keywords,
                score=max(score_card(raw_card, query, extra_terms), 12),
            )
        if card is None or card.card_id in selected_ids:
            continue
        selected.append(card)
        selected_ids.add(card.card_id)
        if len(selected) >= top_k:
            return selected

    seen_groups: set[str] = {card_group(card.card_id) for card in selected}
    for card in scored_cards:
        if card.card_id in selected_ids:
            continue
        group = card_group(card.card_id)
        if group in seen_groups:
            continue
        selected.append(card)
        selected_ids.add(card.card_id)
        seen_groups.add(group)
        if len(selected) >= top_k:
            return selected

    if len(selected) < top_k:
        for card in scored_cards:
            if card.card_id in selected_ids:
                continue
            selected.append(card)
            selected_ids.add(card.card_id)
            if len(selected) >= top_k:
                break

    return selected


def format_knowledge_cards_for_prompt(cards: Iterable[KnowledgeCard], max_chars_per_card: int = 1200) -> str:
    blocks = []
    for card in cards:
        field_parts: list[str] = []
        for field_name in ["适用问题", "触发词", "核心指标", "核心定义", "推荐图表", "回答要求", "风险边界"]:
            value = extract_field(card.content, field_name)
            if value:
                field_parts.append(f"{field_name}：{truncate_text(value, 120)}")
        for field_name in ["分析路径", "常见假设", "推荐结构"]:
            value = extract_field(card.content, field_name)
            if value:
                field_parts.append(f"{field_name}：{truncate_text(value, 140)}")
                break
        content = "；".join(field_parts)
        if not content:
            content = truncate_text(card.content, max_chars_per_card)
        blocks.append(f"[{card.card_id}] {card.title}（来源：{card.source}，匹配分：{card.score}）\n{content}")
    return "\n\n---\n\n".join(blocks) if blocks else "未检索到相关知识卡。"


def knowledge_card_summary(cards: Iterable[KnowledgeCard]) -> list[dict[str, str | int]]:
    return [
        {
            "知识卡": card.card_id,
            "标题": card.title,
            "主题": card_group(card.card_id),
            "来源": card.source,
            "匹配分": card.score,
        }
        for card in cards
    ]
