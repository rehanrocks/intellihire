"""Application errors.

Services (business logic) raise these instead of FastAPI's HTTPException so
the services do not depend on the web framework. A single exception handler in
`app/main.py` converts them into JSON responses with the right status code.

The `detail` texts are the exact messages the user stories ask for.
"""


class AppError(Exception):
    status_code = 400
    detail = "Bad request"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class EmailAlreadyRegistered(AppError):
    status_code = 409  # Conflict
    detail = "Email already registered"


class InvalidCredentials(AppError):
    status_code = 401  # Unauthorized (really means "not authenticated")
    detail = "Invalid email or password"


class AccountNotVerified(AppError):
    status_code = 403
    detail = "Please verify your email address before logging in"


class AccountSuspended(AppError):
    status_code = 403
    detail = "This account has been suspended. Contact support for help."


class InvalidToken(AppError):
    status_code = 400
    detail = "This link is invalid or has already been used"


class TokenExpired(AppError):
    status_code = 400
    detail = "This link has expired. Please request a new one."


class NotAuthenticated(AppError):
    status_code = 401
    detail = "Not authenticated"


class UnauthorizedAccess(AppError):
    status_code = 403  # Forbidden: we know who you are, you may not do this
    detail = "Unauthorized Access"


class CompanyNotApproved(AppError):
    status_code = 403
    detail = "Your company account is awaiting approval by the platform administrator"


class NotFound(AppError):
    status_code = 404
    detail = "Not found"


class InvalidFile(AppError):
    status_code = 400
    detail = "Invalid file"


class FileTooLarge(AppError):
    status_code = 413
    detail = "File is too large"


class TooManyRequests(AppError):
    status_code = 429
    detail = "Too many requests. Please try again in a minute."
