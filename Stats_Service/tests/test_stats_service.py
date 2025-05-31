import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grpc
import stats_service_pb2
from stats_service import StatsServicer

class TestStatsServicer:
    @pytest.fixture
    def servicer(self):
        clickhouse_client = MagicMock()
        return StatsServicer(clickhouse_client)
    
    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        yield context
    
    def test_get_post_stats(self, servicer, mock_context):
        servicer.clickhouse_client.execute_query.side_effect = [
            [(5,)],
            [(10,)],
            [(3,)]
        ]
        
        request = stats_service_pb2.PostStatsRequest(post_id=1)
        
        response = servicer.GetPostStats(request, mock_context)
        
        assert response.post_id == 1
        assert response.views_count == 5
        assert response.likes_count == 10
        assert response.comments_count == 3
        assert servicer.clickhouse_client.execute_query.call_count == 3
    
    def test_get_post_stats_error(self, servicer, mock_context):
        servicer.clickhouse_client.execute_query.side_effect = Exception("Database error")
        request = stats_service_pb2.PostStatsRequest(post_id=1)
        servicer.GetPostStats(request, mock_context)
        mock_context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)
        assert "Database error" in mock_context.set_details.call_args[0][0]
    
    def test_get_post_views_dynamics(self, servicer, mock_context):
        today = datetime.now().date()
        yesterday = (today - timedelta(days=1))
        mock_result = [
            (yesterday, 3),
            (today, 5)
        ]
        servicer.clickhouse_client.execute_query.return_value = mock_result
        request = stats_service_pb2.PostDynamicsRequest(
            post_id=1,
            start_date=(today - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=today.strftime('%Y-%m-%d')
        )
        response = servicer.GetPostViewsDynamics(request, mock_context)
        assert response.post_id == 1
        assert len(response.daily_stats) == 2
        assert response.daily_stats[0].date == yesterday.strftime('%Y-%m-%d')
        assert response.daily_stats[0].count == 3
        assert response.daily_stats[1].date == today.strftime('%Y-%m-%d')
        assert response.daily_stats[1].count == 5
    
    def test_get_post_likes_dynamics(self, servicer, mock_context):
        today = datetime.now().date()
        yesterday = (today - timedelta(days=1))
        mock_result = [
            (yesterday, 2),
            (today, 4)
        ]
        servicer.clickhouse_client.execute_query.return_value = mock_result
        request = stats_service_pb2.PostDynamicsRequest(
            post_id=1,
            start_date=(today - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=today.strftime('%Y-%m-%d')
        )
        response = servicer.GetPostLikesDynamics(request, mock_context)
        assert response.post_id == 1
        assert len(response.daily_stats) == 2
        
        assert response.daily_stats[0].date == yesterday.strftime('%Y-%m-%d')
        assert response.daily_stats[0].count == 2

        assert response.daily_stats[1].date == today.strftime('%Y-%m-%d')
        assert response.daily_stats[1].count == 4
    
    def test_get_post_comments_dynamics(self, servicer, mock_context):
        today = datetime.now().date()
        yesterday = (today - timedelta(days=1))

        mock_result = [
            (yesterday, 1),
            (today, 3)
        ]
        servicer.clickhouse_client.execute_query.return_value = mock_result

        request = stats_service_pb2.PostDynamicsRequest(
            post_id=1,
            start_date=(today - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=today.strftime('%Y-%m-%d')
        )

        response = servicer.GetPostCommentsDynamics(request, mock_context)

        assert response.post_id == 1
        assert len(response.daily_stats) == 2

        assert response.daily_stats[0].date == yesterday.strftime('%Y-%m-%d')
        assert response.daily_stats[0].count == 1

        assert response.daily_stats[1].date == today.strftime('%Y-%m-%d')
        assert response.daily_stats[1].count == 3
    
    def test_get_top_posts_views(self, servicer, mock_context):
        mock_result = [
            (1, 100),
            (2, 50),
            (3, 25)
        ]
        servicer.clickhouse_client.execute_query.return_value = mock_result

        request = stats_service_pb2.TopRequest(
            metric_type=stats_service_pb2.TopRequest.MetricType.VIEWS,
            limit=3
        )

        response = servicer.GetTopPosts(request, mock_context)

        assert len(response.posts) == 3
        assert response.posts[0].post_id == 1
        assert response.posts[0].count == 100
        assert response.posts[1].post_id == 2
        assert response.posts[1].count == 50
        assert response.posts[2].post_id == 3
        assert response.posts[2].count == 25
    
    def test_get_top_posts_invalid_metric(self, servicer, mock_context):
        request = stats_service_pb2.TopRequest(
            metric_type=999,
            limit=10
        )
        servicer.GetTopPosts(request, mock_context)
        mock_context.set_code.assert_called_with(grpc.StatusCode.INVALID_ARGUMENT)
        assert "Invalid metric type" in mock_context.set_details.call_args[0][0]
    
    def test_get_top_users(self, servicer, mock_context):
        mock_result = [
            (101, 50),
            (102, 30),
            (103, 20)
        ]
        servicer.clickhouse_client.execute_query.return_value = mock_result
        request = stats_service_pb2.TopRequest(
            metric_type=stats_service_pb2.TopRequest.MetricType.LIKES,
            limit=3
        )
        response = servicer.GetTopUsers(request, mock_context)
        assert len(response.users) == 3
        
        assert response.users[0].user_id == 101
        assert response.users[0].count == 50
        
        assert response.users[1].user_id == 102
        assert response.users[1].count == 30
        
        assert response.users[2].user_id == 103
        assert response.users[2].count == 20
