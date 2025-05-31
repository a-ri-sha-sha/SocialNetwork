import grpc
import time
import stats_service_pb2
import stats_service_pb2_grpc
from concurrent import futures
import logging
import os
from clickhouse_client import ClickHouseClient
from kafka_consumer import KafkaConsumer
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def serve():
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Stats Service")

    clickhouse_client = ClickHouseClient()

    max_retries = 10
    for i in range(max_retries):
        logger.info(f"Attempting to connect to ClickHouse (attempt {i+1}/{max_retries})...")
        if clickhouse_client.connect():
            logger.info(f"Successfully connected to ClickHouse on attempt {i+1}")
            break
        else:
            logger.warning(f"Failed to connect to ClickHouse on attempt {i+1}, retrying in 5 seconds...")
            time.sleep(5)
    else:
        logger.error(f"Failed to connect to ClickHouse after {max_retries} attempts, exiting")
        return

    try:
        logger.info("Initializing ClickHouse schema...")

        clickhouse_client.execute_query('''
            CREATE TABLE IF NOT EXISTS post_views (
                user_id UInt32,
                post_id UInt32,
                view_time DateTime,
                event_time DateTime
            ) ENGINE = MergeTree()
            ORDER BY (post_id, view_time)
        ''')
        
        # Создание таблицы для лайков, если она не существует
        clickhouse_client.execute_query('''
            CREATE TABLE IF NOT EXISTS post_likes (
                user_id UInt32,
                post_id UInt32,
                is_like UInt8,
                like_time DateTime,
                event_time DateTime
            ) ENGINE = MergeTree()
            ORDER BY (post_id, like_time)
        ''')

        clickhouse_client.execute_query('''
            CREATE TABLE IF NOT EXISTS post_comments (
                user_id UInt32,
                post_id UInt32,
                comment_id UInt32,
                comment_time DateTime,
                event_time DateTime
            ) ENGINE = MergeTree()
            ORDER BY (post_id, comment_time)
        ''')
        
        logger.info("ClickHouse schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse schema: {e}")
        return
    
    try:
        logger.info("Initializing Kafka Consumer...")
        kafka_bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        kafka_consumer = KafkaConsumer(
            bootstrap_servers=kafka_bootstrap_servers,
            group_id='stats-service',
            topics=['post-views', 'post-likes', 'post-comments'],
            clickhouse_client=clickhouse_client
        )
        
        kafka_consumer.start()
        logger.info("Kafka Consumer started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Kafka Consumer: {e}")

    port = os.environ.get('GRPC_PORT', '50053')

    try:
        logger.info(f"Starting gRPC server on port {port}...")
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        stats_service_pb2_grpc.add_StatsServiceServicer_to_server(
            StatsServicer(clickhouse_client), server
        )
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        logger.info(f"Stats Service gRPC server started on port {port}")
        
        try:
            while True:
                time.sleep(86400)
        except KeyboardInterrupt:
                logger.info("Shutting down server...")
                server.stop(0)
                if 'kafka_consumer' in locals():
                    kafka_consumer.stop()
                logger.info("Server stopped")
    
    except Exception as e:
        logger.error(f"Failed to start gRPC server: {e}")
        if 'kafka_consumer' in locals():
            kafka_consumer.stop()

class StatsServicer(stats_service_pb2_grpc.StatsServiceServicer):
    def __init__(self, clickhouse_client):
        self.clickhouse_client = clickhouse_client
    
    def GetPostStats(self, request, context):
        post_id = request.post_id
        
        try:
            views_query = f"""
                SELECT COUNT(DISTINCT user_id) as views_count
                FROM stats.post_views
                WHERE post_id = {post_id}
            """
            views_result = self.clickhouse_client.execute_query(views_query)
            views_count = views_result[0][0] if views_result else 0

            likes_query = f"""
                SELECT
                    sum(if(is_like = 1, 1, 0)) - sum(if(is_like = 0, 1, 0)) as likes_count
                FROM stats.post_likes
                WHERE post_id = {post_id}
            """
            likes_result = self.clickhouse_client.execute_query(likes_query)
            likes_count = likes_result[0][0] if likes_result else 0

            comments_query = f"""
                SELECT COUNT(DISTINCT comment_id) as comments_count
                FROM stats.post_comments
                WHERE post_id = {post_id}
            """
            comments_result = self.clickhouse_client.execute_query(comments_query)
            comments_count = comments_result[0][0] if comments_result else 0
            
            return stats_service_pb2.PostStatsResponse(
                post_id=post_id,
                views_count=views_count,
                likes_count=likes_count,
                comments_count=comments_count
            )
        
        except Exception as e:
            logger.error(f"Error getting post stats: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting post stats: {str(e)}")
            return stats_service_pb2.PostStatsResponse()
    
    def GetPostViewsDynamics(self, request, context):
        post_id = request.post_id
        start_date = request.start_date
        end_date = request.end_date
        
        try:
            query = f"""
                SELECT
                    toDate(view_time) as day,
                    COUNT(DISTINCT user_id) as views_count
                FROM stats.post_views
                WHERE post_id = {post_id}
                    AND view_time >= '{start_date} 00:00:00'
                    AND view_time <= '{end_date} 23:59:59'
                GROUP BY day
                ORDER BY day
            """
            
            result = self.clickhouse_client.execute_query(query)
            
            daily_stats = []
            for day, count in result:
                daily_stats.append(stats_service_pb2.DailyStats(
                    date=day.strftime('%Y-%m-%d'),
                    count=count
                ))
            
            return stats_service_pb2.PostDynamicsResponse(
                post_id=post_id,
                daily_stats=daily_stats
            )
        
        except Exception as e:
            logger.error(f"Error getting post views dynamics: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting post views dynamics: {str(e)}")
            return stats_service_pb2.PostDynamicsResponse()
    
    def GetPostLikesDynamics(self, request, context):
        post_id = request.post_id
        start_date = request.start_date
        end_date = request.end_date
        
        try:
            query = f"""
                SELECT
                    toDate(like_time) as day,
                    sum(if(is_like = 1, 1, 0)) - sum(if(is_like = 0, 1, 0)) as likes_count
                FROM stats.post_likes
                WHERE post_id = {post_id}
                AND like_time >= '{start_date} 00:00:00'
                    AND like_time <= '{end_date} 23:59:59'
                GROUP BY day
                ORDER BY day
            """
            
            result = self.clickhouse_client.execute_query(query)
            
            daily_stats = []
            for day, count in result:
                daily_stats.append(stats_service_pb2.DailyStats(
                    date=day.strftime('%Y-%m-%d'),
                    count=count
                ))
            
            return stats_service_pb2.PostDynamicsResponse(
                post_id=post_id,
                daily_stats=daily_stats
            )
        
        except Exception as e:
            logger.error(f"Error getting post likes dynamics: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting post likes dynamics: {str(e)}")
            return stats_service_pb2.PostDynamicsResponse()
    
    def GetPostCommentsDynamics(self, request, context):
        post_id = request.post_id
        start_date = request.start_date
        end_date = request.end_date
        
        try:
            query = f"""
                SELECT
                    toDate(comment_time) as day,
                    COUNT(DISTINCT comment_id) as comments_count
                FROM stats.post_comments
                WHERE post_id = {post_id}
                    AND comment_time >= '{start_date} 00:00:00'
                    AND comment_time <= '{end_date} 23:59:59'
                GROUP BY day
                ORDER BY day
            """
            
            result = self.clickhouse_client.execute_query(query)
            
            daily_stats = []
            for day, count in result:
                daily_stats.append(stats_service_pb2.DailyStats(
                    date=day.strftime('%Y-%m-%d'),
                    count=count
                ))
            
            return stats_service_pb2.PostDynamicsResponse(
                post_id=post_id,
                daily_stats=daily_stats
            )
        
        except Exception as e:
            logger.error(f"Error getting post comments dynamics: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting post comments dynamics: {str(e)}")
            return stats_service_pb2.PostDynamicsResponse()
    
    def GetTopPosts(self, request, context):
        metric_type = request.metric_type
        limit = request.limit if request.limit > 0 else 10
        
        try:
            if metric_type == stats_service_pb2.TopRequest.MetricType.VIEWS:
                query = f"""
                    SELECT
                        post_id,
                        COUNT(DISTINCT user_id) as count
                    FROM stats.post_views
                    GROUP BY post_id
                    ORDER BY count DESC
                    LIMIT {limit}
                """
            elif metric_type == stats_service_pb2.TopRequest.MetricType.LIKES:
                query = f"""
                    SELECT
                        post_id,
                        sum(if(is_like = 1, 1, 0)) - sum(if(is_like = 0, 1, 0)) as count
                    FROM stats.post_likes
                    GROUP BY post_id
                    ORDER BY count DESC
                    LIMIT {limit}
                """
            elif metric_type == stats_service_pb2.TopRequest.MetricType.COMMENTS:
                query = f"""
                    SELECT
                        post_id,
                        COUNT(DISTINCT comment_id) as count
                    FROM stats.post_comments
                    GROUP BY post_id
                    ORDER BY count DESC
                    LIMIT {limit}
                """
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid metric type")
                return stats_service_pb2.TopPostsResponse()
            
            result = self.clickhouse_client.execute_query(query)
            
            posts = []
            for post_id, count in result:
                posts.append(stats_service_pb2.PostStats(
                    post_id=post_id,
                    count=count
                ))
            
            return stats_service_pb2.TopPostsResponse(posts=posts)
        
        except Exception as e:
            logger.error(f"Error getting top posts: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting top posts: {str(e)}")
            return stats_service_pb2.TopPostsResponse()
    
    def GetTopUsers(self, request, context):
        metric_type = request.metric_type
        limit = request.limit if request.limit > 0 else 10
        
        try:
            if metric_type == stats_service_pb2.TopRequest.MetricType.VIEWS:
                query = f"""
                    SELECT
                        user_id,
                        COUNT(DISTINCT post_id) as count
                    FROM stats.post_views
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT {limit}
                """
            elif metric_type == stats_service_pb2.TopRequest.MetricType.LIKES:
                query = f"""
                    SELECT
                        user_id,
                        COUNT(DISTINCT post_id) as count
                    FROM stats.post_likes
                    WHERE is_like = 1
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT {limit}
                """
            elif metric_type == stats_service_pb2.TopRequest.MetricType.COMMENTS:
                query = f"""
                    SELECT
                        user_id,
                        COUNT(DISTINCT comment_id) as count
                    FROM stats.post_comments
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT {limit}
                """
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid metric type")
                return stats_service_pb2.TopUsersResponse()
            
            result = self.clickhouse_client.execute_query(query)
            
            users = []
            for user_id, count in result:
                users.append(stats_service_pb2.UserStats(
                    user_id=user_id,
                    count=count
                ))
            
            return stats_service_pb2.TopUsersResponse(users=users)
        
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting top users: {str(e)}")
            return stats_service_pb2.TopUsersResponse()

if __name__ == '__main__':
    serve()
