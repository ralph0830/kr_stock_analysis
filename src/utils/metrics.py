"""
메트릭 수집 시스템
Prometheus 스타일 메트릭 수집
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class MetricType(Enum):
    """메트릭 타입"""
    COUNTER = "counter"  # 단조 증가
    GAUGE = "gauge"      # 증감 가능
    HISTOGRAM = "histogram"  # 분포


@dataclass
class Metric:
    """메트릭 데이터"""
    name: str
    type: MetricType
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class HistogramBucket:
    """Histogram 버킷"""
    count: int = 0
    sum: float = 0.0
    buckets: Dict[float, int] = field(default_factory=dict)


class Counter:
    """
    Counter 메트릭 (단조 증가)

    Usage:
        counter = Counter("api_requests_total", "Total API requests")
        counter.inc()
        counter.inc(5)
        counter.get() -> 6.0
    """

    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self._value = 0.0

    def inc(self, amount: float = 1.0) -> None:
        """값 증가"""
        if amount < 0:
            raise ValueError("Counter can only increment by non-negative amounts")
        self._value += amount

    def get(self) -> float:
        """현재값 반환"""
        return self._value

    def reset(self) -> None:
        """리셋"""
        self._value = 0.0


class Gauge:
    """
    Gauge 메트릭 (증감 가능)

    Usage:
        gauge = Gauge("active_connections", "Active connections")
        gauge.inc()
        gauge.dec()
        gauge.set(10)
        gauge.get() -> 10.0
    """

    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self._value = 0.0

    def inc(self, amount: float = 1.0) -> None:
        """값 증가"""
        self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """값 감소"""
        self._value -= amount

    def set(self, value: float) -> None:
        """값 설정"""
        self._value = value

    def get(self) -> float:
        """현재값 반환"""
        return self._value

    def reset(self) -> None:
        """리셋"""
        self._value = 0.0


class Histogram:
    """
    Histogram 메트릭 (분포)

    Usage:
        histogram = Histogram("request_duration_seconds", "Request duration", buckets=[0.1, 0.5, 1.0, 5.0])
        histogram.observe(0.3)
        histogram.observe(1.5)
        histogram.get() -> {"count": 2, "sum": 1.8, "buckets": {...}}
        histogram.get_percentile(0.95) -> 1.5  # P95
    """

    def __init__(
        self,
        name: str,
        help_text: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self._bucket = HistogramBucket()
        self._observations: List[float] = []  # 정확한 백분위수 계산용

        # 기본 버킷
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

        # 버킷 초기화 (+Inf 포함)
        for b in buckets:
            self._bucket.buckets[b] = 0
        self._bucket.buckets[float("inf")] = 0

    def observe(self, value: float) -> None:
        """값 관측"""
        self._bucket.count += 1
        self._bucket.sum += value

        # 관측값 저장 (정확한 백분위수 계산용)
        self._observations.append(value)

        # 버킷 업데이트
        for bucket_bound in sorted(self._bucket.buckets.keys()):
            if value <= bucket_bound:
                self._bucket.buckets[bucket_bound] += 1

    def get(self) -> Dict:
        """Histogram 데이터 반환"""
        return {
            "count": self._bucket.count,
            "sum": self._bucket.sum,
            "buckets": dict(self._bucket.buckets),
            "p50": self.get_percentile(0.50),
            "p95": self.get_percentile(0.95),
            "p99": self.get_percentile(0.99),
            "avg": self._bucket.sum / self._bucket.count if self._bucket.count > 0 else 0,
        }

    def get_percentile(self, percentile: float) -> float:
        """
        백분위수 계산

        Args:
            percentile: 백분위수 (0.0 ~ 1.0)

        Returns:
            백분위수 값
        """
        if not self._observations:
            return 0.0

        sorted_obs = sorted(self._observations)
        n = len(sorted_obs)
        index = int(n * percentile)

        if index >= n:
            index = n - 1

        return sorted_obs[index]

    def reset(self) -> None:
        """리셋"""
        self._bucket = HistogramBucket()
        self._observations = []
        for bucket_bound in self._bucket.buckets.keys():
            self._bucket.buckets[bucket_bound] = 0


class MetricsRegistry:
    """
    메트릭 레지스트리

    Usage:
        registry = MetricsRegistry()

        # Counter 생성
        counter = registry.counter("api_requests_total", "Total API requests")
        counter.inc()

        # Gauge 생성
        gauge = registry.gauge("active_connections", "Active connections")
        gauge.inc()

        # Histogram 생성
        histogram = registry.histogram("request_duration_seconds", "Request duration")
        histogram.observe(0.5)

        # Prometheus 형식으로 내보내기
        registry.export()
    """

    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}

    def counter(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """Counter 생성 또는 조회"""
        if name not in self._counters:
            self._counters[name] = Counter(name, help_text, labels)
        return self._counters[name]

    def gauge(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """Gauge 생성 또는 조회"""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, help_text, labels)
        return self._gauges[name]

    def histogram(
        self,
        name: str,
        help_text: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> Histogram:
        """Histogram 생성 또는 조회"""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, help_text, buckets, labels)
        return self._histograms[name]

    def export(self) -> str:
        """
        Prometheus 텍스트 형식으로 내보내기

        Returns:
            Prometheus 텍스트 형식 메트릭
        """
        lines = []

        # HELP 및 TYPE
        for counter in self._counters.values():
            lines.append(f"# HELP {counter.name} {counter.help_text}")
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f"{counter.name} {counter.get()}")

        for gauge in self._gauges.values():
            lines.append(f"# HELP {gauge.name} {gauge.help_text}")
            lines.append(f"# TYPE {gauge.name} gauge")
            lines.append(f"{gauge.name} {gauge.get()}")

        for histogram in self._histograms.values():
            lines.append(f"# HELP {histogram.name} {histogram.help_text}")
            lines.append(f"# TYPE {histogram.name} histogram")

            data = histogram.get()
            lines.append(f"{histogram.name}_count {data['count']}")
            lines.append(f"{histogram.name}_sum {data['sum']}")

            # 버킷 (le: less than or equal)
            for bucket_bound, count in sorted(data["buckets"].items()):
                if bucket_bound == float("inf"):
                    bucket_str = "+Inf"
                else:
                    bucket_str = str(bucket_bound)
                lines.append(f'{histogram.name}_bucket{{le="{bucket_str}"}} {count}')

        return "\n".join(lines)

    def get_all_metrics(self) -> Dict[str, Dict]:
        """모든 메트릭 반환 (JSON 형식)"""
        metrics = {}

        for counter in self._counters.values():
            metrics[counter.name] = {
                "type": "counter",
                "value": counter.get(),
                "help": counter.help_text,
            }

        for gauge in self._gauges.values():
            metrics[gauge.name] = {
                "type": "gauge",
                "value": gauge.get(),
                "help": gauge.help_text,
            }

        for histogram in self._histograms.values():
            # Histogram 데이터 복사 및 inf를 문자열로 변환
            data = histogram.get()
            buckets_serializable = {}
            for bucket_bound, count in sorted(data["buckets"].items()):
                if bucket_bound == float("inf"):
                    buckets_serializable["+Inf"] = count
                else:
                    buckets_serializable[str(bucket_bound)] = count

            metrics[histogram.name] = {
                "type": "histogram",
                "value": {
                    "count": data["count"],
                    "sum": data["sum"],
                    "buckets": buckets_serializable,
                    "p50": data.get("p50", 0),
                    "p95": data.get("p95", 0),
                    "p99": data.get("p99", 0),
                    "avg": data.get("avg", 0),
                },
                "help": histogram.help_text,
            }

        return metrics

    def reset_all(self) -> None:
        """모든 메트릭 리셋"""
        for counter in self._counters.values():
            counter.reset()
        for gauge in self._gauges.values():
            gauge.reset()
        for histogram in self._histograms.values():
            histogram.reset()


# 전역 메트릭 레지스트리
metrics_registry = MetricsRegistry()


# 자주 사용되는 메트릭 생성 함수
def increment_counter(name: str, amount: float = 1.0) -> None:
    """Counter 증가"""
    counter = metrics_registry.counter(name)
    counter.inc(amount)


def set_gauge(name: str, value: float) -> None:
    """Gauge 설정"""
    gauge = metrics_registry.gauge(name)
    gauge.set(value)


def observe_histogram(name: str, value: float) -> None:
    """Histogram 관측"""
    histogram = metrics_registry.histogram(name)
    histogram.observe(value)
