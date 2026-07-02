from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db_models import Feedback, FollowUp


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 2)


@dataclass
class ApiMetrics:
    request_count: int = 0
    endpoint_counts: dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    total_response_time_ms: float = 0.0


@dataclass
class RetrievalMetrics:
    retrieval_count: int = 0
    retrieval_latency_ms_total: float = 0.0
    retrieval_failures: int = 0


@dataclass
class RecommendationMetrics:
    recommendation_count: int = 0


@dataclass
class OpportunityMetrics:
    opportunity_generation_count: int = 0


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0


@dataclass
class BackgroundTaskMetrics:
    dispatch_count: int = 0
    dispatch_failures: int = 0


@dataclass
class MetricsSnapshot:
    uptime_seconds: float
    started_at: datetime
    api: dict[str, Any]
    retrieval: dict[str, Any]
    recommendations: dict[str, Any]
    opportunities: dict[str, Any]
    cache: dict[str, Any]
    background_tasks: dict[str, Any]
    dependency_status: dict[str, Any]


class MetricsService:
    def __init__(self) -> None:
        self.started_at = _utcnow()
        self.api = ApiMetrics()
        self.retrieval = RetrievalMetrics()
        self.recommendations = RecommendationMetrics()
        self.opportunities = OpportunityMetrics()
        self.cache = CacheMetrics()
        self.background_tasks = BackgroundTaskMetrics()

    def record_api_request(self, path: str, response_time_ms: float, status_code: int) -> None:
        self.api.request_count += 1
        self.api.endpoint_counts[path] = self.api.endpoint_counts.get(path, 0) + 1
        self.api.total_response_time_ms += response_time_ms
        if status_code >= 400:
            self.api.error_count += 1

    def record_retrieval(self, latency_ms: float, failed: bool = False) -> None:
        self.retrieval.retrieval_count += 1
        self.retrieval.retrieval_latency_ms_total += max(0.0, latency_ms)
        if failed:
            self.retrieval.retrieval_failures += 1

    def record_recommendation_generation(self, count: int) -> None:
        self.recommendations.recommendation_count += max(0, count)

    def record_opportunity_generation(self, count: int) -> None:
        self.opportunities.opportunity_generation_count += max(0, count)

    def record_cache_hit(self) -> None:
        self.cache.hits += 1

    def record_cache_miss(self) -> None:
        self.cache.misses += 1

    def record_task_dispatch(self) -> None:
        self.background_tasks.dispatch_count += 1

    def record_task_dispatch_failure(self) -> None:
        self.background_tasks.dispatch_failures += 1

    def snapshot(self) -> MetricsSnapshot:
        from app.services.health_service import get_dependency_health

        uptime_seconds = round((_utcnow() - self.started_at).total_seconds(), 2)
        avg_response_time_ms = _safe_ratio(
            self.api.total_response_time_ms,
            self.api.request_count,
        )
        avg_retrieval_latency_ms = _safe_ratio(
            self.retrieval.retrieval_latency_ms_total,
            self.retrieval.retrieval_count,
        )
        hit_total = self.cache.hits + self.cache.misses
        return MetricsSnapshot(
            uptime_seconds=uptime_seconds,
            started_at=self.started_at,
            api={
                "request_count": self.api.request_count,
                "endpoint_count": len(self.api.endpoint_counts),
                "endpoint_counts": dict(sorted(self.api.endpoint_counts.items())),
                "error_count": self.api.error_count,
                "average_response_time_ms": avg_response_time_ms,
            },
            retrieval={
                "retrieval_count": self.retrieval.retrieval_count,
                "average_retrieval_latency_ms": avg_retrieval_latency_ms,
                "retrieval_failures": self.retrieval.retrieval_failures,
            },
            recommendations={
                "recommendation_count": self.recommendations.recommendation_count,
            },
            opportunities={
                "opportunity_generation_count": self.opportunities.opportunity_generation_count,
            },
            cache={
                "cache_hits": self.cache.hits,
                "cache_misses": self.cache.misses,
                "hit_ratio": _safe_ratio(self.cache.hits, hit_total),
            },
            background_tasks={
                "dispatch_count": self.background_tasks.dispatch_count,
                "dispatch_failures": self.background_tasks.dispatch_failures,
            },
            dependency_status=get_dependency_health(),
        )


_metrics_service = MetricsService()


def get_metrics_service() -> MetricsService:
    return _metrics_service


def reset_metrics_service() -> None:
    global _metrics_service
    _metrics_service = MetricsService()


def _load_recommendation_feedback_summary(db: Session, user_id: int) -> dict[str, float]:
    entries = (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id, Feedback.target_type == "recommendation")
        .all()
    )
    total = len(entries)
    accepted = sum(1 for entry in entries if (entry.category or entry.action) in {"accepted", "helpful", "like"})
    rejected = sum(
        1
        for entry in entries
        if (entry.category or entry.action) in {"dismissed", "not_helpful", "irrelevant", "too_generic", "dislike"}
    )
    return {
        "acceptance_rate": _safe_ratio(accepted, total),
        "rejection_rate": _safe_ratio(rejected, total),
        "feedback_count": total,
    }


def _load_opportunity_summary(db: Session, user_id: int) -> dict[str, float]:
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()
    completed = sum(1 for item in follow_ups if item.status.lower() == "done")
    return {
        "opportunity_conversion_rate": _safe_ratio(completed, len(follow_ups)),
        "completed_follow_ups": completed,
        "tracked_follow_ups": len(follow_ups),
    }


def get_metrics_payload(db: Session, user_id: Optional[int] = None) -> dict[str, Any]:
    snapshot = get_metrics_service().snapshot()
    payload = {
        "uptime_seconds": snapshot.uptime_seconds,
        "started_at": snapshot.started_at,
        "api": snapshot.api,
        "retrieval": snapshot.retrieval,
        "recommendations": snapshot.recommendations,
        "opportunities": snapshot.opportunities,
        "cache": snapshot.cache,
        "background_tasks": snapshot.background_tasks,
        "service_health_snapshot": snapshot.dependency_status["status"],
        "dependency_status": snapshot.dependency_status["dependencies"],
    }
    if user_id is not None:
        payload["user_effectiveness"] = {
            "recommendations": _load_recommendation_feedback_summary(db, user_id),
            "opportunities": _load_opportunity_summary(db, user_id),
        }
    return payload


def get_metrics_summary_payload(db: Session, user_id: Optional[int] = None) -> dict[str, Any]:
    payload = get_metrics_payload(db, user_id=user_id)
    summary_lines = [
        f"Uptime: {payload['uptime_seconds']}s.",
        (
            f"API handled {payload['api']['request_count']} request(s) across "
            f"{payload['api']['endpoint_count']} endpoint(s) with "
            f"{payload['api']['error_count']} error(s)."
        ),
        (
            f"Retrieval ran {payload['retrieval']['retrieval_count']} time(s) with "
            f"{payload['retrieval']['retrieval_failures']} failure(s)."
        ),
        (
            f"Cache hit ratio is {payload['cache']['hit_ratio']} "
            f"from {payload['cache']['cache_hits']} hit(s) and {payload['cache']['cache_misses']} miss(es)."
        ),
        (
            f"Background task dispatch attempts: {payload['background_tasks']['dispatch_count']}, "
            f"failures: {payload['background_tasks']['dispatch_failures']}."
        ),
        f"Service health snapshot: {payload['service_health_snapshot']}.",
    ]
    if user_id is not None:
        recommendation_summary = payload["user_effectiveness"]["recommendations"]
        opportunity_summary = payload["user_effectiveness"]["opportunities"]
        summary_lines.append(
            "Recommendation acceptance rate: "
            f"{recommendation_summary['acceptance_rate']}, rejection rate: {recommendation_summary['rejection_rate']}."
        )
        summary_lines.append(
            "Opportunity conversion rate: "
            f"{opportunity_summary['opportunity_conversion_rate']}."
        )
    payload["summary"] = " ".join(summary_lines)
    return payload
