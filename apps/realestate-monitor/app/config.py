import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 성북구 geohashes (precision 5) — 6 cells covering the district with overlap
SEONGBUK_GEOHASHES = ["wydmc", "wydmf", "wydmg", "wydq1", "wydq4", "wydq5"]

# 성북구 법정동 코드 prefix
SEONGBUK_BJD_PREFIX = "11290"

# 조건
DEPOSIT_MAX = int(os.getenv("DEPOSIT_MAX", "3000"))   # 만원
RENT_MAX = int(os.getenv("RENT_MAX", "120"))          # 만원
ROOM_TYPES = {"투룸", "쓰리룸"}
SALES_TYPE = "월세"

# 크론
DAILY_HOUR_KST = int(os.getenv("DAILY_HOUR_KST", "8"))
DAILY_MINUTE_KST = int(os.getenv("DAILY_MINUTE_KST", "0"))

# 스크래퍼
ZIGBANG_LIST_URL = "https://apis.zigbang.com/v2/items/villa"
ZIGBANG_DETAIL_URL = "https://apis.zigbang.com/v3/items/{item_id}"
ZIGBANG_WEB_URL = "https://www.zigbang.com/home/villa/items/{item_id}"
DETAIL_CONCURRENCY = int(os.getenv("DETAIL_CONCURRENCY", "5"))
DETAIL_DELAY_MS = int(os.getenv("DETAIL_DELAY_MS", "150"))
