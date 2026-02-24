# Ralph Stock Analysis - 모니터링 시스템 설계서

**작성일**: 2026-02-06
**작성자**: DevOps Architect (Claude Code Agent)
**버전**: 1.0

---

## 1. 개요

### 1.1 목표
- **가시성 확보**: 전체 시스템 상태 실시간 모니터링
- **신속한 장애 감지**: 1분 이내 장애 알림
- **성능 최적화**: 병목 지점 식별 및 개선
- **용량 계획**: 리소스 사용 추이 분석

### 1.2 범위
- **Metrics**: Prometheus + Grafana
- **Logs**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Alerts**: AlertManager + PagerDuty/Slack
- **Health Check**: 통합 헬스체크 시스템

---

## 2. 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Monitoring Stack                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ Grafana  │◄───┤Prometheus│◄───┤Exporter  │◄───┤ Services │     │
│  │ :3000    │    │ :9090    │    │  9100+   │    │          │     │
│  └──────────┘    └────┬─────┘    └──────────┘    └──────────┘     │
│                        │                                              │
│                   ┌────▼─────┐                                       │
│                   │AlertMana │                                       │
│                   │  :9093   │                                       │
│                   └────┬─────┘                                       │
│                        │                                              │
│                   ┌────▼─────┐                                       │
│                   │ Slack    │                                       │
│                   │ Email    │                                       │
│                   └──────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          Logging Stack                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │  Kibana  │◄───┤Logstash  │◄───┤Filebeat  │◄───┤ Services │     │
│  │ :5601    │    │ :5044    │    │  (log)   │    │          │     │
│  └──────────┘    └────┬─────┘    └──────────┘    └──────────┘     │
│                       │                                              │
│                  ┌────▼─────┐                                       │
│                  │Elasticsearch                                    │
│                  │ :9200    │                                       │
│                  └──────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Exporter 구성

| Exporter | Port | 수집 메트릭 | 대상 |
|----------|------|-------------|------|
| Node Exporter | 9100 | CPU, Memory, Disk, Network | Host 시스템 |
| cAdvisor | 9800 | Container CPU/Memory/Network | Docker 컨테이너 |
| PostgreSQL Exporter | 9187 | Connections, Queries, Replication | PostgreSQL |
| Redis Exporter | 9121 | Commands, Connections, Memory | Redis |
| Celery Exporter | 9540 | Tasks, Workers, Brokers | Celery |
| FastAPI Exporter | 8000 | Custom metrics | Python Services |

---

## 3. Prometheus 구성

### 3.1 설치 계획

#### Docker Compose 추가
```yaml
# docker/compose/services/monitoring.yml

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - ralph-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning
    networks:
      - ralph-network

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./config/alertmanager:/etc/alertmanager
      - alertmanager-data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - ralph-network

  # Node Exporter - Host 시스템 메트릭
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    networks:
      - ralph-network

  # cAdvisor - 컨테이너 메트릭
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    networks:
      - ralph-network

  # PostgreSQL Exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres-exporter
    restart: unless-stopped
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres:postgres@postgres:5432/ralph_stock?sslmode=disable
    networks:
      - ralph-network

  # Redis Exporter
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    restart: unless-stopped
    environment:
      - REDIS_ADDR=redis://redis:6379
    networks:
      - ralph-network

volumes:
  prometheus-data:
    name: ralph-prometheus-data
  grafana-data:
    name: ralph-grafana-data
  alertmanager-data:
    name: ralph-alertmanager-data
```

### 3.2 Prometheus 설정

```yaml
# docker/compose/config/prometheus/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'ralph-stock'
    environment: 'production'

# AlertManager 관리
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

# 알림 규칙 로드
rule_files:
  - 'alerts/*.yml'

# 메트릭 수집 대상
scrape_configs:
  # Prometheus 자체 메트릭
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # API Gateway
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:5111']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # VCP Scanner
  - job_name: 'vcp-scanner'
    static_configs:
      - targets: ['vcp-scanner:5112']
    metrics_path: '/metrics'

  # Signal Engine
  - job_name: 'signal-engine'
    static_configs:
      - targets: ['signal-engine:5113']
    metrics_path: '/metrics'

  # Daytrading Scanner
  - job_name: 'daytrading-scanner'
    static_configs:
      - targets: ['daytrading-scanner:5115']
    metrics_path: '/metrics'

  # Chatbot
  - job_name: 'chatbot'
    static_configs:
      - targets: ['chatbot:5114']
    metrics_path: '/metrics'

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Node Exporter (시스템)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  # cAdvisor (컨테이너)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

### 3.3 Alert 규칙

```yaml
# docker/compose/config/prometheus/alerts/services.yml

groups:
  - name: service_health
    interval: 30s
    rules:
      # 서비스 다운 감지
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "서비스 다운: {{ $labels.instance }}"
          description: "{{ $labels.job }} 서비스가 1분 이상 응답하지 않습니다."

      # 높은 오류율
      - alert: HighErrorRate
        expr: |
          (
            rate(http_requests_total{status=~"5.."}[5m])
            /
            rate(http_requests_total[5m])
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "높은 오류율: {{ $labels.instance }}"
          description: "5xx 오류율이 5% 이상입니다 (현재: {{ $value | humanizePercentage }})"

      # 높은 지연 시간
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "높은 지연시간: {{ $labels.instance }}"
          description: "P95 지연시간이 1초 이상입니다 (현재: {{ $value }}s)"

  - name: resource_usage
    interval: 30s
    rules:
      # 높은 CPU 사용률
      - alert: HighCPUUsage
        expr: |
          (
            rate(process_cpu_seconds_total[5m]) * 100
          ) > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "높은 CPU 사용률: {{ $labels.instance }}"
          description: "CPU 사용률이 80% 이상입니다 (현재: {{ $value }}%)"

      # 높은 메모리 사용률
      - alert: HighMemoryUsage
        expr: |
          (
            process_resident_memory_bytes
            /
            node_memory_MemTotal_bytes
          ) * 100 > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "높은 메모리 사용률: {{ $labels.instance }}"
          description: "메모리 사용률이 80% 이상입니다 (현재: {{ $value }}%)"

      # 디스크 공간 부족
      - alert: DiskSpaceLow
        expr: |
          (
            node_filesystem_avail_bytes{mountpoint="/"}
            /
            node_filesystem_size_bytes{mountpoint="/"}
          ) * 100 < 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "디스크 공간 부족: {{ $labels.instance }}"
          description: "루트 파티션 남은 공간이 10% 미만입니다 (현재: {{ $value }}%)"

  - name: database
    interval: 30s
    rules:
      # PostgreSQL 연결 과다
      - alert: PostgresTooManyConnections
        expr: |
          (
            pg_stat_database_numbackends
            /
            pg_settings_max_connections
          ) * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL 연결 과다"
          description: "연결 수가 최대의 80% 이상입니다 (현재: {{ $value }}%)"

      # PostgreSQL 쿼리 느림
      - alert: PostgresSlowQueries
        expr: |
          rate(pg_stat_statements_mean_exec_time_seconds[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL 느린 쿼리"
          description: "평균 쿼리 실행 시간이 1초 이상입니다 (현재: {{ $value }}s)"

  - name: celery
    interval: 30s
    rules:
      # Celery Task Queue 길이
      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery Queue 밀림"
          description: "대기 중인 작업이 1000개 이상입니다 (현재: {{ $value }})"

      # Celery Worker 다운
      - alert: CeleryWorkerDown
        expr: celery_worker_up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Celery Worker 다운"
          description: "Celery Worker가 응답하지 않습니다."

  - name: websocket
    interval: 30s
    rules:
      # WebSocket 연결 급증
      - alert: WebSocketConnectionSpike
        expr: |
          rate(websocket_connections_total[5m]) > 100
        for: 2m
        labels:
          severity: info
        annotations:
          summary: "WebSocket 연결 급증"
          description: "WebSocket 연결이 급증하고 있습니다 ({{ $value }}/s)"

      # WebSocket 연결 수 이상
      - alert: TooManyWebSocketConnections
        expr: websocket_connections_active > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "WebSocket 연결 과다"
          description: "활성 WebSocket 연결이 5000개 이상입니다 (현재: {{ $value }})"
```

### 3.4 AlertManager 설정

```yaml
# docker/compose/config/alertmanager/alertmanager.yml

global:
  resolve_timeout: 5m
  slack_api_url: '${SLACK_WEBHOOK_URL}'

# 알림 라우팅
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    # Critical 알림 (즉시)
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 0s
      repeat_interval: 5m

    # Warning 알림 (5분 대기)
    - match:
        severity: warning
      receiver: 'warning-alerts'
      group_wait: 5m
      repeat_interval: 1h

    # Info 알림 (1시간 대기)
    - match:
        severity: info
      receiver: 'info-alerts'
      group_wait: 1h
      repeat_interval: 24h

# 수신자 설정
receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: '🚨 {{ .GroupLabels.alertname }}'
        text: |
          *Summary*: {{ .CommonAnnotations.summary }}
          *Description*: {{ .CommonAnnotations.description }}
          *Severity*: {{ .CommonLabels.severity }}

  - name: 'critical-alerts'
    slack_configs:
      - channel: '#alerts-critical'
        send_resolved: true
        title: '🔴 CRITICAL: {{ .GroupLabels.alertname }}'
        color: 'danger'
        text: |
          *Summary*: {{ .CommonAnnotations.summary }}
          *Description*: {{ .CommonAnnotations.description }}
          *Severity*: {{ .CommonLabels.severity }}
    email_configs:
      - to: 'admin@ralphpark.com'
        send_resolved: true

  - name: 'warning-alerts'
    slack_configs:
      - channel: '#alerts-warning'
        send_resolved: true
        title: '⚠️ WARNING: {{ .GroupLabels.alertname }}'
        color: 'warning'
        text: |
          *Summary*: {{ .CommonAnnotations.summary }}
          *Description*: {{ .CommonAnnotations.description }}

  - name: 'info-alerts'
    slack_configs:
      - channel: '#alerts-info'
        send_resolved: true
        title: 'ℹ️ INFO: {{ .GroupLabels.alertname }}'

# 억제 규칙 (중복 알림 방지)
inhibit_rules:
  # Critical이 발생하면 related 억제
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

---

## 4. Grafana 대시보드

### 4.1 Dashboard 목록

| Dashboard | 목적 | 주요 패널 |
|-----------|------|-----------|
| **System Overview** | 전체 시스템 현황 | CPU, Memory, Disk, Network |
| **Service Health** | 서비스 상태 | Uptime, Request Rate, Error Rate |
| **API Performance** | API 성능 | Latency, Throughput, Status Codes |
| **Database** | PostgreSQL | Connections, Queries, Cache Hit Ratio |
| **Celery** | 배치 작업 | Task Rate, Worker Status, Queue Length |
| **WebSocket** | 실시간 연결 | Connections, Messages, Broadcast Time |
| **Kiwoom Integration** | 외부 API | Rate Limit, Errors, Response Time |

### 4.2 핵심 Grafana Panel 예시

#### System Overview Dashboard
```json
{
  "title": "System Overview",
  "panels": [
    {
      "title": "CPU Usage %",
      "targets": [
        {
          "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
        }
      ],
      "type": "graph"
    },
    {
      "title": "Memory Usage %",
      "targets": [
        {
          "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
        }
      ],
      "type": "gauge"
    },
    {
      "title": "Disk Usage %",
      "targets": [
        {
          "expr": "(1 - (node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"})) * 100"
        }
      ],
      "type": "gauge"
    },
    {
      "title": "Network Traffic",
      "targets": [
        {
          "expr": "rate(node_network_receive_bytes_total[5m])",
          "legendFormat": "In {{instance}}"
        },
        {
          "expr": "rate(node_network_transmit_bytes_total[5m])",
          "legendFormat": "Out {{instance}}"
        }
      ],
      "type": "graph"
    }
  ]
}
```

#### Service Health Dashboard
```json
{
  "title": "Service Health",
  "panels": [
    {
      "title": "Service Uptime",
      "targets": [
        {
          "expr": "up{job=~\"api-gateway|vcp-scanner|signal-engine|chatbot|daytrading-scanner\"}"
        }
      ],
      "type": "stat"
    },
    {
      "title": "Request Rate (req/s)",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[5m])) by (job)"
        }
      ],
      "type": "graph"
    },
    {
      "title": "Error Rate (%)",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (job) / sum(rate(http_requests_total[5m])) by (job) * 100"
        }
      ],
      "type": "gauge"
    },
    {
      "title": "P95 Latency (s)",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, job))"
        }
      ],
      "type": "graph"
    }
  ]
}
```

### 4.3 Grafana Provisioning

```yaml
# docker/compose/config/grafana/provisioning/dashboards/dashboard.yml

apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

```yaml
# docker/compose/config/grafana/provisioning/datasources/prometheus.yml

apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

---

## 5. ELK Stack 구성

### 5.1 Docker Compose 추가

```yaml
# docker/compose/services/logging.yml

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: elasticsearch
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
      - xpack.security.enrollment.enabled=false
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - ralph-network

  logstash:
    image: docker.elastic.co/logstash/logstash:8.12.0
    container_name: logstash
    restart: unless-stopped
    volumes:
      - ./config/logstash:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch
    networks:
      - ralph-network

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: kibana
    restart: unless-stopped
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - ralph-network

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.12.0
    container_name: filebeat
    restart: unless-stopped
    user: root
    volumes:
      - ./config/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: filebeat -e -strict.perms=false
    networks:
      - ralph-network

volumes:
  elasticsearch-data:
    name: ralph-elasticsearch-data
```

### 5.2 Filebeat 설정

```yaml
# docker/compose/config/filebeat/filebeat.yml

filebeat.inputs:
  - type: container
    paths:
      - /var/lib/docker/containers/*/*.log
    processors:
      - add_docker_metadata:
          host: "unix:///var/run/docker.sock"

# Docker 컨테이너 로그만 수집
processors:
  - drop_event:
      when:
        not:
          or:
            - equals:
                docker.container.name: "api-gateway"
            - equals:
                docker.container.name: "vcp-scanner"
            - equals:
                docker.container.name: "signal-engine"
            - equals:
                docker.container.name: "daytrading-scanner"
            - equals:
                docker.container.name: "chatbot"
            - equals:
                docker.container.name: "frontend"
            - equals:
                docker.container.name: "celery-worker"
            - equals:
                docker.container.name: "celery-beat"

  # 로그 레벨 파싱
  - dissect:
      tokenizer: '%{timestamp} - %{logger} - %{level} - %{message}'
      field: "message"
      target_prefix: "parsed"

# Logstash로 전송
output.logstash:
  hosts: ["logstash:5044"]

# Kibana 대시보드 자동 설정
setup.kibana:
  host: "http://kibana:5601"

# 인덱스 설정
output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "ralph-stock-logs-%{+yyyy.MM.dd}"
  setup.template.name: "ralph-stock"
  setup.template.pattern: "ralph-stock-*"

# 로그 수집 주기
logging.level: info
logging.metrics.enabled: false
```

### 5.3 Logstash 파이프라인

```ruby
# docker/compose/config/logstash/pipeline.conf

input {
  beats {
    port => 5044
  }
}

filter {
  # JSON 파싱
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
    }
  }

  # Docker 메타데이터 추가
  if [docker][container][name] {
    mutate {
      add_field => {
        "service" => "%{[docker][container][name]}"
      }
    }
  }

  # 로그 레벨 파싱 (Python 로그 형식)
  grok {
    match => {
      "message" => "(?<timestamp>%{YEAR}-%{MONTHNUM}-%{MONTHDAY} %{TIME}) - (?<logger>[^ ]+) - (?<level>[^ ]+) - (?<message>.*)"
    }
  }

  # 날짜 파싱
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }

  # 에러 로그 태그
  if [level] == "ERROR" or [level] == "CRITICAL" {
    mutate {
      add_tag => ["error"]
    }
  }

  # Kiwoom API 관련 로그
  if [message] =~ /Kiwoom/ {
    mutate {
      add_tag => ["kiwoom"]
    }
  }

  # WebSocket 로그
  if [message] =~ /WebSocket/ {
    mutate {
      add_tag => ["websocket"]
    }
  }

  # 불필요한 필드 제거
  mutate {
    remove_field => ["agent", "ecs", "host", "@version"]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "ralph-stock-logs-%{+YYYY.MM.dd}"

    # 에러 로그는 별도 인덱스
    if "error" in [tags] {
      index => "ralph-stock-errors-%{+YYYY.MM.dd}"
    }
  }

  # 디버깅용 stdout
  stdout {
    codec => rubydebug
  }
}
```

---

## 6. Health Check 개선

### 6.1 통합 헬스체크 엔드포인트

```python
# services/api_gateway/health.py

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import httpx
from sqlalchemy import text
from src.database.session import get_db_session

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    통합 헬스체크
    - 서비스 상태
    - 데이터베이스 연결
    - Redis 연결
    - 외부 서비스 연결
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # PostgreSQL 체크
    try:
        async with get_db_session() as db:
            result = await db.execute(text("SELECT 1"))
            health_status["checks"]["postgres"] = {
                "status": "healthy",
                "latency_ms": result.elapsed * 1000 if hasattr(result, 'elapsed') else 0
            }
    except Exception as e:
        health_status["checks"]["postgres"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"

    # Redis 체크
    try:
        redis_client.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # VCP Scanner 체크
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.vcp_scanner_url}/health",
                timeout=2.0
            )
            health_status["checks"]["vcp_scanner"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy"
            }
    except Exception as e:
        health_status["checks"]["vcp_scanner"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Signal Engine 체크
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.signal_engine_url}/health",
                timeout=2.0
            )
            health_status["checks"]["signal_engine"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy"
            }
    except Exception as e:
        health_status["checks"]["signal_engine"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    return health_status

@router.get("/health/ready")
async def readiness_check():
    """
    Readiness Probe
    - 트래픽 받을 준비 되었는지
    """
    # DB 연결만 확인
    try:
        async with get_db_session() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="not ready")

@router.get("/health/live")
async def liveness_check():
    """
    Liveness Probe
    - 프로세스 살아있는지
    """
    return {"status": "alive"}
```

### 6.2 Docker Compose Health Check 업데이트

```yaml
# docker/compose/profiles/prod.yml

services:
  api-gateway:
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:5111/health/ready"]
      interval: 15s
      timeout: 5s
      start_period: 60s
      retries: 3

  celery-worker:
    healthcheck:
      test: ["CMD", "celery", "-A", "tasks.celery_app", "inspect", "ping"]
      interval: 30s
      timeout: 10s
      start_period: 60s
      retries: 3
```

---

## 7. 구현 Phase

### Phase 1: Prometheus + Grafana (Week 1)
- [ ] Docker Compose에 모니터링 서비스 추가
- [ ] Prometheus 설정
- [ ] AlertManager 설정
- [ ] Grafana 설치 및 Provisioning
- [ ] 핵심 Dashboard 생성
- [ ] Slack 알림 연동

### Phase 2: Exporter 배포 (Week 1-2)
- [ ] Node Exporter 배포
- [ ] cAdvisor 배포
- [ ] PostgreSQL Exporter 배포
- [ ] Redis Exporter 배포
- [ ] FastAPI /metrics 엔드포인트 점검

### Phase 3: Alert 규칙 (Week 2)
- [ ] Service Health Alert
- [ ] Resource Usage Alert
- [ ] Database Alert
- [ ] Celery Alert
- [ ] WebSocket Alert

### Phase 4: ELK Stack (Week 3-4)
- [ ] Elasticsearch 설치
- [ ] Logstash 설치
- [ ] Kibana 설치
- [ ] Filebeat 설정
- [ ] 로그 파이프라인 구축

### Phase 5: 고급 기능 (Week 5+)
- [ ] Grafana Loki (선택)
- [ ] Jaeger Tracing (선택)
- [ ] PagerDuty 연동 (선택)
- [ ] SMS 알림 (선택)

---

## 8. 포트 매핑

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Prometheus | 9090 | 메트릭 수집 |
| Grafana | 3000 | 대시보드 |
| AlertManager | 9093 | 알림 관리 |
| Node Exporter | 9100 | 시스템 메트릭 |
| cAdvisor | 9800 | 컨테이너 메트릭 |
| PostgreSQL Exporter | 9187 | DB 메트릭 |
| Redis Exporter | 9121 | Redis 메트릭 |
| Elasticsearch | 9200 | 로그 저장소 |
| Kibana | 5601 | 로그 대시보드 |
| Logstash | 5044 | 로그 수집 |

---

## 9. 리소스 예상

### 9.1 모니터링 스택 리소스

| 서비스 | CPU | Memory | Disk |
|--------|-----|--------|------|
| Prometheus | 2 core | 2GB | 50GB/30일 |
| Grafana | 1 core | 512MB | 1GB |
| AlertManager | 0.5 core | 256MB | 1GB |
| Node Exporter | 0.1 core | 64MB | - |
| cAdvisor | 0.5 core | 256MB | - |
| PostgreSQL Exporter | 0.1 core | 64MB | - |
| Redis Exporter | 0.1 core | 64MB | - |
| Elasticsearch | 2 core | 2GB | 100GB/30일 |
| Logstash | 1 core | 1GB | - |
| Kibana | 1 core | 1GB | 1GB |
| Filebeat | 0.1 core | 64MB | - |
| **총계** | **8.5 core** | **~8GB** | **~150GB** |

---

## 10. 결론

### 10.1 기대 효과
- ✅ 장애 감지 시간: 1분 이내
- ✅ 모니터링 커버리지: 100%
- ✅ 로그 검색: 실시간
- ✅ 성능 병목 식별: 가능
- ✅ 용량 계획: 데이터 기반

### 10.2 다음 단계
1. **즉시**: Phase 1-2 (Prometheus + Grafana + Exporters)
2. **2주 내**: Phase 3 (Alert Rules)
3. **한달 내**: Phase 4 (ELK Stack)

---

*이 설계서는 DevOps Architect에 의해 작성되었습니다.*
