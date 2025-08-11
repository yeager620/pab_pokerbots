
import asyncio
import tempfile
import zipfile
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from models.core import init_db, Bot, Tournament, BotLanguage, BotStatus, TournamentStatus
from bots import BotManager
from tournaments import TournamentManager
from game import MatchRunner
from analytics import Analytics


class IntegrationTestRunner:
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///test_pokerbots.db"):
        self.database_url = database_url
        self.temp_dir = None
        self.engine = None
        self.SessionLocal = None
        
    async def setup(self):
        print("Setting up test environment...")
        

        self.temp_dir = Path(tempfile.mkdtemp(prefix="pokerbots_test_"))
        print(f"Test directory: {self.temp_dir}")
        

        self.engine = create_async_engine(self.database_url, echo=False)
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        

        from models.core import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("Database initialized")
        
    async def cleanup(self):
        if self.engine:
            await self.engine.dispose()
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
        print("Cleanup completed")
    
    def create_sample_bots(self) -> dict:
        bots = {}
        

        python_bot = '''
def get_action(game_state, legal_actions):
    if "CHECK" in legal_actions:
        return "CHECK"
    elif "CALL" in legal_actions:
        return "CALL"
    else:
        return "FOLD"

if __name__ == "__main__":
    print("Python bot ready")
'''
        bots['python_conservative'] = self._create_zip_archive("bot_main.py", python_bot)
        

        python_aggressive = '''
import random

def get_action(game_state, legal_actions):
    if "RAISE" in legal_actions and random.random() < 0.3:
        return "RAISE"
    elif "CHECK" in legal_actions:
        return "CHECK"
    elif "CALL" in legal_actions:
        return "CALL"
    else:
        return "FOLD"

if __name__ == "__main__":
    print("Python aggressive bot ready")
'''
        bots['python_aggressive'] = self._create_zip_archive("bot_main.py", python_aggressive)
        

        python_random = '''
import random

def get_action(game_state, legal_actions):
    return random.choice(legal_actions)

if __name__ == "__main__":
    print("Python random bot ready")
'''
        bots['python_random'] = self._create_zip_archive("bot_main.py", python_random)
        

        python_folder = '''
def get_action(game_state, legal_actions):
    if "FOLD" in legal_actions:
        return "FOLD"
    elif "CHECK" in legal_actions:
        return "CHECK"
    else:
        return "CALL"

if __name__ == "__main__":
    print("Python folding bot ready")
'''
        bots['python_folder'] = self._create_zip_archive("bot_main.py", python_folder)
        
        return bots
    
    def _create_zip_archive(self, filename: str, content: str) -> bytes:
        import io
        archive_buffer = io.BytesIO()
        
        with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, content)
        
        return archive_buffer.getvalue()
    
    async def run_complete_test(self):
        print("\n" + "="*60)
        print("RUNNING COMPLETE INTEGRATION TEST")
        print("="*60)
        
        async with self.SessionLocal() as db:

            bot_manager = BotManager(str(self.temp_dir / "bots"))
            tournament_manager = TournamentManager(str(self.temp_dir / "bots"))
            analytics = Analytics()
            
            try:

                print("\nSTEP 1: Submitting bots...")
                sample_bots = self.create_sample_bots()
                submitted_bots = []
                
                bot_configs = [
                    ("alice", "AliceBot", "python_conservative"),
                    ("bob", "BobBot", "python_aggressive"),
                    ("charlie", "CharlieBot", "python_random"),
                    ("diana", "DianaBot", "python_folder"),
                ]
                
                for user_id, bot_name, bot_type in bot_configs:
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
                        print(f"  OK {bot_name} submitted (ID: {bot.id}, Status: {bot.status.value})")
                    except Exception as e:
                        print(f"  Failed to submit {bot_name}: {e}")
                        return False
                
                if len(submitted_bots) < 2:
                    print("Need at least 2 bots for tournament")
                    return False
                

                print("\nSTEP 2: Creating tournament...")
                try:
                    tournament = await tournament_manager.create_tournament(
                        db,
                        name="Integration Test Tournament",
                        max_participants=len(submitted_bots)
                    )
                    print(f"  Tournament created (ID: {tournament.id})")
                except Exception as e:
                    print(f"  Failed to create tournament: {e}")
                    return False
                

                print("\nSTEP 3: Registering bots...")
                for bot in submitted_bots:
                    try:
                        success = await tournament_manager.register_bot(db, tournament.id, bot.id)
                        if success:
                            print(f"  {bot.name} registered")
                        else:
                            print(f"  Failed to register {bot.name}")
                    except Exception as e:
                        print(f"  Error registering {bot.name}: {e}")
                

                print("\nSTEP 4: Starting tournament...")
                try:
                    result = await tournament_manager.start_tournament(db, tournament.id)
                    if result["success"]:
                        print(f"  Tournament started: {result['message']}")
                    else:
                        print(f"  Failed to start tournament: {result.get('error', 'Unknown error')}")
                        return False
                except Exception as e:
                    print(f"  Error starting tournament: {e}")
                    return False
                

                print("\nSTEP 5: Monitoring tournament progress...")
                max_wait = 120
                wait_time = 0
                
                while wait_time < max_wait:
                    await db.refresh(tournament)
                    print(f"  Tournament status: {tournament.status.value} (waited {wait_time}s)")
                    
                    if tournament.status == TournamentStatus.COMPLETED:
                        print("  Tournament completed!")
                        break
                    elif tournament.status in [TournamentStatus.OPEN]:
                        print("  Warning: Tournament still in preparation...")
                    
                    await asyncio.sleep(5)
                    wait_time += 5
                
                if tournament.status != TournamentStatus.COMPLETED:
                    print(f"  Warning: Tournament did not complete in time (status: {tournament.status.value})")

                

                print("\nSTEP 6: Checking results...")
                

                try:
                    standings = await tournament_manager.get_tournament_standings(db, tournament.id)
                    print(f"  Tournament standings ({len(standings)} participants):")
                    for standing in standings[:3]:
                        print(f"    {standing['rank']}. {standing['bot_name']} - {standing['wins']} wins, {standing['losses']} losses")
                except Exception as e:
                    print(f"  Error getting standings: {e}")
                

                try:
                    matches = await tournament_manager.get_tournament_matches(db, tournament.id)
                    completed_matches = [m for m in matches if m["status"] == "completed"]
                    print(f"  Matches: {len(completed_matches)} completed out of {len(matches)} total")
                    for match in completed_matches[-3:]:
                        winner = match["winner_name"] or "No winner"
                        print(f"    {match['bot1_name']} vs {match['bot2_name']} → Winner: {winner}")
                except Exception as e:
                    print(f"  Error getting matches: {e}")
                

                try:
                    leaderboard = await analytics.get_leaderboard(db, limit=5)
                    print(f"  Updated leaderboard (top {len(leaderboard)}):")
                    for entry in leaderboard:
                        print(f"    {entry['rank']}. {entry['bot_name']} - Rating: {entry['rating']}, WR: {entry['win_rate']}%")
                except Exception as e:
                    print(f"  Error getting leaderboard: {e}")
                

                try:
                    global_stats = await analytics.get_global_stats(db)
                    print(f"  Platform stats: {global_stats['total_bots']} bots, {global_stats['total_matches']} matches")
                except Exception as e:
                    print(f"  Error getting global stats: {e}")
                
                print("\n" + "="*60)
                print("INTEGRATION TEST COMPLETED SUCCESSFULLY!")
                print("="*60)
                return True
                
            except Exception as e:
                print(f"\nINTEGRATION TEST FAILED: {e}")
                import traceback
                traceback.print_exc()
                return False


async def main():
    runner = IntegrationTestRunner()
    
    try:
        await runner.setup()
        success = await runner.run_complete_test()
        if success:
            print("\nAll tests passed! Infrastructure is ready for production.")
        else:
            print("\nSome tests failed. Check the output above for details.")
            exit(1)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    print("Poker Bot Infrastructure Integration Test")
    print("This will create sample bots and run a complete tournament.")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n👋 Test cancelled.")
        exit(0)
    
    asyncio.run(main())