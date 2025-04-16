from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.routing import APIRouter
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from inventory_management_python.database import engine
from inventory_management_python.database.user import (
    AuthenticateUserModel,
    CreateUserModel,
    UserRepository,
)

router = APIRouter()


@router.post("/login")
async def login(payload: AuthenticateUserModel) -> dict:
    try:
        session = Session(engine)

        repository = UserRepository(session)

        payload = AuthenticateUserModel.model_validate(payload)

        user = repository.authenticate(payload)

        if not user:
            return {"error": "invalid email or password"}

        access_key = "random-key-please-update-me"
        refresh_key = "random-refresh-key-please-update-me!!"

        claims = {
            "sub": user.id,
            "iss": "inventory-management",
            "aud": "inventory-management",
            "nbf": datetime.now(timezone.utc) - timedelta(seconds=5),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4()),
        }

        access_claims = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(hours=1), **claims},
            access_key,
        )

        refresh_claims = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(hours=1), **claims},
            refresh_key,
        )

        return {
            "access_token": access_claims,
            "refresh_token": refresh_claims,
            "token_type": "Bearer",
            "exp": 3600,
        }

    except ValidationError as e:
        return {"error": str(e)}


@router.post("/register")
async def register(payload: CreateUserModel) -> dict:
    try:
        session = Session(engine)

        repository = UserRepository(session)

        payload = CreateUserModel.model_validate(payload)

        repository.create(payload)

        return {"message": "user created successfully"}

    except ValidationError as e:
        return {"error": str(e)}
    except IntegrityError as _:
        return {"error": "email already exists"}
    except Exception as _:
        return {"error": "Internal server error"}
