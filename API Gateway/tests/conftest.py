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
    api_gateway_url = os.environ.get("API_GATEWAY_URL", "http://localhost:5000")
    
    # Ожидание запуска API Gateway
    assert wait_for_service(f"{api_gateway_url}/healthcheck"), "API Gateway не запустился"

@pytest.fixture
def api_gateway_url():
    """URL для API Gateway."""
    return os.environ.get("API_GATEWAY_URL", "http://localhost:5000")

@pytest.fixture
def api_gateway_client(api_gateway_url):
    """Клиент для API Gateway."""
    class ApiGatewayClient:
        def __init__(self, base_url):
            self.base_url = base_url
        
        def get(self, path, **kwargs):
            return requests.get(f"{self.base_url}{path}", **kwargs)
        
        def post(self, path, **kwargs):
            return requests.post(f"{self.base_url}{path}", **kwargs)
        
        def put(self, path, **kwargs):
            return requests.put(f"{self.base_url}{path}", **kwargs)
        
        def delete(self, path, **kwargs):
            return requests.delete(f"{self.base_url}{path}", **kwargs)
    
    return ApiGatewayClient(api_gateway_url)
