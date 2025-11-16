
# orders_purger.pytz

import os
import sys
import random
import time
import yaml
from datetime import datetime, timedelta
import pytz
import logging
from sqlalchemy import Table, MetaData, select, func, text
from multiprocessing import Process

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common')))
import my_logging

from db_handler import load_config, DBConnectionHandler

local_tz = pytz.timezone('Asia/Macau')

# Load configuration
config = load_config()
default_config = config['services']['default_config']
service_config = config['services']['orders_purger']

# wait_time in milliseconds
wait_time_ms = service_config.get('WAIT_TIME_MS', service_config.get('WAIT_TIME'))
num_processes = service_config['NUM_PROCESSES']
retention_hours = service_config['RETENTION_HOURS']
batch_size = service_config['BATCH_SIZE']

def purge_data():
    db_url = service_config.get('DATABASE_URL') or default_config.get('DATABASE_URL')
    handler = DBConnectionHandler(db_url, timeout_seconds=default_config.get('TIMEOUT_SECONDS', 30), max_retries=default_config.get('MAX_RETRIES', 3))
    engine = handler.get_engine()
    metadata = MetaData()
    schema = service_config.get('SCHEMA') or default_config.get('SCHEMA')
    orders = Table('orders', metadata, autoload_with=engine, schema=schema)

    while True:
        wait_ms = random.randint(int(wait_time_ms[0]), int(wait_time_ms[1]))
        logging.info(f"RETENTION_HOURS: {retention_hours}; Waiting for {wait_ms} ms before purging...")
        # interruptible sleep
        end_time = time.time() + (wait_ms / 1000.0)
        while time.time() < end_time:
            time.sleep(min(0.1, end_time - time.time()))

        with engine.connect() as connection:
            try:
                select_stmt = select(orders.c.order_id).where(text(f"DATEDIFF(HOUR, updated_at, GETDATE()) > {retention_hours}")).limit(batch_size)
                result = connection.execute(select_stmt)
                rows_to_delete = result.fetchall()

                while rows_to_delete:
                    delete_stmt = orders.delete().where(orders.c.order_id.in_([row['order_id'] for row in rows_to_delete]))
                    result = connection.execute(delete_stmt)

                    logging.info(f"Deleted rows: {result.rowcount}")

                    result = connection.execute(select_stmt)
                    rows_to_delete = result.fetchall()

            except Exception:
                continue


if __name__ == "__main__":
    processes = []

    for _ in range(num_processes):
        p = Process(target=purge_data)
        p.start()
        logging.info(f"Process started with PID: {p.pid}")
        processes.append(p)

    for p in processes:
        p.join()

