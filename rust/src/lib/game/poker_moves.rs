use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PokerMove {
    Fold,
    Call,
    Check,
    Raise(i32),
}

impl fmt::Display for PokerMove {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PokerMove::Fold => write!(f, "Fold"),
            PokerMove::Call => write!(f, "Call"),
            PokerMove::Check => write!(f, "Check"),
            PokerMove::Raise(amount) => write!(f, "Raise({})", amount),
        }
    }
}

