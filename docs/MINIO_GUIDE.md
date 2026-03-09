# MinIO Data Lake 설정 가이드

## 현재 구성

### 서비스 위치
- **MinIO Server**: 데스크탑 노드 (`docker-compose.desktop.yml`)
- **데이터 저장**: `D:\minio-data` (WSL: `/mnt/d/minio-data`)

### 접속 정보
| 항목 | 값 |
|------|-----|
| API Endpoint | `http://<DESKTOP_IP>:9000` |
| Console | `http://<DESKTOP_IP>:9001` |
| Access Key | `minio` |
| Secret Key | `<your-password>` |

### 현재 버킷 구조
```
minio/
├── raw/              # Raw 데이터 (원본)
├── processed/        # 처리된 데이터
├── aggregated/       # 집계 데이터
└── iceberg-warehouse/ # Iceberg 테이블 (현재 미사용)
```

---

## 향후 작업 계획

### 1. Iceberg 테이블 재활성화
현재 Iceberg가 비활성화된 상태입니다. 정상화하려면:

```python
# shop_streaming.py에서 다시 활성화
spark.sql("CREATE NAMESPACE IF NOT EXISTS my_catalog.shop")
spark.sql("""
    CREATE TABLE IF NOT EXISTS my_catalog.shop.hourly_sales (...)
    USING iceberg
    LOCATION 's3a://iceberg-warehouse/shop/hourly_sales'
""")
```

**주의**: 각 테이블에 명시적 `LOCATION` 지정 필요

### 2. 데이터 보존 정책
- **Raw 데이터**: 7일 보존 후 삭제 또는 Cold Storage
- **Aggregated 데이터**: 영구 보존
- **Iceberg 테이블**: 스냅샷 기반 Time Travel

### 3. 백업 전략
```bash
# D 드라이브 데이터 외부 백업
rsync -av /mnt/d/minio-data/ /path/to/backup/
```

---

## Spark ↔ MinIO 연결 설정

### spark-submit 옵션
```bash
--conf spark.sql.catalog.my_catalog=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.my_catalog.type=hadoop
--conf spark.sql.catalog.my_catalog.warehouse=s3a://iceberg-warehouse/
--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000
--conf spark.hadoop.fs.s3a.access.key=minio
--conf spark.hadoop.fs.s3a.secret.key=<your-password>
--conf spark.hadoop.fs.s3a.path.style.access=true
--conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem
```

### Python에서 직접 접근
```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://<DESKTOP_IP>:9000',
    aws_access_key_id='minio',
    aws_secret_access_key='<your-password>'
)

# 파일 업로드
s3.upload_file('local_file.parquet', 'raw', 'data/file.parquet')

# 파일 목록
for obj in s3.list_objects_v2(Bucket='raw')['Contents']:
    print(obj['Key'])
```

---

## 보안 개선 (TODO)

1. **자격증명 변경**: 기본 `minio/<your-password>` → 강력한 비밀번호
2. **환경변수 관리**: `.env` 파일로 분리
3. **네트워크 제한**: 내부망에서만 접근 가능하도록

```yaml
# .env 파일
MINIO_ROOT_USER=your_secure_user
MINIO_ROOT_PASSWORD=your_secure_password_here
```

---

## 명령어 레퍼런스

### MinIO CLI (mc)
```bash
# 별칭 설정
mc alias set myminio http://<DESKTOP_IP>:9000 minio <your-password>

# 버킷 목록
mc ls myminio

# 버킷 생성
mc mb myminio/new-bucket

# 파일 복사
mc cp local_file.csv myminio/raw/

# 버킷 용량 확인
mc du myminio/raw
```

### 컨테이너 내부에서 실행
```bash
docker exec -it junho-data-platform-minio-1 mc ls local
```
