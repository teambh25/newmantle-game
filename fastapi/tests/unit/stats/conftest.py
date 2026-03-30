from app.features.stats.dto import QuizResultEntry


def make_entry(
    status: str, guess_count: int = 0, hint_count: int = 0
) -> QuizResultEntry:
    """Create a result_map entry."""
    return QuizResultEntry(
        status=status,
        guess_count=guess_count,
        hint_count=hint_count,
    )
