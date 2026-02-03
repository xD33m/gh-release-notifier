from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from app import database, github_client, scheduler
from app.config import config, reload_config
from app.notifications import telegram, discord

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await database.init_db()
    await scheduler.initial_sync()
    scheduler.start_scheduler()
    yield
    # Shutdown
    scheduler.stop_scheduler()

app = FastAPI(title="GitHub Release Notifier", lifespan=lifespan)

# Setup templates and static files
templates_path = Path(__file__).parent / "templates"
static_path = Path(__file__).parent.parent / "static"

templates = Jinja2Templates(directory=str(templates_path))

if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, tag: Optional[int] = Query(None)):
    """Main dashboard page."""
    repos = await database.get_repositories(tag_id=tag)
    releases = await database.get_releases(limit=50, tag_id=tag)
    tags = await database.get_tags()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "repos": repos,
        "releases": releases,
        "tags": tags,
        "selected_tag": tag,
        "config": config
    })

@app.post("/repos/add")
async def add_repository(repo: str = Form(...), tag_id: Optional[int] = Form(None)):
    """Add a new repository to track."""
    repo = repo.strip()
    
    if '/' not in repo:
        raise HTTPException(status_code=400, detail="Invalid repository format. Use owner/repo")
    
    owner, name = repo.split('/', 1)
    
    # Validate repository exists
    if not await github_client.validate_repository(owner, name):
        raise HTTPException(status_code=404, detail=f"Repository {repo} not found or not accessible")
    
    result = await database.add_repository(owner, name, tag_id if tag_id else None)
    if result is None:
        raise HTTPException(status_code=400, detail="Repository already tracked")
    
    # Fetch initial releases
    repo_id = result
    releases = await github_client.get_releases(owner, name, per_page=10)
    for release_data in releases:
        release_id, is_new = await database.add_release(repo_id, release_data)
        if is_new and release_id:
            await database.mark_release_notified(release_id)
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/repos/remove")
async def remove_repository(repo: str = Form(...)):
    """Remove a repository from tracking."""
    if '/' not in repo:
        raise HTTPException(status_code=400, detail="Invalid repository format")
    
    owner, name = repo.split('/', 1)
    await database.remove_repository(owner, name)
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/check-now")
async def check_now():
    """Manually trigger a release check."""
    await scheduler.check_releases()
    return RedirectResponse(url="/", status_code=303)

@app.post("/test/telegram")
async def test_telegram_notification():
    """Test Telegram notification."""
    # Reload config first to ensure we have latest values
    reload_config()
    success, message = await telegram.test_telegram()
    if success:
        return {"status": "success", "message": message}
    raise HTTPException(status_code=400, detail=message)

@app.post("/test/discord")
async def test_discord_notification():
    """Test Discord notification."""
    reload_config()
    success, message = await discord.test_discord()
    if success:
        return {"status": "success", "message": message}
    raise HTTPException(status_code=400, detail=message)

@app.get("/api/debug-config")
async def debug_config():
    """Debug endpoint to check loaded config."""
    return {
        "telegram": {
            "enabled": config.notifications.telegram.enabled,
            "bot_token_set": bool(config.notifications.telegram.bot_token),
            "bot_token_preview": config.notifications.telegram.bot_token[:10] + "..." if config.notifications.telegram.bot_token else None,
            "chat_id": config.notifications.telegram.chat_id,
        },
        "discord": {
            "enabled": config.notifications.discord.enabled,
            "webhook_url_set": bool(config.notifications.discord.webhook_url),
        },
        "check_interval": config.check_interval,
    }

@app.get("/api/releases")
async def get_releases(limit: int = 50, tag_id: Optional[int] = None):
    """Get recent releases as JSON."""
    releases = await database.get_releases(limit=limit, tag_id=tag_id)
    return releases

@app.get("/api/repos")
async def get_repos(tag_id: Optional[int] = None):
    """Get tracked repositories as JSON."""
    repos = await database.get_repositories(tag_id=tag_id)
    return repos

# ============ Tags/Categories ============

@app.post("/tags/add")
async def add_tag(name: str = Form(...), color: str = Form("#8b5cf6")):
    """Add a new tag/category."""
    if not name.strip():
        raise HTTPException(status_code=400, detail="Tag name is required")
    
    result = await database.add_tag(name.strip(), color)
    if result is None:
        raise HTTPException(status_code=400, detail="Tag already exists")
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/tags/{tag_id}/update")
async def update_tag(
    tag_id: int,
    name: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    notifications_enabled: Optional[str] = Form(None)
):
    """Update a tag's properties."""
    notif = None
    if notifications_enabled is not None:
        notif = notifications_enabled == "on" or notifications_enabled == "true" or notifications_enabled == "1"
    
    await database.update_tag(tag_id, name=name, color=color, notifications_enabled=notif)
    return RedirectResponse(url="/", status_code=303)

@app.post("/tags/{tag_id}/toggle-notifications")
async def toggle_tag_notifications(tag_id: int):
    """Toggle notifications for a tag."""
    tag = await database.get_tag_by_id(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    new_state = not tag['notifications_enabled']
    await database.update_tag(tag_id, notifications_enabled=new_state)
    return {"status": "success", "notifications_enabled": new_state}

@app.post("/tags/{tag_id}/delete")
async def delete_tag(tag_id: int):
    """Delete a tag."""
    await database.delete_tag(tag_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/repos/set-tag")
async def set_repo_tag(repo: str = Form(...), tag_id: Optional[int] = Form(None)):
    """Assign a tag to a repository."""
    if '/' not in repo:
        raise HTTPException(status_code=400, detail="Invalid repository format")
    
    owner, name = repo.split('/', 1)
    # Convert empty string or 0 to None
    tag_id_value = tag_id if tag_id and tag_id > 0 else None
    await database.set_repo_tag(owner, name, tag_id_value)
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/tags")
async def get_tags():
    """Get all tags as JSON."""
    tags = await database.get_tags()
    return tags

@app.post("/api/reload-config")
async def api_reload_config():
    """Hot reload configuration from files."""
    new_config = reload_config()
    return {
        "status": "success",
        "message": "Configuration reloaded",
        "config": {
            "check_interval": new_config.check_interval,
            "telegram_enabled": new_config.notifications.telegram.enabled,
            "telegram_configured": bool(new_config.notifications.telegram.bot_token and new_config.notifications.telegram.chat_id),
            "discord_enabled": new_config.notifications.discord.enabled,
            "discord_configured": bool(new_config.notifications.discord.webhook_url),
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
