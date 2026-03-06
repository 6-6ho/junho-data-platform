# Docker 볼륨 WSL2 내부 경로 마이그레이션

## 배경

현재 Docker data-root가 Windows D: 드라이브(`/mnt/d/docker-data`)에 있어 WSL2 ↔ Windows 파일시스템 충돌로 Iceberg 메타데이터 손상 발생.

## 현재 상태

- **data-root**: `/mnt/d/docker-data` (Windows D:)
- **데이터 크기**: ~25GB (이미지 8.8GB, 볼륨 14.6GB)
- **WSL2 여유 공간**: 944GB

## 마이그레이션 옵션

### Option A: 클린 스타트 (권장)

데이터를 새로 시작. 기존 Iceberg 손상 데이터 정리.

```bash
# 1. 모든 컨테이너 중지
cd /home/junho/junho-data-platform
docker compose -f docker-compose.desktop.yml down

# 2. Docker 데몬 중지
sudo service docker stop

# 3. 새 디렉토리 생성
sudo mkdir -p /home/junho/docker-data

# 4. daemon.json 수정
sudo nano /etc/docker/daemon.json
# "data-root": "/home/junho/docker-data" 로 변경

# 5. Docker 재시작
sudo service docker start

# 6. 이미지 다시 pull 및 빌드
docker compose -f docker-compose.desktop.yml build
docker compose -f docker-compose.desktop.yml up -d
```

### Option B: 데이터 마이그레이션

기존 데이터 보존. 시간 소요 (~30분).

```bash
# 1. 모든 컨테이너 중지
docker compose -f docker-compose.desktop.yml down

# 2. Docker 데몬 중지
sudo service docker stop

# 3. 데이터 복사 (rsync로 권한 보존)
sudo mkdir -p /home/junho/docker-data
sudo rsync -aP /mnt/d/docker-data/ /home/junho/docker-data/

# 4. daemon.json 수정
sudo nano /etc/docker/daemon.json
# "data-root": "/home/junho/docker-data" 로 변경

# 5. Docker 재시작
sudo service docker start

# 6. 컨테이너 시작
docker compose -f docker-compose.desktop.yml up -d
```

## daemon.json 변경 내용

**Before**:
```json
{
  "data-root": "/mnt/d/docker-data"
}
```

**After**:
```json
{
  "data-root": "/home/junho/docker-data"
}
```

## 마이그레이션 후 체크리스트

- [ ] `docker ps` - 모든 컨테이너 실행 확인
- [ ] `docker volume ls` - 볼륨 목록 확인
- [ ] PostgreSQL 연결 테스트
- [ ] Kafka 토픽 확인
- [ ] MinIO 버킷 확인
- [ ] Spark job 제출 테스트
- [ ] shop-generator 데이터 생성 확인

## 롤백 절차

문제 발생 시:
```bash
sudo service docker stop
sudo nano /etc/docker/daemon.json
# "data-root": "/mnt/d/docker-data" 로 복원
sudo service docker start
```

## 주의사항

1. **PostgreSQL 데이터**: 볼륨에 저장됨. Option A 선택 시 모든 mart 데이터 초기화
2. **Kafka 데이터**: 볼륨에 저장됨. Option A 선택 시 토픽 데이터 손실
3. **MinIO 데이터**: 볼륨에 저장됨. Option A 선택 시 체크포인트/raw 데이터 손실
4. **추천**: Option A (클린 스타트) - 이미 Iceberg 손상으로 데이터 신뢰성 낮음
