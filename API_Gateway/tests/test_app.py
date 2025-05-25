import pytest
import json
import jwt
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import post_service_pb2
import grpc

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client

@pytest.fixture
def auth_headers():
    token = jwt.encode(
        {"username": "testuser"},
        app.app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    return {"Authorization": token}

@pytest.fixture
def mock_user_data():
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }

@pytest.fixture
def mock_authenticate_user(monkeypatch, mock_user_data):
    def mock_auth(request):
        return mock_user_data, None, None
    
    monkeypatch.setattr(app, "authenticate_user", mock_auth)
    return mock_auth

@pytest.fixture
def mock_grpc_stub():
    with patch('app.get_post_service_stub') as mock_get_stub:
        mock_stub = MagicMock()
        mock_get_stub.return_value = mock_stub
        yield mock_stub

def test_create_post_success(client, mock_authenticate_user, mock_grpc_stub):
    post_data = {
        "title": "Test Post",
        "description": "This is a test post",
        "is_private": False,
        "tags": ["test", "api"]
    }

    mock_response = MagicMock()
    mock_response.id = 1
    mock_response.title = "Test Post"
    mock_response.description = "This is a test post"
    mock_response.creator_id = 1
    mock_response.created_at = datetime.now().isoformat()
    mock_response.updated_at = datetime.now().isoformat()
    mock_response.is_private = False
    mock_response.tags = ["test", "api"]
    
    mock_grpc_stub.CreatePost.return_value = mock_response

    response = client.post('/posts', json=post_data)

    assert response.status_code == 201
    
    response_data = json.loads(response.data)
    assert response_data['title'] == "Test Post"
    assert response_data['description'] == "This is a test post"
    assert response_data['creator_id'] == 1
    assert not response_data['is_private']
    assert response_data['tags'] == ["test", "api"]

    mock_grpc_stub.CreatePost.assert_called_once()
    args, _ = mock_grpc_stub.CreatePost.call_args
    assert args[0].title == "Test Post"
    assert args[0].description == "This is a test post"
    assert args[0].creator_id == 1
    assert not args[0].is_private
    assert list(args[0].tags) == ["test", "api"]

def test_create_post_missing_title(client, mock_authenticate_user):
    post_data = {
        "description": "This is a test post",
        "is_private": False
    }

    response = client.post('/posts', json=post_data)

    assert response.status_code == 400
    
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Title is required' in response_data['error']

def test_get_post_success(client, mock_authenticate_user, mock_grpc_stub):
    mock_response = MagicMock()
    mock_response.id = 1
    mock_response.title = "Test Post"
    mock_response.description = "This is a test post"
    mock_response.creator_id = 1
    mock_response.created_at = datetime.now().isoformat()
    mock_response.updated_at = datetime.now().isoformat()
    mock_response.is_private = False
    mock_response.tags = ["test", "api"]
    
    mock_grpc_stub.GetPost.return_value = mock_response

    response = client.get('/posts/1')

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['id'] == 1
    assert response_data['title'] == "Test Post"
    assert response_data['description'] == "This is a test post"

    mock_grpc_stub.GetPost.assert_called_once()
    args, _ = mock_grpc_stub.GetPost.call_args
    assert args[0].post_id == 1
    assert args[0].user_id == 1

def test_get_post_not_found(client, mock_authenticate_user, mock_grpc_stub):
    error = grpc.RpcError()
    error._code = grpc.StatusCode.NOT_FOUND
    mock_grpc_stub.GetPost.side_effect = error

    response = client.get('/posts/999')

    assert response.status_code == 404
    
    response_data = json.loads(response.data)
    assert 'error' in response_data

def test_update_post_success(client, mock_authenticate_user, mock_grpc_stub):
    post_data = {
        "title": "Updated Post",
        "description": "This is an updated post",
        "is_private": True
    }
    
    mock_response = MagicMock()
    mock_response.id = 1
    mock_response.title = "Updated Post"
    mock_response.description = "This is an updated post"
    mock_response.creator_id = 1
    mock_response.created_at = datetime.now().isoformat()
    mock_response.updated_at = datetime.now().isoformat()
    mock_response.is_private = True
    mock_response.tags = []
    
    mock_grpc_stub.UpdatePost.return_value = mock_response
    response = client.put('/posts/1', json=post_data)

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['title'] == "Updated Post"
    assert response_data['description'] == "This is an updated post"
    assert response_data['is_private'] == True

    mock_grpc_stub.UpdatePost.assert_called_once()
    args, _ = mock_grpc_stub.UpdatePost.call_args
    assert args[0].post_id == 1
    assert args[0].title == "Updated Post"
    assert args[0].description == "This is an updated post"
    assert args[0].user_id == 1
    assert args[0].is_private == True

def test_delete_post_success(client, mock_authenticate_user, mock_grpc_stub):
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.message = "Post deleted successfully"
    
    mock_grpc_stub.DeletePost.return_value = mock_response

    response = client.delete('/posts/1')

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['success'] == True
    assert "deleted successfully" in response_data['message']

    mock_grpc_stub.DeletePost.assert_called_once()
    args, _ = mock_grpc_stub.DeletePost.call_args
    assert args[0].post_id == 1
    assert args[0].user_id == 1
def test_list_posts(client, mock_authenticate_user, mock_grpc_stub):
    mock_post1 = MagicMock()
    mock_post1.id = 1
    mock_post1.title = "Post 1"
    mock_post1.description = "Description 1"
    mock_post1.creator_id = 1
    mock_post1.created_at = datetime.now().isoformat()
    mock_post1.updated_at = datetime.now().isoformat()
    mock_post1.is_private = False
    mock_post1.tags = ["tag1"]
    
    mock_post2 = MagicMock()
    mock_post2.id = 2
    mock_post2.title = "Post 2"
    mock_post2.description = "Description 2"
    mock_post2.creator_id = 2
    mock_post2.created_at = datetime.now().isoformat()
    mock_post2.updated_at = datetime.now().isoformat()
    mock_post2.is_private = False
    mock_post2.tags = ["tag2"]
    
    mock_response = MagicMock()
    mock_response.posts = [mock_post1, mock_post2]
    mock_response.total = 2
    mock_response.page = 1
    mock_response.per_page = 10
    
    mock_grpc_stub.ListPosts.return_value = mock_response

    response = client.get('/posts?page=1&per_page=10')

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert len(response_data['posts']) == 2
    assert response_data['total'] == 2
    assert response_data['page'] == 1
    assert response_data['per_page'] == 10

    first_post = response_data['posts'][0]
    assert first_post['id'] == 1
    assert first_post['title'] == "Post 1"

    mock_grpc_stub.ListPosts.assert_called_once()
    args, _ = mock_grpc_stub.ListPosts.call_args
    assert args[0].page == 1
    assert args[0].per_page == 10
    assert args[0].user_id == 1

def test_authentication_failure(client):
    response = client.get('/posts/1')

    assert response.status_code == 401
    
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Authentication token is missing' in response_data['error']
