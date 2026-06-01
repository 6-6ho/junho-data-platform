import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# OAuth (MCP) — same pattern as rag-server.
OAUTH_ISSUER = os.getenv("OAUTH_ISSUER", "https://todo.6-6ho.com")
TODO_LOGIN_TOKEN = os.getenv("TODO_LOGIN_TOKEN") or None
OAUTH_STATE_DIR = os.getenv("OAUTH_STATE_DIR", "/data/oauth-state")

# 카테고리 프리셋: gen_projects.py 가 만든 프로젝트 이름 목록 (없으면 fallback)
PROJECTS_FILE = os.getenv("TODO_PROJECTS_FILE", "/data/projects.json")

STATUSES = ("todo", "doing", "done")
PRIORITIES = ("high", "med", "low")
