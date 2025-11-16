import os
import sys
import random
import time
import yaml
import pytz
from datetime import datetime
from faker import Faker
from abc import ABC, abstractmethod
from multiprocessing import Process
import logging

from db_handler import DBConnectionHandler, load_config

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common')))
import my_logging


class BaseCreator(ABC):
    """
    Abstract base class for MSSQL data creators.
    Provides configuration loading, DB handler initialization and process management.
    """

    def __init__(self, service_name):
        self.service_name = service_name
        self.local_tz = pytz.timezone('Asia/Macau')
        self.fake = Faker()

        # Load configuration
        self._load_config()

        # Initialize database
        self._init_database()

    def _load_config(self):
        # load config from mssql_inventory/config.yml
        self.config = load_config()
        self.default_config = self.config['services']['default_config']
        self.db_url = self.default_config['DATABASE_URL']
        self.timeout_seconds = self.default_config['TIMEOUT_SECONDS']
        self.max_retries = self.default_config['MAX_RETRIES']

        self.service_config = self.config['services'][self.service_name]
        # WAIT_TIME_MS holds [min_ms, max_ms]
        self.wait_time = self.service_config.get('WAIT_TIME_MS', self.service_config.get('WAIT_TIME'))
        self.num_processes = self.service_config['NUM_PROCESSES']

        # optional schema for MSSQL (e.g. inventory.INV)
        self.schema = self.service_config.get('SCHEMA') or self.default_config.get('SCHEMA')

    def _init_database(self):
        self.db_handler = DBConnectionHandler(
            self.db_url, timeout_seconds=self.timeout_seconds, max_retries=self.max_retries
        )

    def get_engine(self):
        return self.db_handler.get_engine()

    def close_db(self):
        self.db_handler.close()

    def get_random_wait_time(self):
        # return milliseconds
        return random.randint(int(self.wait_time[0]), int(self.wait_time[1]))

    def sleep_random_time(self):
        wait_ms = self.get_random_wait_time()
        logging.info(f"{self.service_name}: Sleeping {wait_ms} ms")
        # sleep in seconds
        time.sleep(wait_ms / 1000.0)

    def get_table(self, table_name, engine):
        from sqlalchemy import Table, MetaData
        metadata = MetaData()
        if self.schema:
            return Table(table_name, metadata, autoload_with=engine, schema=self.schema)
        return Table(table_name, metadata, autoload_with=engine)

    @abstractmethod
    def insert_data(self):
        pass

    @abstractmethod
    def get_table_name(self):
        pass

    def start_processes(self):
        processes = []
        for _ in range(self.num_processes):
            p = Process(target=self.insert_data)
            p.start()
            logging.info(f"Process started with PID: {p.pid}")
            processes.append(p)

        for p in processes:
            p.join()

        self.close_db()

    def run(self):
        try:
            self.start_processes()
        except KeyboardInterrupt:
            logging.info("Process interrupted by user")
        except Exception as e:
            logging.error(f"Error during execution: {e}")
        finally:
            self.close_db()
