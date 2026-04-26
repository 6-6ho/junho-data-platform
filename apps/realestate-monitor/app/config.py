import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 성북구 커버하는 geohashes (precision 5)
GEOHASHES = ["wydmc", "wydmf", "wydmg", "wydq1", "wydq4", "wydq5"]

# 법정동 코드 prefix — 성북구만
ALLOWED_BJD_PREFIXES = ("11290",)

# 조건
DEPOSIT_MAX = int(os.getenv("DEPOSIT_MAX", "5000"))
RENT_MAX = int(os.getenv("RENT_MAX", "150"))
ROOM_TYPES = {"투룸", "쓰리룸"}  # zigbang은 1.5룸을 투룸으로 분류
SALES_TYPE = "월세"

DAILY_HOUR_KST = int(os.getenv("DAILY_HOUR_KST", "8"))
DAILY_MINUTE_KST = int(os.getenv("DAILY_MINUTE_KST", "0"))

# 스크래퍼 — 빌라(VL) + 오피스텔(OF) 두 카테고리
ZIGBANG_LIST_URLS = {
    "villa": "https://apis.zigbang.com/v2/items/villa",
    "officetel": "https://apis.zigbang.com/v2/items/officetel",
}
ZIGBANG_DETAIL_URL = "https://apis.zigbang.com/v3/items/{item_id}"
ZIGBANG_VILLA_WEB_URL = "https://www.zigbang.com/home/villa/items/{item_id}"
ZIGBANG_OFFICETEL_WEB_URL = "https://www.zigbang.com/home/officetel/items/{item_id}"
DETAIL_CONCURRENCY = int(os.getenv("DETAIL_CONCURRENCY", "5"))
DETAIL_DELAY_MS = int(os.getenv("DETAIL_DELAY_MS", "150"))
