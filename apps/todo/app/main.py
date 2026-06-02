"""개인 할일 보드 — 웹 UI + 클로드용 MCP 를 한 FastMCP 앱에 얹는다.

- `@mcp.tool`      → 클로드가 쓰는 도구 (OAuth 게이트됨)
- `@mcp.custom_route` → 웹 UI(HTML) + JSON API (OAuth 안 탐, URL-only 공개)
- DB(todo 스키마)는 양쪽이 공유

`python -m app.main` → mcp.run(streamable-http) 로 8000 포트 서빙.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from . import config, queries
from .personal_auth import PersonalAuthProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("todo")

BASE_DIR = Path(__file__).parent
TPL = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)

# React(Vite singlefile) 빌드 산출물. Dockerfile 멀티스테이지가 여기에 떨군다.
WEB_INDEX = BASE_DIR.parent / "web" / "dist" / "index.html"

PRESET_CATEGORIES = ["trade", "shop", "realestate", "rag", "infra", "개인"]

# 공유 칸반 보드 seed — 서버가 프론트에 주입 (멤버=담당자, 프로젝트=카테고리).
MEMBERS = [
    {"id": "junho",  "name": "준호", "initial": "준", "tone": "t1"},
    {"id": "taegyu", "name": "태규", "initial": "태", "tone": "t2"},
    {"id": "uiyeol", "name": "의열", "initial": "의", "tone": "t3"},
]
PROJECTS = [
    {"key": "TRADE",      "label": "트레이딩 봇"},
    {"key": "REALESTATE", "label": "부동산 분석"},
    {"key": "RAG",        "label": "RAG 파이프라인"},
    {"key": "BAENAE",     "label": "배내"},
    {"key": "SAJU",       "label": "사주댕"},
    {"key": "INFRA",      "label": "인프라"},
    {"key": "ETL",        "label": "데이터 ETL"},
    {"key": "CRAWLER",    "label": "크롤러"},
    {"key": "DASH",       "label": "대시보드"},
    {"key": "ML",         "label": "ML"},
]


def load_projects() -> list[str]:
    """gen_projects.py 가 갱신하는 프로젝트 목록 파일을 읽어 카테고리 프리셋으로.
    파일이 없거나 깨졌으면 내장 fallback. 매 렌더마다 읽어 cron 갱신을 즉시 반영."""
    try:
        with open(config.PROJECTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        names = [str(x).strip() for x in data if str(x).strip()]
        if names:
            return names
    except Exception:
        pass
    return PRESET_CATEGORIES


def _json_for_html(obj) -> str:
    """JSON safe to embed inside a <script> tag."""
    return json.dumps(obj, ensure_ascii=False, default=str).replace("<", "\\u003c")


# --- OAuth provider (MCP only) ---
auth = PersonalAuthProvider(
    base_url=config.OAUTH_ISSUER,
    password=config.TODO_LOGIN_TOKEN,
    allowed_redirect_domains=["claude.ai", "claude.com", "localhost"],
    state_dir=config.OAUTH_STATE_DIR,
)

mcp = FastMCP(
    name="junho-todo",
    instructions=(
        "Junho 의 개인 할일 보드. 카테고리(프로젝트: trade/shop/realestate/rag/infra/개인 등)별로 "
        "할일을 적고 상태(todo/doing/done)를 추적한다. `list_tasks` 로 현황을 보고, `add_task` 로 추가, "
        "`set_task_status` 로 진행/완료 처리, `update_task` 로 필드 수정, `delete_task` 로 삭제한다."
    ),
    auth=auth,
)


# ============================ Web UI + JSON API ============================

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "todo"})


@mcp.custom_route("/robots.txt", methods=["GET"])
async def robots(request: Request) -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@mcp.custom_route("/", methods=["GET"])
async def index(request: Request) -> HTMLResponse:
    """React(Vite singlefile) 빌드 결과를 통째로 서빙. seed 는 /api/board 로 가져간다."""
    try:
        html = WEB_INDEX.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>칸반 빌드 없음</h1><p>web/dist/index.html 이 없습니다 (Dockerfile 빌드 단계 확인).</p>",
            status_code=503,
        )
    return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow"})


# ============================ 공유 칸반 보드 API ============================

@mcp.custom_route("/api/board", methods=["GET"])
async def api_board_get(request: Request) -> JSONResponse:
    """공유 보드 전체 + seed(멤버·프로젝트). 프론트가 부팅 시 1회 호출."""
    tasks = await queries.get_board()
    return JSONResponse({"tasks": tasks, "members": MEMBERS, "projects": PROJECTS})


@mcp.custom_route("/api/board", methods=["PUT"])
async def api_board_put(request: Request) -> JSONResponse:
    """카드 배열 전체를 통째 저장 (last-write-wins). 변경 발생 시 프론트가 디바운스 호출."""
    body = await request.json()
    tasks = body.get("tasks")
    if not isinstance(tasks, list):
        return JSONResponse({"error": "tasks must be an array"}, status_code=400)
    await queries.save_board(tasks, updated_by=(body.get("by") or None))
    return JSONResponse({"ok": True, "count": len(tasks)})


def _clean_status(s: str | None) -> str:
    return s if s in config.STATUSES else "todo"


def _clean_priority(p: str | None) -> str | None:
    return p if p in config.PRIORITIES else None


@mcp.custom_route("/api/add", methods=["POST"])
async def api_add(request: Request) -> JSONResponse:
    body = await request.json()
    title = (body.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    task = await queries.add_task(
        title=title[:500],
        category=(body.get("category") or "").strip() or None,
        due_date=body.get("due_date") or None,
        priority=_clean_priority(body.get("priority")),
        memo=(body.get("memo") or "").strip() or None,
        status=_clean_status(body.get("status")),
    )
    return JSONResponse(task)


@mcp.custom_route("/api/update", methods=["POST"])
async def api_update(request: Request) -> JSONResponse:
    body = await request.json()
    tid = body.get("id")
    if tid is None:
        return JSONResponse({"error": "id required"}, status_code=400)
    fields = {k: body[k] for k in ("title", "category", "due_date", "priority", "memo") if k in body}
    if "priority" in fields:
        fields["priority"] = _clean_priority(fields["priority"])
    task = await queries.update_task(int(tid), **fields)
    if not task:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(task)


@mcp.custom_route("/api/status", methods=["POST"])
async def api_status(request: Request) -> JSONResponse:
    body = await request.json()
    tid = body.get("id")
    if tid is None:
        return JSONResponse({"error": "id required"}, status_code=400)
    task = await queries.set_status(int(tid), _clean_status(body.get("status")))
    if not task:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(task)


@mcp.custom_route("/api/reorder", methods=["POST"])
async def api_reorder(request: Request) -> JSONResponse:
    body = await request.json()
    status = _clean_status(body.get("status"))
    ids = [int(x) for x in (body.get("ids") or [])]
    n = await queries.reorder(status, ids)
    return JSONResponse({"updated": n})


@mcp.custom_route("/api/delete", methods=["POST"])
async def api_delete(request: Request) -> JSONResponse:
    body = await request.json()
    tid = body.get("id")
    if tid is None:
        return JSONResponse({"error": "id required"}, status_code=400)
    ok = await queries.delete_task(int(tid))
    return JSONResponse({"ok": ok})


@mcp.custom_route("/api/clear-done", methods=["POST"])
async def api_clear_done(request: Request) -> JSONResponse:
    n = await queries.clear_done()
    return JSONResponse({"deleted": n})


# ============================ MCP tools (for Claude) ============================

@mcp.tool
async def list_tasks(status: str | None = None, category: str | None = None) -> str:
    """할일 목록을 조회한다.

    사용자가 "할일 뭐 있어?", "trade 쪽 뭐 남았어?", "지금 진행중인 거" 처럼 현황을 물으면 사용.

    Args:
        status: 'todo' | 'doing' | 'done' 중 하나로 필터. None 이면 전체.
        category: 프로젝트명으로 필터 (예: 'trade', '개인'). None 이면 전체.
    """
    s = status if status in config.STATUSES else None
    rows = await queries.list_tasks(status=s, category=category or None)
    return json.dumps(rows, ensure_ascii=False, default=str)


@mcp.tool
async def add_task(
    title: str,
    category: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    memo: str | None = None,
) -> str:
    """할일을 추가한다.

    사용자가 "이거 할일에 넣어줘", "trade 백테스트 추가" 처럼 요청하면 사용.

    Args:
        title: 할일 제목 (필수).
        category: 프로젝트/카테고리 (예: 'trade', 'shop', '개인'). 선택.
        due_date: 마감일 'YYYY-MM-DD'. 선택.
        priority: 'high' | 'med' | 'low'. 선택.
        memo: 상세 메모. 선택.
    """
    if not (title or "").strip():
        return json.dumps({"error": "title required"}, ensure_ascii=False)
    task = await queries.add_task(
        title=title.strip()[:500],
        category=(category or "").strip() or None,
        due_date=due_date or None,
        priority=priority if priority in config.PRIORITIES else None,
        memo=(memo or "").strip() or None,
    )
    return json.dumps(task, ensure_ascii=False, default=str)


@mcp.tool
async def update_task(
    id: int,
    title: str | None = None,
    category: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    memo: str | None = None,
) -> str:
    """기존 할일의 필드를 수정한다 (제목/카테고리/마감일/우선순위/메모). None 인 필드는 안 건드림."""
    fields = {}
    if title is not None:
        fields["title"] = title.strip()[:500]
    if category is not None:
        fields["category"] = category.strip()
    if due_date is not None:
        fields["due_date"] = due_date
    if priority is not None:
        fields["priority"] = priority if priority in config.PRIORITIES else None
    if memo is not None:
        fields["memo"] = memo
    task = await queries.update_task(int(id), **fields)
    if not task:
        return json.dumps({"error": "not found"}, ensure_ascii=False)
    return json.dumps(task, ensure_ascii=False, default=str)


@mcp.tool
async def set_task_status(id: int, status: str) -> str:
    """할일 상태를 바꾼다. status 는 'todo'(할일) | 'doing'(진행중) | 'done'(완료).

    완료 처리할 때 이 도구를 쓴다. 완료해도 삭제되지 않고 done 으로 보존된다.
    """
    if status not in config.STATUSES:
        return json.dumps({"error": "status must be todo|doing|done"}, ensure_ascii=False)
    task = await queries.set_status(int(id), status)
    if not task:
        return json.dumps({"error": "not found"}, ensure_ascii=False)
    return json.dumps(task, ensure_ascii=False, default=str)


@mcp.tool
async def delete_task(id: int) -> str:
    """할일을 영구 삭제한다. 완료 보관과 달리 되돌릴 수 없으니 사용자가 명시적으로 지울 때만 사용."""
    ok = await queries.delete_task(int(id))
    return json.dumps({"ok": ok}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
