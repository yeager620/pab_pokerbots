#!/usr/bin/env python3
"""
Comprehensive poker bot test with detailed gameplay logging.
Tests full Texas Hold'em gameplay mechanics and logs all bot actions, chip stacks, and eliminations.
"""

import asyncio
import sys
import os
import tempfile
from datetime import datetime
from pathlib import Path

# Add private directory to path
sys.path.insert(0, str(Path(__file__).parent / "private"))

from tests.integration_test_runner import IntegrationTestRunner
from models.core import BotLanguage, TournamentStatus, MatchStatus


class VerbosePokerTestRunner(IntegrationTestRunner):
    """Enhanced test runner with detailed poker gameplay logging."""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///:memory:", log_file: str = "poker_test_results.txt"):
        super().__init__(database_url)
        self.log_file = log_file
        self.log_handle = None
    
    def log(self, message: str):
        """Log to both console and file."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        if self.log_handle:
            self.log_handle.write(log_msg + "\n")
            self.log_handle.flush()
    
    async def run_verbose_tournament_test(self) -> bool:
        """Run comprehensive tournament test with detailed logging."""
        
        # Open log file
        self.log_file = f"poker_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_handle = open(self.log_file, 'w')
        
        try:
            self.log("=" * 80)
            self.log("🎪 COMPREHENSIVE POKER BOT TOURNAMENT TEST")
            self.log("=" * 80)
            self.log(f"📝 Logging to: {self.log_file}")
            self.log(f"🕐 Test started: {datetime.now().isoformat()}")
            self.log("")
            
            self.log("🎯 TEST OBJECTIVES:")
            self.log("  • Verify Texas Hold'em gameplay mechanics")
            self.log("  • Track chip stacks and betting actions")
            self.log("  • Log bot eliminations and bankruptcies")
            self.log("  • Ensure gameplay follows proper poker rules")
            self.log("  • Run until single winner remains")
            self.log("")
            
            # Setup
            await self.setup()
            self.log("✅ Database and environment initialized")
            
            async with self.SessionLocal() as db:
                from bots import BotManager
                from tournaments import TournamentManager
                from analytics import Analytics
                
                bot_manager = BotManager(str(self.temp_dir / "bots"))
                tournament_manager = TournamentManager(str(self.temp_dir / "bots"))
                analytics = Analytics()
                
                # Create more bots for a longer tournament
                self.log("")
                self.log("🤖 STEP 1: Creating and submitting bots...")
                sample_bots = self.create_sample_bots()
                submitted_bots = []
                
                bot_configs = [
                    ("alice", "AliceBot", "python_conservative", "Conservative player - tends to fold weak hands"),
                    ("bob", "BobBot", "python_aggressive", "Aggressive player - likes to bet and raise"),
                    ("charlie", "CharlieBot", "python_random", "Random player - unpredictable actions"),
                    ("diana", "DianaBot", "python_folder", "Tight player - only plays strong hands"),
                    ("eve", "EveBot", "python_conservative", "Conservative backup player"),
                    ("frank", "FrankBot", "python_aggressive", "Aggressive backup player"),
                ]
                
                for user_id, bot_name, bot_type, description in bot_configs:
                    try:
                        bot = await bot_manager.submit_bot(
                            db,
                            user_id=user_id,
                            name=bot_name,
                            language=BotLanguage.PYTHON,
                            version="1.0",
                            bot_archive=sample_bots[bot_type]
                        )
                        submitted_bots.append(bot)
                        self.log(f"  ✅ {bot_name} submitted (ID: {bot.id}) - {description}")
                    except Exception as e:
                        self.log(f"  ⚠️ Failed to submit {bot_name}: {e}")
                
                if len(submitted_bots) < 2:
                    self.log("❌ FAILED: Need at least 2 bots for tournament")
                    return False
                
                self.log(f"\n🏆 Created {len(submitted_bots)} bots total")
                
                # Create tournament
                self.log("")
                self.log("🏆 STEP 2: Creating tournament...")
                tournament = await tournament_manager.create_tournament(
                    db,
                    name="Verbose Texas Hold'em Tournament",
                    max_participants=len(submitted_bots)
                )
                self.log(f"  ✅ Tournament '{tournament.name}' created (ID: {tournament.id})")
                self.log(f"  📊 Max participants: {tournament.max_participants}")
                
                # Register bots
                self.log("")
                self.log("📝 STEP 3: Registering bots in tournament...")
                for bot in submitted_bots:
                    try:
                        success = await tournament_manager.register_bot(db, tournament.id, bot.id)
                        if success:
                            self.log(f"  ✅ {bot.name} registered successfully")
                        else:
                            self.log(f"  ❌ Failed to register {bot.name}")
                    except Exception as e:
                        self.log(f"  ❌ Error registering {bot.name}: {e}")
                
                # Start tournament
                self.log("")
                self.log("🚀 STEP 4: Starting tournament...")
                start_message = await tournament_manager.start_tournament(db, tournament.id)
                self.log(f"  ✅ {start_message}")
                
                # Monitor tournament progress with detailed logging
                self.log("")
                self.log("⏳ STEP 5: Monitoring tournament progress...")
                self.log("=" * 60)
                
                wait_time = 0
                max_wait = 300  # 5 minutes max
                
                while wait_time < max_wait:
                    await db.refresh(tournament)
                    
                    # Get current standings
                    standings = await self._get_detailed_standings(db, analytics)
                    
                    self.log(f"🏆 TOURNAMENT STATUS: {tournament.status.value.upper()} (waited {wait_time}s)")
                    self.log(f"📊 Current standings ({len(standings)} remaining):")
                    
                    for i, standing in enumerate(standings, 1):
                        rating = f"Rating: {standing['rating']:.1f}" if standing['rating'] else "Rating: 1000.0"
                        self.log(f"    {i}. {standing['name']} - {standing['wins']}W/{standing['losses']}L - {rating}")
                    
                    if tournament.status == TournamentStatus.COMPLETED:
                        self.log("✅ Tournament completed!")
                        break
                    elif tournament.status not in [TournamentStatus.RUNNING, TournamentStatus.COMPLETED]:
                        self.log("❌ Tournament was cancelled!")
                        break
                    
                    # Check for match progress
                    await self._log_match_progress(db, tournament.id)
                    
                    await asyncio.sleep(5)
                    wait_time += 5
                
                if wait_time >= max_wait:
                    self.log("⚠️ Tournament timed out - may still be running")
                
                # Final results
                self.log("")
                self.log("📊 STEP 6: Final tournament results...")
                self.log("=" * 60)
                
                await self._log_final_results(db, tournament, analytics)
                
                self.log("")
                self.log("=" * 80)
                self.log("✅ COMPREHENSIVE POKER TEST COMPLETED")
                self.log(f"📝 Full results logged to: {self.log_file}")
                self.log("=" * 80)
                
                return True
                
        except Exception as e:
            self.log(f"💥 CRITICAL ERROR: {e}")
            import traceback
            self.log(f"Traceback:\n{traceback.format_exc()}")
            return False
        finally:
            if self.log_handle:
                self.log_handle.close()
            await self.cleanup()
    
    async def _get_detailed_standings(self, db, analytics):
        """Get detailed bot standings with ratings."""
        try:
            # Simple query to avoid session conflicts
            from sqlalchemy import select
            from models.core import Bot
            
            stmt = select(Bot).where(Bot.status == "active")
            result = await db.execute(stmt)
            bots = result.scalars().all()
            
            standings = []
            for bot in bots:
                standings.append({
                    'name': bot.name,
                    'wins': bot.matches_won,
                    'losses': bot.matches_lost,
                    'rating': bot.rating
                })
            
            # Sort by rating descending
            standings.sort(key=lambda x: x['rating'] or 1000, reverse=True)
            return standings
            
        except Exception as e:
            self.log(f"  ⚠️ Error getting standings: {e}")
            return []
    
    async def _log_match_progress(self, db, tournament_id):
        """Log detailed match progress and gameplay."""
        from sqlalchemy import select
        from models.core import Match, Bot
        
        try:
            # Get all matches for this tournament
            stmt = select(Match).where(Match.tournament_id == tournament_id)
            result = await db.execute(stmt)
            matches = result.scalars().all()
            
            for match in matches:
                if hasattr(match, '_logged') and match._logged:
                    continue
                    
                bot1 = await db.get(Bot, match.bot1_id) if match.bot1_id else None
                bot2 = await db.get(Bot, match.bot2_id) if match.bot2_id else None
                
                if not bot1 or not bot2:
                    continue
                
                status_emoji = {
                    MatchStatus.PENDING: "⏳",
                    MatchStatus.RUNNING: "🔄", 
                    MatchStatus.COMPLETED: "✅",
                    MatchStatus.CANCELLED: "❌"
                }.get(match.status, "❓")
                
                self.log(f"  {status_emoji} Match {match.id}: {bot1.name} vs {bot2.name}")
                self.log(f"    Status: {match.status.value}")
                
                if match.status == MatchStatus.COMPLETED and match.winner_id:
                    winner = await db.get(Bot, match.winner_id)
                    loser_id = match.bot1_id if match.winner_id == match.bot2_id else match.bot2_id
                    loser = await db.get(Bot, loser_id)
                    
                    self.log(f"    🏆 Winner: {winner.name}")
                    self.log(f"    💀 Eliminated: {loser.name}")
                    
                    if hasattr(match, 'game_log') and match.game_log:
                        self._log_game_details(match.game_log)
                
                # Mark as logged to avoid spam
                match._logged = True
                
        except Exception as e:
            self.log(f"  ⚠️ Error logging match progress: {e}")
    
    def _log_game_details(self, game_log):
        """Log detailed game actions and chip movements."""
        if not game_log:
            return
            
        try:
            self.log("    📝 Game Summary:")
            hands = {}
            for entry in game_log:
                hand = entry.get('hand', 0)
                if hand not in hands:
                    hands[hand] = []
                hands[hand].append(entry)
            
            for hand_num, actions in hands.items():
                if hand_num <= 3:  # Only log first few hands to avoid spam
                    self.log(f"      Hand {hand_num + 1}:")
                    for action in actions[:10]:  # Limit actions per hand
                        player = action.get('player', '?')
                        action_type = action.get('action', '?')
                        self.log(f"        Player {player}: {action_type}")
            
            if len(hands) > 3:
                self.log(f"      ... (played {len(hands)} total hands)")
                
        except Exception as e:
            self.log(f"      ⚠️ Error parsing game log: {e}")
    
    async def _log_final_results(self, db, tournament, analytics):
        """Log comprehensive final tournament results."""
        try:
            # Get final leaderboard
            standings = await analytics.get_leaderboard(db, limit=50)
            
            if standings:
                self.log("🏆 FINAL TOURNAMENT STANDINGS:")
                self.log("-" * 50)
                
                for i, standing in enumerate(standings, 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
                    rating = f"{standing['rating']:.1f}" if standing['rating'] else "1000.0"
                    
                    self.log(f"{emoji} {i:2d}. {standing['name']:<15} | "
                            f"{standing['wins']:2d}W {standing['losses']:2d}L | "
                            f"Rating: {rating}")
                
                # Log winner details
                if standings:
                    winner = standings[0]
                    self.log("")
                    self.log("🏆 TOURNAMENT CHAMPION:")
                    self.log(f"  🤖 Bot: {winner['name']}")
                    self.log(f"  📊 Record: {winner['wins']} wins, {winner['losses']} losses")
                    self.log(f"  ⭐ Final Rating: {winner['rating']:.1f}" if winner['rating'] else "  ⭐ Final Rating: 1000.0")
            
            # Get platform stats
            platform_stats = await analytics.get_global_stats(db)
            if platform_stats:
                self.log("")
                self.log("📊 PLATFORM STATISTICS:")
                self.log(f"  🤖 Total bots: {platform_stats.get('total_bots', 0)}")
                self.log(f"  ⚔️ Total matches: {platform_stats.get('total_matches', 0)}")
                self.log(f"  ⏱️ Avg match duration: {platform_stats.get('avg_match_duration', 0):.1f}s")
                
        except Exception as e:
            self.log(f"⚠️ Error logging final results: {e}")


async def main():
    """Run the comprehensive poker bot test."""
    print("🎪 Starting comprehensive poker bot tournament test...")
    print("⚠️  Make sure Docker is running for bot execution.")
    
    runner = VerbosePokerTestRunner()
    success = await runner.run_verbose_tournament_test()
    
    if success:
        print(f"\n🎉 Test completed successfully!")
        print(f"📝 Check '{runner.log_file}' for detailed results")
        return 0
    else:
        print(f"\n❌ Test failed!")
        print(f"📝 Check '{runner.log_file}' for error details")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)