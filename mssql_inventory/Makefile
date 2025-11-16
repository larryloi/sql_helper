

include Makefile.env
# include ../Makefile

# Default variables (can be overridden)

# ct ?= orders-creator
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
	@echo "  db=<mssql|mssql>     - Database type (default: mssql)"
	@echo "  service=<name>       - Specific service name"
	@echo "  tag=<version>        - Docker image tag (default: latest)"
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make help"
	@echo "  make logs ct=orders-creator"
	@echo "  make up ct=orders-creator"


# ===================================
# Docker Compose Service Management
# ===================================

.PHONY: up.all
up.all: ## Start services (usage: make up db=mssql)
	@echo "$(GREEN)Starting services...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)✓ Services started successfully$(RESET)"


.PHONY: up
up: ## Start single service (usage: make up ct=orders-creator)
	@if [ -z "$(ct)" ]; then \
		echo "$(RED)Error: service parameter required. Usage: make up ct=orders-creator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Starting $(ct)...$(RESET)"
	docker compose up $(ct) -d
	@echo "$(GREEN)✓ Service started successfully$(RESET)"

.PHONY: down
down: ## Stop and remove services (usage: make down db=mssql)
	@if [ -z "$(ct)" ]; then \
		echo "$(RED)Error: service parameter required. Usage: make down ct=orders-creator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Stopping $(ct) service...$(RESET)"
	@docker compose stop $(ct) || true
	@docker compose rm -f $(ct) || true
	@echo "$(GREEN)✓ Service stopped and removed successfully$(RESET)"

.PHONY: down.all
down.all: ## Stop and remove all services
	@echo "$(GREEN)Stopping all services...$(RESET)"
	docker compose down
	@echo "$(GREEN)✓ All services stopped successfully$(RESET)"

.PHONY: down.all.clean
down.all.clean: ## Stop services and remove volumes
	@echo "$(GREEN)Stopping all services and cleaning volumes...$(RESET)"
	docker compose down -v
	@echo "$(GREEN)✓ Services stopped and volumes cleaned$(RESET)"

.PHONY: restart
restart: down.all up.all ## Restart services
	@echo "$(GREEN)✓ Services restarted successfully$(RESET)"

# ===================================
# Monitoring & Debugging Targets
# ===================================

.PHONY: ps status
ps status: ## Show running services status
	@echo "$(GREEN)Service Status:$(RESET)"
	docker compose ps -a
	
.PHONY: logs
logs: ## Follow logs for services (usage: make logs db=mssql)
	@if [ -z "$(ct)" ]; then \
		echo "$(RED)Error: service parameter required. Usage: make logs ct=orders-creator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Following $(ct) service logs...$(RESET)"
	@docker compose logs -f $(ct)

.PHONY: logs.all
logs.all: ## Follow logs for all services
	@echo "$(GREEN)Following all service logs...$(RESET)"
	@docker compose logs -f


.PHONY: shell
shell: ## Execute command in running service (usage: make shell ct=orders-creator [cmd="ls -la"]) 
	@if [ -z "$(ct)" ]; then \
		echo "$(RED)Error: service parameter required$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Executing command in $(ct)...$(RESET)"; \
	if [ -z "$(cmd)" ]; then \
		docker compose exec $(ct) bash; \
	else \
		docker compose exec $(ct) sh -c '$(cmd)'; \
	fi

.PHONY: stats
stats: ## Show container resource usage
	@echo "$(GREEN)Container Resource Usage:$(RESET)"
	docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# ===================================
# Health Check Targets
# ===================================

.PHONY: health
health: ## Check service health
	@echo "$(GREEN)Checking service health...$(RESET)"
	@docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Health}}"

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
	@echo "db: $(db)"
	@echo "ct: $(ct)"

.PHONY: version
version: ## Show version information
	@echo "$(GREEN)Version Information:$(RESET)"
	@echo "Base Version: $(BASE_VER)"
	@echo "App Version: $(APP_VER)"
	@echo "Image: $(IMAGE_REPO_ROOT)/$(PROJECT_NAME)-$(APP_NAME):$(APP_VER)"

