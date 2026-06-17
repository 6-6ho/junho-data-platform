import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config, db, queries
from .brief import run_brief

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("marketing-brief")

BASE_DIR = Path(__file__).parent
TPL = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)
scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_schema()
    scheduler.add_job(
        run_brief,
        CronTrigger(hour=config.DAILY_HOUR_KST, minute=config.DAILY_MINUTE_KST),
        id="daily_marketing_brief",
        replace_existing=True,
    )
    scheduler.start()
    log.info("scheduler started: daily at %02d:%02d KST", config.DAILY_HOUR_KST, config.DAILY_MINUTE_KST)
    yield
    scheduler.shutdown(wait=False)
    await db.close_pool()


app = FastAPI(lifespan=lifespan)


async def _page(brief: dict | None) -> HTMLResponse:
    dates = await queries.recent_dates(30)
    html = TPL.get_template("index.html").render(
        brief=brief,
        dates=dates,
        hh=config.DAILY_HOUR_KST,
        mm=config.DAILY_MINUTE_KST,
        has_key=bool(config.GEMINI_API_KEY),
    )
    return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow"})


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
async def index():
    return await _page(await queries.latest_brief())


@app.get("/d/{d}", response_class=HTMLResponse)
async def by_date(d: str):
    try:
        dd = date.fromisoformat(d)
    except ValueError:
        raise HTTPException(400, "bad date format (YYYY-MM-DD)")
    brief = await queries.brief_by_date(dd)
    if not brief:
        raise HTTPException(404, "해당 날짜 브리핑 없음")
    return await _page(brief)


@app.post("/admin/run")
async def admin_run(request: Request):
    if not config.ADMIN_TOKEN:
        raise HTTPException(503, "ADMIN_TOKEN not configured")
    if request.headers.get("X-Admin-Token") != config.ADMIN_TOKEN:
        raise HTTPException(401, "unauthorized")
    return JSONResponse(await run_brief())


@app.get("/robots.txt")
async def robots():
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")
