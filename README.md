# Poker at Berkeley PokerBots

This framework supports bot development in multiple programming languages for the Poker at Berkeley competition.

## Multi-Language Support

The framework is organized to support bots written in different programming languages:

- `python/`: Python implementation
- `java/`: Java implementation (coming soon)
- `cpp/`: C++ implementation (coming soon)

## Python Implementation

### Structure

- `python/bot_main.py`: Main bot implementation that players should modify
- `python/lib/`:
  - `game/`: Game state and actions
    - `poker_moves.py`: Defines poker actions (Fold, Call, Check, Raise)
    - `poker_state.py`: Game state representations and logic
  - `base/`:
    - `base_bot.py`: Base bot interface with required methods
  - `engine/`:
    - `engine_client.py`: Communication with the poker engine

### PokerStrategy Class

TODO: add docs

### Game State Information

- `game_state`: Overall game information (bankroll, game clock, round number)
- `round_state`: information for the current round (cards, bets, stacks)
- `active`: player index (0 or 1)

## Example Strategy

The default implementation includes a simple randomized strategy

## Adding Support for New Languages

To add support for a new language:

1. Create a new directory for the language (e.g., `rust/`)
2. Implement the core functionality (game state, actions, engine communication)
3. Create a bot template that students can modify
4. Add appropriate build and run commands in a commands.json file
