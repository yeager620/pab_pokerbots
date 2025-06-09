# Rust Poker Bot

Rust implementation of the base poker bot

## Structure

- `src/main.rs` - Main entry point and poker strategy implementation
- `src/lib/` - Library code
  - `base/` - Base bot trait
  - `engine/` - Engine client for communication with the poker engine
  - `game/` - Game state and poker moves

## Building and Running

To build the bot:

```bash
cargo build --release
```

To run the bot:

```bash
cargo run --release -- --host <host> <port>
```

## Strategy

current implementation uses same strategy as the Python bot:
- 40% chance to raise the minimum amount if raising is legal
- Always check if checking is legal
- 20% chance to fold otherwise
- Call as a default action