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

# Set up logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common')))
import my_logging

class BaseCreator(ABC):
    """
    Abstract base class for data creators.
    Provides common functionality for configuration loading, database handling,
    and multiprocessing management.
    """
    
    def __init__(self, service_name):
        """
        Initialize the base creator.
        
        Args:
            service_name (str): Name of the service configuration to load
        """
        self.service_name = service_name
        self.local_tz = pytz.timezone('Asia/Macau')
        self.fake = Faker()
        
        # Load configuration
        self._load_config()
        
        # Initialize database handler
        self._init_database()
        
    def _load_config(self):
        """Load configuration from YAML file."""
        self.config = load_config()
        
        # Load default configuration
        self.default_config = self.config['services']['default_config']
        self.db_url = self.default_config['DATABASE_URL']
        self.timeout_seconds = self.default_config['TIMEOUT_SECONDS']
        self.max_retries = self.default_config['MAX_RETRIES']
        
        # Load service-specific configuration
        self.service_config = self.config['services'][self.service_name]
        # WAIT_TIME_MS holds [min_ms, max_ms]
        self.wait_time = self.service_config.get('WAIT_TIME_MS', self.service_config.get('WAIT_TIME'))
        self.num_processes = self.service_config['NUM_PROCESSES']
        
    def _init_database(self):
        """Initialize database connection handler."""
        self.db_handler = DBConnectionHandler(
            self.db_url, 
            timeout_seconds=self.timeout_seconds, 
            max_retries=self.max_retries
        )
        
    def get_engine(self):
        """Get database engine."""
        return self.db_handler.get_engine()
        
    def close_db(self):
        """Close database connection."""
        self.db_handler.close()
        
    def get_random_wait_time(self):
        """Get random wait time based on configuration."""
        # returns milliseconds
        return random.randint(int(self.wait_time[0]), int(self.wait_time[1]))
        
    def sleep_random_time(self):
        """Sleep for a random amount of time."""
        wait_ms = random.randint(int(self.wait_time[0]), int(self.wait_time[1]))
        # Log the chosen sleep time (ms)
        logging.info(f"{self.service_name}: Sleeping {wait_ms} ms")
        time.sleep(wait_ms / 1000.0)
        
    @abstractmethod
    def insert_data(self):
        """
        Abstract method to implement data insertion logic.
        This method should contain the main data insertion loop.
        """
        pass
        
    @abstractmethod
    def get_table_name(self):
        """
        Abstract method to return the table name for this creator.
        
        Returns:
            str: The name of the database table
        """
        pass
        
    def start_processes(self):
        """Start multiple processes for data insertion."""
        processes = []
        
        for _ in range(self.num_processes):
            process = Process(target=self.insert_data)
            process.start()
            logging.info(f"Process started with PID: {process.pid}")
            processes.append(process)
            
        # Wait for all processes to complete
        for process in processes:
            process.join()
            
        # Close database connection when done
        self.close_db()
        
    def run(self):
        """Main entry point to run the creator."""
        try:
            self.start_processes()
        except KeyboardInterrupt:
            logging.info("Process interrupted by user")
        except Exception as e:
            logging.error(f"Error during execution: {e}")
        finally:
            self.close_db()