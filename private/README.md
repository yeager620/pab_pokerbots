# PAB PokerBots - Simplified Infrastructure

Streamlined Python backend for the poker bot competition platform.

## Project Structure

```
private/
├── models/
│   └── core.py           # All database models (Bot, Tournament, Match, etc.)
├── api.py                # Unified FastAPI application with all endpoints
├── bots.py               # Bot submission, validation, and management
├── tournaments.py        # Tournament management (single-elimination)
├── game.py               # Poker game engine and match execution
├── analytics.py          # ELO ratings and leaderboards
├── config.py             # Simple configuration management
├── pyproject.toml        # Dependencies and build configuration
└── README.md             # This file
```

## Core Components

### Database Models (`models/core.py`)
- **Bot**: Bot information, ratings, match statistics
- **Tournament**: Tournament structure and participants
- **Match**: Individual matches between bots
- **ELO Rating System**: Built-in rating calculations

### API (`api.py`)
FastAPI application with endpoints for:
- Bot submission and management
- Tournament creation and registration
- Match execution
- Analytics and leaderboards

### Bot Management (`bots.py`)
- Bot submission with file validation
- Multi-language support (Python, Rust, Java, C++)
- Docker-based bot execution
- File storage management

### Tournament System (`tournaments.py`)
- Single-elimination tournaments
- Bracket generation
- Automated match scheduling

### Game Engine (`game.py`)
- Simplified poker game logic
- Docker-based bot isolation
- Match execution and scoring

### Analytics (`analytics.py`)
- ELO rating system
- Leaderboards
- Performance statistics
- Head-to-head comparisons

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Start the API server**:
   ```bash
   python -m private.api
   ```

3. **Submit a bot**:
   ```bash
   curl -X POST "http://localhost:8000/bots" \
     -F "name=MyBot" \
     -F "language=python" \
     -F "version=1.0" \
     -F "user_id=user123" \
     -F "bot_file=@bot.zip"
   ```

4. **Create and start a tournament**:
   ```bash
   # Create tournament
   curl -X POST "http://localhost:8000/tournaments" \
     -F "name=Test Tournament" \
     -F "max_participants=8"
   
   # Register bots
   curl -X POST "http://localhost:8000/tournaments/1/register" \
     -F "bot_id=1"
   
   # Start tournament
   curl -X POST "http://localhost:8000/tournaments/1/start"
   ```

## Configuration

Environment variables (optional):
- `DATABASE_URL`: Database connection string
- `BOT_STORAGE_DIR`: Bot file storage directory
- `PORT`: API server port
- `MAX_HANDS_PER_MATCH`: Hands per match limit

## Bot Requirements

Bots must include:
- **Python**: `bot_main.py` with required functions
- **Rust**: `src/main.rs` and `Cargo.toml`  
- **Java**: `src/BotMain.java`
- **C++**: `bot_main.cpp`

## API Endpoints

- `GET /health` - Health check
- `POST /bots` - Submit bot
- `GET /bots/{id}` - Get bot details
- `POST /tournaments` - Create tournament
- `POST /tournaments/{id}/register` - Register bot
- `POST /tournaments/{id}/start` - Start tournament
- `GET /leaderboard` - Get leaderboard
- `GET /stats/global` - Global statistics

See `/docs` for complete API documentation.

## Development

The infrastructure is designed to be:
- **Simple**: Single-file modules with clear responsibilities
- **Robust**: Basic error handling and validation
- **Scalable**: Async/await throughout, Docker isolation
- **Maintainable**: Minimal dependencies, clear structure

Core philosophy: Essential functionality only, no over-engineering.