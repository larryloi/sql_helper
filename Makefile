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
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Options:$(RESET)"
	@echo "  db=<mysql|mssql>     - Database type (default: mysql)"
	@echo "  service=<name>       - Specific service name"
	@echo "  tag=<version>        - Docker image tag (default: latest)"
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make build.app                # build the application image"
	@echo "  make build.all                # build base + app images"
	@echo "  make run.shell                # run an interactive shell from the app image"
	@echo "  make test.config              # lint/validate YAML config files"



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