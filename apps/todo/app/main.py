"""팀 칸반 보드 — 웹 전용 (MCP 제거됨).

라우트:
- GET  /            React(Vite) 빌드 서빙
- GET  /health      헬스체크
- GET  /robots.txt  noindex
- GET  /api/board   카드 배열 + members/projects seed + rev
- PUT  /api/board   카드 배열 통째 저장. 낙관적 잠금(base_rev) — 충돌 시 409 + 최신본

`python -m app.main` → uvicorn 으로 8000 포트 서빙.
"""
from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route

from . import queries

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("todo")

BASE_DIR = Path(__file__).parent
# React(Vite) 빌드 산출물. Dockerfile 멀티스테이지가 여기에 떨군다.
WEB_INDEX = BASE_DIR.parent / "web" / "dist" / "index.html"

# 팀 멤버 (담당자) — 보드 seed. (준호 기획 · 태규 개발 · 의열 홍보)
MEMBERS = [
    {"id": "junho",  "name": "준호", "initial": "준", "tone": "t1"},
    {"id": "taegyu", "name": "태규", "initial": "태", "tone": "t2"},
    {"id": "uiyeol", "name": "의열", "initial": "의", "tone": "t3"},
]


# 프로젝트 목록 (고정 seed). 카드 issue-key 는 key, 드롭다운 라벨은 한글.
# createTask 기본값은 'OPS'(공통/운영).
PROJECTS = [
    {"key": "OPS",    "label": "공통/운영"},
    {"key": "LOTTO",  "label": "로또풀이"},
    {"key": "SAJU",   "label": "사주댕냥"},
    {"key": "BAENAE", "label": "첫이름"},
]


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "todo"})


async def robots(request: Request) -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


async def index(request: Request) -> HTMLResponse:
    try:
        html = WEB_INDEX.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>칸반 빌드 없음</h1><p>web/dist/index.html 이 없습니다 (Dockerfile 빌드 단계 확인).</p>",
            status_code=503,
        )
    return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow"})


async def board(request: Request) -> JSONResponse:
    if request.method == "GET":
        b = await queries.get_board()
        projects = await queries.get_projects() or PROJECTS
        return JSONResponse({
            "tasks": b["tasks"],
            "rev": b["rev"],
            "members": MEMBERS,
            "projects": projects,
        })

    # PUT — 카드 배열 통째 저장 (낙관적 잠금)
    body = await request.json()
    tasks = body.get("tasks")
    if not isinstance(tasks, list):
        return JSONResponse({"error": "tasks must be an array"}, status_code=400)
    base_rev = body.get("base_rev")
    if not isinstance(base_rev, int):
        return JSONResponse({"error": "base_rev (int) required"}, status_code=400)
    result = await queries.save_board(tasks, base_rev, updated_by=(body.get("by") or None))
    if result is None:
        # 그 사이 다른 사람이 저장 → 최신본 + rev 동봉해 409
        fresh = await queries.get_board()
        return JSONResponse(
            {"error": "conflict", "rev": fresh["rev"], "tasks": fresh["tasks"]},
            status_code=409,
        )
    return JSONResponse({"ok": True, "rev": result["rev"], "count": len(tasks)})


async def goals(request: Request) -> JSONResponse:
    """그 달의 목표(자유 메모). GET ?month=YYYY-MM → {month,text}. PUT {month,text,by}."""
    if request.method == "GET":
        month = request.query_params.get("month", "").strip()
        if not month:
            return JSONResponse({"error": "month required"}, status_code=400)
        return JSONResponse({"month": month, "text": await queries.get_goal(month)})

    body = await request.json()
    month = (body.get("month") or "").strip()
    if not month:
        return JSONResponse({"error": "month required"}, status_code=400)
    text = body.get("text") or ""
    if not isinstance(text, str):
        return JSONResponse({"error": "text must be a string"}, status_code=400)
    await queries.set_goal(month, text[:5000], updated_by=(body.get("by") or None))
    return JSONResponse({"ok": True})


async def projects_route(request: Request) -> JSONResponse:
    """프로젝트 목록(사용자 관리). GET → {projects}. PUT {projects:[{key,label}], by} 전체 교체."""
    if request.method == "GET":
        return JSONResponse({"projects": (await queries.get_projects()) or PROJECTS})

    body = await request.json()
    raw = body.get("projects")
    if not isinstance(raw, list):
        return JSONResponse({"error": "projects must be an array"}, status_code=400)
    clean: list[dict] = []
    seen: set[str] = set()
    for p in raw:
        if not isinstance(p, dict):
            continue
        key = str(p.get("key") or "").strip().upper()
        label = str(p.get("label") or "").strip() or key
        if not key or key in seen:
            continue
        seen.add(key)
        clean.append({"key": key, "label": label})
    if not clean:
        return JSONResponse({"error": "at least one project required"}, status_code=400)
    await queries.set_projects(clean, updated_by=(body.get("by") or None))
    return JSONResponse({"ok": True, "projects": clean})


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/robots.txt", robots, methods=["GET"]),
    Route("/", index, methods=["GET"]),
    Route("/api/board", board, methods=["GET", "PUT"]),
    Route("/api/goals", goals, methods=["GET", "PUT"]),
    Route("/api/projects", projects_route, methods=["GET", "PUT"]),
]

app = Starlette(routes=routes)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
