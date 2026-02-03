import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional

DATABASE_PATH = Path("/app/data/releases.db")

async def init_db():
    """Initialize the SQLite database."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#8b5cf6',
                notifications_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                tag_id INTEGER,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner, name),
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                name TEXT,
                body TEXT,
                html_url TEXT,
                published_at TIMESTAMP,
                notified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(repo_id, tag_name)
            )
        """)
        
        # Migration: add tag_id column if it doesn't exist
        try:
            await db.execute("ALTER TABLE repositories ADD COLUMN tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL")
        except:
            pass  # Column already exists
        
        await db.commit()

# ============ Tags ============

async def add_tag(name: str, color: str = "#8b5cf6") -> Optional[int]:
    """Add a new tag/category."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)",
                (name.strip(), color)
            )
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None

async def get_tags() -> list[dict]:
    """Get all tags with repository counts."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT t.*, COUNT(r.id) as repo_count
            FROM tags t
            LEFT JOIN repositories r ON r.tag_id = t.id
            GROUP BY t.id
            ORDER BY t.name
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_tag_by_id(tag_id: int) -> Optional[dict]:
    """Get a tag by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_tag(tag_id: int, name: str = None, color: str = None, notifications_enabled: bool = None) -> bool:
    """Update a tag's properties."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name.strip())
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if notifications_enabled is not None:
            updates.append("notifications_enabled = ?")
            params.append(notifications_enabled)
        
        if not updates:
            return False
        
        params.append(tag_id)
        await db.execute(f"UPDATE tags SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
        return True

async def delete_tag(tag_id: int) -> bool:
    """Delete a tag (repos will have tag_id set to NULL)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        await db.commit()
        return cursor.rowcount > 0

async def set_repo_tag(owner: str, name: str, tag_id: Optional[int]) -> bool:
    """Assign a tag to a repository."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE repositories SET tag_id = ? WHERE owner = ? AND name = ?",
            (tag_id, owner, name)
        )
        await db.commit()
        return cursor.rowcount > 0

async def add_repository(owner: str, name: str, tag_id: Optional[int] = None) -> Optional[int]:
    """Add a repository to track."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO repositories (owner, name, tag_id) VALUES (?, ?, ?)",
                (owner, name, tag_id)
            )
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None

async def remove_repository(owner: str, name: str) -> bool:
    """Remove a repository from tracking."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM repositories WHERE owner = ? AND name = ?",
            (owner, name)
        )
        await db.commit()
        return cursor.rowcount > 0

async def get_repositories(tag_id: Optional[int] = None) -> list[dict]:
    """Get all tracked repositories, optionally filtered by tag."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if tag_id is not None:
            cursor = await db.execute(
                """SELECT r.*, t.name as tag_name, t.color as tag_color, t.notifications_enabled as tag_notifications
                   FROM repositories r
                   LEFT JOIN tags t ON r.tag_id = t.id
                   WHERE r.enabled = 1 AND r.tag_id = ?
                   ORDER BY r.owner, r.name""",
                (tag_id,)
            )
        else:
            cursor = await db.execute(
                """SELECT r.*, t.name as tag_name, t.color as tag_color, t.notifications_enabled as tag_notifications
                   FROM repositories r
                   LEFT JOIN tags t ON r.tag_id = t.id
                   WHERE r.enabled = 1
                   ORDER BY r.owner, r.name"""
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_repositories_with_notifications() -> list[dict]:
    """Get repositories that have notifications enabled (via their tag)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT r.*, t.name as tag_name, t.color as tag_color, t.notifications_enabled as tag_notifications
               FROM repositories r
               LEFT JOIN tags t ON r.tag_id = t.id
               WHERE r.enabled = 1 AND (r.tag_id IS NULL OR t.notifications_enabled = 1)
               ORDER BY r.owner, r.name"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_repository_by_name(owner: str, name: str) -> Optional[dict]:
    """Get a repository by owner and name."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM repositories WHERE owner = ? AND name = ?",
            (owner, name)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_release(repo_id: int, release_data: dict) -> tuple[Optional[int], bool]:
    """Add a release. Returns (id, is_new)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                """INSERT INTO releases (repo_id, tag_name, name, body, html_url, published_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    repo_id,
                    release_data["tag_name"],
                    release_data.get("name", ""),
                    release_data.get("body", ""),
                    release_data.get("html_url", ""),
                    release_data.get("published_at", "")
                )
            )
            await db.commit()
            return cursor.lastrowid, True
        except aiosqlite.IntegrityError:
            return None, False

async def get_releases(limit: int = 50, tag_id: Optional[int] = None) -> list[dict]:
    """Get recent releases across all repositories, optionally filtered by tag."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if tag_id is not None:
            cursor = await db.execute(
                """SELECT r.*, repo.owner, repo.name as repo_name, t.name as category_name, t.color as category_color
                   FROM releases r
                   JOIN repositories repo ON r.repo_id = repo.id
                   LEFT JOIN tags t ON repo.tag_id = t.id
                   WHERE repo.tag_id = ?
                   ORDER BY r.published_at DESC
                   LIMIT ?""",
                (tag_id, limit)
            )
        else:
            cursor = await db.execute(
                """SELECT r.*, repo.owner, repo.name as repo_name, t.name as category_name, t.color as category_color
                   FROM releases r
                   JOIN repositories repo ON r.repo_id = repo.id
                   LEFT JOIN tags t ON repo.tag_id = t.id
                   ORDER BY r.published_at DESC
                   LIMIT ?""",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_releases_for_repo(repo_id: int, limit: int = 20) -> list[dict]:
    """Get releases for a specific repository."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM releases WHERE repo_id = ? ORDER BY published_at DESC LIMIT ?""",
            (repo_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def mark_release_notified(release_id: int):
    """Mark a release as notified."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE releases SET notified = 1 WHERE id = ?",
            (release_id,)
        )
        await db.commit()

async def get_unnotified_releases() -> list[dict]:
    """Get releases that haven't been notified yet."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT r.*, repo.owner, repo.name as repo_name
               FROM releases r
               JOIN repositories repo ON r.repo_id = repo.id
               WHERE r.notified = 0
               ORDER BY r.published_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
