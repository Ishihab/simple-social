class BaseException(Exception):
    pass

class DatabaseWriteError(BaseException):
    pass

class DatabaseReadError(BaseException):
    pass