import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.main import app

# Sets up a temparary database in memory
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Credentials for the shared test user
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123",
}


@pytest.fixture()
def db_engine():
    
    # This is the test db engine 
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        
        # This allows the test to connect to the test db multiple times without getting a diffrent db everytime
        poolclass=StaticPool,   
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    
    # once the egine is done being used get rid of it
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    
    # Set up the test session to allow for testing tokens and user auth
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    
    # gets the db session to user for testing
    def override_get_db():
        yield db_session

    # Sets up the proper test client for the tests to use
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    """Register the standard test user and return the response body."""
    
    # Sets up and adds the test user to the temp test db
    resp = client.post("/api/users/register", json=TEST_USER)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def auth_token(client, registered_user):
    """Log in as the test user and return the raw JWT string."""
    
    # Sets up the test users access token
    resp = client.post(
        "/api/users/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]

@pytest.fixture
def auth_headers(auth_token):  # noqa: ARG001
    return {"Authorization": f"Bearer {auth_token}"}
