import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Gemini (요약 + 인사이트)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# 텔레그램
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 매일 생성 시각 (KST)
DAILY_HOUR_KST = int(os.getenv("DAILY_HOUR_KST", "6"))
DAILY_MINUTE_KST = int(os.getenv("DAILY_MINUTE_KST", "30"))

TOP_N = int(os.getenv("TOP_N", "5"))          # GeekNews / GitHub
TOP_TRENDS = int(os.getenv("TOP_TRENDS", "8"))
TOP_PH = int(os.getenv("TOP_PH", "6"))
TOP_HN = int(os.getenv("TOP_HN", "6"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# 소스 (전부 무료·무인증)
GEEKNEWS_BASE = "https://news.hada.io"
GEEKNEWS_MAX_PAGES = int(os.getenv("GEEKNEWS_MAX_PAGES", "4"))
GITHUB_TRENDING_URL = os.getenv("GITHUB_TRENDING_URL", "https://github.com/trending/python?since=daily")
GOOGLE_TRENDS_KR_RSS = "https://trends.google.com/trending/rss?geo=KR"
PRODUCTHUNT_RSS = "https://www.producthunt.com/feed"
HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=12"
HTTP_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 마케팅 읽을거리 — 앱/마케팅 실무 매체 RSS (최신 기사)
MARKETING_FEEDS = [
    {"source": "모비인사이드", "url": "https://www.mobiinside.co.kr/feed/"},
    {"source": "디지털인사이트", "url": "https://ditoday.com/feed/"},
]
TOP_READS = int(os.getenv("TOP_READS", "6"))

# 인사이트 합성 참고 — 우리 앱
APPS = [
    "사주댕냥 (반려동물 사주·운세)",
    "첫이름 (아기 작명)",
    "로또풀이 (로또 번호 추천)",
]

# 네이버 데이터랩 — '돈 쓰는 세대' 세그먼트별 관심사 추이
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
# ages: 5=30~34 6=35~39 7=40~44 8=45~49 9=50~54 10=55~59. gender ""=전체
SEGMENTS = [
    {"label": "30·40대 여성", "gender": "f", "ages": ["5", "6", "7", "8"]},
    {"label": "30·40대 남성", "gender": "m", "ages": ["5", "6", "7", "8"]},
    {"label": "40·50대", "gender": "", "ages": ["7", "8", "9", "10"]},
]
INTEREST_GROUPS = [
    {"groupName": "운세·타로", "keywords": ["운세", "타로", "사주"]},
    {"groupName": "다이어트", "keywords": ["다이어트", "운동"]},
    {"groupName": "뷰티", "keywords": ["화장품", "뷰티"]},
    {"groupName": "여행", "keywords": ["여행", "호텔"]},
    {"groupName": "연애·MBTI", "keywords": ["연애", "MBTI"]},
    {"groupName": "패션", "keywords": ["패션", "원피스"]},
    {"groupName": "재테크", "keywords": ["재테크", "적금"]},
    {"groupName": "자기계발", "keywords": ["자기계발", "독서"]},
    {"groupName": "결혼·육아", "keywords": ["결혼", "육아"]},
    {"groupName": "맛집·카페", "keywords": ["맛집", "카페"]},
]
