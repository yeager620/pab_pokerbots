# Poker at Berkeley PokerBots Competition
## [EY] updated 8/11/25

Infra for running a poker bot competition;
participants can create and submit bots that compete against each other in poker tournaments

## Overview

the goal is to:
- provide a platform for developing, testing, submitting, and competing with similarly developed rival poker bots via a unified, intuitive API
- develop core tournament running infrastructure (to be used internally) for efficient, flexible, and simple conduction of pokerbot tournaments by P@B 
- support multiple programming languages, each with their own base implementation and mini-SDK (maybe a better term for this?)
 
### More specifically, pab_pokerbots should provide:
- a game engine that enforces rules and manages gameplay
- bot sandboxing
- tournament management with flexible competition structure and ranking systems
- support for multiple programming languages (Python, Rust, Java, C++, ...)
- bot performance metrics and analytics

## Structure

### Public

contains templates and API for participants ("mini-SDKs"):

- `python/` (in progress)
- `rust/` (in progress)
- `java/` (in progress)
- `cpp/` (in progress)
- `csharp/` (in progress)

Each mini-sdk should include:
- Bot templates with required methods
- Game state representations
- Action definitions
- Engine communication utilities

### Private

#### TODO: actually make this private?

Contains the competition infrastructure and unified API backend:

- `engine/`: Match running and game logic (todo)
- `models/`: Data models for bots, matches, and game logs (todo)
- `tournament/`: Tournament structures and ranking systems (todo)

## setup

### Prereqs

- Python 3.13 or higher
- uv ( package management and virtual environments)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/poker-at-berkeley/pab-pokerbots.git
   cd pab-pokerbots
   ```

2. Set up the environment using uv:
   ```bash
   pip install uv
   
   uv venv
   source .venv/bin/activate  # if on windows: .venv\Scripts\activate
   
   uv pip install -e . # deps install
   ```

> **Important**: contributors / pab board should use uv and not pip or venv for package management and virtual environments (pls)

## dsk usage

### Creating a Bot

1. choose preferred language (Python, Rust, Java, C++, ...)
2. Copy template from the corresponding directory in `public/`
3. Implement strategy by modifying the template

Example (.py):
```python
# TODO: revise dummy python example below
from lib.game.poker_moves import FoldAction, CallAction, CheckAction, RaiseAction
from lib.base.base_bot import BaseBot

class MyPokerBot(BaseBot):
    def get_action(self, game_state, round_state, active):
        # impl strategy here
        return CheckAction() # example action
```

### TODO: add testing docs

## Infra and API usage:

### bot submission 
```bash
curl -X POST "http://localhost:8000/bots" \
  -F "name=MyBot" \
  -F "language=python" \
  -F "version=1.0" \
  -F "user_id=user123" \
  -F "bot_file=@bot.zip"
```

### tournament running
```bash
curl -X POST "http://localhost:8000/tournaments" \
  -F "name=Weekly Tournament" \
  -F "max_participants=8"

curl -X POST "http://localhost:8000/tournaments/1/register" \
  -F "bot_id=1"

curl -X POST "http://localhost:8000/tournaments/1/start"
```

### Viewing Results
```bash
# Leaderboard
curl "http://localhost:8000/leaderboard"

# Tournament standings
curl "http://localhost:8000/tournaments/1/standings"
```

## Acknowledgments

Developed by Poker at Berkeley

#### TODO: there is probably a better way to cite this
Credits to MIT PokerBots and their open-sourced materials for inspo and guidance
