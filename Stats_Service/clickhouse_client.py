import clickhouse_connect
import logging
import os

logger = logging.getLogger(__name__)

class ClickHouseClient:
    def __init__(self):
        self.host = os.environ.get('CLICKHOUSE_HOST', 'clickhouse')
        self.port = int(os.environ.get('CLICKHOUSE_HTTP_PORT', 8123))
        self.user = os.environ.get('CLICKHOUSE_USER', 'default')
        self.password = os.environ.get('CLICKHOUSE_PASSWORD', '123456')
        self.database = 'stats'
        self.client = None
    
    def connect(self):
        try:
            temp_client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                connect_timeout=30
            )
            temp_client.command('CREATE DATABASE IF NOT EXISTS stats')

            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                database=self.database
            )
            
            logger.info(f"Connected to ClickHouse at {self.host}:{self.port}, database: {self.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            return False
    
    def execute_query(self, query, params=None):
        if self.client is None and not self.connect():
            raise Exception("Not connected to ClickHouse")
        
        try:
            if params:
                if query.strip().upper().startswith('INSERT'):
                    table_name = query.split('INTO')[1].split('(')[0].strip()
                    column_names = [col.strip() for col in query.split('(')[1].split(')')[0].split(',')]

                    self.client.insert(table_name, params, column_names=column_names)
                    return True
                else:
                    result = self.client.query(query, parameters=params)
                    return result.result_rows
            else:
                result = self.client.query(query)
                return result.result_rows
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            if self.connect():
                try:
                    if params:
                        if query.strip().upper().startswith('INSERT'):
                            table_name = query.split('INTO')[1].split('(')[0].strip()
                            column_names = [col.strip() for col in query.split('(')[1].split(')')[0].split(',')]
                            
                            self.client.insert(table_name, params, column_names=column_names)
                            return True
                        else:
                            result = self.client.query(query, parameters=params)
                            return result.result_rows
                    else:
                        result = self.client.query(query)
                        return result.result_rows
                except Exception as e:
                    logger.error(f"Error executing query after reconnect: {e}")
                    raise
            else:
                raise
