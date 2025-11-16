import random
import sqlalchemy
from datetime import datetime
from sqlalchemy import Table, MetaData, select
import logging

from base_creator import BaseCreator


class SupplierCreator(BaseCreator):
    """
    Supplier creator that inherits from BaseCreator.
    Handles supplier-specific data generation and insertion.
    """
    
    def __init__(self):
        """Initialize the SupplierCreator."""
        super().__init__('supplier_creator')
        self._load_supplier_config()
        
    def _load_supplier_config(self):
        """Load supplier-specific configuration."""
        self.supplier_types = self.service_config['TYPE']
        
    def get_table_name(self):
        """Return the table name for suppliers."""
        return 'suppliers'
        
    def generate_unique_supplier_name(self, connection):
        """
        Generate a unique supplier name that doesn't exist in the database.
        
        Args:
            connection: Database connection object
            
        Returns:
            str: Unique supplier name
        """
        metadata = MetaData()
        suppliers_table = Table(self.get_table_name(), metadata, autoload_with=connection)
        
        max_attempts = 10
        attempts = 0
        
        while attempts < max_attempts:
            supplier_name = self.fake.company() + ' ' + self.fake.company_suffix()
            
            try:
                # Check if the supplier name already exists
                select_stmt = select(sqlalchemy.func.count()).select_from(suppliers_table).where(
                    suppliers_table.c.name == supplier_name
                )
                result = connection.execute(select_stmt)
                count = result.scalar()
                
                if count == 0:
                    return supplier_name
                    
            except Exception as e:
                logging.warning(f"Error checking supplier name uniqueness: {e}")
                
            attempts += 1
            
        # If we can't find a unique name after max attempts, use a UUID suffix
        import uuid
        return f"{self.fake.company()} {self.fake.company_suffix()} {str(uuid.uuid4())[:8]}"
        
    def generate_supplier_data(self, connection):
        """
        Generate data for a single supplier.
        
        Args:
            connection: Database connection object
            
        Returns:
            dict: Dictionary containing supplier data
        """
        supplier_name = self.generate_unique_supplier_name(connection)
        supplier_type = random.choice(self.supplier_types)
        
        supplier_data = {
            "name": supplier_name,
            "type": supplier_type,
            "created_at": datetime.now(self.local_tz),
            "updated_at": datetime.now(self.local_tz)
        }
        
        return supplier_data
        
    def insert_data(self):
        """
        Main data insertion loop for suppliers.
        This method runs continuously and inserts supplier data.
        """
        engine = self.get_engine()
        metadata = MetaData()
        table_name = self.get_table_name()
        suppliers_table = Table(table_name, metadata, autoload_with=engine)
        
        while True:
            # Sleep for random time
            self.sleep_random_time()
            
            try:
                with engine.connect() as connection:
                    # Generate supplier data
                    supplier_data = self.generate_supplier_data(connection)
                    
                    # Create insert statement
                    insert_stmt = suppliers_table.insert().values(supplier_data)
                    
                    # Execute insert
                    result = connection.execute(insert_stmt)
                    connection.commit()
                    
                    logging.info(f"Inserted supplier: {supplier_data['name']} (ID: {result.inserted_primary_key})")
                    
            except sqlalchemy.exc.IntegrityError as e:
                logging.warning(f"Integrity error (likely duplicate): {e}")
                continue
                
            except sqlalchemy.exc.DatabaseError as e:
                logging.error(f"Database error: {e}")
                continue
                
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                continue


if __name__ == "__main__":
    """Main entry point for the supplier creator."""
    creator = SupplierCreator()
    creator.run()