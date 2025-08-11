#!/usr/bin/env python3
"""
Detailed poker bot test that logs every action, stack change, and game state.
Provides complete visibility into Texas Hold'em gameplay mechanics.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add private directory to path
sys.path.insert(0, str(Path(__file__).parent / "private"))

from tests.integration_test_runner import IntegrationTestRunner
from models.core import BotLanguage, TournamentStatus, MatchStatus


class DetailedPokerLogger(IntegrationTestRunner):
    """Test runner with comprehensive poker gameplay logging."""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///:memory:"):
        super().__init__(database_url)
        self.log_file = f"detailed_poker_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_handle = None
    
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with timestamps and levels."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        log_msg = f"[{timestamp}] [{level:5}] {message}"
        print(log_msg)
        if self.log_handle:
            self.log_handle.write(log_msg + "\n")
            self.log_handle.flush()
    
    async def run_detailed_poker_test(self) -> bool:
        """Run comprehensive test with detailed poker action logging."""
        
        # Open log file
        self.log_handle = open(self.log_file, 'w')
        
        try:
            self.log("=" * 100, "INFO")
            self.log("🎪 DETAILED POKER BOT GAMEPLAY ANALYSIS", "INFO")
            self.log("=" * 100, "INFO")
            self.log(f"📝 Detailed log file: {self.log_file}", "INFO")
            self.log(f"🕐 Test started: {datetime.now().isoformat()}", "INFO")
            self.log("", "INFO")
            
            self.log("🎯 POKER ANALYSIS OBJECTIVES:", "INFO")
            self.log("  • Log every player action (fold/call/check/raise)", "INFO")
            self.log("  • Track chip stacks before and after each action", "INFO") 
            self.log("  • Monitor pot sizes and betting rounds", "INFO")
            self.log("  • Verify Texas Hold'em rules compliance", "INFO")
            self.log("  • Capture complete game state transitions", "INFO")
            self.log("", "INFO")
            
            # Setup
            await self.setup()
            self.log("✅ Database and environment initialized", "INFO")
            
            async with self.SessionLocal() as db:
                from bots import BotManager
                from tournaments import TournamentManager
                from models.core import Match, Bot
                from sqlalchemy import select
                
                bot_manager = BotManager(str(self.temp_dir / "bots"))
                tournament_manager = TournamentManager(str(self.temp_dir / "bots"))
                
                # Create and submit bots
                self.log("", "INFO")
                self.log("🤖 CREATING POKER BOTS...", "INFO")
                self.log("-" * 60, "INFO")
                
                sample_bots = self.create_sample_bots()
                submitted_bots = []
                
                bot_configs = [
                    ("alice", "ConservativeAlice", "python_conservative"),
                    ("bob", "AggressiveBob", "python_aggressive"),
                ]
                
                for user_id, bot_name, bot_type in bot_configs:
                    bot = await bot_manager.submit_bot(
                        db,
                        user_id=user_id,
                        name=bot_name,
                        language=BotLanguage.PYTHON,
                        version="1.0",
                        bot_archive=sample_bots[bot_type]
                    )
                    submitted_bots.append(bot)
                    self.log(f"✅ {bot_name} (Player {len(submitted_bots)-1}) created with starting rating {bot.rating}", "BOT")
                
                # Create and start tournament
                self.log("", "INFO")
                self.log("🏆 STARTING TOURNAMENT...", "INFO")
                
                tournament = await tournament_manager.create_tournament(
                    db, name="Detailed Poker Analysis", max_participants=2
                )
                
                for bot in submitted_bots:
                    await tournament_manager.register_bot(db, tournament.id, bot.id)
                    self.log(f"📝 {bot.name} registered in tournament", "TOUR")
                
                await tournament_manager.start_tournament(db, tournament.id)
                self.log("🚀 Tournament started - waiting for matches to complete...", "TOUR")
                
                # Monitor and log matches
                await self._monitor_and_log_matches(db, tournament.id)
                
                self.log("", "INFO")
                self.log("=" * 100, "INFO")
                self.log("✅ DETAILED POKER ANALYSIS COMPLETED", "INFO")
                self.log(f"📝 Complete gameplay log saved to: {self.log_file}", "INFO")
                self.log("=" * 100, "INFO")
                
                return True
                
        except Exception as e:
            self.log(f"💥 CRITICAL ERROR: {e}", "ERROR")
            import traceback
            self.log(f"Traceback:\n{traceback.format_exc()}", "ERROR")
            return False
        finally:
            if self.log_handle:
                self.log_handle.close()
            await self.cleanup()
    
    async def _monitor_and_log_matches(self, db, tournament_id):
        """Monitor tournament matches and extract detailed gameplay logs."""
        from sqlalchemy import select
        from models.core import Match, Bot
        
        logged_matches = set()
        
        # Wait for matches to complete and log results
        for wait_time in range(0, 120, 5):  # Wait up to 2 minutes
            stmt = select(Match).where(Match.tournament_id == tournament_id)
            result = await db.execute(stmt)
            matches = result.scalars().all()
            
            for match in matches:
                if match.id in logged_matches:
                    continue
                    
                if match.status == MatchStatus.COMPLETED:
                    await self._log_detailed_match(db, match)
                    logged_matches.add(match.id)
            
            # Check if all matches are done
            if all(m.status == MatchStatus.COMPLETED for m in matches):
                break
                
            await asyncio.sleep(5)
    
    async def _log_detailed_match(self, db, match):
        """Extract and log detailed gameplay from match results."""
        from models.core import Bot
        
        bot1 = await db.get(Bot, match.bot1_id)
        bot2 = await db.get(Bot, match.bot2_id)
        
        self.log("", "INFO")
        self.log("=" * 80, "MATCH")
        self.log(f"⚔️  MATCH {match.id}: {bot1.name} vs {bot2.name}", "MATCH")
        self.log("=" * 80, "MATCH")
        
        if not match.game_log or 'detailed_log' not in match.game_log:
            self.log("⚠️ No detailed game log available for this match", "WARN")
            return
        
        detailed_log = match.game_log['detailed_log']
        summary = match.game_log.get('summary', {})
        
        self.log(f"🏆 Winner: {summary.get('winner', 'Unknown')}", "MATCH")
        self.log(f"🎲 Total Hands: {summary.get('total_hands', 0)}", "MATCH") 
        self.log(f"📊 Final Scores: {summary.get('final_scores', [0, 0])}", "MATCH")
        self.log("", "MATCH")
        
        current_hand = 0
        
        for i, log_entry in enumerate(detailed_log):
            event = log_entry.get('event', 'unknown')
            
            if event == 'match_start':
                self.log("🎮 MATCH STARTING:", "GAME")
                self.log(f"   Players: {log_entry['bot1_name']} (Player 0) vs {log_entry['bot2_name']} (Player 1)", "GAME")
                self.log(f"   Starting Stacks: {log_entry['starting_stacks']}", "GAME")
                self.log(f"   Max Hands: {log_entry['max_hands']}", "GAME")
                self.log("", "GAME")
                
            elif event == 'hand_start':
                current_hand = log_entry['hand_number']
                self.log("🃏 " + "=" * 60, "HAND")
                self.log(f"🃏 HAND #{current_hand}", "HAND")
                self.log("🃏 " + "=" * 60, "HAND") 
                self.log(f"   Stacks Before: Player 0: {log_entry['stacks_before'][0]}, Player 1: {log_entry['stacks_before'][1]}", "HAND")
                self.log(f"   Button Player: {log_entry['button_player']}", "HAND")
                self.log(f"   Blinds: Small={log_entry['blinds_posted']['small_blind']}, Big={log_entry['blinds_posted']['big_blind']}", "HAND")
                self.log("", "HAND")
                
            elif event == 'player_action':
                player_name = log_entry['player_name']
                action = log_entry['action']
                stack_before = log_entry['stack_before']
                legal_actions = log_entry['legal_actions']
                continue_cost = log_entry.get('continue_cost', 0)
                
                self.log(f"👤 {player_name} (Player {log_entry['player']}):", "ACTION")
                self.log(f"   💰 Stack: {stack_before} chips", "ACTION")
                self.log(f"   🎯 Legal Actions: {legal_actions}", "ACTION")
                if continue_cost > 0:
                    self.log(f"   💸 Cost to Continue: {continue_cost} chips", "ACTION")
                self.log(f"   ✅ ACTION: {action}", "ACTION")
                
            elif event == 'action_result':
                player_name = log_entry['player_name']
                action = log_entry['action']
                stack_after = log_entry['stack_after']
                stack_change = log_entry['stack_change']
                pot_total = log_entry['pot_total']
                
                self.log(f"📈 Result for {player_name}:", "RESULT")
                self.log(f"   💰 Stack After: {stack_after} chips", "RESULT")
                if stack_change != 0:
                    change_str = f"+{stack_change}" if stack_change > 0 else str(stack_change)
                    self.log(f"   📊 Stack Change: {change_str} chips", "RESULT")
                self.log(f"   🏆 Total Pot: {pot_total} chips", "RESULT")
                self.log(f"   ⏭️  Game Continues: {log_entry['game_continues']}", "RESULT")
                self.log("", "RESULT")
                
            elif event == 'hand_end':
                winner_name = log_entry['winner_name']
                pot_won = log_entry['pot_won']
                final_stacks = log_entry['final_stacks']
                
                self.log("🏁 HAND RESULT:", "HAND")
                self.log(f"   🏆 Winner: {winner_name} (Player {log_entry['winner']})", "HAND")
                self.log(f"   💰 Pot Won: {pot_won} chips", "HAND")
                self.log(f"   📊 Final Stacks: Player 0: {final_stacks[0]}, Player 1: {final_stacks[1]}", "HAND")
                self.log("", "HAND")
                
            elif event == 'match_end':
                self.log("🏁 MATCH COMPLETE:", "MATCH")
                self.log(f"   🏆 Winner: {log_entry['winner_name']} (Player {log_entry['winner']})", "MATCH")
                self.log(f"   🎲 Total Hands Played: {log_entry['total_hands']}", "MATCH")
                self.log(f"   📊 Final Scores: {log_entry['final_scores']}", "MATCH")
                self.log("", "MATCH")
        
        self.log("=" * 80, "MATCH")
        self.log(f"✅ Match {match.id} analysis complete", "MATCH")
        self.log("=" * 80, "MATCH")


async def main():
    """Run the detailed poker gameplay analysis."""
    print("🎪 Starting detailed poker gameplay analysis...")
    print("⚠️  Make sure Docker is running for bot execution.")
    print()
    
    logger = DetailedPokerLogger()
    success = await logger.run_detailed_poker_test()
    
    if success:
        print(f"\n🎉 Detailed poker analysis completed successfully!")
        print(f"📝 Check '{logger.log_file}' for complete gameplay details")
        return 0
    else:
        print(f"\n❌ Analysis failed!")
        print(f"📝 Check '{logger.log_file}' for error details")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)