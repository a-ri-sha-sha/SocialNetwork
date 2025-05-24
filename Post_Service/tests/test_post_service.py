import pytest
import grpc
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import post_service_pb2
import post_service_pb2_grpc
from post_service import PostServicer
from database import Post, Base

class TestPostServicer:
    @pytest.fixture
    def servicer(self):
        return PostServicer()
    
    @pytest.fixture
    def mock_session(self, monkeypatch):
        mock_session = MagicMock()
        
        with patch('post_service.Session') as mock_Session:
            mock_Session.return_value = mock_session
            yield mock_session
    
    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        yield context
    
    def test_create_post(self, servicer, mock_session, mock_context):
        request = post_service_pb2.CreatePostRequest(
            title="Test Post",
            description="This is a test post",
            creator_id=1,
            is_private=False,
            tags=["test", "unit-test"]
        )
        
        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.title = "Test Post"
        mock_post.description = "This is a test post"
        mock_post.creator_id = 1
        mock_post.created_at = datetime.now()
        mock_post.updated_at = datetime.now()
        mock_post.is_private = False
        mock_post.tags = ["test", "unit-test"]
        
        def add_side_effect(post):
            post.id = 1
            post.created_at = mock_post.created_at
            post.updated_at = mock_post.updated_at
            return None
        
        mock_session.add.side_effect = add_side_effect
        
        response = servicer.CreatePost(request, mock_context)
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        
        assert response.title == "Test Post"
        assert response.description == "This is a test post"
        assert response.creator_id == 1
        assert response.is_private == False
        assert list(response.tags) == ["test", "unit-test"]
    
    def test_get_post_success(self, servicer, mock_session, mock_context):
        request = post_service_pb2.GetPostRequest(
            post_id=1,
            user_id=1
        )
        
        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.title = "Test Post"
        mock_post.description = "This is a test post"
        mock_post.creator_id = 1
        mock_post.created_at = datetime.now()
        mock_post.updated_at = datetime.now()
        mock_post.is_private = False
        mock_post.tags = ["test", "unit-test"]
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post
        mock_session.query.return_value = mock_query

        response = servicer.GetPost(request, mock_context)
        
        mock_session.query.assert_called_once_with(Post)
        mock_session.close.assert_called_once()
        
        assert response.id == 1
        assert response.title == "Test Post"
        assert response.description == "This is a test post"
        assert response.creator_id == 1
        assert response.is_private == False
        assert list(response.tags) == ["test", "unit-test"]
    
    def test_get_post_not_found(self, servicer, mock_session, mock_context):
        request = post_service_pb2.GetPostRequest(
            post_id=999,
            user_id=1
        )
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        servicer.GetPost(request, mock_context)
        
        mock_context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)
        mock_context.set_details.assert_called_with(f"Post with ID {request.post_id} not found")
    
    def test_get_private_post_denied(self, servicer, mock_session, mock_context):
        request = post_service_pb2.GetPostRequest(
            post_id=1,
            user_id=2
        )
        
        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.title = "Private Post"
        mock_post.description = "This is a private post"
        mock_post.creator_id = 1
        mock_post.created_at = datetime.now()
        mock_post.updated_at = datetime.now()
        mock_post.is_private = True
        mock_post.tags = ["private"]
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post
        mock_session.query.return_value = mock_query
        
        servicer.GetPost(request, mock_context)
        
        mock_context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)
    
    def test_update_post_success(self, servicer, mock_session, mock_context):
        request = post_service_pb2.UpdatePostRequest(
            post_id=1,
            title="Updated Post",
            description="This is an updated post",
            user_id=1,
            is_private=True,
            tags=["updated", "test"]
        )
        
        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.title = "Original Post"
        mock_post.description = "This is the original post"
        mock_post.creator_id = 1
        mock_post.created_at = datetime.now()
        mock_post.updated_at = datetime.now()
        mock_post.is_private = False
        mock_post.tags = ["original"]
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post
        mock_session.query.return_value = mock_query
        
        response = servicer.UpdatePost(request, mock_context)
        
        mock_session.commit.assert_called_once()
        
        assert mock_post.title == "Updated Post"
        assert mock_post.description == "This is an updated post"
        assert mock_post.is_private == True
        assert mock_post.tags == ["updated", "test"]
        
        assert response.title == "Updated Post"
        assert response.description == "This is an updated post"
        assert response.is_private == True
        assert list(response.tags) == ["updated", "test"]
    
    def test_delete_post_success(self, servicer, mock_session, mock_context):
        request = post_service_pb2.DeletePostRequest(
            post_id=1,
            user_id=1
        )
        
        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.creator_id = 1
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post
        mock_session.query.return_value = mock_query
        
        response = servicer.DeletePost(request, mock_context)
        
        mock_session.delete.assert_called_once_with(mock_post)
        mock_session.commit.assert_called_once()
        
        assert response.success == True
        assert "deleted successfully" in response.message
    
    def test_list_posts(self, servicer, mock_session, mock_context):
        request = post_service_pb2.ListPostsRequest(
            page=1,
            per_page=10,
            user_id=1
        )
        
        mock_posts = []
        for i in range(3):
            mock_post = MagicMock()
            mock_post.id = i + 1
            mock_post.title = f"Post {i+1}"
            mock_post.description = f"Description {i+1}"
            mock_post.creator_id = 1
            mock_post.created_at = datetime.now()
            mock_post.updated_at = datetime.now()
            mock_post.is_private = False
            mock_post.tags = [f"tag{i+1}"]
            mock_posts.append(mock_post)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(mock_posts)
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_posts
        mock_session.query.return_value = mock_query
        
        response = servicer.ListPosts(request, mock_context)
        
        assert len(response.posts) == 3
        assert response.total == 3
        assert response.page == 1
        assert response.per_page == 10
        
        first_post = response.posts[0]
        assert first_post.id == 1
        assert first_post.title == "Post 1"
