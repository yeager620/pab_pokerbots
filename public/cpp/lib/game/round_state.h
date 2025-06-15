#ifndef ROUND_STATE_H
#define ROUND_STATE_H

#include <array>
#include <memory>
#include <string>
#include <vector>
#include <variant>
#include <unordered_set>
#include <algorithm>
#include "game_constants.h"
#include "poker_moves.h"
#include "terminal_state.h"

class RoundState : public std::enable_shared_from_this<RoundState> {
private:
    int button;
    int street;
    std::array<int, 2> pips;
    std::array<int, 2> stacks;
    std::array<std::vector<std::string>, 2> hands;
    std::array<std::string, 2> bounties;
    std::vector<std::string> deck;
    std::shared_ptr<RoundState> previousState;

public:
    RoundState(int button, int street,
               const std::array<int, 2>& pips, 
               const std::array<int, 2>& stacks,
               const std::array<std::vector<std::string>, 2>& hands, 
               const std::array<std::string, 2>& bounties,
               const std::vector<std::string>& deck, 
               std::shared_ptr<RoundState> previousState)
        : button(button), street(street), pips(pips), stacks(stacks),
          hands(hands), bounties(bounties), deck(deck), previousState(previousState) {}

    int getButton() const {
        return button;
    }

    int getStreet() const {
        return street;
    }

    const std::array<int, 2>& getPips() const {
        return pips;
    }

    const std::array<int, 2>& getStacks() const {
        return stacks;
    }

    const std::array<std::vector<std::string>, 2>& getHands() const {
        return hands;
    }

    const std::array<std::string, 2>& getBounties() const {
        return bounties;
    }

    const std::vector<std::string>& getDeck() const {
        return deck;
    }

    std::shared_ptr<RoundState> getPreviousState() const {
        return previousState;
    }

    std::array<bool, 2> getBountyHits() const {
        std::array<bool, 2> hits = {false, false};

        if (bounties[0] != "-1") {
            char bountyRank = bounties[0][0];
            for (const auto& card : hands[0]) {
                if (!card.empty() && card[0] == bountyRank) {
                    hits[0] = true;
                    break;
                }
            }
            if (!hits[0]) {
                for (const auto& card : deck) {
                    if (!card.empty() && card[0] == bountyRank) {
                        hits[0] = true;
                        break;
                    }
                }
            }
        }

        if (bounties[1] != "-1") {
            char bountyRank = bounties[1][0];
            for (const auto& card : hands[1]) {
                if (!card.empty() && card[0] == bountyRank) {
                    hits[1] = true;
                    break;
                }
            }
            if (!hits[1]) {
                for (const auto& card : deck) {
                    if (!card.empty() && card[0] == bountyRank) {
                        hits[1] = true;
                        break;
                    }
                }
            }
        }

        return hits;
    }

    std::shared_ptr<TerminalState> showdown() const {
        return std::make_shared<TerminalState>(std::array<int, 2>{0, 0}, nullptr, 
                                              std::const_pointer_cast<RoundState>(shared_from_this()));
    }

    std::unordered_set<PokerMove::Type> getLegalActions() const {
        int active = button % 2;
        int continueCost = pips[1 - active] - pips[active];
        std::unordered_set<PokerMove::Type> actions;

        if (continueCost == 0) {
            bool betsForbidden = stacks[0] == 0 || stacks[1] == 0;
            actions.insert(PokerMove::Type::CHECK);
            actions.insert(PokerMove::Type::FOLD);

            if (!betsForbidden) {
                actions.insert(PokerMove::Type::RAISE);
            }
        } else {
            bool raisesForbidden = continueCost == stacks[active] || stacks[1 - active] == 0;
            actions.insert(PokerMove::Type::FOLD);
            actions.insert(PokerMove::Type::CALL);

            if (!raisesForbidden) {
                actions.insert(PokerMove::Type::RAISE);
            }
        }

        return actions;
    }

    std::array<int, 2> getRaiseBounds() const {
        int active = button % 2;
        int continueCost = pips[1 - active] - pips[active];
        int maxContribution = std::min(stacks[active], stacks[1 - active] + continueCost);
        int minContribution = std::min(maxContribution, 
                                      continueCost + std::max(continueCost, GameConstants::BIG_BLIND));

        return {pips[active] + minContribution, pips[active] + maxContribution};
    }

    std::variant<std::shared_ptr<RoundState>, std::shared_ptr<TerminalState>> proceedStreet() const {
        if (street == 5) {
            return showdown();
        }

        int newStreet = street == 0 ? 3 : street + 1;

        return std::make_shared<RoundState>(1, newStreet, std::array<int, 2>{0, 0}, stacks,
                                           hands, bounties, deck, 
                                           std::const_pointer_cast<RoundState>(shared_from_this()));
    }

    std::variant<std::shared_ptr<RoundState>, std::shared_ptr<TerminalState>> proceed(const PokerMove& action) const {
        int active = button % 2;

        if (action.getType() == PokerMove::Type::FOLD) {
            int delta = active == 0 ? stacks[0] - GameConstants::STARTING_STACK 
                                    : GameConstants::STARTING_STACK - stacks[1];
            return std::make_shared<TerminalState>(std::array<int, 2>{delta, -delta}, &getBountyHits(), 
                                                  std::const_pointer_cast<RoundState>(shared_from_this()));
        }

        if (action.getType() == PokerMove::Type::CALL) {
            if (button == 0) {
                return std::make_shared<RoundState>(1, 0, 
                                                  std::array<int, 2>{GameConstants::BIG_BLIND, GameConstants::BIG_BLIND},
                                                  std::array<int, 2>{GameConstants::STARTING_STACK - GameConstants::BIG_BLIND, 
                                                                    GameConstants::STARTING_STACK - GameConstants::BIG_BLIND},
                                                  hands, bounties, deck, 
                                                  std::const_pointer_cast<RoundState>(shared_from_this()));
            }

            std::array<int, 2> newPips = pips;
            std::array<int, 2> newStacks = stacks;
            int contribution = newPips[1 - active] - newPips[active];
            newStacks[active] -= contribution;
            newPips[active] += contribution;

            auto state = std::make_shared<RoundState>(button + 1, street, newPips, newStacks, hands, bounties, deck, 
                                                     std::const_pointer_cast<RoundState>(shared_from_this()));
            return state->proceedStreet();
        }

        if (action.getType() == PokerMove::Type::CHECK) {
            if ((street == 0 && button > 0) || button > 1) {
                return proceedStreet();
            }

            return std::make_shared<RoundState>(button + 1, street, pips, stacks, hands, bounties, deck, 
                                               std::const_pointer_cast<RoundState>(shared_from_this()));
        }

        if (action.getType() == PokerMove::Type::RAISE) {
            int amount = dynamic_cast<const RaiseAction&>(action).getAmount();
            std::array<int, 2> newPips = pips;
            std::array<int, 2> newStacks = stacks;
            int contribution = amount - newPips[active];
            newStacks[active] -= contribution;
            newPips[active] += contribution;

            return std::make_shared<RoundState>(button + 1, street, newPips, newStacks, hands, bounties, deck, 
                                               std::const_pointer_cast<RoundState>(shared_from_this()));
        }

        throw std::invalid_argument("Unknown action type");
    }

    std::string toString() const {
        std::string result = "RoundState{button=" + std::to_string(button) +
                             ", street=" + std::to_string(street) +
                             ", pips=[" + std::to_string(pips[0]) + ", " + std::to_string(pips[1]) + "]" +
                             ", stacks=[" + std::to_string(stacks[0]) + ", " + std::to_string(stacks[1]) + "]" +
                             ", bounties=[" + bounties[0] + ", " + bounties[1] + "]" +
                             "}";
        return result;
    }
};

#endif
