import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import config
from app import database, github_client
from app.notifications import telegram, discord

scheduler = AsyncIOScheduler()

async def check_releases():
    """Check all tracked repositories for new releases."""
    print("Checking for new releases...")
    
    repos = await database.get_repositories()
    
    for repo in repos:
        owner = repo['owner']
        name = repo['name']
        repo_id = repo['id']
        tag_notifications = repo.get('tag_notifications', True)  # Default to True if no tag
        
        print(f"Checking {owner}/{name}...")
        
        releases = await github_client.get_releases(owner, name, per_page=5)
        
        for release_data in releases:
            release_id, is_new = await database.add_release(repo_id, release_data)
            
            if is_new and release_id:
                print(f"New release found: {owner}/{name} - {release_data['tag_name']}")
                
                # Get full release info for notification
                release_info = {
                    'id': release_id,
                    'owner': owner,
                    'repo_name': name,
                    'tag_name': release_data['tag_name'],
                    'name': release_data.get('name', ''),
                    'body': release_data.get('body', ''),
                    'html_url': release_data.get('html_url', ''),
                    'published_at': release_data.get('published_at', ''),
                    'category_name': repo.get('tag_name', ''),
                }
                
                # Only send notifications if tag allows it (or no tag assigned)
                if tag_notifications is None or tag_notifications:
                    await send_notifications(release_info)
                else:
                    print(f"Skipping notification for {owner}/{name} - tag notifications disabled")
                
                # Mark as notified
                await database.mark_release_notified(release_id)
        
        # Small delay between repos to avoid rate limiting
        await asyncio.sleep(1)
    
    print("Release check complete.")

async def send_notifications(release: dict):
    """Send notifications for a new release."""
    tasks = []
    
    if config.notifications.telegram.enabled:
        tasks.append(telegram.send_telegram_notification(release))
    
    if config.notifications.discord.enabled:
        tasks.append(discord.send_discord_notification(release))
    
    if tasks:
        await asyncio.gather(*tasks)

async def initial_sync():
    """Sync configured repositories and fetch initial releases."""
    print("Running initial sync...")
    
    # Add configured repositories
    for repo_str in config.repositories:
        if '/' in repo_str:
            owner, name = repo_str.split('/', 1)
            repo = await database.get_repository_by_name(owner, name)
            if not repo:
                await database.add_repository(owner, name)
                print(f"Added configured repository: {owner}/{name}")
    
    # Fetch releases for all repos (without notifying for existing ones)
    repos = await database.get_repositories()
    
    for repo in repos:
        owner = repo['owner']
        name = repo['name']
        repo_id = repo['id']
        
        releases = await github_client.get_releases(owner, name, per_page=10)
        
        for release_data in releases:
            release_id, is_new = await database.add_release(repo_id, release_data)
            if is_new and release_id:
                # Mark initial releases as already notified
                await database.mark_release_notified(release_id)
        
        await asyncio.sleep(0.5)
    
    print("Initial sync complete.")

def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        check_releases,
        IntervalTrigger(minutes=config.check_interval),
        id='check_releases',
        name='Check for new releases',
        replace_existing=True
    )
    scheduler.start()
    print(f"Scheduler started. Checking every {config.check_interval} minutes.")

def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
