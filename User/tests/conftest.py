import pytest
import requests
import time
import os

# Ожидание запуска сервисов
def wait_for_service(url, max_retries=30, delay=1):
    """Ожидание доступности сервиса."""
    for i in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200 or response.status_code == 404:
                print(f"Service at {url} is ready!")
                return True
        except requests.exceptions.ConnectionError:
            print(f"Waiting for {url} to be ready... Attempt {i+1}/{max_retries}")
            time.sleep(delay)
    return False

@pytest.fixture(scope="session", autouse=True)
def ensure_services():
    """Убедиться, что сервисы запущены."""
    user_service_url = os.environ.get("USER_SERVICE_URL", "http://localhost:5001")
    
    # Ожидание запуска User Service
    assert wait_for_service(f"{user_service_url}/healthcheck"), "User Service не запустился"

@pytest.fixture
def user_service_url():
    """URL для User Service."""
    return os.environ.get("USER_SERVICE_URL", "http://localhost:5001")

@pytest.fixture
def user_service_client(user_service_url):
    """Клиент для User Service."""
    class UserServiceClient:
        def __init__(self, base_url):
            self.base_url = base_url
            self.token = None
        
        def register(self, username, email, password):
            response = requests.post(
                f"{self.base_url}/register",
                json={"username": username, "email": email, "password": password}
            )
            return response
        
        def login(self, username, password):
            response = requests.post(
                f"{self.base_url}/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                self.token = response.json().get('token')
            return response
        
        def get_profile(self):
            headers = {}
            if self.token:
                headers['Authorization'] = self.token
            return requests.get(f"{self.base_url}/profile", headers=headers)
        
        def update_profile(self, data):
            headers = {}
            if self.token:
                headers['Authorization'] = self.token
            return requests.put(f"{self.base_url}/profile", headers=headers, json=data)
        
        def logout(self):
            self.token = None
    
    return UserServiceClient(user_service_url)

@pytest.fixture
def registered_user(user_service_client):
    """Фикстура для создания зарегистрированного пользователя."""
    username = f"test_user_{int(time.time())}"
    email = f"{username}@example.com"
    password = "password124"
    
    # Регистрируем пользователя
    response = user_service_client.register(username, email, password)
    assert response.status_code == 201
    
    return {"username": username, "email": email, "password": password}

@pytest.fixture
def authenticated_client(user_service_client, registered_user):
    """Фикстура для аутентифицированного клиента."""
    response = user_service_client.login(registered_user["username"], registered_user["password"])
    assert response.status_code == 200
    return user_service_client
