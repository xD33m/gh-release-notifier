import httpx
from typing import Optional
from app.config import config

GITHUB_API_BASE = "https://api.github.com"

async def get_releases(owner: str, repo: str, per_page: int = 10) -> list[dict]:
    """Fetch releases for a GitHub repository."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Release-Notifier/1.0"
    }
    
    if config.github_token:
        headers["Authorization"] = f"Bearer {config.github_token}"
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers=headers,
                params={"per_page": per_page},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching releases for {owner}/{repo}: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"Error fetching releases for {owner}/{repo}: {e}")
            return []

async def get_latest_release(owner: str, repo: str) -> Optional[dict]:
    """Fetch the latest release for a GitHub repository."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Release-Notifier/1.0"
    }
    
    if config.github_token:
        headers["Authorization"] = f"Bearer {config.github_token}"
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/latest"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None  # No releases
            print(f"Error fetching latest release for {owner}/{repo}: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"Error fetching latest release for {owner}/{repo}: {e}")
            return None

async def validate_repository(owner: str, repo: str) -> bool:
    """Check if a repository exists and is accessible."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Release-Notifier/1.0"
    }
    
    if config.github_token:
        headers["Authorization"] = f"Bearer {config.github_token}"
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            return response.status_code == 200
        except Exception:
            return False
