import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from datetime import datetime, timedelta, timezone

import config
import auth
import queries
import export as excel_export
import db

_DIR = Path(__file__).resolve().parent

_TZ_UTC8 = timezone(timedelta(hours=8))


def _utc_to_utc8(dt: datetime | None) -> datetime | None:
    """Convert a UTC datetime to UTC+8."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ_UTC8)


def _format_utc8(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a UTC datetime as UTC+8 string."""
    if dt is None:
        return ""
    return _utc_to_utc8(dt).strftime(fmt)


def _default_date_range(days: int = 7) -> tuple[str, str]:
    """Return (start, end) ISO date strings for the last N days (UTC+8)."""
    today = datetime.now(_TZ_UTC8).date()
    start = (today - timedelta(days=days)).isoformat()
    end = today.isoformat()
    return start, end


def _resolve_dates(start: str | None, end: str | None, default_days: int = 7) -> tuple[str | None, str | None]:
    """Resolve date params: None → default N days, 'all'/'' → no filter, else pass through.

    Date strings from the UI are in UTC+8. When filtering MongoDB (UTC),
    callers should convert with _date_str_to_utc_range.
    """
    if start is None and end is None:
        return _default_date_range(default_days)
    if start == "all" or end == "all" or start == "" or end == "":
        return None, None
    return start, end


def _date_str_to_utc_range(start: str | None, end: str | None) -> tuple[str | None, str | None]:
    """Convert UTC+8 date strings to UTC date strings for MongoDB queries.

    start → beginning of that day in UTC+8 → UTC equivalent
    end   → end of that day in UTC+8 → UTC equivalent
    Returns (start_utc_iso, end_utc_iso) or (None, None) if inputs are None.
    """
    if start is None and end is None:
        return None, None

    start_utc = None
    end_utc = None

    if start:
        start_dt = datetime.fromisoformat(start).replace(tzinfo=_TZ_UTC8)
        start_utc = start_dt.astimezone(timezone.utc).isoformat()

    if end:
        end_dt = datetime.fromisoformat(end).replace(
            hour=23, minute=59, second=59, tzinfo=_TZ_UTC8
        )
        end_utc = end_dt.astimezone(timezone.utc).isoformat()

    return start_utc, end_utc


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    db.close()


app = FastAPI(title="LibreChat Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_DIR / "templates")
templates.env.filters["format_utc8"] = _format_utc8
templates.env.filters["utc8"] = _utc_to_utc8


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if "ServerSelectionTimeoutError" in type(exc).__name__ or "ConnectionFailure" in type(exc).__name__:
        return templates.TemplateResponse(request=request, name="error.html", context={
            "title": "数据库连接失败",
            "message": f"无法连接到 MongoDB ({config.MONGO_URI})，请检查数据库是否已启动。",
        }, status_code=503)
    raise exc


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, password: str = Form(...)):
    if password != config.DASHBOARD_PASSWORD:
        return templates.TemplateResponse(
            request=request, name="login.html", context={"error": "密码错误"}
        )
    token = auth.create_token()
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        auth.COOKIE_NAME, token,
        httponly=True, max_age=config.JWT_EXPIRE_HOURS * 3600,
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# Auth middleware helper
# ---------------------------------------------------------------------------

def _check_auth(request: Request):
    token = auth.get_token_from_request(request)
    if not token or not auth.verify_token(token):
        return None
    return True


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    summary = await queries.get_summary()
    trend = await queries.get_token_trend(30)
    by_model = await queries.get_token_by_model()
    top_users = await queries.get_top_users(10)

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "summary": summary,
        "trend": trend,
        "by_model": by_model,
        "top_users": top_users,
    })


# ---------------------------------------------------------------------------
# Token reconciliation
# ---------------------------------------------------------------------------

@app.get("/tokens", response_class=HTMLResponse)
async def token_page(
    request: Request,
    start: str = Query(None),
    end: str = Query(None),
    page: int = Query(1, ge=1),
    tab: str = Query("user"),
):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    start, end = _resolve_dates(start, end)
    q_start, q_end = _date_str_to_utc_range(start, end)
    by_user = await queries.get_token_by_user(q_start, q_end, page)
    by_model = await queries.get_token_by_model_detail(q_start, q_end)

    return templates.TemplateResponse(request=request, name="tokens.html", context={
        "by_user": by_user,
        "by_model": by_model,
        "start": start,
        "end": end,
        "tab": tab,
    })


# HTMX partial: token table
@app.get("/tokens/table", response_class=HTMLResponse)
async def token_table_partial(
    request: Request,
    start: str = Query(None),
    end: str = Query(None),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)

    start, end = _resolve_dates(start, end)
    q_start, q_end = _date_str_to_utc_range(start, end)
    by_user = await queries.get_token_by_user(q_start, q_end, page)
    return templates.TemplateResponse(request=request, name="partials/token_table.html", context={
        "by_user": by_user,
        "start": start or "",
        "end": end or "",
    })


# ---------------------------------------------------------------------------
# Usage records (detailed transaction log)
# ---------------------------------------------------------------------------

@app.get("/usage", response_class=HTMLResponse)
async def usage_page(
    request: Request,
    start: str = Query(None),
    end: str = Query(None),
    user_id: str = Query(None),
    model: str = Query(None),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    start, end = _resolve_dates(start, end)
    q_start, q_end = _date_str_to_utc_range(start, end)
    records = await queries.get_usage_records(q_start, q_end, user_id, model, page)
    models = await queries.get_distinct_models()
    users = await queries.get_distinct_users_with_transactions()

    return templates.TemplateResponse(request=request, name="usage.html", context={
        "records": records,
        "models": models,
        "users": users,
        "start": start or "",
        "end": end or "",
        "selected_user": user_id or "",
        "selected_model": model or "",
    })


# HTMX partial: usage records table
@app.get("/usage/table", response_class=HTMLResponse)
async def usage_table_partial(
    request: Request,
    start: str = Query(None),
    end: str = Query(None),
    user_id: str = Query(None),
    model: str = Query(None),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)

    start, end = _resolve_dates(start, end)
    q_start, q_end = _date_str_to_utc_range(start, end)
    records = await queries.get_usage_records(q_start, q_end, user_id, model, page)
    return templates.TemplateResponse(request=request, name="partials/usage_table.html", context={
        "records": records,
        "start": start or "",
        "end": end or "",
        "selected_user": user_id or "",
        "selected_model": model or "",
    })


# ---------------------------------------------------------------------------
# User sessions
# ---------------------------------------------------------------------------

@app.get("/sessions", response_class=HTMLResponse)
async def sessions_page(
    request: Request,
    search: str = Query(""),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    user_list = await queries.get_user_list(search, page)
    return templates.TemplateResponse(request=request, name="sessions.html", context={
        "user_list": user_list,
        "search": search,
    })


# HTMX partial: user list
@app.get("/sessions/users", response_class=HTMLResponse)
async def sessions_users_partial(
    request: Request,
    search: str = Query(""),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)

    user_list = await queries.get_user_list(search, page)
    return templates.TemplateResponse(request=request, name="partials/user_list.html", context={
        "user_list": user_list,
        "search": search,
    })


# HTMX partial: conversation list for a user
@app.get("/sessions/conversations", response_class=HTMLResponse)
async def conversations_partial(
    request: Request,
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)

    convos = await queries.get_user_conversations(user_id, page)
    return templates.TemplateResponse(request=request, name="partials/conversation_list.html", context={
        "convos": convos,
        "user_id": user_id,
    })


# HTMX partial: message list for a conversation
@app.get("/sessions/messages", response_class=HTMLResponse)
async def messages_partial(
    request: Request,
    conversation_id: str = Query(...),
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
):
    if not _check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)

    messages = await queries.get_conversation_messages(conversation_id, user_id, page)
    return templates.TemplateResponse(request=request, name="partials/message_list.html", context={
        "messages": messages,
        "conversation_id": conversation_id,
        "user_id": user_id,
    })


# ---------------------------------------------------------------------------
# Excel exports
# ---------------------------------------------------------------------------

@app.get("/export/transactions")
async def export_transactions(
    request: Request,
    start: str = Query(None),
    end: str = Query(None),
):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    start, end = _resolve_dates(start, end)
    q_start, q_end = _date_str_to_utc_range(start, end)
    transactions = await queries.get_transactions_for_export(q_start, q_end)
    buf = excel_export.export_transactions(transactions)
    filename = f"token_reconciliation_{start or 'all'}_{end or 'all'}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/messages")
async def export_messages(
    request: Request,
    conversation_id: str = Query(...),
    user_id: str = Query(...),
):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    messages = await queries.get_messages_for_export(conversation_id, user_id)
    buf = excel_export.export_messages(messages)
    filename = f"messages_{conversation_id[:16]}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/usage")
async def export_usage(
    request: Request,
    start: str = Query(None),
    end: str = Query(None),
    user_id: str = Query(None),
    model: str = Query(None),
):
    if not _check_auth(request):
        return RedirectResponse("/login", status_code=302)

    start, end = _resolve_dates(start, end)
    q_start, q_end = _date_str_to_utc_range(start, end)
    records = await queries.get_usage_records_for_export(q_start, q_end, user_id, model)
    buf = excel_export.export_usage_records(records)
    filename = f"usage_records_{start or 'all'}_{end or 'all'}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, str(_DIR))
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
