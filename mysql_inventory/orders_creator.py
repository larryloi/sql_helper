import uuid
import json
import random
import string
import sqlalchemy
from datetime import datetime
from sqlalchemy import Table, MetaData, select, func
from faker_vehicle import VehicleProvider
from faker_music import MusicProvider
import logging

from base_creator import BaseCreator
from suppliers_creator import SupplierCreator


class OrdersCreator(BaseCreator):
    """
    Orders creator that inherits from BaseCreator.
    Handles orders-specific data generation and insertion.
    """
    
    def __init__(self):
        """Initialize the OrdersCreator."""
        super().__init__('orders_creator')
        self._load_orders_config()
        # default supplier id range (keeps previous behavior as fallback)
        self.min_supplier_id = 1
        self.max_supplier_id = 150
        # ensure suppliers exist / pre-generate if requested
        self._prepare_suppliers()
        
    def _load_orders_config(self):
        """Load orders-specific configuration."""
        self.orders_status = self.service_config['STATUS']
        self.orders_types = self.service_config['TYPE']
        self.complex_config = self.service_config.get('COMPLEX', 'JSON')
        # Optional size limit for bigtext (KB). Can be number, string number, or 'NONE'/None.
        self.bigtext_size_kb = self.service_config.get('BIGTEXT_SIZE_KB', self.default_config.get('BIGTEXT_SIZE_KB'))
        
    def get_table_name(self):
        """Return the table name for orders."""
        return 'orders'
        
    def create_fake_data(self, type_info):
        """
        Create fake data based on type information.
        
        Args:
            type_info (dict): Type information containing name, provider, and method
            
        Returns:
            dict: Generated fake data specification
        """
        type_name = type_info['name']
        provider_name = type_info['provider']
        method = type_info['method']
        
        # Add the provider to faker
        self.fake.add_provider(globals()[provider_name])
        
        # Generate fake value using eval (note: eval should be used carefully in production)
        # Make fake available in the eval context
        fake_value = eval(method, {"fake": self.fake})
        
        spec = {"type": type_name, "spec": fake_value}
        return spec
        
    def _resolve_bigtext_size_bytes(self):
        """Return desired bigtext size in bytes based on config, or None for NULL.
        Clamps to a maximum of 10 MiB.
        """
        val = self.bigtext_size_kb
        # Treat unspecified / None / 'NONE' as NULL
        if val is None:
            return None
        if isinstance(val, str):
            if val.strip().upper() == 'NONE' or val.strip() == '':
                return None
            try:
                val = int(val.strip())
            except Exception:
                logging.warning(f"Invalid BIGTEXT_SIZE_KB value '{self.bigtext_size_kb}', setting bigtext to NULL")
                return None
        else:
            try:
                val = int(val)
            except Exception:
                logging.warning(f"Invalid BIGTEXT_SIZE_KB value '{self.bigtext_size_kb}', setting bigtext to NULL")
                return None
        if val <= 0:
            return None
        max_kb = 10 * 1024  # 10 MiB cap
        if val > max_kb:
            logging.warning(f"BIGTEXT_SIZE_KB={val}KB exceeds 10MB cap; clamping to {max_kb}KB")
            val = max_kb
        return val * 1024

    def _random_ascii_of_size(self, n_bytes: int) -> str:
        """Generate a pseudo-random ASCII string of exactly n_bytes length."""
        if n_bytes <= 0:
            return ''
        alphabet = string.ascii_letters + string.digits
        # Build in chunks to avoid huge single allocations from random.choices
        chunk_size = min(4096, n_bytes)
        chunk = ''.join(random.choices(alphabet, k=chunk_size))
        full_repeats, remainder = divmod(n_bytes, chunk_size)
        if remainder:
            tail = ''.join(random.choices(alphabet, k=remainder))
        else:
            tail = ''
        return (chunk * full_repeats) + tail

    def generate_order_data(self):
        """
        Generate data for a single order.
        
        Returns:
            dict: Dictionary containing order data
        """
        type_info = random.choice(self.orders_types)
        
        # Handle COMPLEX configuration
        if self.complex_config == "JSON":
            spec = self.create_fake_data(type_info)
            spec_value = json.dumps(spec)
        else:
            spec_value = None  # Set spec to NULL if COMPLEX is NONE
            
        # Compute bigtext value (may be NULL)
        size_bytes = self._resolve_bigtext_size_bytes()
        if size_bytes is None:
            bigtext_value = None
        else:
            bigtext_value = self._random_ascii_of_size(size_bytes)
        
        # Generate random order status based on weights
        random_orders_status = random.choices(
            list(self.orders_status.keys()), 
            weights=list(self.orders_status.values())
        )[0]
        
        # pick supplier id from the available range
        supplier_id = random.randint(self.min_supplier_id, self.max_supplier_id)

        # Generate order data
        order_data = {
            "order_id": str(uuid.uuid4()),
            "supplier_id": supplier_id,
            "item_id": random.randint(1, 100),
            "status": random_orders_status,
            "qty": random.randint(1, 20) * 100,
            "net_price": random.randint(1, 500) * 10,
            "tax_rate": random.uniform(1, 10),
            "issued_at": datetime.now(self.local_tz),
            "completed_at": datetime.now(self.local_tz),
            "spec": spec_value,
            "bigtext": bigtext_value,
            "created_at": datetime.now(self.local_tz),
            "updated_at": datetime.now(self.local_tz)
        }
        
        return order_data

    def _prepare_suppliers(self):
        """Ensure suppliers exist before orders insertion.

        This will pre-generate suppliers according to `services.supplier_creator.PREGENERATE_COUNT`
        (if present), and set `self.min_supplier_id` and `self.max_supplier_id` based on the
        suppliers table.
        """
        supplier_cfg = self.config['services'].get('supplier_creator', {})
        pre_count = int(supplier_cfg.get('PREGENERATE_COUNT', 0))

        engine = self.get_engine()
        metadata = MetaData()
        suppliers_table = Table('suppliers', metadata, autoload_with=engine)

        try:
            with engine.connect() as conn:
                existing = int(conn.execute(select(func.count()).select_from(suppliers_table)).scalar() or 0)
                to_create = max(0, pre_count - existing)

                # If there are no suppliers at all and PREGENERATE_COUNT==0, create 1 so orders can reference
                if existing == 0 and pre_count == 0:
                    to_create = 1

                if to_create > 0:
                    logging.info(f"Pre-generating {to_create} suppliers before running orders creator")
                    supplier_creator = SupplierCreator()
                    for _ in range(to_create):
                        supplier_data = supplier_creator.generate_supplier_data(conn)
                        with conn.begin():
                            conn.execute(suppliers_table.insert().values(supplier_data))
                    logging.info(f"Pre-generated {to_create} suppliers")
                else:
                    logging.info(f"No pre-generation required: existing suppliers={existing}, PREGENERATE_COUNT={pre_count}")

                # query min/max id
                row = conn.execute(select(func.min(suppliers_table.c.id), func.max(suppliers_table.c.id))).fetchone()
                min_id, max_id = row if row is not None else (None, None)

                if min_id is None or max_id is None:
                    # fallback values
                    self.min_supplier_id = 1
                    self.max_supplier_id = max(1, existing + to_create)
                else:
                    self.min_supplier_id = int(min_id)
                    self.max_supplier_id = int(max_id)

                logging.info(f"Supplier ID range set to {self.min_supplier_id}..{self.max_supplier_id}")

        except Exception as e:
            logging.warning(f"Unable to prepare suppliers automatically: {e}")
            # keep fallback range
            return
        finally:
            # Dispose any engine created during pre-generation in the parent process so
            # it won't be inherited by child processes (avoids "Command Out of Sync" and
            # lost connection errors caused by sharing DB connections across forks).
            try:
                if hasattr(self, 'db_handler') and self.db_handler and self.db_handler.engine:
                    self.db_handler.close()
                    logging.info("Closed parent DB engine after pre-generation to avoid fork-safety issues")
            except Exception:
                # don't let cleanup errors prevent startup
                pass
        
    def insert_data(self):
        """
        Main data insertion loop for orders.
        This method runs continuously and inserts order data.
        """
        engine = self.get_engine()
        metadata = MetaData()
        table_name = self.get_table_name()
        orders_table = Table(table_name, metadata, autoload_with=engine)
        
        while True:
            # Sleep for random time
            self.sleep_random_time()
            
            # Generate order data
            order_data = self.generate_order_data()
            
            # Create insert statement
            insert_stmt = orders_table.insert().values(order_data)
            
            try:
                with engine.connect() as connection:
                    result = connection.execute(insert_stmt)
                    logging.info(f"Inserted order: {result.inserted_primary_key}")
                    
            except sqlalchemy.exc.ProgrammingError as e:
                logging.error(f"Database error: {e}")
                
            except Exception as e:
                logging.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    """Main entry point for the orders creator."""
    creator = OrdersCreator()
    creator.run()