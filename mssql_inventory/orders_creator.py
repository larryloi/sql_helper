
import logging
from datetime import datetime
import json
from base_creator import BaseCreator
import random
from faker import Faker
import uuid
from sqlalchemy import Table, MetaData, select, func, Column, Integer, String, DateTime, Float, Text
from supplier_creator import SupplierCreator


class OrdersCreator(BaseCreator):
    def __init__(self):
        super().__init__('orders_creator')
        self._load_orders_config()
        # default supplier id range
        self.min_supplier_id = 1
        self.max_supplier_id = 150
        # ensure suppliers exist / pre-generate if requested
        self._prepare_suppliers()

    def _load_orders_config(self):
        self.orders_status = self.service_config['STATUS']
        self.orders_types = self.service_config['TYPE']
        self.complex_config = self.service_config.get('COMPLEX', 'JSON')

    def get_table_name(self):
        return 'orders'

    def create_fake_data(self, type_info):
        type_name = type_info['name']
        provider_name = type_info['provider']
        method = type_info['method']

        self.fake.add_provider(globals()[provider_name])
        fake_value = eval(method, {"fake": self.fake})
        spec = {"type": type_name, "spec": fake_value}
        return spec

    def generate_order_data(self):
        type_info = random.choice(self.orders_types)

        if self.complex_config == 'JSON':
            spec = self.create_fake_data(type_info)
            spec_value = json.dumps(spec)
        else:
            spec_value = None

        random_orders_status = random.choices(
            list(self.orders_status.keys()), weights=list(self.orders_status.values())
        )[0]

        order_data = {
            "order_id": str(uuid.uuid4()),
            "supplier_id": random.randint(self.min_supplier_id, self.max_supplier_id),
            "item_id": random.randint(1, 100),
            "status": random_orders_status,
            "qty": random.randint(1, 20) * 100,
            "net_price": random.randint(1, 500) * 10,
            "tax_rate": random.uniform(1, 10),
            "issued_at": datetime.now(self.local_tz),
            "completed_at": datetime.now(self.local_tz),
            "spec": spec_value,
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

        try:
            # Try to reflect the existing table; if it doesn't exist, create a simple suppliers table
            try:
                suppliers_table = Table('suppliers', metadata, autoload_with=engine, schema=self.schema if hasattr(self, 'schema') else None)
            except Exception as reflect_exc:
                # If table missing, create it with a basic schema so pre-generation can proceed
                logging.info("`suppliers` table not found; creating basic suppliers table")
                suppliers_table = Table(
                    'suppliers', metadata,
                    Column('id', Integer, primary_key=True, autoincrement=True),
                    Column('name', String(255)),
                    Column('type', String(64)),
                    Column('created_at', DateTime),
                    Column('updated_at', DateTime),
                    schema=self.schema if hasattr(self, 'schema') else None
                )
                metadata.create_all(engine)

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
            # it won't be inherited by child processes (avoids fork-safety issues).
            try:
                if hasattr(self, 'db_handler') and self.db_handler and self.db_handler.engine:
                    self.db_handler.close()
                    logging.info("Closed parent DB engine after pre-generation to avoid fork-safety issues")
            except Exception:
                pass

    def insert_data(self):
        engine = self.get_engine()
        # Ensure orders table exists; if not, create a minimal schema so inserts can proceed
        try:
            orders_table = self.get_table(self.get_table_name(), engine)
        except Exception:
            logging.info("`orders` table not found; creating basic orders table")
            metadata = MetaData()
            orders_table = Table(
                'orders', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('order_id', String(64)),
                Column('supplier_id', Integer),
                Column('item_id', Integer),
                Column('status', String(64)),
                Column('qty', Integer),
                Column('net_price', Integer),
                Column('tax_rate', Float),
                Column('issued_at', DateTime),
                Column('completed_at', DateTime),
                Column('spec', Text),
                Column('created_at', DateTime),
                Column('updated_at', DateTime),
                schema=self.schema if hasattr(self, 'schema') else None
            )
            metadata.create_all(engine)

        while True:
            self.sleep_random_time()

            order_data = self.generate_order_data()
            insert_stmt = orders_table.insert().values(order_data)

            try:
                with engine.connect() as connection:
                    result = connection.execute(insert_stmt)
                    logging.info(f"Inserted order: {result.inserted_primary_key}")
            except Exception as e:
                logging.error(f"Error inserting order: {e}")


if __name__ == '__main__':
    creator = OrdersCreator()
    creator.run()

