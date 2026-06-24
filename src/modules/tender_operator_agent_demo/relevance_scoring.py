from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .supplier_profile import SupplierProfile


class RelevanceStatus(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_RECOMMENDED = "not_recommended"


class RelevanceRecommendation(StrEnum):
    PARTICIPATE = "participate"
    PARTICIPATE_CONDITIONALLY = "participate_conditionally"
    DO_NOT_PARTICIPATE = "do_not_participate"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class RelevanceScoreResult:
    score: float
    status: RelevanceStatus
    recommendation: RelevanceRecommendation
    reasons: list[str]
    breakdown: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "status": self.status.value,
            "recommendation": self.recommendation.value,
            "reasons": self.reasons,
            "breakdown": self.breakdown,
        }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _tokens(text: str) -> set[str]:
    return set(_normalize(text).split())


def _words(text: str) -> list[str]:
    return _normalize(text).split()


def _stem_prefix(w1: str, w2: str, min_prefix: int = 7) -> bool:
    shorter, longer = (w1, w2) if len(w1) <= len(w2) else (w2, w1)
    if len(shorter) >= 3 and shorter in longer:
        return True
    match_len = min(min_prefix, len(w1), len(w2))
    if match_len < 4:
        return w1 == w2
    return w1[:match_len] == w2[:match_len]


def _word_matches(title_tokens: set[str], word: str) -> bool:
    if len(word) < 3:
        return word in title_tokens
    for tw in title_tokens:
        if _stem_prefix(word, tw):
            return True
    return False


def _all_words_match(title_tokens: set[str], phrase: str) -> bool:
    words = [w for w in _words(phrase) if len(w) >= 3]
    if not words:
        return False
    return all(_word_matches(title_tokens, w) for w in words)


def _keyword_matches_title(title_tokens: set[str], keyword: str) -> bool:
    return _all_words_match(title_tokens, keyword)


def _stop_word_matches_title(title_tokens: set[str], stop_word: str) -> bool:
    return _all_words_match(title_tokens, stop_word)


def _keyword_match_score(title: str, keywords: list[str]) -> tuple[float, list[str]]:
    if not keywords:
        return 0.0, []
    tokens = _tokens(title)
    score = 0.0
    reasons: list[str] = []
    matched_keywords = 0
    for kw in keywords:
        if _keyword_matches_title(tokens, kw):
            matched_keywords += 1
            reasons.append(f"Найдено ключевое слово: «{kw}»")
    if matched_keywords > 0:
        ratio = matched_keywords / len(keywords)
        score = min(ratio * 40.0, 40.0)
    else:
        reasons.append("Ключевые слова поставщика не найдены в названии закупки")
    return score, reasons


def _stop_word_penalty(title: str, stop_words: list[str]) -> tuple[float, list[str]]:
    if not stop_words:
        return 0.0, []
    tokens = _tokens(title)
    score = 0.0
    reasons: list[str] = []
    for sw in stop_words:
        if _stop_word_matches_title(tokens, sw):
            score -= 15.0
            reasons.append(f"Стоп-слово в названии: «{sw}»")
    return score, reasons


def _price_range_score(
    price: float | None,
    price_min: float | None,
    price_max: float | None,
) -> tuple[float, list[str]]:
    if price is None:
        return 5.0, ["Цена не указана — частичный балл"]
    reasons: list[str] = []
    if price_min is not None and price_max is not None:
        if price_min <= price <= price_max:
            reasons.append(f"Цена {price:,.0f} ₽ в диапазоне поставщика {price_min:,.0f}–{price_max:,.0f} ₽")
            return 20.0, reasons
        elif price < price_min:
            reasons.append(f"Цена {price:,.0f} ₽ ниже минимальной {price_min:,.0f} ₽")
            return 5.0, reasons
        else:
            reasons.append(f"Цена {price:,.0f} ₽ выше максимальной {price_max:,.0f} ₽")
            return 5.0, reasons
    if price_min is not None:
        if price >= price_min:
            reasons.append(f"Цена {price:,.0f} ₽ не ниже минимальной {price_min:,.0f} ₽")
            return 15.0, reasons
        else:
            reasons.append(f"Цена {price:,.0f} ₽ ниже минимальной {price_min:,.0f} ₽")
            return 5.0, reasons
    if price_max is not None:
        if price <= price_max:
            reasons.append(f"Цена {price:,.0f} ₽ не выше максимальной {price_max:,.0f} ₽")
            return 15.0, reasons
        else:
            reasons.append(f"Цена {price:,.0f} ₽ выше максимальной {price_max:,.0f} ₽")
            return 5.0, reasons
    return 0.0, []


def _deadline_score(submission_deadline: str | None, max_delay_days: int | None) -> tuple[float, list[str]]:
    if not submission_deadline:
        return 5.0, ["Срок подачи не указан — частичный балл"]
    return 10.0, []


def _risk_flag_score(
    title: str,
    customer_name: str | None,
    risk_preferences: object,
) -> tuple[float, list[str]]:
    score = 15.0
    reasons: list[str] = ["Риски не обнаружены"]
    return score, reasons


def score_procurement_card(
    *,
    title: str,
    initial_price: float | None = None,
    customer_name: str | None = None,
    submission_deadline: str | None = None,
    profile: SupplierProfile | None = None,
) -> RelevanceScoreResult:
    if profile is None:
        return RelevanceScoreResult(
            score=0.0,
            status=RelevanceStatus.NOT_RECOMMENDED,
            recommendation=RelevanceRecommendation.MANUAL_REVIEW_REQUIRED,
            reasons=["Профиль поставщика не загружен — скоринг недоступен"],
            breakdown={},
        )

    breakdown: dict[str, float] = {}
    all_reasons: list[str] = []

    kw_score, kw_reasons = _keyword_match_score(title, profile.criteria.keywords)
    breakdown["keywords"] = round(kw_score, 1)
    all_reasons.extend(kw_reasons)

    stop_penalty, stop_reasons = _stop_word_penalty(title, profile.criteria.stop_words)
    breakdown["stop_words"] = round(stop_penalty, 1)
    all_reasons.extend(stop_reasons)

    price_score, price_reasons = _price_range_score(
        initial_price,
        profile.criteria.price_min,
        profile.criteria.price_max,
    )
    breakdown["price_range"] = round(price_score, 1)
    all_reasons.extend(price_reasons)

    deadline_score, deadline_reasons = _deadline_score(submission_deadline, profile.risk_preferences.max_delay_days)
    breakdown["deadline"] = round(deadline_score, 1)
    all_reasons.extend(deadline_reasons)

    risk_score, risk_reasons = _risk_flag_score(title, customer_name, profile.risk_preferences)
    breakdown["risk"] = round(risk_score, 1)
    all_reasons.extend(risk_reasons)

    total = sum(breakdown.values())
    total = max(0.0, min(total, 100.0))

    if total >= 65:
        status = RelevanceStatus.HIGH
        recommendation = RelevanceRecommendation.PARTICIPATE
    elif total >= 40:
        status = RelevanceStatus.MEDIUM
        recommendation = RelevanceRecommendation.PARTICIPATE_CONDITIONALLY
    elif total >= 20:
        status = RelevanceStatus.LOW
        recommendation = RelevanceRecommendation.MANUAL_REVIEW_REQUIRED
    else:
        status = RelevanceStatus.NOT_RECOMMENDED
        recommendation = RelevanceRecommendation.DO_NOT_PARTICIPATE

    return RelevanceScoreResult(
        score=round(total, 1),
        status=status,
        recommendation=recommendation,
        reasons=all_reasons,
        breakdown=breakdown,
    )


def score_procurement_document_text(
    *,
    text: str,
    profile: SupplierProfile | None = None,
) -> dict:
    if profile is None:
        return {
            "document_score": 0.0,
            "document_match_found": False,
            "document_reasons": ["Профиль поставщика не загружен"],
            "document_matched_terms": [],
        }
    tokens = _tokens(text)
    matched_terms: list[str] = []
    for kw in profile.criteria.keywords:
        if _all_words_match(tokens, kw):
            matched_terms.append(kw)
    for cert in profile.certificates:
        if _all_words_match(tokens, cert):
            matched_terms.append(cert)
    score = min(len(matched_terms) * 10.0, 100.0)
    return {
        "document_score": round(score, 1),
        "document_match_found": score >= 20.0,
        "document_reasons": (
            [f"Найдено совпадений: {len(matched_terms)} терминов"] if matched_terms
            else ["Совпадений по тексту документа не найдено"]
        ),
        "document_matched_terms": matched_terms,
    }
