#!/usr/bin/env python3
"""
Detailed poker game analysis test - shows complete hand-by-hand gameplay
"""

import asyncio
import tempfile
import json
from datetime import datetime

from tests.integration_test_runner import IntegrationTestRunner


class DetailedPokerAnalyzer(IntegrationTestRunner):
    """Run detailed poker analysis with full logging."""
    
    def __init__(self):
        super().__init__()
        self.log_entries = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = f"[{timestamp}] [{level:5}] {message}"
        print(log_msg)
        self.log_entries.append(log_msg)
    
    async def run_single_detailed_match(self):
        """Run a single match with detailed analysis."""
        await self.setup()
        
        try:
            from bots import BotManager
            from tournaments import TournamentManager
            from models.core import Match, Bot, BotLanguage
            
            self.log("Creating two bots for detailed analysis", "SETUP")
            
            async with self.SessionLocal() as db:
                bot_manager = BotManager(str(self.temp_dir / "bots"))
                tournament_manager = TournamentManager(str(self.temp_dir / "bots"))
                
                # Create sample bots
                sample_bots = self.create_sample_bots()
                
                # Submit two bots
                bot1 = await bot_manager.submit_bot(
                    db,
                    user_id="detail_user1",
                    name="DetailBot1", 
                    language=BotLanguage.PYTHON,
                    version="1.0",
                    bot_archive=sample_bots["python_conservative"]
                )
                
                bot2 = await bot_manager.submit_bot(
                    db,
                    user_id="detail_user2", 
                    name="DetailBot2",
                    language=BotLanguage.PYTHON, 
                    version="1.0",
                    bot_archive=sample_bots["python_aggressive"]
                )
                
                self.log(f"Bot 1: {bot1.name} (ID: {bot1.id})", "SETUP")
                self.log(f"Bot 2: {bot2.name} (ID: {bot2.id})", "SETUP")
                
                # Create and start tournament
                tournament = await tournament_manager.create_tournament(
                    db, "Detailed Analysis", max_participants=2
                )
                
                # Register bots
                await tournament_manager.register_bot(db, tournament.id, bot1.id)
                await tournament_manager.register_bot(db, tournament.id, bot2.id)
                
                # Start tournament
                result = await tournament_manager.start_tournament(db, tournament.id)
                self.log(f"Tournament started: {result}", "SETUP")
                
                # Wait for completion
                while True:
                    await db.refresh(tournament)
                    if tournament.status.value == "completed":
                        break
                    await asyncio.sleep(1)
                
                # Get match results using SQLAlchemy query
                from sqlalchemy import select
                result = await db.execute(
                    select(Match).where(Match.tournament_id == tournament.id)
                )
                matches = result.scalars().all()
                
                if matches:
                    match = matches[0]
                    
                    self.log(f"Match completed: {bot1.name} vs {bot2.name}", "MATCH")
                    self.log(f"Winner ID: {match.winner_id}", "RESULT") 
                    self.log(f"Final scores: {match.bot1_score} - {match.bot2_score}", "RESULT")
                    
                    # Analyze detailed log
                    if match.game_log and 'detailed_log' in match.game_log:
                        self.analyze_detailed_log(match.game_log['detailed_log'])
                    
                    return {
                        "bot1_name": bot1.name,
                        "bot2_name": bot2.name,
                        "winner_id": match.winner_id,
                        "bot1_score": match.bot1_score,
                        "bot2_score": match.bot2_score,
                        "game_log": match.game_log
                    }
            
        finally:
            await self.cleanup()
    
    def analyze_detailed_log(self, detailed_log):
        """Analyze the detailed game log."""
        self.log("ANALYZING DETAILED POKER GAMEPLAY", "ANALYSIS")
        self.log("=" * 60, "ANALYSIS")
        
        hand_count = 0
        
        for entry in detailed_log:
            event = entry.get("event", "")
            
            if event == "match_start":
                self.log(f"Match started: {entry['bot1_name']} vs {entry['bot2_name']}", "MATCH")
                self.log(f"Starting stacks: {entry['starting_stacks']}", "MATCH")
                
            elif event == "hand_start":
                hand_count += 1
                self.log(f"\n--- HAND #{entry['hand_number']} ---", "HAND")
                self.log(f"Stacks before: {entry['stacks_before']}", "HAND")
                self.log(f"Button player: {entry['button_player']}", "HAND")
                
                # Show hole cards
                if 'hole_cards' in entry:
                    self.log(f"Player 0 hole cards: {entry['hole_cards']['player_0']}", "CARDS")
                    self.log(f"Player 1 hole cards: {entry['hole_cards']['player_1']}", "CARDS")
                
                self.log(f"Pot after blinds: {entry['pot_after_blinds']}", "HAND")
                
            elif event == "player_action":
                street_info = f" ({entry['pre_action_state']['street_name']})" if 'pre_action_state' in entry and 'street_name' in entry['pre_action_state'] else ""
                self.log(f"Player {entry['player']} ({entry['player_name']}) {street_info}: {entry['action']}", "ACTION")
                self.log(f"  Legal actions: {entry['legal_actions']}", "ACTION")
                self.log(f"  Call amount: {entry['call_amount']}", "ACTION")
                
                # Show community cards if available
                if 'pre_action_state' in entry and 'community_cards' in entry['pre_action_state']:
                    community = entry['pre_action_state']['community_cards']
                    if community:
                        self.log(f"  Community cards: {community}", "CARDS")
                
            elif event == "action_result":
                self.log(f"  Result: Stack → {entry['stack_after']} (change: {entry['stack_change']})", "RESULT")
                self.log(f"  Pot size: {entry['pot_after']}", "RESULT")
                self.log(f"  Current bets: {entry['current_bets_after']}", "RESULT")
                
            elif event == "hand_end":
                self.log(f"\n*** HAND END ***", "HAND")
                self.log(f"Winner: {entry['winner_name']}", "HAND")
                
                # Show final community cards
                if 'final_community_cards' in entry:
                    self.log(f"Final board: {entry['final_community_cards']}", "CARDS")
                
                # Show hole cards
                if 'hole_cards' in entry:
                    self.log(f"Player 0 showed: {entry['hole_cards']['player_0']}", "CARDS")
                    self.log(f"Player 1 showed: {entry['hole_cards']['player_1']}", "CARDS")
                
                self.log(f"Pot size: {entry['pot_size']}", "HAND")
                self.log(f"Final scores: {entry['final_scores']}", "HAND")
                
            elif event == "match_end":
                self.log(f"\n*** MATCH END ***", "MATCH")
                self.log(f"Total hands played: {entry['total_hands']}", "MATCH")
                self.log(f"Match winner: {entry['winner_name']}", "MATCH")
                self.log(f"Final match scores: {entry['final_scores']}", "MATCH")
                
        self.log(f"\nAnalysis complete: {hand_count} hands analyzed", "ANALYSIS")


async def main():
    """Run detailed poker analysis."""
    analyzer = DetailedPokerAnalyzer()
    
    print("DETAILED POKER GAME ANALYSIS")
    print("=" * 50)
    
    try:
        match_result = await analyzer.run_single_detailed_match()
        
        # Save detailed log to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detailed_poker_analysis_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            for log_entry in analyzer.log_entries:
                f.write(log_entry + "\n")
            
            # Also save raw match data
            f.write("\n" + "="*60 + "\n")
            f.write("RAW MATCH DATA\n")
            f.write("="*60 + "\n")
            f.write(json.dumps(match_result, indent=2, default=str))
        
        print(f"\nAnalysis complete! Detailed log saved to: {filename}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())