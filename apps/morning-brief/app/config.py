import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Gemini (요약 엔진)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# 매일 생성 시각 (KST)
DAILY_HOUR_KST = int(os.getenv("DAILY_HOUR_KST", "6"))
DAILY_MINUTE_KST = int(os.getenv("DAILY_MINUTE_KST", "30"))

TOP_N = int(os.getenv("TOP_N", "5"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# 소스
GEEKNEWS_BASE = "https://news.hada.io"
GITHUB_TRENDING_URL = os.getenv(
    "GITHUB_TRENDING_URL", "https://github.com/trending/python?since=daily"
)
HTTP_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
GEEKNEWS_MAX_PAGES = int(os.getenv("GEEKNEWS_MAX_PAGES", "4"))
