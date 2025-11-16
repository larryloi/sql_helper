
# orders_modifier.py

import os
import sys
import random
import time
import yaml
from datetime import datetime, timedelta
import pytz
import logging
from sqlalchemy import Table, MetaData, select, update
from multiprocessing import Process

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common')))
import my_logging

from db_handler import load_config, DBConnectionHandler

local_tz = pytz.timezone('Asia/Macau')

# Load configuration
config = load_config()
default_config = config['services']['default_config']
service_config = config['services']['orders_modifier']

# wait_time in ms
wait_time_ms = service_config.get('WAIT_TIME_MS', service_config.get('WAIT_TIME'))
status = service_config['STATUS']
num_processes = service_config['NUM_PROCESSES']
rand_last_hours = service_config['RAND_LAST_HOURS']

def modify_data():
    db_url = service_config.get('DATABASE_URL') or default_config.get('DATABASE_URL')
    handler = DBConnectionHandler(db_url, timeout_seconds=default_config.get('TIMEOUT_SECONDS', 30), max_retries=default_config.get('MAX_RETRIES', 3))
    engine = handler.get_engine()
    metadata = MetaData()
    schema = service_config.get('SCHEMA') or default_config.get('SCHEMA')
    orders = Table('orders', metadata, autoload_with=engine, schema=schema)

    while True:
        # pick random wait in milliseconds
        wait_ms = random.randint(int(wait_time_ms[0]), int(wait_time_ms[1]))
        logging.info(f"Waiting {wait_ms} ms before next modification")
        # interruptible sleep in small slices
        end_time = time.time() + (wait_ms / 1000.0)
        while time.time() < end_time:
            time.sleep(min(0.1, end_time - time.time()))

        with engine.connect() as connection:
            try:
                random_status = random.choices(list(status.keys()), weights=list(status.values()))[0]
                random_time = datetime.now(local_tz) - timedelta(hours=random.random() * rand_last_hours)

                select_stmt = select(orders).where(orders.c.created_at >= random_time).order_by(orders.c.id).limit(1)
                result = connection.execute(select_stmt)
                row = result.fetchone()

                if row is not None:
                    update_stmt = update(orders).where(orders.c.id == row['id']).values({
                        "status": random_status,
                        "updated_at": datetime.now(local_tz)
                    })

                    logging.info(f"Random time for modifier: {random_time}")
                    logging.info(f"{update_stmt}")
                    connection.execute(update_stmt)
            except Exception:
                continue


if __name__ == "__main__":
    processes = []

    for _ in range(num_processes):
        p = Process(target=modify_data)
        p.start()
        logging.info(f"Process started with PID: {p.pid}")
        processes.append(p)

    for p in processes:
        p.join()

