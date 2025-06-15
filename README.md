# Poker at Berkeley PokerBots Competition
## [EY] updated 6/9/25

Infra for running a poker bot competition;
participants can create and submit bots that compete against each other in poker tournaments

## Overview

the goal is to:
- provide a platform for developing, testing, and competing with similarly developed rival poker bots via a unified API.
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

## Usage

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

### Testing Your Bot

####  TODO: add testing docs

tentative heads up match example:

```bash
python -m private.engine.test_match --bot1 path/to/your/bot --bot2 public/python/bot_main.py
```

## License

[uhh probably add this at some point]

## Acknowledgments

Developed by Poker at Berkeley

#### TODO: there is probably a better way to cite this
Credits to MIT PokerBots and their open-sourced materials for inspo and guidance