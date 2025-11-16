import os
import sys
import random
import time
import yaml
import pytz
from datetime import datetime
from faker import Faker
from sqlalchemy import create_engine, Table, MetaData
from multiprocessing import Process
import mysql.connector
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common')))
import my_logging 

local_tz = pytz.timezone('Asia/Macau')
fake = Faker()

# Load configuration from YAML file
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

service_config = config['services']['supplier_creator']
db_url = service_config['DATABASE_URL']
wait_time = service_config['WAIT_TIME']
supplier_types = service_config['TYPE']
num_processes = service_config['NUM_PROCESSES']

def generate_unique_supplier_name():
    while True:
        supplier_name = fake.company() + ' ' + fake.company_suffix()
        try:
            # Check if the supplier name already exists
            select_stmt = "SELECT COUNT(*) FROM suppliers WHERE name = %s"
            cursor.execute(select_stmt, (supplier_name,))
            if cursor.fetchone()[0] == 0:
                return supplier_name
        except mysql.connector.Error:
            continue

def insert_supplier_data():
    engine = create_engine(db_url)
    metadata = MetaData()

    table_name = 'suppliers'
    suppliers = Table(table_name, metadata, autoload_with=engine)

    while True:
        wait_time_seconds = random.randint(wait_time[0], wait_time[1])

        time.sleep(wait_time_seconds)

        supplier_name = generate_unique_supplier_name()
        supplier_type = random.choice(supplier_types)

        try:
            insert_stmt = "INSERT INTO suppliers (name, type, created_at, updated_at) VALUES (%s, %s,NOW(), NOW()) "
            cursor.execute(insert_stmt, (supplier_name, supplier_type))
            conn.commit()
            
        except mysql.connector.Error:
            continue

if __name__ == "__main__":

    conn = mysql.connector.connect(
        host=db_url.split('@')[1].split(':')[0],
        user=db_url.split('://')[1].split(':')[0],
        password=db_url.split('://')[1].split(':')[1].split('@')[0],
        database=db_url.split('/')[3]
    )
    cursor = conn.cursor()

    processes = []

    for _ in range(num_processes):
        p = Process(target=insert_supplier_data)
        p.start()
        logging.info(f"Process started with PID: {p.pid}")
        processes.append(p)

    for p in processes:
        p.join()
