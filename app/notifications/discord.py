import httpx
from app.config import config

async def send_discord_notification(release: dict) -> bool:
    """Send a release notification via Discord webhook."""
    discord_config = config.notifications.discord
    
    if not discord_config.enabled or not discord_config.webhook_url:
        return False
    
    repo_name = f"{release['owner']}/{release['repo_name']}"
    tag = release['tag_name']
    title = release.get('name') or tag
    url = release.get('html_url', '')
    
    # Format body
    body = release.get('body', '')
    if body:
        body = body[:1000] + '...' if len(body) > 1000 else body
    
    # Discord embed
    embed = {
        "title": f"🚀 {title}",
        "url": url,
        "color": 5814783,  # GitHub purple
        "fields": [
            {
                "name": "📦 Repository",
                "value": f"[{repo_name}](https://github.com/{repo_name})",
                "inline": True
            },
            {
                "name": "🏷️ Tag",
                "value": tag,
                "inline": True
            }
        ],
        "footer": {
            "text": "GitHub Release Notifier"
        }
    }
    
    if body:
        embed["description"] = body
    
    payload = {
        "embeds": [embed]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                discord_config.webhook_url,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
            return False

async def test_discord() -> tuple[bool, str]:
    """Test Discord webhook configuration."""
    discord_config = config.notifications.discord
    
    if not discord_config.webhook_url:
        return False, "Webhook URL not configured"
    
    embed = {
        "title": "✅ Test Notification",
        "description": "GitHub Release Notifier: Test notification successful!",
        "color": 5814783,
        "footer": {
            "text": "GitHub Release Notifier"
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                discord_config.webhook_url,
                json={"embeds": [embed]},
                timeout=30.0
            )
            response.raise_for_status()
            return True, "Test message sent successfully"
        except httpx.HTTPStatusError as e:
            return False, f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
