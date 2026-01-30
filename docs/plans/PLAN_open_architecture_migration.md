# Open Architecture Migration Plan

**Status**: ✅ 완료 (7/7 Phases)
**기간**: 2026-01-23 ~ 완료

> **전체 문서**: `docs/archive_originals/PLAN_open_architecture_migration.md` (973줄)

---

## 개요

Monolithic Flask 기반 시스템을 Open Architecture (Microservices + Event-Driven)로 재구성:
- CSV/JSON → PostgreSQL/TimescaleDB
- Celery + Redis 기반 비동기 처리
- 서비스 분리 및 이벤트 버스 통신

---

## 완료된 Phases

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | Database Layer (PostgreSQL + TimescaleDB) | ✅ |
| 2 | API Gateway (Service Discovery) | ✅ |
| 3 | VCP Scanner Service | ✅ |
| 4 | Signal Engine Service | ✅ |
| 5 | Celery Async Processing | ✅ |
| 6 | Event Bus (Redis Pub/Sub) | ✅ |
| 7 | Caching & Optimization | ✅ |

---

## 아키텍처 결정사항

| 결정 | 근거 | Trade-off |
|------|------|-----------|
| PostgreSQL + TimescaleDB | 시계열 데이터 최적화, ACID | NoSQL 유연성 포기 |
| Redis + Celery | Python 친화적, 간단한 구현 | Kafka의 대용량 처리 포기 |
| FastAPI (신규 서비스) | 비동기 처리, 자동 문서 | Flask 생태계 호환성 |
| Redis Pub/Sub | 간단한 구현, 기존 Redis 활용 | RabbitMQ 안정성 포기 |

---

## 마이크로서비스 구조

```
Frontend (5110) → API Gateway (5111)
                        ├→ VCP Scanner (5112)
                        ├→ Signal Engine (5113)
                        └→ Market Analyzer (5114)
                        ↓
                    Event Bus (Redis)
                        ↓
                    Celery Worker
```
