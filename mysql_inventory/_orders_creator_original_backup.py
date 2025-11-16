
# mysql orders_creator.py
import os
import sys
import random
import time
import uuid
import yaml
import json
from datetime import datetime
import pytz
import sqlalchemy
from sqlalchemy import Table, MetaData, select, func
from sqlalchemy.sql import text
from multiprocessing import Process
from faker import Faker
from faker_vehicle import VehicleProvider
from faker_music import MusicProvider
import logging
from db_handler import DBConnectionHandler, load_config  # Import the DB connection handler and load_config

# Set up logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common')))
import my_logging

local_tz = pytz.timezone('Asia/Macau')

# Load configuration from YAML file
config = load_config()

default_config = config['services']['default_config']
orders_service_config = config['services']['orders_creator']

db_url = default_config['DATABASE_URL']
timeout_seconds = default_config['TIMEOUT_SECONDS']
max_retries = default_config['MAX_RETRIES']


orders_wait_time = orders_service_config['WAIT_TIME']
orders_status = orders_service_config['STATUS']
orders_num_processes = orders_service_config['NUM_PROCESSES']
orders_types = orders_service_config['TYPE']



complex_config = orders_service_config.get('COMPLEX', 'JSON')  # Get COMPLEX config, default to JSON

# Initialize DB connection handler
db_handler = DBConnectionHandler(db_url, timeout_seconds=timeout_seconds, max_retries=max_retries)

def create_fake_data(fake, type_info):
    type_name = type_info['name']
    provider_name = type_info['provider']
    method = type_info['method']

    fake.add_provider(globals()[provider_name])
    fake_value = eval(method)
    spec = {"type": type_name, "spec": fake_value}
    return spec

def orders_insert():
    engine = db_handler.get_engine()
    metadata = MetaData()
    table_name = 'orders'
    orders = Table(table_name, metadata, autoload_with=engine)

    while True:
        wait_time_seconds = random.randint(orders_wait_time[0], orders_wait_time[1])
        time.sleep(wait_time_seconds)

        type_info = random.choice(orders_types)
        fake = Faker()

        # Handle COMPLEX configuration
        if complex_config == "JSON":
            spec = create_fake_data(fake, type_info)
            spec_value = json.dumps(spec)
        else:
            spec_value = None  # Set spec to NULL if COMPLEX is NONE

        random_orders_status = random.choices(list(orders_status.keys()), weights=list(orders_status.values()))[0]

        insert_values = {
            "order_id": str(uuid.uuid4()),
            "supplier_id": random.randint(1, 150),
            "item_id": random.randint(1, 100),
            "status": random_orders_status,
            "qty": random.randint(1, 20) * 100,
            "net_price": random.randint(1, 500) * 10,
            "tax_rate": random.uniform(1, 10),
            "issued_at": datetime.now(local_tz),
            "completed_at": datetime.now(local_tz),
            "spec": spec_value,
            "created_at": datetime.now(local_tz),
            "updated_at": datetime.now(local_tz)
        }

        # Add spec column only if COMPLEX is JSON
        #if complex_config == "JSON":
        #    insert_values["spec"] = spec_value

        insert_stmt = orders.insert().values(insert_values)

        try:
            with engine.connect() as connection:
                result = connection.execute(insert_stmt)
                logging.info(f"Inserted: {result.inserted_primary_key}")

        except sqlalchemy.exc.ProgrammingError as e:
            logging.error(f"Database error: {e}")

        except Exception as e:
            logging.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    processes = []

    for _ in range(orders_num_processes):
        p_orders = Process(target=orders_insert)
        p_orders.start()
        logging.info(f"Process started with PID: {p_orders.pid}")
        processes.append(p_orders)

    for p_orders in processes:
        p_orders.join()

    # Close the database connection when done
    db_handler.close()
