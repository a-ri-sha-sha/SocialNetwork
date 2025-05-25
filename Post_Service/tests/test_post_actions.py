import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grpc
import post_service_pb2
from database import Post, PostView, PostLike, Comment
from post_service import PostServicer

class TestPostActions:
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
    
    @pytest.fixture
    def mock_kafka_producer(self, monkeypatch):
        """Мокирование Kafka Producer для тестов"""
        with patch('post_service.send_post_view_event') as mock_view_event, \
             patch('post_service.send_post_like_event') as mock_like_event, \
             patch('post_service.send_post_comment_event') as mock_comment_event:
            yield {
                'view': mock_view_event,
                'like': mock_like_event,
                'comment': mock_comment_event
            }
    
    def test_view_post_success(self, servicer, mock_session, mock_context, mock_kafka_producer):
        """Тест успешного просмотра поста"""
        request = post_service_pb2.ViewPostRequest(
            post_id=1,
            user_id=1
        )

        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.views_count = 5

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post
        mock_session.query.return_value = mock_query

        mock_view_query = MagicMock()
        mock_view_query.filter.return_value.first.return_value = None
        mock_session.query.side_effect = [mock_query, mock_view_query]

        response = servicer.ViewPost(request, mock_context)

        assert response.success == True
        assert response.views_count == 6
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_kafka_producer['view'].assert_called_once()
    
    def test_view_post_already_viewed(self, servicer, mock_session, mock_context, mock_kafka_producer):
        """Тест просмотра поста, который уже был просмотрен пользователем"""
        request = post_service_pb2.ViewPostRequest(
            post_id=1,
            user_id=1
        )

        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.views_count = 5

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post

        mock_view_query = MagicMock()
        mock_existing_view = MagicMock()
        mock_view_query.filter.return_value.first.return_value = mock_existing_view

        mock_session.query.side_effect = [mock_query, mock_view_query]

        response = servicer.ViewPost(request, mock_context)

        assert response.success == True
        assert response.views_count == 5
        mock_session.add.assert_not_called()
        mock_kafka_producer['view'].assert_not_called()
    
    def test_view_post_not_found(self, servicer, mock_session, mock_context):
        """Тест просмотра несуществующего поста"""
        request = post_service_pb2.ViewPostRequest(
            post_id=999,
            user_id=1
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        response = servicer.ViewPost(request, mock_context)

        assert response.success == False
        mock_context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    
    def test_like_post_success(self, servicer, mock_session, mock_context, mock_kafka_producer):
        """Тест успешного лайка поста"""
        request = post_service_pb2.LikePostRequest(
            post_id=1,
            user_id=1,
            is_like=True
        )

        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.likes_count = 10

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post

        mock_like_query = MagicMock()
        mock_like_query.filter.return_value.first.return_value = None

        mock_session.query.side_effect = [mock_query, mock_like_query]

        response = servicer.LikePost(request, mock_context)

        assert response.success == True
        assert response.likes_count == 11
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_kafka_producer['like'].assert_called_once()
    
    def test_like_post_update_existing(self, servicer, mock_session, mock_context, mock_kafka_producer):
        """Тест обновления существующего лайка на дизлайк"""
        request = post_service_pb2.LikePostRequest(
            post_id=1,
            user_id=1,
            is_like=False
        )

        mock_post = MagicMock()
        mock_post.id = 1
        mock_post.likes_count = 10

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post

        mock_like_query = MagicMock()
        mock_existing_like = MagicMock()
        mock_existing_like.is_like = True
        mock_like_query.filter.return_value.first.return_value = mock_existing_like

        mock_session.query.side_effect = [mock_query, mock_like_query]

        response = servicer.LikePost(request, mock_context)

        assert response.success == True
        assert response.likes_count == 8
        assert mock_existing_like.is_like == False
        mock_session.commit.assert_called_once()
        mock_kafka_producer['like'].assert_called_once()
    
    def test_comment_post_success(self, servicer, mock_session, mock_context, mock_kafka_producer):
        """Тест успешного комментирования поста"""
        request = post_service_pb2.CommentPostRequest(
            post_id=1,
            user_id=1,
            text="Test comment"
        )
        mock_post = MagicMock()
        mock_post.id = 1

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post
        mock_session.query.return_value = mock_query

        def add_side_effect(comment):
            comment.id = 1
            comment.created_at = datetime.utcnow()
            return None
        
        mock_session.add.side_effect = add_side_effect

        response = servicer.CommentPost(request, mock_context)

        assert response.id == 1
        assert response.post_id == 1
        assert response.user_id == 1
        assert response.text == "Test comment"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_kafka_producer['comment'].assert_called_once()
    
    def test_get_post_comments(self, servicer, mock_session, mock_context):
        """Тест получения комментариев к посту"""
        request = post_service_pb2.GetPostCommentsRequest(
            post_id=1,
            page=1,
            per_page=10
        )

        mock_post = MagicMock()
        mock_post.id = 1

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_post

        mock_count_query = MagicMock()
        mock_count_query.filter.return_value.scalar.return_value = 2

        mock_comments_query = MagicMock()
        mock_comment1 = MagicMock(id=1, post_id=1, user_id=1, text="Comment 1", created_at=datetime.utcnow())
        mock_comment2 = MagicMock(id=2, post_id=1, user_id=2, text="Comment 2", created_at=datetime.utcnow())
        mock_comments_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            mock_comment1, mock_comment2
        ]

        mock_session.query.side_effect = [mock_query, mock_count_query, mock_comments_query]

        response = servicer.GetPostComments(request, mock_context)

        assert response.total == 2
        assert response.page == 1
        assert response.per_page == 10
        assert len(response.comments) == 2
        assert response.comments[0].id == 1
        assert response.comments[0].text == "Comment 1"
        assert response.comments[1].id == 2
        assert response.comments[1].text == "Comment 2"
