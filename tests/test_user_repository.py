from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from inventory_management_python.database import Base
from inventory_management_python.database.user import (
    AuthenticateUserModel,
    CreateUserModel,
    UpdateUserModel,
    UserRepository,
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Create a new database session for testing."""
    with Session(in_memory_db) as session:
        yield session


@pytest.fixture
def user_repository(db_session):
    """Create a UserRepository instance with the test session."""
    return UserRepository(db_session)


@pytest.fixture
def sample_user_data():
    """Return sample user data for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "securepassword123",
    }


@pytest.fixture
def created_user(user_repository, sample_user_data):
    """Create and return a test user."""
    user_data = CreateUserModel(**sample_user_data)
    return user_repository.create(user_data)


class TestUserRepository:
    def test_create_user(self, user_repository, sample_user_data):
        """Test creating a new user."""
        user_data = CreateUserModel(**sample_user_data)
        user = user_repository.create(user_data)

        assert user.id is not None
        assert user.name == sample_user_data["name"]
        assert user.email == sample_user_data["email"]
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_get_user_by_id(self, user_repository, created_user):
        """Test retrieving a user by ID."""
        user = user_repository.get_by_id(created_user.id)

        assert user is not None
        assert user.id == created_user.id
        assert user.name == created_user.name
        assert user.email == created_user.email

    def test_get_nonexistent_user_by_id(self, user_repository):
        """Test retrieving a non-existent user by ID."""
        random_id = str(uuid4())
        user = user_repository.get_by_id(random_id)

        assert user is None

    def test_get_user_by_email(self, user_repository, sample_user_data, created_user):
        """Test retrieving a user by email."""
        user = user_repository.get_by_email(sample_user_data["email"])

        assert user is not None
        assert user.id == created_user.id
        assert user.name == created_user.name
        assert user.email == created_user.email

    def test_list_users(self, user_repository, created_user):
        """Test listing users with pagination."""
        # Create a few more users to test pagination
        for i in range(5):
            user_data = CreateUserModel(
                name=f"Test User {i}",
                email=f"test{i}@example.com",
                password="password123",
            )
            user_repository.create(user_data)

        # Test first page with default values
        result = user_repository.list_users()
        assert len(result.users) <= 10
        assert result.total >= 6  # The created_user fixture + 5 more
        assert result.page == 1
        assert result.size == 10

        # Test with custom pagination
        result = user_repository.list_users(page=1, size=3)
        assert len(result.users) == 3
        assert result.total >= 6
        assert result.page == 1
        assert result.size == 3

    def test_update_user(self, user_repository, created_user):
        """Test updating a user."""
        update_data = UpdateUserModel(name="Updated Name", email="updated@example.com")

        updated_user = user_repository.update(created_user.id, update_data)

        assert updated_user is not None
        assert updated_user.id == created_user.id
        assert updated_user.name == "Updated Name"
        assert updated_user.email == "updated@example.com"
        assert updated_user.updated_at != created_user.updated_at

    def test_update_nonexistent_user(self, user_repository):
        """Test updating a non-existent user."""
        random_id = str(uuid4())
        update_data = UpdateUserModel(name="Will Not Update")

        updated_user = user_repository.update(random_id, update_data)
        assert updated_user is None

    def test_update_password(self, user_repository, created_user, db_session):
        """Test updating a user's password."""
        new_password = "newpassword456"
        update_data = UpdateUserModel(password=new_password)

        updated_user = user_repository.update(created_user.id, update_data)
        assert updated_user is not None

        # Get the user entity to test password
        user_entity = user_repository.get_by_email(updated_user.email)
        assert user_entity.check_password(new_password) is True

    def test_delete_user(self, user_repository, created_user):
        """Test deleting a user."""
        result = user_repository.delete(created_user.id)
        assert result is True

        # Verify user is deleted
        user = user_repository.get_by_id(created_user.id)
        assert user is None

    def test_delete_nonexistent_user(self, user_repository):
        """Test deleting a non-existent user."""
        random_id = str(uuid4())
        result = user_repository.delete(random_id)
        assert result is False

    def test_authenticate_user_valid(
        self,
        user_repository,
        sample_user_data,
        created_user,
    ):
        """Test authenticating a user with valid credentials."""
        auth_data = AuthenticateUserModel(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
        )

        user = user_repository.authenticate(auth_data)
        assert user is not None
        assert user.id == created_user.id
        assert user.email == created_user.email

    def test_authenticate_user_invalid_password(
        self,
        user_repository,
        sample_user_data,
        created_user,
    ):
        """Test authenticating a user with invalid password."""
        auth_data = AuthenticateUserModel(
            email=sample_user_data["email"],
            password="wrongpassword",
        )

        user = user_repository.authenticate(auth_data)
        assert user is None

    def test_authenticate_user_nonexistent(self, user_repository):
        """Test authenticating a non-existent user."""
        auth_data = AuthenticateUserModel(
            email="nonexistent@example.com",
            password="somepassword",
        )

        user = user_repository.authenticate(auth_data)
        assert user is None
