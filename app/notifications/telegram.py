import httpx
from app.config import config

async def send_telegram_notification(release: dict) -> bool:
    """Send a release notification via Telegram."""
    telegram_config = config.notifications.telegram
    
    if not telegram_config.enabled or not telegram_config.bot_token or not telegram_config.chat_id:
        return False
    
    repo_name = f"{release['owner']}/{release['repo_name']}"
    tag = release['tag_name']
    title = release.get('name') or tag
    url = release.get('html_url', '')
    
    # Format message with Markdown
    message = f"""🚀 *New Release!*

📦 *{repo_name}*
🏷️ *{title}*
🔗 [View Release]({url})"""
    
    # Truncate body if present
    body = release.get('body', '')
    if body:
        body = body[:500] + '...' if len(body) > 500 else body
        # Escape markdown special characters in body
        body = body.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        message += f"\n\n📝 {body}"
    
    api_url = f"https://api.telegram.org/bot{telegram_config.bot_token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                api_url,
                json={
                    "chat_id": telegram_config.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                },
                timeout=30.0
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")
            return False

async def test_telegram() -> tuple[bool, str]:
    """Test Telegram configuration."""
    telegram_config = config.notifications.telegram
    
    if not telegram_config.bot_token:
        return False, "Bot token not configured"
    if not telegram_config.chat_id:
        return False, "Chat ID not configured"
    
    api_url = f"https://api.telegram.org/bot{telegram_config.bot_token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                api_url,
                json={
                    "chat_id": telegram_config.chat_id,
                    "text": "✅ GitHub Release Notifier: Test notification successful!",
                    "parse_mode": "Markdown"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return True, "Test message sent successfully"
        except httpx.HTTPStatusError as e:
            # Get detailed error from Telegram
            try:
                error_body = e.response.json()
                error_desc = error_body.get("description", str(e.response.status_code))
            except:
                error_desc = str(e.response.status_code)
            return False, f"Telegram error: {error_desc}"
        except Exception as e:
            return False, f"Error: {str(e)}"
