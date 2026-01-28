"""
메트릭 수집 테스트
"""

import pytest
from src.utils.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    metrics_registry,
    increment_counter,
    set_gauge,
    observe_histogram,
)


class TestCounter:
    """Counter 테스트"""

    def test_increment(self):
        """증가 테스트"""
        counter = Counter("test_counter", "Test counter")
        counter.inc()
        assert counter.get() == 1.0

    def test_increment_by_amount(self):
        """지정된 양만큼 증가 테스트"""
        counter = Counter("test_counter")
        counter.inc(5)
        assert counter.get() == 5.0

    def test_negative_increment_raises_error(self):
        """음수 증가 에러 테스트"""
        counter = Counter("test_counter")
        with pytest.raises(ValueError):
            counter.inc(-1)

    def test_reset(self):
        """리셋 테스트"""
        counter = Counter("test_counter")
        counter.inc(10)
        counter.reset()
        assert counter.get() == 0.0


class TestGauge:
    """Gauge 테스트"""

    def test_increment(self):
        """증가 테스트"""
        gauge = Gauge("test_gauge")
        gauge.inc()
        assert gauge.get() == 1.0

    def test_decrement(self):
        """감소 테스트"""
        gauge = Gauge("test_gauge")
        gauge.set(10)
        gauge.dec()
        assert gauge.get() == 9.0

    def test_set(self):
        """설정 테스트"""
        gauge = Gauge("test_gauge")
        gauge.set(42.0)
        assert gauge.get() == 42.0

    def test_reset(self):
        """리셋 테스트"""
        gauge = Gauge("test_gauge")
        gauge.set(100)
        gauge.reset()
        assert gauge.get() == 0.0


class TestHistogram:
    """Histogram 테스트"""

    def test_observe(self):
        """관측 테스트"""
        histogram = Histogram("test_histogram", buckets=[1.0, 5.0, 10.0])
        histogram.observe(2.5)
        histogram.observe(7.5)

        data = histogram.get()
        assert data["count"] == 2
        assert data["sum"] == 10.0

    def test_buckets(self):
        """버킷 분류 테스트"""
        histogram = Histogram("test_histogram", buckets=[1.0, 5.0])

        histogram.observe(0.5)  # <= 1.0
        histogram.observe(3.0)  # <= 5.0
        histogram.observe(10.0)  # > 5.0 (le=+Inf)

        data = histogram.get()
        assert data["buckets"][1.0] == 1
        assert data["buckets"][5.0] == 2
        assert data["buckets"][float("inf")] == 3

    def test_default_buckets(self):
        """기본 버킷 테스트"""
        histogram = Histogram("test_histogram")

        # 기본 버킷이 있는지 확인
        data = histogram.get()
        assert len(data["buckets"]) > 0
        assert float("inf") in data["buckets"]

    def test_reset(self):
        """리셋 테스트"""
        histogram = Histogram("test_histogram")
        histogram.observe(1.0)
        histogram.observe(2.0)

        histogram.reset()

        data = histogram.get()
        assert data["count"] == 0
        assert data["sum"] == 0.0


class TestMetricsRegistry:
    """MetricsRegistry 테스트"""

    def test_counter_creation(self):
        """Counter 생성 테스트"""
        registry = MetricsRegistry()
        counter = registry.counter("test_counter", "Test counter")

        assert isinstance(counter, Counter)
        counter.inc()
        assert counter.get() == 1.0

    def test_gauge_creation(self):
        """Gauge 생성 테스트"""
        registry = MetricsRegistry()
        gauge = registry.gauge("test_gauge", "Test gauge")

        assert isinstance(gauge, Gauge)
        gauge.set(10.0)
        assert gauge.get() == 10.0

    def test_histogram_creation(self):
        """Histogram 생성 테스트"""
        registry = MetricsRegistry()
        histogram = registry.histogram("test_histogram", "Test histogram")

        assert isinstance(histogram, Histogram)
        histogram.observe(5.0)
        data = histogram.get()
        assert data["count"] == 1

    def test_export_prometheus_format(self):
        """Prometheus 형식 내보내기 테스트"""
        registry = MetricsRegistry()

        counter = registry.counter("api_requests_total", "Total API requests")
        counter.inc(42)

        export = registry.export()

        assert "# HELP api_requests_total Total API requests" in export
        assert "# TYPE api_requests_total counter" in export
        assert "api_requests_total 42.0" in export

    def test_export_with_histogram(self):
        """Histogram 포함 내보내기 테스트"""
        registry = MetricsRegistry()

        histogram = registry.histogram("request_duration_seconds", "Request duration")
        histogram.observe(0.5)
        histogram.observe(1.5)

        export = registry.export()

        assert "# TYPE request_duration_seconds histogram" in export
        assert "request_duration_seconds_count 2" in export
        assert "request_duration_seconds_sum 2.0" in export
        assert 'request_duration_seconds_bucket{le="+Inf"}' in export

    def test_get_all_metrics(self):
        """모든 메트릭 조회 테스트"""
        registry = MetricsRegistry()

        counter = registry.counter("test_counter")
        gauge = registry.gauge("test_gauge")
        histogram = registry.histogram("test_histogram")

        counter.inc(10)
        gauge.set(5)
        histogram.observe(1.0)

        metrics = registry.get_all_metrics()

        assert "test_counter" in metrics
        assert "test_gauge" in metrics
        assert "test_histogram" in metrics
        assert metrics["test_counter"]["type"] == "counter"
        assert metrics["test_gauge"]["type"] == "gauge"
        assert metrics["test_histogram"]["type"] == "histogram"

    def test_reset_all(self):
        """전체 리셋 테스트"""
        registry = MetricsRegistry()

        counter = registry.counter("test_counter")
        gauge = registry.gauge("test_gauge")
        histogram = registry.histogram("test_histogram")

        counter.inc(100)
        gauge.set(50)
        histogram.observe(10)

        registry.reset_all()

        assert counter.get() == 0.0
        assert gauge.get() == 0.0
        assert histogram.get()["count"] == 0

    def test_same_metric_returns_same_instance(self):
        """동일 메트릭 이름에 대해 같은 인스턴스 반환 테스트"""
        registry = MetricsRegistry()

        counter1 = registry.counter("shared_counter")
        counter2 = registry.counter("shared_counter")

        assert counter1 is counter2

        gauge1 = registry.gauge("shared_gauge")
        gauge2 = registry.gauge("shared_gauge")

        assert gauge1 is gauge2

        histogram1 = registry.histogram("shared_histogram")
        histogram2 = registry.histogram("shared_histogram")

        assert histogram1 is histogram2


class TestGlobalRegistry:
    """전역 레지스트리 테스트"""

    def test_global_functions(self):
        """전역 함수 테스트"""
        increment_counter("global_counter", 5.0)
        set_gauge("global_gauge", 10.0)
        observe_histogram("global_histogram", 2.5)

        metrics = metrics_registry.get_all_metrics()

        assert metrics["global_counter"]["value"] == 5.0
        assert metrics["global_gauge"]["value"] == 10.0
        assert metrics["global_histogram"]["value"]["count"] == 1

    def test_export(self):
        """전역 레지스트리 내보내기 테스트"""
        increment_counter("export_test", 1.0)

        export = metrics_registry.export()
        assert "export_test 1.0" in export


class TestMetricLabels:
    """메트릭 라벨 테스트"""

    def test_counter_with_labels(self):
        """Counter 라벨 테스트"""
        counter = Counter(
            "test_counter",
            "Test counter",
            labels={"endpoint": "/api/test", "method": "GET"}
        )

        assert counter.labels == {"endpoint": "/api/test", "method": "GET"}

    def test_gauge_with_labels(self):
        """Gauge 라벨 테스트"""
        gauge = Gauge(
            "test_gauge",
            "Test gauge",
            labels={"service": "api_gateway"}
        )

        assert gauge.labels == {"service": "api_gateway"}

    def test_histogram_with_labels(self):
        """Histogram 라벨 테스트"""
        histogram = Histogram(
            "test_histogram",
            "Test histogram",
            labels={"status": "200"}
        )

        assert histogram.labels == {"status": "200"}
