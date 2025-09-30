class BaseAppException(Exception):
    def __init__(self, msg=""):
        self.msg = msg
        super().__init__(self.msg)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.msg}"


class AuthenticationFailed(BaseAppException):
    """invalid authentication credentials"""

    pass


class QuizNotFound(BaseAppException):
    """Raised when the requested quiz data does not exist in Redis."""

    pass


class QuizValidationError(BaseAppException):
    """Raised when the quiz data fails domain-specific validation rules."""

    pass


class QuizInconsistentError(BaseAppException):
    """Raised when the quiz data is inconsistent."""

    pass


class WordNotFound(BaseAppException):
    """Raised when the guessed word does not exist in the current quiz context."""

    pass


class RankNotFound(BaseAppException):
    """Raised when the rank associated with a score cannot be found."""

    pass


class DateNotAllowed(BaseAppException):
    """Raised when the requested date is not allowed for the operation,
    such as querying future answers or restricted historical data."""

    pass
