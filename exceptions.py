class LoggedOnlyError(Exception):
    """Error only logged, no message sent to the user."""

    pass


class NoHomeworksError(Exception):
    """The list of homeworks is empty."""

    pass

class ApiNotRespondingError(Exception):
    """API did not respond."""

    pass
