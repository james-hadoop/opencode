from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt
import uuid


class User(BaseModel):
    id: str
    name: str
    email: str
    team_id: str
    role: str = "user"


class TokenData(BaseModel):
    user_id: str
    team_id: str


class AuthConfig(BaseModel):
    secret_key: str = "mineru-studio-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class UserContext(BaseModel):
    current_user_id: str
    current_team_id: str


class AuthService:
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self._users: dict[str, dict] = {
            "u_admin": {
                "id": "u_admin",
                "name": "Admin",
                "email": "admin@example.com",
                "password": "admin123",
                "team_id": "t_default",
                "role": "admin",
            },
            "u_demo": {
                "id": "u_demo",
                "name": "Demo User",
                "email": "demo@example.com",
                "password": "demo123",
                "team_id": "t_default",
                "role": "user",
            },
        }
        self._teams: dict[str, dict] = {
            "t_default": {
                "id": "t_default",
                "name": "Default Team",
            },
        }

    def authenticate(self, email: str, password: str) -> User | None:
        for user in self._users.values():
            if user["email"] == email and user["password"] == password:
                return User(
                    id=user["id"],
                    name=user["name"],
                    email=user["email"],
                    team_id=user["team_id"],
                    role=user["role"],
                )
        return None

    def create_access_token(self, user: User) -> str:
        expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
        to_encode = {
            "user_id": user.id,
            "team_id": user.team_id,
            "exp": expire,
        }
        return jwt.encode(to_encode, self.config.secret_key, algorithm=self.config.algorithm)

    def verify_token(self, token: str) -> TokenData | None:
        try:
            payload = jwt.decode(token, self.config.secret_key, algorithms=[self.config.algorithm])
            return TokenData(user_id=payload["user_id"], team_id=payload["team_id"])
        except jwt.PyJWTError:
            return None

    def get_user(self, user_id: str) -> User | None:
        user = self._users.get(user_id)
        if user:
            return User(
                id=user["id"],
                name=user["name"],
                email=user["email"],
                team_id=user["team_id"],
                role=user["role"],
            )
        return None

    def list_users(self) -> list[User]:
        return [
            User(
                id=u["id"],
                name=u["name"],
                email=u["email"],
                team_id=u["team_id"],
                role=u["role"],
            )
            for u in self._users.values()
        ]

    def get_request_context(self, user_id: str, team_id: str) -> UserContext:
        return UserContext(current_user_id=user_id, current_team_id=team_id)


auth_service = AuthService()