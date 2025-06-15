#ifndef POKER_MOVES_H
#define POKER_MOVES_H

#include <string>
#include <memory>

class PokerMove {
public:
    enum class Type {
        FOLD,
        CALL,
        CHECK,
        RAISE
    };

    virtual ~PokerMove() = default;
    virtual Type getType() const = 0;
    virtual std::string toString() const = 0;
    virtual int getAmount() const { return 0; }
};

class FoldAction : public PokerMove {
public:
    Type getType() const override {
        return Type::FOLD;
    }

    std::string toString() const override {
        return "Fold";
    }
};

class CallAction : public PokerMove {
public:
    Type getType() const override {
        return Type::CALL;
    }

    std::string toString() const override {
        return "Call";
    }
};

class CheckAction : public PokerMove {
public:
    Type getType() const override {
        return Type::CHECK;
    }

    std::string toString() const override {
        return "Check";
    }
};

class RaiseAction : public PokerMove {
private:
    int amount;

public:
    explicit RaiseAction(int amount) : amount(amount) {}

    Type getType() const override {
        return Type::RAISE;
    }

    int getAmount() const override {
        return amount;
    }

    std::string toString() const override {
        return "Raise to " + std::to_string(amount);
    }
};

#endif
