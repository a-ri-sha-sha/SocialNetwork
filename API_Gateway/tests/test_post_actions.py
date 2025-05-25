import pytest
import json
import jwt
from unittest.mock import patch, MagicMock
import grpc
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import post_service_pb2

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
    return {"Authorization": f"Bearer {token}"}

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

def test_view_post_success(client, mock_authenticate_user, mock_grpc_stub):
    """Тест успешного просмотра поста"""
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.views_count = 5
    
    mock_grpc_stub.ViewPost.return_value = mock_response

    response = client.post('/posts/1/view')

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['success'] == True
    assert response_data['views_count'] == 5

    mock_grpc_stub.ViewPost.assert_called_once()
    args, _ = mock_grpc_stub.ViewPost.call_args
    assert args[0].post_id == 1
    assert args[0].user_id == 1

def test_view_post_not_found(client, mock_authenticate_user, mock_grpc_stub):
    """Тест просмотра несуществующего поста"""
    error = grpc.RpcError()
    error.code = lambda: grpc.StatusCode.NOT_FOUND
    error.details = lambda: "Post not found"
    mock_grpc_stub.ViewPost.side_effect = error

    response = client.post('/posts/999/view')

    assert response.status_code == 404
    
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Post not found' in response_data['error']

def test_like_post_success(client, mock_authenticate_user, mock_grpc_stub):
    """Тест успешного лайка поста"""
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.likes_count = 10
    
    mock_grpc_stub.LikePost.return_value = mock_response

    response = client.post('/posts/1/like', 
                          json={"is_like": True})

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['success'] == True
    assert response_data['likes_count'] == 10

    mock_grpc_stub.LikePost.assert_called_once()
    args, _ = mock_grpc_stub.LikePost.call_args
    assert args[0].post_id == 1
    assert args[0].user_id == 1
    assert args[0].is_like == True

def test_dislike_post(client, mock_authenticate_user, mock_grpc_stub):
    """Тест дизлайка поста"""
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.likes_count = 9
    
    mock_grpc_stub.LikePost.return_value = mock_response
    
    response = client.post('/posts/1/like', 
                          json={"is_like": False})

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['success'] == True
    assert response_data['likes_count'] == 9

    mock_grpc_stub.LikePost.assert_called_once()
    args, _ = mock_grpc_stub.LikePost.call_args
    assert args[0].is_like == False

def test_add_comment_success(client, mock_authenticate_user, mock_grpc_stub):
    """Тест успешного добавления комментария"""
    mock_response = MagicMock()
    mock_response.id = 1
    mock_response.post_id = 1
    mock_response.user_id = 1
    mock_response.text = "Test comment"
    mock_response.created_at = "2025-05-25T10:00:00"
    
    mock_grpc_stub.CommentPost.return_value = mock_response

    response = client.post('/posts/1/comments', 
                          json={"text": "Test comment"})

    assert response.status_code == 201
    
    response_data = json.loads(response.data)
    assert response_data['id'] == 1
    assert response_data['post_id'] == 1
    assert response_data['text'] == "Test comment"

    mock_grpc_stub.CommentPost.assert_called_once()
    args, _ = mock_grpc_stub.CommentPost.call_args
    assert args[0].post_id == 1
    assert args[0].user_id == 1
    assert args[0].text == "Test comment"

def test_add_comment_missing_text(client, mock_authenticate_user):
    """Тест добавления комментария без текста"""
    response = client.post('/posts/1/comments', 
                          json={})

    assert response.status_code == 400
    
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Comment text is required' in response_data['error']
def test_get_comments_success(client, mock_authenticate_user, mock_grpc_stub):
    """Тест успешного получения комментариев"""
    mock_comment1 = MagicMock()
    mock_comment1.id = 1
    mock_comment1.post_id = 1
    mock_comment1.user_id = 1
    mock_comment1.text = "Comment 1"
    mock_comment1.created_at = "2025-05-25T10:00:00"
    
    mock_comment2 = MagicMock()
    mock_comment2.id = 2
    mock_comment2.post_id = 1
    mock_comment2.user_id = 2
    mock_comment2.text = "Comment 2"
    mock_comment2.created_at = "2025-05-25T10:15:00"
    
    mock_response = MagicMock()
    mock_response.comments = [mock_comment1, mock_comment2]
    mock_response.total = 2
    mock_response.page = 1
    mock_response.per_page = 10
    
    mock_grpc_stub.GetPostComments.return_value = mock_response

    response = client.get('/posts/1/comments?page=1&per_page=10')

    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['total'] == 2
    assert response_data['page'] == 1
    assert response_data['per_page'] == 10
    assert len(response_data['comments']) == 2
    assert response_data['comments'][0]['id'] == 1
    assert response_data['comments'][0]['text'] == "Comment 1"
    assert response_data['comments'][1]['id'] == 2
    assert response_data['comments'][1]['text'] == "Comment 2"

    mock_grpc_stub.GetPostComments.assert_called_once()
    args, _ = mock_grpc_stub.GetPostComments.call_args
    assert args[0].post_id == 1
    assert args[0].page == 1
    assert args[0].per_page == 10
