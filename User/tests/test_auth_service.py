import pytest
import time
import json

def test_register_success(user_service_client):
    """Тест успешной регистрации пользователя."""
    username = f"user_{int(time.time())}"
    email = f"{username}@example.com"
    password = "password123"
    
    response = user_service_client.register(username, email, password)
    
    assert response.status_code == 201
    data = response.json()
    assert data['message'] == 'Users registered successfully'

def test_register_duplicate_username(user_service_client, registered_user):
    """Тест регистрации с существующим username."""
    # Пытаемся зарегистрировать пользователя с тем же username
    response = user_service_client.register(
        registered_user["username"],
        "another@example.com",
        "password123"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data['error'] == 'Username already exists'

def test_register_duplicate_email(user_service_client):
    """Тест регистрации с существующим email."""
    username = f"user_{int(time.time())}"
    
    # Пытаемся зарегистрировать пользователя с тем же email
    response = user_service_client.register(
        username,
        registered_user["email"],
        "password123"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data['error'] == 'Email already in use'

def test_login_success(user_service_client, registered_user):
    """Тест успешного входа в систему."""
    response = user_service_client.login(
        registered_user["username"],
        registered_user["password"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'token' in data
    assert data['token'] is not None

def test_login_invalid_credentials(user_service_client, registered_user):
    """Тест входа с неверными учетными данными."""
    # Пытаемся войти с неверным паролем
    response = user_service_client.login(
        registered_user["username"],
        "wrongpassword"
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data['error'] == 'Invalid credentials'
    
    # Пытаемся войти с несуществующим пользователем
    response = user_service_client.login(
        "nonexistentuser",
        "password123"
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data['error'] == 'Invalid credentials'

def test_profile_get_success(authenticated_client):
    """Тест успешного получения профиля."""
    response = authenticated_client.get_profile()
    
    assert response.status_code == 200
    data = response.json()
    assert 'username' in data
    assert 'email' in data
    assert 'first_name' in data
    assert 'last_name' in data
    assert 'birth_date' in data
    assert 'phone' in data
    assert 'created_at' in data
    assert 'updated_at' in data

def test_profile_get_missing_token(user_service_client):
    """Тест получения профиля без токена."""
    response = user_service_client.get_profile()
    
    assert response.status_code == 401
    data = response.json()
    assert data['error'] == 'Token is missing'

# def test_profile_update_success(authenticated_client):
#     """Тест успешного обновления профиля."""
#     # Данные для обновления
#     update_data = {
#         "first_name": "John"}
