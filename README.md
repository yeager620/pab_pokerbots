# Poker at Berkeley PokerBots

The framework is organized to support bots written in different programming languages:

- `python/`: Python implementation
- `java/`: Java implementation (TODO)
- `cpp/`: C++ implementation (TODO)

## Python Implementation

### Structure

- `python/bot_main.py`: Main bot implementation that players should modify
- `python/lib/`:
  - `game/`: Game state and actions
    - `poker_moves.py`: defines poker actions (fold, call, check, raise)
    - `poker_state.py`: Game state representations and logic
  - `base/`:
    - `base_bot.py`: Base bot interface with required methods
  - `engine/`:
    - `engine_client.py`: Communication with the poker engine

### PokerStrategy Class

TODO: add docs

### Game State Information

- `game_state`: overall game information (bankroll, game clock, round number)
- `round_state`: information for the current round (cards, bets, stacks)
- `active`: player index (0 or 1)

## Example Strategy

The default implementation includes a simple randomized strategy
