import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config, db, queries
from .scraper import run_scrape

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("realestate-monitor")

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
        run_scrape,
        CronTrigger(hour=config.DAILY_HOUR_KST, minute=config.DAILY_MINUTE_KST),
        id="daily_scrape",
        replace_existing=True,
    )
    scheduler.start()
    log.info("scheduler started: daily at %02d:%02d KST", config.DAILY_HOUR_KST, config.DAILY_MINUTE_KST)
    yield
    scheduler.shutdown(wait=False)
    await db.close_pool()


app = FastAPI(lifespan=lifespan)

if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
async def index():
    days = await queries.listings_grouped_by_day(days=14)
    last_run = await queries.latest_run()
    total = await queries.total_active()
    districts = await queries.district_counts()
    template = TPL.get_template("index.html")
    html = template.render(
        days=days,
        last_run=last_run,
        total=total,
        districts=districts,
        deposit_max=config.DEPOSIT_MAX,
        total_rent_min=config.TOTAL_RENT_MIN,
        total_rent_max=config.TOTAL_RENT_MAX,
    )
    return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow"})


@app.post("/admin/scrape")
async def admin_trigger(request: Request):
    """Manual trigger. Protected by ADMIN_TOKEN env var."""
    token = os.getenv("ADMIN_TOKEN", "")
    if not token:
        raise HTTPException(503, "ADMIN_TOKEN not configured")
    if request.headers.get("X-Admin-Token") != token:
        raise HTTPException(401, "unauthorized")
    result = await run_scrape()
    return JSONResponse(result)


@app.get("/robots.txt")
async def robots():
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")
