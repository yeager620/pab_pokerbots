#ifndef ENGINE_CLIENT_H
#define ENGINE_CLIENT_H

#include <array>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include <variant>
#include "../base/base_bot.h"
#include "../game/game_constants.h"
#include "../game/game_state.h"
#include "../game/poker_moves.h"
#include "../game/round_state.h"
#include "../game/terminal_state.h"

class EngineClient {
private:
    BaseBot& pokerbot;
    std::istream& in;
    std::ostream& out;

public:
    EngineClient(BaseBot& pokerbot, std::istream& in, std::ostream& out)
        : pokerbot(pokerbot), in(in), out(out) {}

    void send(const PokerMove& action) {
        std::string code;
        switch (action.getType()) {
            case PokerMove::Type::FOLD:
                code = "F";
                break;
            case PokerMove::Type::CALL:
                code = "C";
                break;
            case PokerMove::Type::CHECK:
                code = "K";
                break;
            case PokerMove::Type::RAISE:
                code = "R" + std::to_string(action.getAmount());
                break;
        }
        out << code << std::endl;
    }

    void run() {
        GameState gameState(0, 0.0, 1);
        std::shared_ptr<RoundState> roundState = nullptr;
        int active = 0;
        bool roundFlag = true;

        std::string line;
        while (std::getline(in, line)) {
            std::istringstream iss(line);
            std::string clause;
            while (iss >> clause) {
                if (clause.empty()) {
                    continue;
                }

                char firstChar = clause[0];
                std::string rest = clause.substr(1);

                switch (firstChar) {
                    case 'T': {
                        double time = std::stod(rest);
                        gameState = GameState(gameState.getBankroll(), time, gameState.getRoundNum());
                        break;
                    }
                    case 'P': {
                        active = static_cast<int>(std::stod(rest));
                        break;
                    }
                    case 'H': {
                        std::array<std::vector<std::string>, 2> hands;
                        std::istringstream handStream(rest);
                        std::string card;
                        while (std::getline(handStream, card, ',')) {
                            hands[active].push_back(card);
                        }
                        std::array<int, 2> pips = {GameConstants::SMALL_BLIND, GameConstants::BIG_BLIND};
                        std::array<int, 2> stacks = {
                            GameConstants::STARTING_STACK - GameConstants::SMALL_BLIND,
                            GameConstants::STARTING_STACK - GameConstants::BIG_BLIND
                        };
                        std::array<std::string, 2> bounties = {"-1", "-1"};
                        roundState = std::make_shared<RoundState>(0, 0, pips, stacks, hands, bounties, 
                                                                std::vector<std::string>(), nullptr);
                        break;
                    }
                    case 'G': {
                        if (roundState) {
                            std::array<std::string, 2> bounties = roundState->getBounties();
                            bounties[active] = rest;
                            roundState = std::make_shared<RoundState>(
                                roundState->getButton(), roundState->getStreet(),
                                roundState->getPips(), roundState->getStacks(),
                                roundState->getHands(), bounties, roundState->getDeck(),
                                roundState->getPreviousState()
                            );
                            if (roundFlag) {
                                pokerbot.handleNewRound(gameState, *roundState, active);
                                roundFlag = false;
                            }
                        }
                        break;
                    }
                    case 'F': {
                        if (roundState) {
                            auto result = roundState->proceed(FoldAction());
                            if (std::holds_alternative<std::shared_ptr<RoundState>>(result)) {
                                roundState = std::get<std::shared_ptr<RoundState>>(result);
                            }
                        }
                        break;
                    }
                    case 'C': {
                        if (roundState) {
                            auto result = roundState->proceed(CallAction());
                            if (std::holds_alternative<std::shared_ptr<RoundState>>(result)) {
                                roundState = std::get<std::shared_ptr<RoundState>>(result);
                            }
                        }
                        break;
                    }
                    case 'K': {
                        if (roundState) {
                            auto result = roundState->proceed(CheckAction());
                            if (std::holds_alternative<std::shared_ptr<RoundState>>(result)) {
                                roundState = std::get<std::shared_ptr<RoundState>>(result);
                            }
                        }
                        break;
                    }
                    case 'R': {
                        if (roundState) {
                            int amount = std::stoi(rest);
                            auto result = roundState->proceed(RaiseAction(amount));
                            if (std::holds_alternative<std::shared_ptr<RoundState>>(result)) {
                                roundState = std::get<std::shared_ptr<RoundState>>(result);
                            }
                        }
                        break;
                    }
                    case 'B': {
                        if (roundState) {
                            std::vector<std::string> deck;
                            std::istringstream deckStream(rest);
                            std::string card;
                            while (std::getline(deckStream, card, ',')) {
                                deck.push_back(card);
                            }
                            roundState = std::make_shared<RoundState>(
                                roundState->getButton(), roundState->getStreet(),
                                roundState->getPips(), roundState->getStacks(),
                                roundState->getHands(), roundState->getBounties(), deck,
                                roundState->getPreviousState()
                            );
                        }
                        break;
                    }
                    case 'O': {
                        if (roundState && roundState->getPreviousState()) {
                            auto prevState = roundState->getPreviousState();
                            auto hands = prevState->getHands();
                            std::istringstream handStream(rest);
                            std::string card;
                            hands[1 - active].clear();
                            while (std::getline(handStream, card, ',')) {
                                hands[1 - active].push_back(card);
                            }
                            auto newState = std::make_shared<RoundState>(
                                prevState->getButton(), prevState->getStreet(),
                                prevState->getPips(), prevState->getStacks(),
                                hands, prevState->getBounties(), prevState->getDeck(),
                                prevState->getPreviousState()
                            );
                            roundState = newState;
                        }
                        break;
                    }
                    case 'D': {
                        if (roundState) {
                            int delta = std::stoi(rest);
                            std::array<int, 2> deltas = {-delta, -delta};
                            deltas[active] = delta;
                            gameState = GameState(gameState.getBankroll() + delta,
                                                gameState.getGameClock(), gameState.getRoundNum());
                        }
                        break;
                    }
                    case 'Y': {
                        if (roundState) {
                            bool heroHitBounty = rest[0] == '1';
                            bool opponentHitBounty = rest[1] == '1';
                            std::array<bool, 2> bountyHits = active == 1 ?
                                std::array<bool, 2>{opponentHitBounty, heroHitBounty} :
                                std::array<bool, 2>{heroHitBounty, opponentHitBounty};
                            auto terminalState = TerminalState(std::array<int, 2>{0, 0}, &bountyHits, roundState);
                            pokerbot.handleRoundOver(gameState, terminalState, active);
                            gameState = GameState(gameState.getBankroll(), gameState.getGameClock(),
                                                gameState.getRoundNum() + 1);
                            roundFlag = true;
                        }
                        break;
                    }
                    case 'Q': {
                        return;
                    }
                }
            }

            if (roundFlag) {
                send(CheckAction());
            } else if (roundState) {
                assert(active == roundState->getButton() % 2);
                PokerMove action = pokerbot.getAction(gameState, *roundState, active);
                send(action);
            }
        }
    }
};

#endif
