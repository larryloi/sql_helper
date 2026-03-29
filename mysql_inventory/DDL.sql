CREATE DATABASE inventory;
GO

USE inventory;
GO

CREATE TABLE inventory.suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY (name, type)
);

CREATE INDEX idx_created_at ON suppliers (created_at);

CREATE INDEX idx_updated_at ON suppliers (updated_at);

CREATE INDEX suppliers_type_IDX USING BTREE ON suppliers (`type`);




CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT NOT NULL,
    order_id VARCHAR(36) NOT NULL,
    supplier_id INT NOT NULL,
    item_id INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    qty INT NOT NULL,
    net_price INT NOT NULL,
    tax_rate FLOAT NOT NULL,
    issued_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    spec json DEFAULT NULL,
    bigtext MEDIUMTEXT NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE INDEX IDX_orders_issued_at ON orders (issued_at);
CREATE UNIQUE INDEX IDX_orders_order_id ON orders (order_id);
CREATE INDEX IDX_orders_completed_at ON orders (completed_at);
CREATE INDEX IDX_orders_created_at ON orders (created_at);
CREATE INDEX IDX_orders_updated_at ON orders (updated_at);

