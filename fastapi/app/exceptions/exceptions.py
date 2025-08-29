class BaseAppException(Exception):
    def __init__(self, msg=''):
        self.msg = msg
        super().__init__(self.msg)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.msg}'


class AuthenticationFailed(BaseAppException):
    """invalid authentication credentials"""
    pass


class InvalidParameter(BaseAppException):
    """raised when an parameter violates a defined business/domain rule"""
    pass


# class EntityDoesNotExist(BaseAppException):
#     """database returns nothing"""
#     pass


# class EntityAlreadyExists(BaseAppException):
#     """conflict detected, like trying to create a resource that already exists"""
#     pass


# class InvalidEntity(BaseAppException):
#     """raised when an entity violates a defined business/domain rule"""
#     pass
