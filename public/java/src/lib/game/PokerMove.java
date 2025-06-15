package lib.game;

public abstract class PokerMove {
    public static class Fold extends PokerMove {
        @Override
        public String toString() {
            return "Fold";
        }
    }

    public static class Call extends PokerMove {
        @Override
        public String toString() {
            return "Call";
        }
    }

    public static class Check extends PokerMove {
        @Override
        public String toString() {
            return "Check";
        }
    }

    public static class Raise extends PokerMove {
        private final int amount;

        public Raise(int amount) {
            this.amount = amount;
        }

        public int getAmount() {
            return amount;
        }

        @Override
        public String toString() {
            return "Raise to " + amount;
        }
    }

    public static Fold fold() {
        return new Fold();
    }

    public static Call call() {
        return new Call();
    }

    public static Check check() {
        return new Check();
    }

    public static Raise raise(int amount) {
        return new Raise(amount);
    }
}