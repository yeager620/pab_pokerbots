"""
Simple configuration management for the poker bot platform.
Basic settings with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Basic configuration settings."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///pokerbots.db")
    
    # File storage
    BOT_STORAGE_DIR: str = os.getenv("BOT_STORAGE_DIR", "/tmp/pokerbots")
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Game settings
    STARTING_STACK: int = int(os.getenv("STARTING_STACK", "400"))
    SMALL_BLIND: int = int(os.getenv("SMALL_BLIND", "1"))
    BIG_BLIND: int = int(os.getenv("BIG_BLIND", "2"))
    MAX_HANDS_PER_MATCH: int = int(os.getenv("MAX_HANDS_PER_MATCH", "100"))
    
    # Bot execution limits
    BOT_MEMORY_LIMIT: str = os.getenv("BOT_MEMORY_LIMIT", "256m")
    BOT_CPU_QUOTA: int = int(os.getenv("BOT_CPU_QUOTA", "50000"))  # 0.5 CPU
    BOT_TIMEOUT: int = int(os.getenv("BOT_TIMEOUT", "10"))  # seconds
    
    # Tournament settings
    DEFAULT_TOURNAMENT_SIZE: int = int(os.getenv("DEFAULT_TOURNAMENT_SIZE", "8"))
    
    # Analytics
    LEADERBOARD_LIMIT: int = int(os.getenv("LEADERBOARD_LIMIT", "50"))
    
    # Docker images for each language
    DOCKER_IMAGES = {
        "python": "python:3.13-slim",
        "rust": "rust:1.75-slim",
        "java": "openjdk:17-slim",
        "cpp": "gcc:11-slim"
    }
    
    @classmethod
    def get_bot_storage_path(cls) -> Path:
        """Get bot storage directory as Path object."""
        path = Path(cls.BOT_STORAGE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @classmethod
    def get_docker_image(cls, language: str) -> str:
        """Get Docker image for language."""
        return cls.DOCKER_IMAGES.get(language.lower(), cls.DOCKER_IMAGES["python"])


# Global config instance
config = Config()