import pytest
import json
import requests
from unittest import mock
import random
import secrets
import string

def generate_secure_random_string(max_length=80):
    length = random.randint(1, max_length)
    alphabet = string.ascii_letters + string.digits + string.punctuation
    random_string = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return random_string

def test_proxy_register(api_gateway_client):
    """Тест проксирования запросов к реальному сервису."""
    # Сначала регистрируем пользователя через API Gateway
    response = api_gateway_client.post("/user/register", json={
        "username": generate_secure_random_string(),
        "email": generate_secure_random_string(),
        "password": "password124"
    })
    
    # Проверяем, что запрос был успешно проксирован
    assert response.status_code == 201
    data = response.json()
    assert data['message'] == 'Users registered successfully'
    
def test_proxy_login(api_gateway_client):
    """Тест проксирования запросов к реальному сервису."""
    # Сначала регистрируем пользователя через API Gateway
    response = api_gateway_client.post("/user/login", json={
        "username": "proxy_test_user",
        "password": "password123"
    })
    
    # Проверяем, что запрос был успешно проксирован
    assert response.status_code == 200

def test_proxy_profile_info(api_gateway_client):
    """Тест проксирования запросов к реальному сервису."""
    # Сначала регистрируем пользователя через API Gateway
    response = api_gateway_client.post("/user/login", json={
        "username": "proxy_test_user",
        "password": "password123"
    })
    
    cookies = response.cookies
    
    response = api_gateway_client.get("/user/profile", json={}, cookies=cookies)
    
    # Проверяем, что запрос был успешно проксирован
    assert response.status_code == 200
    data = response.json()
    assert data['email'] ==  'proxy_test@example.com'

def test_proxy_update_profile_info(api_gateway_client):
    """Тест проксирования запросов к реальному сервису."""
    # Сначала регистрируем пользователя через API Gateway
    response = api_gateway_client.post("/user/login", json={
        "username": "proxy_test_user",
        "password": "password123"
    })
    
    cookies = response.cookies
    
    response = api_gateway_client.put("/user/profile", json={'first_name': generate_secure_random_string()}, cookies=cookies)
    
    # Проверяем, что запрос был успешно проксирован
    assert response.status_code == 200
    data = response.json()
    assert data ==  {
       'message': 'Profile updated successfully'
    }

def test_proxy_nonexistent_service(api_gateway_client):
    """Тест запроса к несуществующему сервису."""
    response = api_gateway_client.get('/nonexistent/endpoint')
    
    # Проверяем, что получаем ошибку о несуществующем сервисе
    assert response.status_code == 404
    data = response.json()
    assert data['error'] == 'Service not found'
