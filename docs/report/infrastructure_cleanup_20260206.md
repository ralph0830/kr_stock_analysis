# Infrastructure Cleanup Report - 로그/덤프 정리

**정리 일시:** 2026-02-06 09:32 (KST)
**상태:** ✅ **COMPLETED**

---

## 1. 요약

### 정리 전 → 정리 후

| 항목 | 정리 전 | 정리 후 | 개선 |
|------|---------|---------|------|
| API Gateway 로그 | 21 MB (3개 파일) | 1.7 MB (1개 파일) | **-92%** ✅ |
| 이전 로그 파일 | 20 MB (2개) | 0 bytes | **-100%** ✅ |
| Core dump 파일 | 확인 결과 없음 | - | **해당 없음** |

---

## 2. 로그 파일 정리 상세

### 2.1 정리 전

```
파일명                                              크기
--------------------------------------------------  ----------
1fe8c176bb44...json.log                             1.3 MB (현재)
1fe8c176bb44...json.log.1                           10 MB (회전됨)
1fe8c176bb44...json.log.2                           10 MB (회전됨)
--------------------------------------------------  ----------
총:                                                 21 MB
```

### 2.2 정리 후

```
파일명                                              크기
--------------------------------------------------  ----------
1fe8c176bb44...json.log                             1.7 MB (현재)
1fe8c176bb44...json.log.1                           0 bytes (정리됨)
1fe8c176bb44...json.log.2                           0 bytes (정리됨)
--------------------------------------------------  ----------
총:                                                 1.7 MB
```

### 2.3 정리 명령

```bash
sudo truncate -s 0 /var/lib/docker/containers/.../...-json.log.1
sudo truncate -s 0 /var/lib/docker/containers/.../...-json.log.2
```

---

## 3. Core Dump 파일 확인

### 3.1 검색 결과

| 위치 | 검색 결과 |
|------|----------|
| `/var/lib/docker` | Core dump 없음 |
| `/tmp` | Core dump 없음 |

**결과:** Core dump 파일은 존재하지 않음

---

## 4. Docker 전체 디스크 사용량

```
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          48        39        26.43GB   23.17GB (87%)
Containers      41        40        944.5MB   0B (0%)
Local Volumes   24        14        2.917GB   1.602GB (54%)
Build Cache     98        0         8.417GB   3.246GB
```

### 4.1 reclaimable (회수 가능) 공간

| 항목 | 크기 | 비고 |
|------|------|------|
| 미사용 이미지 | 23.17 GB | 87% |
| 미사용 볼륨 | 1.602 GB | 54% |
| 빌드 캐시 | 3.246 GB | - |
| **총 회수 가능** | **~28 GB** | - |

---

## 5. 권장 사항

### 5.1 로그 관리 정책 설정

Docker Compose에 로그 제한 추가 권장:

```yaml
services:
  api-gateway:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"    # 단일 파일 최대 10MB
        max-file: "3"      # 최대 3개 파일 보존
```

### 5.2 정기 cleanup 명령

```bash
# 미사용 이미지 정리
docker image prune -a

# 미사용 볼륨 정리
docker volume prune

# 미사용 리소스 전체 정리
docker system prune -a
```

---

## 6. 결론

- ✅ **이전 로그 파일 정리 완료** (20 MB → 0 bytes)
- ✅ **현재 로그만 유지** (1.7 MB)
- ✅ **Core dump 파일 없음 확인**
- ℹ️ **28 GB reclaimable 공간 존재** (필요 시 정리 권장)

---

**보고서 작성일:** 2026-02-06 09:35 (KST)
**작성자:** Claude Code QA Agent
