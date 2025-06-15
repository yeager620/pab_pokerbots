#include <iostream>
#include <random>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdlib>
#include "lib/base/base_bot.h"
#include "lib/engine/runner.h"
#include "lib/game/game_constants.h"
#include "lib/game/game_state.h"
#include "lib/game/poker_moves.h"
#include "lib/game/round_state.h"
#include "lib/game/terminal_state.h"

class PokerStrategy : public BaseBot {
private:
    std::mt19937 rng;
    std::uniform_real_distribution<double> dist;

public:
    PokerStrategy() : rng(std::random_device()()), dist(0.0, 1.0) {}

    void handleNewRound(const GameState& gameState, const RoundState& roundState, int active) override {
    }

    void handleRoundOver(const GameState& gameState, const TerminalState& terminalState, int active) override {
        const std::array<bool, 2>* bountyHits = terminalState.getBountyHits();
        if (bountyHits && (*bountyHits)[active]) {
            std::string bountyRank = terminalState.getPreviousState()->getBounties()[active];
            std::cout << "Hit bounty of " << bountyRank << "!" << std::endl;
        }
    }

    PokerMove getAction(const GameState& gameState, const RoundState& roundState, int active) override {
        auto legalActions = roundState.getLegalActions();
        int street = roundState.getStreet();
        const auto& myCards = roundState.getHands()[active];
        std::vector<std::string> boardCards(roundState.getDeck().begin(), 
                                           roundState.getDeck().begin() + street);
        int myPip = roundState.getPips()[active];
        int oppPip = roundState.getPips()[1 - active];
        int myStack = roundState.getStacks()[active];
        int oppStack = roundState.getStacks()[1 - active];
        int continueCost = oppPip - myPip;
        std::string myBounty = roundState.getBounties()[active];

        if (legalActions.find(PokerMove::Type::RAISE) != legalActions.end()) {
            auto raiseBounds = roundState.getRaiseBounds();
            if (dist(rng) < 0.4) {
                return RaiseAction(raiseBounds[0]);
            }
        }

        if (legalActions.find(PokerMove::Type::CHECK) != legalActions.end()) {
            return CheckAction();
        }

        if (dist(rng) < 0.2) {
            return FoldAction();
        }

        return CallAction();
    }
};

bool parseArgs(int argc, char* argv[], std::string& host, int& port) {
    host = "localhost";
    port = 0;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--host" && i + 1 < argc) {
            host = argv[++i];
        } else {
            try {
                port = std::stoi(arg);
            } catch (const std::exception& e) {
                std::cerr << "Invalid port: " << arg << std::endl;
                return false;
            }
        }
    }

    if (port == 0) {
        std::cerr << "Port is required" << std::endl;
        return false;
    }

    return true;
}

int main(int argc, char* argv[]) {
    std::string host;
    int port;

    if (!parseArgs(argc, argv, host, port)) {
        return 1;
    }

    PokerStrategy strategy;
    Runner::runBot(&strategy, host, port);
    return 0;
}