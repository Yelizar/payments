class BaseException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidAmountError(BaseException):
    pass


class InvalidIdempotencyKeyError(BaseException):
    pass


class InvalidStatusTransitionError(BaseException):
    pass
