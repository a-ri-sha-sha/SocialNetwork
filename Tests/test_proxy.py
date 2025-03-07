import pytest
from app import app, SERVICE_ROUTES
from flask import json
import requests_mock

@pytest.fixture
def client():
    """Создаем тестового клиента Flask"""
    app.config['TESTING'] = True
    return app.test_client()

@pytest.fixture
def mock_requests():
    """Создаем мок для запросов к сервисам"""
    with requests_mock.Mocker() as mock:
        yield mock

def test_proxy_get_request(client, mock_requests):
    """Тест перенаправления GET-запроса"""
    service = "user"
    path = "profile"
    service_url = f"{SERVICE_ROUTES[service]}/{path}"

    mock_requests.get(service_url, text='{"message": "User data"}', status_code=200)

    response = client.get(f'/{service}/{path}')

    assert response.status_code == 200
    assert response.json == {"message": "User data"}

def test_proxy_post_request(client, mock_requests):
    """Тест перенаправления POST-запроса с JSON"""
    service = "stats"
    path = "update"
    service_url = f"{SERVICE_ROUTES[service]}/{path}"
    request_data = {"user_id": 123, "score": 95}
    mock_response = {"status": "updated"}

    mock_requests.post(service_url, json=mock_response, status_code=201)

    response = client.post(f'/{service}/{path}', json=request_data)

    assert response.status_code == 201
    assert response.json == mock_response

def test_proxy_invalid_service(client):
    """Тест обработки запроса к несуществующему сервису"""
    response = client.get("/invalid_service/some_path")

    assert response.status_code == 404
    assert response.json == {"error": "Service not found"}

def test_proxy_forward_headers(client, mock_requests):
    """Тест проброса заголовков"""
    service = "user"
    path = "profile"
    service_url = f"{SERVICE_ROUTES[service]}/{path}"
    
    mock_requests.get(service_url, json={"message": "OK"}, status_code=200)
    
    headers = {"Authorization": "Bearer test_token"}
    response = client.get(f'/{service}/{path}', headers=headers)

    assert response.status_code == 200
    assert response.json == {"message": "OK"}

def test_proxy_forward_query_params(client, mock_requests):
    """Тест проброса параметров запроса"""
    service = "stats"
    path = "report"
    query_params = {"date": "2025-03-06"}
    service_url = f"{SERVICE_ROUTES[service]}/{path}?date=2025-03-06"

    mock_requests.get(service_url, json={"report": "data"}, status_code=200)

    response = client.get(f'/{service}/{path}', query_string=query_params)

    assert response.status_code == 200
    assert response.json == {"report": "data"}

def test_proxy_delete_request(client, mock_requests):
    """Тест DELETE-запроса"""
    service = "user"
    path = "account"
    service_url = f"{SERVICE_ROUTES[service]}/{path}"

    mock_requests.delete(service_url, json={"status": "deleted"}, status_code=200)

    response = client.delete(f'/{service}/{path}')

    assert response.status_code == 200
    assert response.json == {"status": "deleted"}

def test_proxy_patch_request(client, mock_requests):
    """Тест PATCH-запроса"""
    service = "user"
    path = "settings"
    service_url = f"{SERVICE_ROUTES[service]}/{path}"
    request_data = {"theme": "dark"}
    mock_response = {"updated": True}

    mock_requests.patch(service_url, json=mock_response, status_code=200)

    response = client.patch(f'/{service}/{path}', json=request_data)

    assert response.status_code == 200
    assert response.json == mock_response
