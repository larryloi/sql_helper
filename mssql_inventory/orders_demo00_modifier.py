import os
import random
import time
import uuid
import yaml
from datetime import datetime, timedelta
import pytz
import sqlalchemy
from sqlalchemy import create_engine, Table, MetaData, update
from sqlalchemy.sql import text, select
from multiprocessing import Process
import logging

logging.basicConfig(
  format="[%(asctime)s] %(levelname)s: %(message)s",
  style="%",
  datefmt="%Y-%m-%d %H:%M:%S",
  level=logging.INFO,
)

local_tz = pytz.timezone('Asia/Macau')

# Load configuration from YAML file
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

service_config = config['services']['orders_demo00_modifier']
wait_time = service_config['WAIT_TIME']
status = service_config['STATUS']
num_processes = service_config['NUM_PROCESSES']
rand_last_hours = service_config['RAND_LAST_HOURS']

def modify_data():
    engine = create_engine(service_config['DATABASE_URL'])
    metadata = MetaData()
    orders_demo00 = Table('orders_demo00', metadata, autoload_with=engine, schema='inventory.INV')

    while True:
        wait_time_seconds = random.randint(wait_time[0], wait_time[1])
        time.sleep(wait_time_seconds)

        with engine.connect() as connection:
            try:
                random_status = random.choices(list(status.keys()), weights=list(status.values()))[0]
                # Randomly define a datetime within the last 3 hours
                random_time = datetime.now(local_tz) - timedelta(hours=random.random() * rand_last_hours)

                # Select the first record after the random time
                select_stmt = select(orders_demo00).where(orders_demo00.c.created_at >= random_time).order_by(orders_demo00.c.id).limit(1)
                #logging.info(f"{select_stmt.compile().string} with parameters {select_stmt.compile().params}")
                result = connection.execute(select_stmt)
                row = result.fetchone()

                if row is not None:
                    # Update the selected record
                    update_stmt = update(orders_demo00).where(orders_demo00.c.id == row['id']).values({
                        "status": random_status,
                        "updated_at": datetime.now(local_tz)
                    })

                    logging.info(f"Random time for modifier: {random_time}")
                    logging.info(f"{update_stmt.compile().string} with parameters {update_stmt.compile().params}")
                    
                    connection.execute(update_stmt)
            except sqlalchemy.exc.ProgrammingError:
                continue


if __name__ == "__main__":
    processes = []

    for _ in range(num_processes):
        p = Process(target=modify_data)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

