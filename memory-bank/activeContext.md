# Active Context

## Current State

GitHub Release Notifier project is fully implemented with all requested features including expandable markdown release notes.

## What Was Built

A complete self-hosted application for tracking GitHub releases with notification support:

### Core Components

- **FastAPI web application** - Lightweight async Python backend
- **SQLite database** - Simple persistence, no external DB needed
- **APScheduler** - Background job for periodic release checks
- **Web UI** - Clean dark-themed dashboard for managing repos and viewing releases
- **Notifications** - Telegram and Discord webhook support
- **Tags/Categories** - Filter repos and releases, enable/disable notifications per tag

### Project Structure

```
release-notif/
├── app/
│   ├── main.py              # FastAPI entry point with tag endpoints
│   ├── config.py            # YAML + env var configuration
│   ├── database.py          # SQLite async operations with tags
│   ├── github_client.py     # GitHub API integration
│   ├── scheduler.py         # Background release checker (respects tag notifications)
│   ├── notifications/
│   │   ├── telegram.py      # Telegram bot notifications
│   │   └── discord.py       # Discord webhook notifications
│   └── templates/
│       └── index.html       # Web UI template with tag filtering
├── static/styles.css        # Dark theme styling with tag components
├── Dockerfile               # Multi-arch ready
├── docker-compose.yml       # With Traefik labels
├── config.yaml              # User configuration
└── requirements.txt         # Python dependencies
```

## Tags/Categories Feature

- Create custom tags with colors (e.g., "DevTools", "Infrastructure", "Frontend")
- Assign tags to repositories when adding or via edit
- Filter releases view by tag
- Enable/disable notifications per tag (toggle 🔔/🔕)
- Tags with notifications disabled won't send Telegram/Discord messages

## UI Enhancements

- **European date format**: DD.MM.YYYY HH:MM in tooltips
- **Relative time**: Shows "X minutes/hours/days ago" for releases
- **Subtle repo differentiation**: Cards have subtle hover effect, category shown as outline badge
- **Expandable release notes**: Click to expand, rendered as markdown using marked.js
- **Markdown styling**: Full GitHub-style markdown (headers, code blocks, lists, tables, etc.)
- **Collapsible sidebar**: Repository list collapses on mobile for focus on releases
- **Compact version tags**: Smaller, monospace font with border styling

## Configuration

- Edit `config.yaml` for non-secret settings (check_interval, enabled flags, initial repos)
- Secrets go in `.env` file (tokens, webhook URLs) - NOT committed to git
- Environment variables can override config values
- **Hot reload**: Click "Reload Config" in UI or `POST /api/reload-config` to apply changes without restart

## Files

- `.env` - Secrets (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL, GITHUB_TOKEN)
- `.env.example` - Template for .env (safe to commit)
- `config.yaml` - Non-secret configuration

## Deployment

```bash
docker-compose up -d
```

Accessible at `http://localhost:8080` or via Traefik at configured domain.

## API Endpoints

- `GET /` - Dashboard with optional `?tag=ID` filter
- `GET /api/tags` - List all tags
- `POST /tags/add` - Create new tag
- `POST /tags/{id}/toggle-notifications` - Toggle tag notifications
- `POST /tags/{id}/delete` - Delete tag
- `POST /repos/set-tag` - Assign tag to repository
