import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 프로젝트 목록 파일 (gen_projects.py + cron 갱신). 없으면 main.py fallback.
PROJECTS_FILE = os.getenv("TODO_PROJECTS_FILE", "/data/projects.json")
