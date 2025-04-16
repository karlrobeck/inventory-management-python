from datetime import datetime, timezone
from hashlib import sha256
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import String, delete, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from inventory_management_python.database import Base, engine


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    password: Mapped[str] = mapped_column(String(100), nullable=False)

    def set_password(self, raw_password: str) -> None:
        self.password = sha256(raw_password.encode("utf-8")).hexdigest()

    def check_password(self, raw_password: str) -> bool:
        return self.password == sha256(raw_password.encode("utf-8")).hexdigest()

    created_at: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CreateUserModel(BaseModel):
    name: str
    email: str
    password: str


class UserModel(BaseModel):
    id: str
    name: str
    email: str
    created_at: str
    updated_at: str


class AuthenticateUserModel(BaseModel):
    email: str
    password: str


class UpdateUserModel(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None


class UserListResponseModel(BaseModel):
    users: List[UserModel]
    total: int
    page: int
    size: int


class UserRepository:
    """
    User repository implementing CRUD operations
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the repository with an optional session
        """
        self.session = db_session or Session(engine)

    def create(self, user_data: CreateUserModel) -> UserModel:
        """
        Create a new user in the database

        Args:
            user_data: The user data to create

        Returns:
            The created user

        Raises:
            IntegrityError: If the email already exists
        """
        user = User(**user_data.model_dump())
        user.set_password(user_data.password)

        self.session.add(user)
        self.session.commit()

        return UserModel(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def get_by_id(self, user_id: str) -> Optional[UserModel]:
        """
        Get a user by ID

        Args:
            user_id: The user ID to look up

        Returns:
            The user if found, None otherwise
        """
        user = self.session.scalar(select(User).where(User.id == user_id))
        if not user:
            return None

        return UserModel(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email

        Args:
            email: The email to look up

        Returns:
            The User entity if found, None otherwise
        """
        return self.session.scalar(select(User).where(User.email == email))

    def list_users(self, page: int = 1, size: int = 10) -> UserListResponseModel:
        """
        List users with pagination

        Args:
            page: The page number (1-based)
            size: The page size

        Returns:
            A paginated list of users
        """
        offset = (page - 1) * size

        # Get total count
        total = self.session.query(User).count()

        # Get paginated results
        users = self.session.scalars(select(User).offset(offset).limit(size)).all()

        user_models = [
            UserModel(
                id=user.id,
                name=user.name,
                email=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user in users
        ]

        return UserListResponseModel(
            users=user_models,
            total=total,
            page=page,
            size=size,
        )

    def update(self, user_id: str, user_data: UpdateUserModel) -> Optional[UserModel]:
        """
        Update a user

        Args:
            user_id: The ID of the user to update
            user_data: The new user data

        Returns:
            The updated user if found, None otherwise
        """
        # Create a dict with only the non-None values
        update_data = {k: v for k, v in user_data.model_dump().items() if v is not None}

        if not update_data:
            # If no fields to update, just return the current user
            return self.get_by_id(user_id)

        # Handle password separately if it exists
        if "password" in update_data:
            raw_password = update_data.pop("password")
            update_data["password"] = sha256(raw_password.encode("utf-8")).hexdigest()

        # Update the user
        result = self.session.execute(
            update(User).where(User.id == user_id).values(**update_data),
        )

        self.session.commit()

        # If no rows affected, user doesn't exist
        if result.rowcount == 0:
            return None

        # Return the updated user
        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> bool:
        """
        Delete a user

        Args:
            user_id: The ID of the user to delete

        Returns:
            True if the user was deleted, False if the user wasn't found
        """
        result = self.session.execute(delete(User).where(User.id == user_id))

        self.session.commit()

        # Return whether any rows were affected
        return result.rowcount > 0

    def authenticate(self, auth_data: AuthenticateUserModel) -> Optional[User]:
        """
        Authenticate a user

        Args:
            auth_data: The authentication data

        Returns:
            The User entity if authentication succeeds, None otherwise
        """
        user = self.get_by_email(auth_data.email)

        if not user or not user.check_password(auth_data.password):
            return None

        return user
