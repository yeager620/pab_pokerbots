"""
Unified API server for the poker bot competition platform.
Consolidates all endpoints into a single FastAPI application.
"""

import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from models.core import get_db, init_db, Bot, Tournament, Match, BotLanguage, BotStatus, TournamentStatus
from bots import BotManager
from tournaments import TournamentManager
from game import MatchRunner
from analytics import Analytics



class BotResponse(BaseModel):
    id: int
    name: str
    user_id: str
    language: str
    status: str
    rating: float
    matches_played: int
    matches_won: int
    created_at: str


class TournamentResponse(BaseModel):
    id: int
    name: str
    status: str
    max_participants: int
    current_participants: int
    created_at: str


class MatchResponse(BaseModel):
    id: int
    bot1_name: str
    bot2_name: str
    status: str
    winner_name: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]



bot_manager = BotManager()
tournament_manager = TournamentManager()
match_runner = MatchRunner()
analytics = Analytics()


app = FastAPI(
    title="PAB PokerBots API",
    description="Simplified API for poker bot competition",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()



@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pokerbots-api"}



@app.post("/bots", response_model=dict)
async def submit_bot(
    name: str = Form(...),
    language: BotLanguage = Form(...),
    version: str = Form(...),
    user_id: str = Form(...),
    bot_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Submit a new bot."""
    try:
        bot_archive = await bot_file.read()
        bot = await bot_manager.submit_bot(db, user_id, name, language, version, bot_archive)
        
        return {
            "success": True,
            "bot_id": bot.id,
            "message": "Bot submitted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/bots/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: int, db: AsyncSession = Depends(get_db)):
    """Get bot details."""
    bot = await bot_manager.get_bot(db, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return BotResponse(
        id=bot.id,
        name=bot.name,
        user_id=bot.user_id,
        language=bot.language.value,
        status=bot.status.value,
        rating=bot.rating,
        matches_played=bot.matches_played,
        matches_won=bot.matches_won,
        created_at=bot.created_at.isoformat()
    )


@app.get("/bots", response_model=List[BotResponse])
async def list_bots(
    user_id: Optional[str] = Query(None),
    status: Optional[BotStatus] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List bots with optional filters."""
    bots = await bot_manager.list_bots(db, user_id, status)
    
    return [
        BotResponse(
            id=bot.id,
            name=bot.name,
            user_id=bot.user_id,
            language=bot.language.value,
            status=bot.status.value,
            rating=bot.rating,
            matches_played=bot.matches_played,
            matches_won=bot.matches_won,
            created_at=bot.created_at.isoformat()
        )
        for bot in bots
    ]



@app.post("/tournaments", response_model=dict)
async def create_tournament(
    name: str = Form(...),
    max_participants: int = Form(8),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tournament."""
    tournament = await tournament_manager.create_tournament(db, name, max_participants)
    
    return {
        "success": True,
        "tournament_id": tournament.id,
        "message": "Tournament created successfully"
    }


@app.get("/tournaments/{tournament_id}", response_model=TournamentResponse)
async def get_tournament(tournament_id: int, db: AsyncSession = Depends(get_db)):
    """Get tournament details."""
    tournament = await db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    return TournamentResponse(
        id=tournament.id,
        name=tournament.name,
        status=tournament.status.value,
        max_participants=tournament.max_participants,
        current_participants=len(tournament.participants),
        created_at=tournament.created_at.isoformat()
    )


@app.post("/tournaments/{tournament_id}/register")
async def register_for_tournament(
    tournament_id: int,
    bot_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Register a bot for a tournament."""
    success = await tournament_manager.register_bot(db, tournament_id, bot_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to register bot")
    
    return {"success": True, "message": "Bot registered successfully"}


@app.post("/tournaments/{tournament_id}/start")
async def start_tournament(tournament_id: int, db: AsyncSession = Depends(get_db)):
    """Start a tournament."""
    result = await tournament_manager.start_tournament(db, tournament_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@app.get("/tournaments/{tournament_id}/standings")
async def get_tournament_standings(tournament_id: int, db: AsyncSession = Depends(get_db)):
    """Get tournament standings."""
    standings = await tournament_manager.get_tournament_standings(db, tournament_id)
    return {"standings": standings}


@app.get("/tournaments/{tournament_id}/matches", response_model=List[MatchResponse])
async def get_tournament_matches(tournament_id: int, db: AsyncSession = Depends(get_db)):
    """Get tournament matches."""
    matches = await tournament_manager.get_tournament_matches(db, tournament_id)
    
    return [
        MatchResponse(
            id=match["id"],
            bot1_name=match["bot1_name"],
            bot2_name=match["bot2_name"], 
            status=match["status"],
            winner_name=match["winner_name"],
            started_at=match["started_at"],
            completed_at=match["completed_at"]
        )
        for match in matches
    ]



@app.post("/matches/{match_id}/run")
async def run_match(match_id: int, db: AsyncSession = Depends(get_db)):
    """Manually run a specific match."""
    try:
        result = await match_runner.run_match(db, match_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get the current leaderboard."""
    leaderboard = await analytics.get_leaderboard(db, limit)
    return {"leaderboard": leaderboard}


@app.get("/bots/{bot_id}/stats")
async def get_bot_stats(bot_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed bot statistics."""
    stats = await analytics.get_bot_stats(db, bot_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return stats


@app.get("/head-to-head/{bot1_id}/{bot2_id}")
async def get_head_to_head(bot1_id: int, bot2_id: int, db: AsyncSession = Depends(get_db)):
    """Get head-to-head statistics between two bots."""
    h2h = await analytics.get_head_to_head(db, bot1_id, bot2_id)
    return h2h


@app.get("/stats/global")
async def get_global_stats(db: AsyncSession = Depends(get_db)):
    """Get global platform statistics."""
    stats = await analytics.get_global_stats(db)
    return stats


@app.get("/stats/ratings")
async def get_rating_distribution(db: AsyncSession = Depends(get_db)):
    """Get rating distribution."""
    distribution = await analytics.get_rating_distribution(db)
    return {"rating_distribution": distribution}



@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "PAB PokerBots API",
        "version": "1.0.0",
        "description": "Simplified poker bot competition platform",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "bots": "/bots",
            "tournaments": "/tournaments", 
            "leaderboard": "/leaderboard",
            "stats": "/stats/global"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)