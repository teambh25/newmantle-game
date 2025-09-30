class BaseAppException(Exception):
    def __init__(self, msg=""):
        self.msg = msg
        super().__init__(self.msg)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.msg}"


class AuthenticationFailed(BaseAppException):
    """invalid authentication credentials"""

    pass


class InvalidParameter(BaseAppException):
    """raised when an parameter violates a defined business/domain rule"""

    pass


class QuizNotFound(BaseAppException):
    """no quiz data existed in Redis"""

    pass


class InconsistentQuizData(BaseAppException):
    """critical data integrity issue, likely caused by a previous partial write."""

    pass
