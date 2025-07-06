"""
Simplified bot management system.
Handles bot submission, validation, storage, and basic operations.
"""

import os
import zipfile
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .models.core import Bot, BotLanguage, BotStatus, hash_file


class BotManager:
    """Unified bot management - submission, validation, storage."""
    
    def __init__(self, storage_dir: str = "/tmp/pokerbots"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def submit_bot(
        self, 
        db: AsyncSession,
        user_id: str, 
        name: str, 
        language: BotLanguage,
        version: str,
        bot_archive: bytes
    ) -> Bot:
        """Submit and validate a new bot."""
        # Create bot record
        bot = Bot(
            user_id=user_id,
            name=name,
            language=language,
            version=version,
            status=BotStatus.INACTIVE
        )
        db.add(bot)
        await db.flush()
        
        try:
            # Validate and store
            bot_dir = await self._validate_and_store(bot.id, language, bot_archive)
            bot.file_path = str(bot_dir)
            bot.status = BotStatus.ACTIVE
            
            await db.commit()
            return bot
            
        except Exception as e:
            bot.status = BotStatus.FAILED
            await db.commit()
            raise ValueError(f"Bot validation failed: {str(e)}")
    
    async def _validate_and_store(self, bot_id: int, language: BotLanguage, archive: bytes) -> Path:
        """Validate bot archive and store files."""
        bot_dir = self.storage_dir / str(bot_id)
        bot_dir.mkdir(exist_ok=True)
        
        # Extract archive
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            archive_file = temp_path / "bot.zip"
            
            with open(archive_file, 'wb') as f:
                f.write(archive)
            
            with zipfile.ZipFile(archive_file, 'r') as zip_ref:
                # Basic security: check for path traversal
                for name in zip_ref.namelist():
                    if ".." in name or name.startswith("/"):
                        raise ValueError(f"Unsafe file path: {name}")
                
                zip_ref.extractall(temp_path / "extracted")
            
            extracted_dir = temp_path / "extracted"
            
            # Language-specific validation
            self._validate_structure(extracted_dir, language)
            self._validate_syntax(extracted_dir, language)
            
            # Copy to permanent storage
            shutil.copytree(extracted_dir, bot_dir, dirs_exist_ok=True)
        
        return bot_dir
    
    def _validate_structure(self, bot_dir: Path, language: BotLanguage):
        """Validate required files exist."""
        required_files = {
            BotLanguage.PYTHON: ["bot_main.py"],
            BotLanguage.RUST: ["src/main.rs", "Cargo.toml"],
            BotLanguage.JAVA: ["src/BotMain.java"],
            BotLanguage.CPP: ["bot_main.cpp"]
        }
        
        for required_file in required_files.get(language, []):
            if not (bot_dir / required_file).exists():
                raise ValueError(f"Missing required file: {required_file}")
    
    def _validate_syntax(self, bot_dir: Path, language: BotLanguage):
        """Basic syntax validation."""
        try:
            if language == BotLanguage.PYTHON:
                # Check Python syntax
                for py_file in bot_dir.rglob("*.py"):
                    result = subprocess.run(
                        ["python3", "-m", "py_compile", str(py_file)],
                        capture_output=True, timeout=10
                    )
                    if result.returncode != 0:
                        raise ValueError(f"Python syntax error in {py_file.name}")
            
            elif language == BotLanguage.RUST:
                result = subprocess.run(
                    ["cargo", "check"], cwd=bot_dir,
                    capture_output=True, timeout=30
                )
                if result.returncode != 0:
                    raise ValueError("Rust compilation error")
            
            # Add other language checks as needed
            
        except subprocess.TimeoutExpired:
            raise ValueError("Syntax validation timed out")
    
    async def get_bot(self, db: AsyncSession, bot_id: int) -> Optional[Bot]:
        """Get bot by ID."""
        stmt = select(Bot).where(Bot.id == bot_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_bots(self, db: AsyncSession, user_id: Optional[str] = None, status: Optional[BotStatus] = None) -> List[Bot]:
        """List bots with optional filters."""
        stmt = select(Bot)
        
        if user_id:
            stmt = stmt.where(Bot.user_id == user_id)
        if status:
            stmt = stmt.where(Bot.status == status)
        
        stmt = stmt.order_by(Bot.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def update_bot_rating(self, db: AsyncSession, bot_id: int, new_rating: float):
        """Update bot rating after match."""
        stmt = update(Bot).where(Bot.id == bot_id).values(rating=new_rating)
        await db.execute(stmt)
    
    async def record_match_result(self, db: AsyncSession, bot_id: int, won: bool):
        """Record match result for bot."""
        bot = await self.get_bot(db, bot_id)
        if bot:
            bot.matches_played += 1
            if won:
                bot.matches_won += 1
            await db.commit()
    
    def get_bot_files(self, bot_id: int) -> Optional[Path]:
        """Get bot files directory."""
        bot_dir = self.storage_dir / str(bot_id)
        return bot_dir if bot_dir.exists() else None