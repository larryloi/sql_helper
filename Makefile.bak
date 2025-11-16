# SQL Helper Project Makefile
# Enhanced version with comprehensive targets for development and operations

include Makefile.env

# Default variables (can be overridden)
db ?= mysql
service ?= all
tag ?= latest
PROFILE ?= $(db)

# Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

# Help target
.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)SQL Helper Project Makefile$(RESET)"
	@echo "$(YELLOW)Usage: make [target] [options]$(RESET)"
	@echo ""
	@echo "$(MAGENTA)Available targets:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Options:$(RESET)"
	@echo "  db=<mysql|mssql>     - Database type (default: mysql)"
	@echo "  service=<name>       - Specific service name"
	@echo "  tag=<version>        - Docker image tag (default: latest)"
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make up db=mysql"
	@echo "  make logs db=mssql service=orders_creator"
	@echo "  make build tag=v1.0.0"

# ===================================
# Build Targets
# ===================================

.PHONY: build.base
build.base: ## Build base Docker image
	@echo "$(GREEN)Building base image...$(RESET)"
	docker build -t $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(BASE_NAME):$(BASE_VER) --target base .
	@echo "$(GREEN)✓ Base image built successfully$(RESET)"

.PHONY: build.app build
build.app build: ## Build application Docker image
	@echo "$(GREEN)Building application image...$(RESET)"
	docker build -t $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER) --target app .
	@echo "$(GREEN)✓ Application image built successfully$(RESET)"

.PHONY: build.all
build.all: build.base build.app ## Build all Docker images
	@echo "$(GREEN)✓ All images built successfully$(RESET)"

.PHONY: build.nocache
build.nocache: ## Build application image without cache
	@echo "$(GREEN)Building application image (no cache)...$(RESET)"
	docker build --no-cache -t $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER) --target app .
	@echo "$(GREEN)✓ Application image built successfully$(RESET)"

# ===================================
# Registry Targets
# ===================================

.PHONY: push.base
push.base: ## Push base image to registry
	@echo "$(GREEN)Pushing base image...$(RESET)"
	docker push $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(BASE_NAME):$(BASE_VER)
	@echo "$(GREEN)✓ Base image pushed successfully$(RESET)"

.PHONY: push.app push
push.app push: ## Push application image to registry
	@echo "$(GREEN)Pushing application image...$(RESET)"
	docker push $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER)
	@echo "$(GREEN)✓ Application image pushed successfully$(RESET)"

.PHONY: push.all
push.all: push.base push.app ## Push all images to registry
	@echo "$(GREEN)✓ All images pushed successfully$(RESET)"

.PHONY: pull
pull: ## Pull application image from registry
	@echo "$(GREEN)Pulling application image...$(RESET)"
	docker pull $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER)
	@echo "$(GREEN)✓ Application image pulled successfully$(RESET)"

# ===================================
# Development & Testing Targets
# ===================================

.PHONY: run.shell
run.shell: ## Run interactive shell in container
	@echo "$(GREEN)Starting interactive shell...$(RESET)"
	docker run --rm -it $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER) /bin/bash

.PHONY: run.mount
run.mount: ## Run interactive shell with mounted volumes
	@echo "$(GREEN)Starting interactive shell with mounted volumes...$(RESET)"
	docker run --rm -it \
		-v ./common/:/app/common/ \
		-v ./$(APP_DB)/config.yml:/app/config.yml \
		-v ./$(APP_DB)/:/app/$(APP_DB)/ \
		$(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER) /bin/bash

.PHONY: test.config
test.config: ## Test configuration files syntax
	@echo "$(GREEN)Testing configuration files...$(RESET)"
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint mysql_inventory/config.yml mssql_inventory/config.yml; \
	else \
		echo "$(YELLOW)Warning: yamllint not installed, skipping YAML validation$(RESET)"; \
	fi
	@echo "$(GREEN)✓ Configuration files validated$(RESET)"

.PHONY: lint
lint: ## Run linting on Python files
	@echo "$(GREEN)Running linting...$(RESET)"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 mysql_inventory/ mssql_inventory/ common/ --max-line-length=120; \
	else \
		echo "$(YELLOW)Warning: flake8 not installed, skipping Python linting$(RESET)"; \
	fi
	@echo "$(GREEN)✓ Linting completed$(RESET)"

# ===================================
# Docker Compose Service Management
# ===================================

.PHONY: up
up: ## Start services (usage: make up db=mysql)
	@echo "$(GREEN)Starting $(db) services...$(RESET)"
	docker compose --profile $(db) up -d
	@echo "$(GREEN)✓ Services started successfully$(RESET)"

.PHONY: up.build
up.build: ## Start services with build (usage: make up.build db=mysql)
	@echo "$(GREEN)Starting $(db) services with build...$(RESET)"
	docker compose --profile $(db) up -d --build
	@echo "$(GREEN)✓ Services started successfully$(RESET)"

.PHONY: up.recreate
up.recreate: ## Recreate and start services
	@echo "$(GREEN)Recreating $(db) services...$(RESET)"
	docker compose --profile $(db) up -d --force-recreate
	@echo "$(GREEN)✓ Services recreated successfully$(RESET)"

.PHONY: up.single
up.single: ## Start single service (usage: make up.single db=mysql service=orders_creator)
	@if [ -z "$(service)" ]; then \
		echo "$(RED)Error: service parameter required. Usage: make up.single db=mysql service=orders_creator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Starting $(db)_$(service)...$(RESET)"
	docker compose up $(db)_$(service) -d
	@echo "$(GREEN)✓ Service started successfully$(RESET)"

.PHONY: down
down: ## Stop and remove services (usage: make down db=mysql)
	@echo "$(GREEN)Stopping $(db) services...$(RESET)"
	docker compose --profile $(db) down
	@echo "$(GREEN)✓ Services stopped successfully$(RESET)"

.PHONY: down.all
down.all: ## Stop and remove all services
	@echo "$(GREEN)Stopping all services...$(RESET)"
	docker compose --profile all down
	@echo "$(GREEN)✓ All services stopped successfully$(RESET)"

.PHONY: down.clean
down.clean: ## Stop services and remove volumes
	@echo "$(GREEN)Stopping $(db) services and cleaning volumes...$(RESET)"
	docker compose --profile $(db) down -v
	@echo "$(GREEN)✓ Services stopped and volumes cleaned$(RESET)"

.PHONY: restart
restart: down up ## Restart services
	@echo "$(GREEN)✓ Services restarted successfully$(RESET)"

# ===================================
# Monitoring & Debugging Targets
# ===================================

.PHONY: ps status
ps status: ## Show running services status
	@echo "$(GREEN)Service Status:$(RESET)"
	docker compose --profile $(db) ps

.PHONY: ps.all
ps.all: ## Show all services status
	@echo "$(GREEN)All Services Status:$(RESET)"
	docker compose --profile all ps

.PHONY: logs
logs: ## Follow logs for services (usage: make logs db=mysql)
	@echo "$(GREEN)Following $(db) service logs...$(RESET)"
	docker compose --profile $(db) logs -f

.PHONY: logs.single
logs.single: ## Follow logs for single service (usage: make logs.single db=mysql service=orders_creator)
	@if [ -z "$(service)" ]; then \
		echo "$(RED)Error: service parameter required. Usage: make logs.single db=mysql service=orders_creator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Following logs for $(db)_$(service)...$(RESET)"
	docker compose logs -f $(db)_$(service)

.PHONY: logs.tail
logs.tail: ## Show last 100 lines of logs
	@echo "$(GREEN)Showing recent $(db) service logs...$(RESET)"
	docker compose --profile $(db) logs --tail=100

.PHONY: exec
exec: ## Execute command in running service (usage: make exec db=mysql service=orders_creator cmd="ls -la")
	@if [ -z "$(service)" ]; then \
		echo "$(RED)Error: service parameter required$(RESET)"; \
		exit 1; \
	fi
	@if [ -z "$(cmd)" ]; then \
		cmd="/bin/bash"; \
	fi; \
	echo "$(GREEN)Executing command in $(db)_$(service)...$(RESET)"; \
	docker compose exec $(db)_$(service) $$cmd

.PHONY: stats
stats: ## Show container resource usage
	@echo "$(GREEN)Container Resource Usage:$(RESET)"
	docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# ===================================
# Maintenance Targets
# ===================================

.PHONY: clean.containers
clean.containers: ## Remove stopped containers
	@echo "$(GREEN)Cleaning stopped containers...$(RESET)"
	docker container prune -f
	@echo "$(GREEN)✓ Stopped containers cleaned$(RESET)"

.PHONY: clean.images
clean.images: ## Remove unused images
	@echo "$(GREEN)Cleaning unused images...$(RESET)"
	docker image prune -f
	@echo "$(GREEN)✓ Unused images cleaned$(RESET)"

.PHONY: clean.volumes
clean.volumes: ## Remove unused volumes
	@echo "$(GREEN)Cleaning unused volumes...$(RESET)"
	docker volume prune -f
	@echo "$(GREEN)✓ Unused volumes cleaned$(RESET)"

.PHONY: clean.networks
clean.networks: ## Remove unused networks
	@echo "$(GREEN)Cleaning unused networks...$(RESET)"
	docker network prune -f
	@echo "$(GREEN)✓ Unused networks cleaned$(RESET)"

.PHONY: clean.all
clean.all: clean.containers clean.images clean.volumes clean.networks ## Clean all unused Docker resources
	@echo "$(GREEN)✓ All unused Docker resources cleaned$(RESET)"

.PHONY: clean.project
clean.project: down.all ## Clean all project containers and images
	@echo "$(GREEN)Cleaning project containers and images...$(RESET)"
	docker compose --profile all down --rmi all -v
	@echo "$(GREEN)✓ Project resources cleaned$(RESET)"

# ===================================
# Health Check Targets
# ===================================

.PHONY: health
health: ## Check service health
	@echo "$(GREEN)Checking service health...$(RESET)"
	@docker compose --profile $(db) ps --format "table {{.Service}}\t{{.Status}}\t{{.Health}}"

.PHONY: health.logs
health.logs: ## Show health check logs
	@echo "$(GREEN)Health check logs:$(RESET)"
	@docker compose --profile $(db) logs --grep healthcheck

# ===================================
# Environment Targets
# ===================================

.PHONY: env
env: ## Show environment configuration
	@echo "$(GREEN)Environment Configuration:$(RESET)"
	@echo "PROJECT_NAME: $(PROJECT_NAME)"
	@echo "APP_NAME: $(APP_NAME)"
	@echo "APP_VER: $(APP_VER)"
	@echo "IMAGE_REPO_ROOT: $(IMAGE_REPO_ROOT)"
	@echo "APP_DB: $(APP_DB)"
	@echo "Database: $(db)"
	@echo "Profile: $(PROFILE)"

.PHONY: version
version: ## Show version information
	@echo "$(GREEN)Version Information:$(RESET)"
	@echo "Base Version: $(BASE_VER)"
	@echo "App Version: $(APP_VER)"
	@echo "Image: $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER)"

# ===================================
# Quick Start Targets
# ===================================

.PHONY: dev.mysql
dev.mysql: ## Quick start MySQL development environment
	@echo "$(GREEN)Starting MySQL development environment...$(RESET)"
	make build
	make up db=mysql
	make logs db=mysql

.PHONY: dev.mssql
dev.mssql: ## Quick start MSSQL development environment
	@echo "$(GREEN)Starting MSSQL development environment...$(RESET)"
	make build
	make up db=mssql
	make logs db=mssql

.PHONY: dev.stop
dev.stop: ## Stop development environment
	@echo "$(GREEN)Stopping development environment...$(RESET)"
	make down.all

# Set default target
.DEFAULT_GOAL := help
