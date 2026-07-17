import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

from bbi_os.observability import timestamp


ROLES = {"admin", "user", "readonly"}
PERMISSIONS = {
    "GET": ROLES,
    "POST": {"admin", "user"},
    "PATCH": {"admin", "user"},
    "DELETE": {"admin"},
}


@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    username: str
    role: str
    created_at: str

    def __post_init__(self) -> None:
        if not self.user_id or not self.username:
            raise ValueError("User ID and username are required")
        if self.role not in ROLES:
            raise ValueError(f"Unsupported role: {self.role}")


ANONYMOUS_USER = UserIdentity(
    user_id="anonymous",
    username="anonymous",
    role="readonly",
    created_at="",
)


class AuthenticationRequired(Exception):
    pass


class InvalidToken(Exception):
    pass


class Forbidden(Exception):
    pass


class Authenticator:
    """Maps opaque bearer tokens to internal user identities."""

    def __init__(self, tokens: Optional[Mapping[str, UserIdentity]] = None) -> None:
        self._tokens = dict(tokens or {})

    def authenticate(self, headers: Mapping[str, str]) -> Tuple[UserIdentity, bool]:
        authorization = headers.get("Authorization", "").strip()
        if not authorization:
            return ANONYMOUS_USER, False
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            raise InvalidToken
        user = self._tokens.get(token.strip())
        if user is None:
            raise InvalidToken
        return user, True

    @staticmethod
    def authorize(user: UserIdentity, authenticated: bool, method: str) -> None:
        allowed_roles = PERMISSIONS.get(method, set())
        if user.role in allowed_roles:
            return
        if not authenticated:
            raise AuthenticationRequired
        raise Forbidden

    @classmethod
    def from_environment(cls) -> "Authenticator":
        """Load tokens from BBIOS_AUTH_TOKENS without persisting credentials."""
        raw_config = os.environ.get("BBIOS_AUTH_TOKENS", "")
        if not raw_config:
            return cls()
        config: Dict[str, Dict[str, Any]] = json.loads(raw_config)
        tokens = {
            token: UserIdentity(
                user_id=details["user_id"],
                username=details["username"],
                role=details["role"],
                created_at=details.get("created_at", timestamp()),
            )
            for token, details in config.items()
        }
        return cls(tokens)

