from confluent_kafka import Producer
import json
import socket
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class KafkaProducer:
    def __init__(self, bootstrap_servers):
        conf = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': socket.gethostname()
        }
        self.producer = Producer(conf)
    
    def delivery_report(self, err, msg):
        """Метод обратного вызова, вызываемый при доставке сообщения."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
    
    def send_message(self, topic, key, value):
        """Отправляет сообщение в Kafka."""
        try:
            value_json = json.dumps(value)

            self.producer.produce(
                topic=topic,
                key=key,
                value=value_json,
                callback=self.delivery_report
            )

            self.producer.poll(0)
            
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
    
    def flush(self):
        """Обеспечивает отправку всех сообщений."""
        self.producer.flush()

USER_REGISTRATION_TOPIC = 'user-registrations'
POST_VIEW_TOPIC = 'post-views'
POST_LIKE_TOPIC = 'post-likes'
POST_COMMENT_TOPIC = 'post-comments'

kafka_producer = KafkaProducer('kafka:29092')

def send_user_registration_event(user_id, registration_date):
    """Отправляет событие регистрации пользователя."""
    message = {
        'user_id': user_id,
        'registration_date': registration_date.isoformat() if hasattr(registration_date, 'isoformat') else registration_date,
        'event_time': datetime.utcnow().isoformat()
    }
    kafka_producer.send_message(USER_REGISTRATION_TOPIC, str(user_id), message)

def send_post_view_event(user_id, post_id, view_time=None):
    """Отправляет событие просмотра поста."""
    if view_time is None:
        view_time = datetime.utcnow()
    
    message = {
        'user_id': user_id,
        'post_id': post_id,
        'view_time': view_time.isoformat() if hasattr(view_time, 'isoformat') else view_time,
        'event_time': datetime.utcnow().isoformat()
    }
    kafka_producer.send_message(POST_VIEW_TOPIC, f"{user_id}_{post_id}", message)

def send_post_like_event(user_id, post_id, is_like, like_time=None):
    """Отправляет событие лайка/дизлайка поста."""
    if like_time is None:
        like_time = datetime.utcnow()
    
    message = {
        'user_id': user_id,
        'post_id': post_id,
        'is_like': is_like,
        'like_time': like_time.isoformat() if hasattr(like_time, 'isoformat') else like_time,
        'event_time': datetime.utcnow().isoformat()
    }
    kafka_producer.send_message(POST_LIKE_TOPIC, f"{user_id}_{post_id}", message)

def send_post_comment_event(user_id, post_id, comment_id, comment_time=None):
    """Отправляет событие комментирования поста."""
    if comment_time is None:
        comment_time = datetime.utcnow()
    
    message = {
        'user_id': user_id,
        'post_id': post_id,
        'comment_id': comment_id,
        'comment_time': comment_time.isoformat() if hasattr(comment_time, 'isoformat') else comment_time,
        'event_time': datetime.utcnow().isoformat()
    }
    kafka_producer.send_message(POST_COMMENT_TOPIC, f"{user_id}_{post_id}_{comment_id}", message)
