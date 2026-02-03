import os
from pathlib import Path
import yaml
from pydantic import BaseModel
from typing import Optional
from threading import Lock

class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""

class DiscordConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""

class NotificationsConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()
    discord: DiscordConfig = DiscordConfig()

class AppConfig(BaseModel):
    github_token: str = ""
    check_interval: int = 30
    notifications: NotificationsConfig = NotificationsConfig()
    repositories: list[str] = []


class ConfigManager:
    """Thread-safe configuration manager with hot reload support."""
    
    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._lock = Lock()
        self._load()
    
    def _get_config_path(self) -> Path:
        """Get the configuration file path."""
        config_path = Path("/app/config/config.yaml")
        if not config_path.exists():
            config_path = Path("config.yaml")
        return config_path
    
    def _load(self) -> AppConfig:
        """Load configuration from YAML file and environment variables."""
        config_path = self._get_config_path()
        
        config_data = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        
        # Environment variable overrides (secrets from .env)
        if os.getenv("GITHUB_TOKEN"):
            config_data["github_token"] = os.getenv("GITHUB_TOKEN")
        if os.getenv("CHECK_INTERVAL"):
            config_data["check_interval"] = int(os.getenv("CHECK_INTERVAL"))
        
        # Telegram config from environment
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            config_data.setdefault("notifications", {}).setdefault("telegram", {})["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
        if os.getenv("TELEGRAM_CHAT_ID"):
            config_data.setdefault("notifications", {}).setdefault("telegram", {})["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")
        
        # Auto-enable telegram if both token and chat_id are set
        telegram_config = config_data.get("notifications", {}).get("telegram", {})
        if telegram_config.get("bot_token") and telegram_config.get("chat_id"):
            telegram_config["enabled"] = config_data.get("notifications", {}).get("telegram", {}).get("enabled", True)
        
        # Discord config from environment
        if os.getenv("DISCORD_WEBHOOK_URL"):
            config_data.setdefault("notifications", {}).setdefault("discord", {})["webhook_url"] = os.getenv("DISCORD_WEBHOOK_URL")
            discord_enabled = config_data.get("notifications", {}).get("discord", {}).get("enabled", True)
            config_data["notifications"]["discord"]["enabled"] = discord_enabled
        
        self._config = AppConfig(**config_data)
        return self._config
    
    def reload(self) -> AppConfig:
        """Hot reload configuration from files."""
        with self._lock:
            # Re-read .env file for updated secrets
            self._reload_env()
            return self._load()
    
    def _reload_env(self):
        """Reload environment variables from .env file."""
        env_paths = [Path("/app/.env"), Path(".env")]
        for env_path in env_paths:
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if value:  # Only set if value is not empty
                                os.environ[key] = value
                break
    
    @property
    def config(self) -> AppConfig:
        """Get current configuration."""
        if self._config is None:
            self._load()
        return self._config
    
    # Convenience accessors
    @property
    def github_token(self) -> str:
        return self.config.github_token
    
    @property
    def check_interval(self) -> int:
        return self.config.check_interval
    
    @property
    def notifications(self) -> NotificationsConfig:
        return self.config.notifications
    
    @property
    def repositories(self) -> list[str]:
        return self.config.repositories


# Global config manager instance
_config_manager = ConfigManager()

def get_config() -> AppConfig:
    """Get current configuration."""
    return _config_manager.config

def reload_config() -> AppConfig:
    """Reload configuration from files."""
    return _config_manager.reload()

# For backwards compatibility
config = _config_manager
