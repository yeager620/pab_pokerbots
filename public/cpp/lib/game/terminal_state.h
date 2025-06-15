#ifndef TERMINAL_STATE_H
#define TERMINAL_STATE_H

#include <array>
#include <memory>
#include <string>

class RoundState;

class TerminalState {
private:
    std::array<int, 2> deltas;
    std::array<bool, 2> bountyHits;
    bool hasBountyHits;
    std::shared_ptr<RoundState> previousState;

public:
    TerminalState(const std::array<int, 2>& deltas,
                  const std::array<bool, 2>* bountyHits,
                  std::shared_ptr<RoundState> previousState)
        : deltas(deltas), 
          hasBountyHits(bountyHits != nullptr),
          previousState(previousState) {
        if (bountyHits) {
            this->bountyHits = *bountyHits;
        }
    }

    const std::array<int, 2>& getDeltas() const {
        return deltas;
    }

    const std::array<bool, 2>* getBountyHits() const {
        return hasBountyHits ? &bountyHits : nullptr;
    }

    std::shared_ptr<RoundState> getPreviousState() const {
        return previousState;
    }
};

#endif
