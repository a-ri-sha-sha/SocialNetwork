import pytest
import json
from unittest.mock import patch, MagicMock
import grpc
import stats_service_pb2
from datetime import datetime, timedelta

import app

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client

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
def mock_stats_stub():
    with patch('app.get_stats_service_stub') as mock_get_stub:
        mock_stub = MagicMock()
        mock_get_stub.return_value = mock_stub
        yield mock_stub

def test_get_post_stats(client, mock_authenticate_user, mock_stats_stub):
    mock_response = MagicMock()
    mock_response.post_id = 1
    mock_response.views_count = 100
    mock_response.likes_count = 50
    mock_response.comments_count = 30
    
    mock_stats_stub.GetPostStats.return_value = mock_response
    
    response = client.get('/stats/posts/1')
    
    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['post_id'] == 1
    assert response_data['views_count'] == 100
    assert response_data['likes_count'] == 50
    assert response_data['comments_count'] == 30
    
    mock_stats_stub.GetPostStats.assert_called_once()
    args, _ = mock_stats_stub.GetPostStats.call_args
    assert args[0].post_id == 1

def test_get_post_views_dynamics(client, mock_authenticate_user, mock_stats_stub):
    mock_response = MagicMock()
    mock_response.post_id = 1
    
    today = datetime.now().date()
    yesterday = (today - timedelta(days=1))
    
    daily_stat1 = MagicMock()
    daily_stat1.date = yesterday.strftime('%Y-%m-%d')
    daily_stat1.count = 10
    
    daily_stat2 = MagicMock()
    daily_stat2.date = today.strftime('%Y-%m-%d')
    daily_stat2.count = 20
    
    mock_response.daily_stats = [daily_stat1, daily_stat2]
    
    mock_stats_stub.GetPostViewsDynamics.return_value = mock_response
    
    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    response = client.get(f'/stats/posts/1/views/dynamics?start_date={start_date}&end_date={end_date}')
    
    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['post_id'] == 1
    assert len(response_data['daily_stats']) == 2
    
    assert response_data['daily_stats'][0]['date'] == yesterday.strftime('%Y-%m-%d')
    assert response_data['daily_stats'][0]['count'] == 10
    
    assert response_data['daily_stats'][1]['date'] == today.strftime('%Y-%m-%d')
    assert response_data['daily_stats'][1]['count'] == 20
    
    mock_stats_stub.GetPostViewsDynamics.assert_called_once()
    args, _ = mock_stats_stub.GetPostViewsDynamics.call_args
    assert args[0].post_id == 1
    assert args[0].start_date == start_date
    assert args[0].end_date == end_date
    
def test_get_post_likes_dynamics(client, mock_authenticate_user, mock_stats_stub):
    mock_response = MagicMock()
    mock_response.post_id = 1
    
    today = datetime.now().date()
    yesterday = (today - timedelta(days=1))
    
    daily_stat1 = MagicMock()
    daily_stat1.date = yesterday.strftime('%Y-%m-%d')
    daily_stat1.count = 5
    
    daily_stat2 = MagicMock()
    daily_stat2.date = today.strftime('%Y-%m-%d')
    daily_stat2.count = 10
    
    mock_response.daily_stats = [daily_stat1, daily_stat2]
    
    mock_stats_stub.GetPostLikesDynamics.return_value = mock_response
    
    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    response = client.get(f'/stats/posts/1/likes/dynamics?start_date={start_date}&end_date={end_date}')
    
    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['post_id'] == 1
    assert len(response_data['daily_stats']) == 2
    
    mock_stats_stub.GetPostLikesDynamics.assert_called_once()

def test_get_post_comments_dynamics(client, mock_authenticate_user, mock_stats_stub):
    mock_response = MagicMock()
    mock_response.post_id = 1
    
    today = datetime.now().date()
    yesterday = (today - timedelta(days=1))
    
    daily_stat1 = MagicMock()
    daily_stat1.date = yesterday.strftime('%Y-%m-%d')
    daily_stat1.count = 3
    
    daily_stat2 = MagicMock()
    daily_stat2.date = today.strftime('%Y-%m-%d')
    daily_stat2.count = 7
    
    mock_response.daily_stats = [daily_stat1, daily_stat2]
    
    mock_stats_stub.GetPostCommentsDynamics.return_value = mock_response
    
    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    response = client.get(f'/stats/posts/1/comments/dynamics?start_date={start_date}&end_date={end_date}')
    
    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['post_id'] == 1
    assert len(response_data['daily_stats']) == 2
    
    mock_stats_stub.GetPostCommentsDynamics.assert_called_once()

def test_get_top_posts(client, mock_authenticate_user, mock_stats_stub):
    mock_response = MagicMock()
    
    post1 = MagicMock()
    post1.post_id = 1
    post1.count = 100
    
    post2 = MagicMock()
    post2.post_id = 2
    post2.count = 80
    
    post3 = MagicMock()
    post3.post_id = 3
    post3.count = 60
    
    mock_response.posts = [post1, post2, post3]
    
    mock_stats_stub.GetTopPosts.return_value = mock_response
    
    response = client.get('/stats/top/posts?metric_type=views&limit=3')
    
    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['metric_type'] == 'views'
    assert len(response_data['posts']) == 3
    
    assert response_data['posts'][0]['post_id'] == 1
    assert response_data['posts'][0]['count'] == 100
    
    mock_stats_stub.GetTopPosts.assert_called_once()
    args, _ = mock_stats_stub.GetTopPosts.call_args
    assert args[0].metric_type == stats_service_pb2.TopRequest.MetricType.VIEWS
    assert args[0].limit == 3
    
def test_get_top_posts_invalid_metric(client, mock_authenticate_user):
    response = client.get('/stats/top/posts?metric_type=invalid&limit=3')
    
    assert response.status_code == 400
    
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Invalid metric_type' in response_data['error']

def test_get_top_users(client, mock_authenticate_user, mock_stats_stub):
    mock_response = MagicMock()
    
    user1 = MagicMock()
    user1.user_id = 101
    user1.count = 50
    
    user2 = MagicMock()
    user2.user_id = 102
    user2.count = 40
    
    user3 = MagicMock()
    user3.user_id = 103
    user3.count = 30
    
    mock_response.users = [user1, user2, user3]
    
    mock_stats_stub.GetTopUsers.return_value = mock_response
    
    response = client.get('/stats/top/users?metric_type=likes&limit=3')
    
    assert response.status_code == 200
    
    response_data = json.loads(response.data)
    assert response_data['metric_type'] == 'likes'
    assert len(response_data['users']) == 3
    
    assert response_data['users'][0]['user_id'] == 101
    assert response_data['users'][0]['count'] == 50
    
    mock_stats_stub.GetTopUsers.assert_called_once()
    args, _ = mock_stats_stub.GetTopUsers.call_args
    assert args[0].metric_type == stats_service_pb2.TopRequest.MetricType.LIKES
    assert args[0].limit == 3
