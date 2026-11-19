"""
FastAPI Web Application Backend for Autonomous Job Scraper Agent.
Provides REST APIs, Server-Sent Events (SSE) live streaming, and static UI serving.
"""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config.settings import settings
from config.logging_config import get_logger
from utils.state_manager import state_manager
from utils.excel_exporter import export_to_excel
from scrapers.board_registry import BOARD_METADATA_REGISTRY, list_all_boards
from discovery.per_job_orchestrator import run_per_job_pipeline

logger = get_logger("WebApp")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time Autonomous Multi-Platform Job Scraper & Direct ATS Enrichment Agent",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import hmac
import secrets
from typing import Set
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# Global background task and event broadcast queue
active_scrape_task: Optional[asyncio.Task] = None
sse_queues: List[asyncio.Queue] = []
VALID_TOKENS: Set[str] = set()


def create_session_token() -> str:
    """Generates a secure random session token."""
    tok = secrets.token_hex(24)
    VALID_TOKENS.add(tok)
    return tok


def get_token_from_request(request: Request) -> Optional[str]:
    """Extracts authentication token from header, cookie, or query parameter."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        elif len(parts) == 1:
            return parts[0].strip()

    x_key = request.headers.get("X-Auth-Key")
    if x_key:
        return x_key.strip()

    cookie_token = request.cookies.get("auth_session")
    if cookie_token:
        return cookie_token.strip()

    query_token = request.query_params.get("token") or request.query_params.get("key")
    if query_token:
        return query_token.strip()

    return None


def is_valid_token(token: Optional[str]) -> bool:
    """Validates session token or master AUTH_KEY."""
    if not token:
        return False
    tok = token.strip()
    if tok in VALID_TOKENS:
        return True
    if hmac.compare_digest(tok, settings.AUTH_KEY.strip()):
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforces authentication across all /api/ endpoints."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Allow static files, root HTML, login, and verify status
        if not path.startswith("/api/") or path in ["/api/auth/login", "/api/auth/verify"]:
            return await call_next(request)

        token = get_token_from_request(request)
        if not is_valid_token(token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized. Please authenticate with the security key."},
            )
        return await call_next(request)


app.add_middleware(AuthMiddleware)


class LoginRequest(BaseModel):
    """Payload for security key authentication."""

    key: str = Field(..., description="Authorization key required to access the agent")


class StartScrapeRequest(BaseModel):
    """Payload for starting a new scraping session."""

    keyword: str = Field(default="AI Engineer", description="Target job title or keyword")
    location: str = Field(default="Remote", description="Target location filter")
    boards: Optional[List[str]] = Field(default=None, description="List of target board names")
    max_jobs_per_board: int = Field(default=20, ge=1, le=50, description="Max jobs to scrape per platform")
    resume: bool = Field(default=False, description="Whether to resume from existing state on disk")


def broadcast_sse(event_type: str, data: Dict[str, Any]) -> None:
    """Pushes an SSE event message to all connected client queues."""
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    for q in list(sse_queues):
        try:
            q.put_nowait(msg)
        except Exception:
            pass


# Hook StateManager events into the SSE broadcaster
def state_event_handler(event_type: str, data: Dict[str, Any]) -> None:
    broadcast_sse(event_type, data)

state_manager.add_listener(state_event_handler)


# ==============================================================================
# Authentication Endpoints
# ==============================================================================

@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response) -> Dict[str, Any]:
    """Authenticates the client against the configured security AUTH_KEY."""
    user_key = req.key.strip() if req.key else ""
    if not hmac.compare_digest(user_key, settings.AUTH_KEY.strip()):
        logger.warning("🔒 Unauthorized login attempt with invalid security key.")
        raise HTTPException(status_code=401, detail="Invalid authorization key.")

    token = create_session_token()
    response.set_cookie(
        key="auth_session",
        value=token,
        httponly=False,
        samesite="lax",
        max_age=86400 * 7,  # 7-day session
    )
    logger.info("🔑 Client successfully authenticated via security gateway.")
    return {"status": "authenticated", "token": token}


@app.get("/api/auth/verify")
async def verify_auth_status(request: Request) -> Dict[str, Any]:
    """Checks whether the client possesses a valid session token."""
    token = get_token_from_request(request)
    return {"authenticated": is_valid_token(token)}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response) -> Dict[str, Any]:
    """Logs out the active session."""
    token = get_token_from_request(request)
    if token and token in VALID_TOKENS:
        VALID_TOKENS.remove(token)
    response.delete_cookie("auth_session")
    return {"status": "logged_out"}


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/api/boards")
async def get_boards() -> Dict[str, Any]:
    """Returns all 55+ supported job boards grouped by category with active status."""
    boards = list_all_boards()
    categories: Dict[str, List[Dict[str, Any]]] = {}

    summary = state_manager.get_summary()
    completed_boards = set(summary.get("completed_boards", []))
    current_board = summary.get("current_board")
    board_stats = summary.get("board_stats", {})

    for b in boards:
        cat = b["category"]
        if cat not in categories:
            categories[cat] = []

        b_name = b["name"]
        stats = board_stats.get(b_name, {})
        status = stats.get("status", "pending")
        if b_name in completed_boards:
            status = "completed"
        elif b_name == current_board:
            status = "in_progress"

        categories[cat].append({
            **b,
            "status": status,
            "jobs_found": stats.get("jobs_found", 0),
            "error": stats.get("error"),
        })

    return {
        "total_boards": len(boards),
        "categorized_boards": categories,
        "raw_boards": boards,
    }


@app.get("/api/scrape/state")
async def get_state() -> Dict[str, Any]:
    """Returns current active scrape state summary and extracted job leads."""
    if not state_manager.state:
        state_manager.load_previous_state()

    summary = state_manager.get_summary()
    jobs = state_manager.state.extracted_jobs if state_manager.state else []

    # Calculate metrics
    verified_direct_count = sum(1 for j in jobs if j.get("direct_apply_link"))
    career_pages_count = sum(1 for j in jobs if j.get("career_page_url"))
    company_domains_count = sum(1 for j in jobs if j.get("company_url"))

    return {
        "summary": summary,
        "metrics": {
            "total_jobs": len(jobs),
            "verified_direct_links": verified_direct_count,
            "career_pages_found": career_pages_count,
            "company_domains_discovered": company_domains_count,
            "completed_boards": len(summary.get("completed_boards", [])),
            "total_boards": len(summary.get("pending_boards", [])) + len(summary.get("completed_boards", [])),
        },
        "jobs": jobs,
    }


@app.post("/api/scrape/start")
async def start_scrape(req: StartScrapeRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Initiates a background multi-platform scraping and direct ATS enrichment session."""
    global active_scrape_task

    if active_scrape_task and not active_scrape_task.done():
        raise HTTPException(status_code=400, detail="A scraping session is already running.")

    boards = req.boards or settings.TARGET_JOB_BOARDS

    if not req.resume:
        state_manager.initialize_state(
            keyword=req.keyword,
            location=req.location,
            target_boards=boards,
            force_reset=True,
        )
        broadcast_sse("session_cleared", {"keyword": req.keyword, "location": req.location})

    async def _run_job():
        try:
            logger.info(f"🌐 [Web UI] Starting scrape for '{req.keyword}' on {len(boards)} boards...")
            broadcast_sse("log", {"message": f"🚀 Starting scraper for keyword '{req.keyword}'..."})
            await run_per_job_pipeline(
                keyword=req.keyword,
                location=req.location,
                target_boards=boards,
                max_jobs_per_board=req.max_jobs_per_board,
                resume=req.resume,
            )
            broadcast_sse("scrape_completed", {"message": "All target boards completed!"})
        except asyncio.CancelledError:
            logger.info("Scraping task was paused/cancelled.")
            broadcast_sse("log", {"message": "⏸️ Scraping paused."})
        except Exception as e:
            logger.error(f"Background scrape error: {e}", exc_info=True)
            broadcast_sse("scrape_error", {"error": str(e)})

    active_scrape_task = asyncio.create_task(_run_job())

    return {
        "status": "started",
        "keyword": req.keyword,
        "location": req.location,
        "boards_count": len(boards),
        "max_jobs_per_board": req.max_jobs_per_board,
    }


@app.post("/api/scrape/pause")
async def pause_scrape() -> Dict[str, Any]:
    """Pauses the current scraping session."""
    global active_scrape_task
    if active_scrape_task and not active_scrape_task.done():
        active_scrape_task.cancel()
        active_scrape_task = None
        if state_manager.state:
            state_manager.state.status = "paused"
        broadcast_sse("session_paused", {"message": "Scraper paused."})
        return {"status": "paused"}
    return {"status": "not_running"}


@app.post("/api/scrape/reset")
async def reset_scrape() -> Dict[str, Any]:
    """Resets the active scrape session and clears disk state."""
    global active_scrape_task
    if active_scrape_task and not active_scrape_task.done():
        active_scrape_task.cancel()
        active_scrape_task = None

    state_manager.clear_state()
    broadcast_sse("session_cleared", {})
    return {"status": "cleared"}


@app.get("/api/scrape/stream")
async def sse_stream() -> StreamingResponse:
    """Server-Sent Events (SSE) streaming endpoint for real-time progress and logs."""
    client_queue: asyncio.Queue = asyncio.Queue()
    sse_queues.append(client_queue)

    async def event_generator():
        try:
            # Send initial connection event
            yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
            while True:
                data = await client_queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            if client_queue in sse_queues:
                sse_queues.remove(client_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/scrape/export")
async def export_excel() -> FileResponse:
    """Generates and downloads the formatted Excel workbook with clickable links."""
    out_path = export_to_excel(output_filename=settings.DEFAULT_EXCEL_FILENAME)
    if not out_path.exists():
        raise HTTPException(status_code=404, detail="No Excel export available.")

    return FileResponse(
        path=out_path,
        filename=out_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ==============================================================================
# Serve Static Web UI Assets
# ==============================================================================

static_path = settings.STATIC_DIR
static_path.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def serve_index() -> HTMLResponse:
    """Serves the main single-page web dashboard."""
    index_file = static_path / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Autonomous Job Scraper Web UI</h1><p>Dashboard UI loading...</p>")

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
