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

# 참고용 우리 앱 (인사이트 합성 시 참고만, 주 타겟은 20-30대 여성)
APPS = [
    "사주댕냥 (반려동물 사주·운세)",
    "첫이름 (아기 작명)",
    "로또풀이 (로또 번호 추천)",
]

# 네이버 데이터랩 (검색어 트렌드) — 20-30대 여성 관심사 추이
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
DATALAB_GENDER = os.getenv("DATALAB_GENDER", "f")   # f=여성
DATALAB_AGES = ["3", "4", "5", "6"]                  # 19~39세
# 추적 관심사 (요청당 5개 제한 → 배치). 대표 키워드 묶음.
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
