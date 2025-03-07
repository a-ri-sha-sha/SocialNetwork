import pytest
import jwt
from auth_service import app, db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    """Создает тестового клиента Flask и чистит БД перед каждым тестом"""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:" 
    with app.app_context():
        db.create_all()
    yield app.test_client()
    with app.app_context():
        db.drop_all()

@pytest.fixture
def create_test_user():
    """Создает тестового пользователя в БД"""
    with app.app_context():
        hashed_password = generate_password_hash("password123")
        user = User(username="testuser", email="test@example.com", password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def generate_token(create_test_user):
    """Создает JWT-токен для тестового пользователя"""
    return jwt.encode({"username": "testuser"}, app.config["SECRET_KEY"], algorithm="HS256")

def test_register_user(client):
    """Тест успешной регистрации пользователя"""
    response = client.post("/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword"
    })
    assert response.status_code == 201
    assert response.json == {"message": "User registered successfully"}

def test_register_duplicate_username(client, create_test_user):
    """Тест ошибки регистрации с существующим username"""
    response = client.post("/register", json={
        "username": "testuser",
        "email": "newemail@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert response.json == {"error": "Username already exists"}

def test_register_duplicate_email(client, create_test_user):
    """Тест ошибки регистрации с существующим email"""
    response = client.post("/register", json={
        "username": "newuser",
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert response.json == {"error": "Email already in use"}

def test_login_success(client, create_test_user):
    """Тест успешного входа"""
    response = client.post("/login", json={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert "token" in response.json

def test_login_invalid_credentials(client):
    """Тест ошибки входа с неправильными данными"""
    response = client.post("/login", json={"username": "testuser", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json == {"error": "Invalid credentials"}

def test_login_non_existing_user(client):
    """Тест ошибки входа с несуществующим пользователем"""
    response = client.post("/login", json={"username": "nonexistent", "password": "password123"})
    assert response.status_code == 401
    assert response.json == {"error": "Invalid credentials"}

def test_get_profile_success(client, generate_token):
    """Тест успешного получения профиля"""
    headers = {"Authorization": generate_token}
    response = client.get("/profile", headers=headers)
    assert response.status_code == 200
    assert response.json["username"] == "testuser"
    assert response.json["email"] == "test@example.com"

def test_get_profile_no_token(client):
    """Тест ошибки при отсутствии токена"""
    response = client.get("/profile")
    assert response.status_code == 401
    assert response.json == {"error": "Token is missing"}

def test_get_profile_invalid_token(client):
    """Тест ошибки при невалидном токене"""
    headers = {"Authorization": "invalid_token"}
    response = client.get("/profile", headers=headers)
    assert response.status_code == 401
    assert response.json == {"error": "Invalid token"}

def test_update_profile_success(client, generate_token):
    """Тест успешного обновления профиля"""
    headers = {"Authorization": generate_token}
    response = client.put("/profile", json={"first_name": "Alice", "last_name": "Doe"}, headers=headers)
    assert response.status_code == 200
    assert response.json == {"message": "Profile updated successfully"}

def test_update_profile_no_token(client):
    """Тест ошибки обновления профиля без токена"""
    response = client.put("/profile", json={"first_name": "Alice"})
    assert response.status_code == 401
    assert response.json == {"error": "Token is missing"}

def test_update_profile_invalid_token(client):
    """Тест ошибки обновления профиля с невалидным токеном"""
    headers = {"Authorization": "invalid_token"}
    response = client.put("/profile", json={"first_name": "Alice"}, headers=headers)
    assert response.status_code == 401
    assert response.json == {"error": "Invalid token"}
