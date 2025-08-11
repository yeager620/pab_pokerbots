"""
Simplified analytics and leaderboard system.
Basic ELO ratings and performance tracking.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from models.core import Bot, Match, MatchStatus, calculate_elo_change


class Analytics:
    """Simplified analytics for bots and tournaments."""
    
    async def get_leaderboard(self, db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """Get bot leaderboard sorted by rating."""
        stmt = (
            select(Bot)
            .where(Bot.matches_played > 0)
            .order_by(desc(Bot.rating))
            .limit(limit)
        )
        result = await db.execute(stmt)
        bots = result.scalars().all()
        
        leaderboard = []
        for i, bot in enumerate(bots, 1):
            win_rate = bot.matches_won / bot.matches_played if bot.matches_played > 0 else 0
            
            leaderboard.append({
                "rank": i,
                "bot_id": bot.id,
                "bot_name": bot.name,
                "user_id": bot.user_id,
                "language": bot.language.value,
                "rating": round(bot.rating, 1),
                "matches_played": bot.matches_played,
                "matches_won": bot.matches_won,
                "win_rate": round(win_rate * 100, 1)
            })
        
        return leaderboard
    
    async def get_bot_stats(self, db: AsyncSession, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed statistics for a bot."""
        bot = await db.get(Bot, bot_id)
        if not bot:
            return None
        

        stmt = (
            select(Match)
            .where(
                ((Match.bot1_id == bot_id) | (Match.bot2_id == bot_id)) &
                (Match.status == MatchStatus.COMPLETED)
            )
            .order_by(desc(Match.completed_at))
            .limit(10)
        )
        result = await db.execute(stmt)
        recent_matches = result.scalars().all()
        

        recent_wins = sum(1 for m in recent_matches if m.winner_id == bot_id)
        recent_win_rate = recent_wins / len(recent_matches) if recent_matches else 0
        

        overall_win_rate = bot.matches_won / bot.matches_played if bot.matches_played > 0 else 0
        
        return {
            "bot_id": bot.id,
            "bot_name": bot.name,
            "user_id": bot.user_id,
            "language": bot.language.value,
            "status": bot.status.value,
            "rating": round(bot.rating, 1),
            "matches_played": bot.matches_played,
            "matches_won": bot.matches_won,
            "overall_win_rate": round(overall_win_rate * 100, 1),
            "recent_matches": len(recent_matches),
            "recent_wins": recent_wins,
            "recent_win_rate": round(recent_win_rate * 100, 1),
            "created_at": bot.created_at.isoformat()
        }
    
    async def get_head_to_head(self, db: AsyncSession, bot1_id: int, bot2_id: int) -> Dict[str, Any]:
        """Get head-to-head statistics between two bots."""

        stmt = select(Match).where(
            (
                ((Match.bot1_id == bot1_id) & (Match.bot2_id == bot2_id)) |
                ((Match.bot1_id == bot2_id) & (Match.bot2_id == bot1_id))
            ) &
            (Match.status == MatchStatus.COMPLETED)
        )
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        bot1_wins = sum(1 for m in matches if m.winner_id == bot1_id)
        bot2_wins = sum(1 for m in matches if m.winner_id == bot2_id)
        total_matches = len(matches)
        

        bot1 = await db.get(Bot, bot1_id)
        bot2 = await db.get(Bot, bot2_id)
        
        return {
            "bot1": {
                "id": bot1_id,
                "name": bot1.name if bot1 else "Unknown",
                "wins": bot1_wins,
                "win_rate": round(bot1_wins / total_matches * 100, 1) if total_matches > 0 else 0
            },
            "bot2": {
                "id": bot2_id, 
                "name": bot2.name if bot2 else "Unknown",
                "wins": bot2_wins,
                "win_rate": round(bot2_wins / total_matches * 100, 1) if total_matches > 0 else 0
            },
            "total_matches": total_matches,
            "last_match": max(m.completed_at for m in matches) if matches else None
        }
    
    async def get_global_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get global platform statistics."""

        total_bots_stmt = select(func.count(Bot.id))
        total_bots = await db.scalar(total_bots_stmt)
        

        active_bots_stmt = select(func.count(Bot.id)).where(Bot.status == "active")
        active_bots = await db.scalar(active_bots_stmt)
        

        total_matches_stmt = select(func.count(Match.id)).where(Match.status == MatchStatus.COMPLETED)
        total_matches = await db.scalar(total_matches_stmt)
        

        lang_stmt = select(Bot.language, func.count(Bot.id)).group_by(Bot.language)
        lang_result = await db.execute(lang_stmt)
        language_dist = {lang.value: count for lang, count in lang_result}
        
        return {
            "total_bots": total_bots or 0,
            "active_bots": active_bots or 0,
            "total_matches": total_matches or 0,
            "language_distribution": language_dist
        }
    
    async def update_ratings_after_match(self, db: AsyncSession, match_id: int):
        """Update bot ratings after a completed match."""
        match = await db.get(Match, match_id)
        if not match or match.status != MatchStatus.COMPLETED or not match.winner_id:
            return
        
        bot1 = await db.get(Bot, match.bot1_id)
        bot2 = await db.get(Bot, match.bot2_id)
        
        if not bot1 or not bot2:
            return
        

        if match.winner_id == bot1.id:
            winner_change, loser_change = calculate_elo_change(bot1.rating, bot2.rating)
            bot1.rating += winner_change
            bot2.rating += loser_change

            bot1.matches_won += 1
        else:
            winner_change, loser_change = calculate_elo_change(bot2.rating, bot1.rating)
            bot2.rating += winner_change  
            bot1.rating += loser_change

            bot2.matches_won += 1
        

        bot1.matches_played += 1
        bot2.matches_played += 1
        
        await db.commit()
    
    async def get_rating_distribution(self, db: AsyncSession) -> Dict[str, int]:
        """Get distribution of ratings across ranges."""
        stmt = select(Bot.rating).where(Bot.matches_played > 0)
        result = await db.execute(stmt)
        ratings = [r for r, in result]
        

        ranges = {
            "Under 1000": 0,
            "1000-1199": 0, 
            "1200-1399": 0,
            "1400-1599": 0,
            "1600-1799": 0,
            "1800+": 0
        }
        
        for rating in ratings:
            if rating < 1000:
                ranges["Under 1000"] += 1
            elif rating < 1200:
                ranges["1000-1199"] += 1
            elif rating < 1400:
                ranges["1200-1399"] += 1
            elif rating < 1600:
                ranges["1400-1599"] += 1
            elif rating < 1800:
                ranges["1600-1799"] += 1
            else:
                ranges["1800+"] += 1
        
        return ranges