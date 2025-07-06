import os
import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, JSON, Float, Boolean


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/pokerbots"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
class BotStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class BotLanguage(str, Enum):
    PYTHON = "python"
    RUST = "rust" 
    JAVA = "java"
    CPP = "cpp"


class TournamentStatus(str, Enum):
    OPEN = "open"
    RUNNING = "running"
    COMPLETED = "completed"


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Models
class Bot(Base):
    __tablename__ = "bots"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    language: Mapped[BotLanguage]
    version: Mapped[str] = mapped_column(String(50))
    status: Mapped[BotStatus] = mapped_column(default=BotStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Simple performance tracking
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    matches_won: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=1200.0)
    
    # File storage path
    file_path: Mapped[Optional[str]] = mapped_column(String(500))


class Tournament(Base):
    __tablename__ = "tournaments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[TournamentStatus] = mapped_column(default=TournamentStatus.OPEN)
    max_participants: Mapped[int] = mapped_column(Integer, default=8)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Participants (JSON list of bot IDs for simplicity)
    participants: Mapped[List[int]] = mapped_column(JSON, default=list)
    
    # Relationships
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="tournament")


class Match(Base):
    __tablename__ = "matches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    bot1_id: Mapped[int] = mapped_column(ForeignKey("bots.id"))
    bot2_id: Mapped[int] = mapped_column(ForeignKey("bots.id"))
    
    status: Mapped[MatchStatus] = mapped_column(default=MatchStatus.SCHEDULED)
    
    # Results
    winner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bots.id"))
    bot1_score: Mapped[int] = mapped_column(Integer, default=0)
    bot2_score: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Game log (simplified)
    game_log: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="matches")
    bot1: Mapped["Bot"] = relationship("Bot", foreign_keys=[bot1_id])
    bot2: Mapped["Bot"] = relationship("Bot", foreign_keys=[bot2_id])
    winner: Mapped[Optional["Bot"]] = relationship("Bot", foreign_keys=[winner_id])


# Simplified utility functions
def calculate_elo_change(winner_rating: float, loser_rating: float, k_factor: float = 32) -> tuple[float, float]:
    """Simple ELO calculation."""
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))
    
    winner_change = k_factor * (1 - expected_winner)
    loser_change = k_factor * (0 - expected_loser)
    
    return winner_change, loser_change


def hash_file(content: bytes) -> str:
    """Generate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()