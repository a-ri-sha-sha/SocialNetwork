from confluent_kafka import Consumer, KafkaError
import json
import logging
import threading
import time
from clickhouse_client import ClickHouseClient

logger = logging.getLogger(__name__)

class KafkaConsumer:
    def __init__(self, bootstrap_servers, group_id, topics, clickhouse_client):
        self.conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        }
        self.topics = topics
        self.clickhouse_client = clickhouse_client
        self.consumer = None
        self.running = False
        self.consumer_thread = None
    
    def start(self):
        if self.running:
            logger.warning("Consumer already running")
            return
        
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
        logger.info(f"Started consuming from topics: {self.topics}")
    
    def _consume(self):
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe(self.topics)
        
        try:
            while self.running:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                
                try:
                    topic = msg.topic()
                    value = json.loads(msg.value().decode('utf-8'))
                    
                    if topic == 'post-views':
                        self._process_view(value)
                    elif topic == 'post-likes':
                        self._process_like(value)
                    elif topic == 'post-comments':
                        self._process_comment(value)
                    else:
                        logger.warning(f"Unknown topic: {topic}")
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        finally:
            self.consumer.close()
    
    def _process_view(self, data):
        try:
            query = """
            INSERT INTO stats.post_views 
            (user_id, post_id, view_time, event_time) 
            VALUES
            """
            
            values = (
                data['user_id'],
                data['post_id'],
                data['view_time'],
                data['event_time']
            )
            
            self.clickhouse_client.execute_query(query, [values])
            logger.info(f"Saved view event: post_id={data['post_id']}, user_id={data['user_id']}")
        
        except Exception as e:
            logger.error(f"Error saving view event: {e}")
    
    def _process_like(self, data):
        try:
            query = """
            INSERT INTO stats.post_likes 
            (user_id, post_id, is_like, like_time, event_time) 
            VALUES
            """
            
            values = (
                data['user_id'],
                data['post_id'],
                1 if data['is_like'] else 0,
                data['like_time'],
                data['event_time']
            )
            
            self.clickhouse_client.execute_query(query, [values])
            logger.info(f"Saved like event: post_id={data['post_id']}, user_id={data['user_id']}, is_like={data['is_like']}")
        
        except Exception as e:
            logger.error(f"Error saving like event: {e}")
    
    def _process_comment(self, data):
        try:
            query = """
            INSERT INTO stats.post_comments 
            (user_id, post_id, comment_id, comment_time, event_time) 
            VALUES
            """
            
            values = (
                data['user_id'],
                data['post_id'],
                data['comment_id'],
                data['comment_time'],
                data['event_time']
            )
            
            self.clickhouse_client.execute_query(query, [values])
            logger.info(f"Saved comment event: post_id={data['post_id']}, user_id={data['user_id']}, comment_id={data['comment_id']}")
        
        except Exception as e:
            logger.error(f"Error saving comment event: {e}")
    
    def stop(self):
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join()
        logger.info("Stopped consuming messages")
