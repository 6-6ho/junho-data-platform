import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Gemini (콘텐츠 아이디어 합성)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# 텔레그램 발송
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("MARKETING_CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "")

# 매일 생성 시각 (KST) — 기술 브리핑(06:30) 다음
DAILY_HOUR_KST = int(os.getenv("DAILY_HOUR_KST", "7"))
DAILY_MINUTE_KST = int(os.getenv("DAILY_MINUTE_KST", "0"))

TOP_TRENDS = int(os.getenv("TOP_TRENDS", "8"))
TOP_PH = int(os.getenv("TOP_PH", "6"))
TOP_HN = int(os.getenv("TOP_HN", "6"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# 소스 (전부 무료·무인증)
GOOGLE_TRENDS_KR_RSS = "https://trends.google.com/trending/rss?geo=KR"
PRODUCTHUNT_RSS = "https://www.producthunt.com/feed"
HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=12"
HTTP_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 콘텐츠 아이디어 합성 대상 — 우리 앱 도메인
APPS = [
    "사주댕냥 (반려동물 사주·운세)",
    "첫이름 (아기 작명)",
    "로또풀이 (로또 번호 추천)",
]
