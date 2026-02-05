.PHONY: help proto build run clean docker-build docker-up docker-down test

# 默认目标
help:
	@echo "Template Recommendation System - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  proto         - Generate protobuf code"
	@echo "  build         - Build Go backend"
	@echo "  run           - Run backend locally"
	@echo "  docker-build  - Build Docker images"
	@echo "  docker-up     - Start all services with Docker Compose"
	@echo "  docker-down   - Stop all services"
	@echo "  clean         - Clean build artifacts"
	@echo "  test          - Run tests"

# 生成 protobuf 代码
proto:
	@echo "Generating protobuf code..."
	@# Go gRPC code
	@bash scripts/generate_proto_go.sh
	@# Python gRPC code
	@bash scripts/generate_proto_python.sh
	@echo "✅ Protobuf code generated for both Go and Python!"

# 编译 Go 后端
build:
	@echo "Building Go backend..."
	cd backend && go build -o bin/api-server ./cmd/api
	@echo "Build complete!"

# 本地运行 Python 后端
run-agent:
	@echo "Starting Python backend server..."
	cd agent && if [ -d "venv" ]; then ./venv/bin/python3 ./server.py; else python3 ./server.py; fi

# 本地运行后端
run-backend:
	@echo "Starting backend server..."
	cd backend && go run ./cmd/api/main.go

# 本地运行前端
run-frontend:
	@echo "Starting frontend server..."
	cd frontend && npm run dev

# 清理构建产物
clean:
	@echo "Cleaning..."
	rm -rf backend/bin
	rm -f agent/proto/*_pb2.py agent/proto/*_pb2_grpc.py
	@echo "Clean complete!"

# 构建 Docker 镜像
docker-build:
	@echo "Building Docker images..."
	docker-compose build
	@echo "Docker images built!"

# 构建并启动 除 agent, backend 之外的其他服务
docker-run-others:
	@echo "Building other Docker images..."
	docker-compose build postgres redis milvus etcd minio
	@echo "Other Docker images built!"
	docker-compose up -d postgres redis milvus etcd minio
	@echo "Other services started!"

# 启动所有服务
docker-up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started!"
	@echo "API: http://localhost:8080"
	@echo "MinIO Console: http://localhost:9001"

# 停止所有服务
docker-down:
	@echo "Stopping all services..."
	docker-compose down
	@echo "Services stopped!"

# 查看日志
logs:
	docker-compose logs -f

# 运行测试
test:
	@echo "Running tests..."
	cd backend && go test ./...
	@echo "Tests complete!"

# 初始化开发环境
init:
	@echo "Initializing development environment..."
	@# 检查依赖
	@command -v go >/dev/null 2>&1 || { echo "Go is not installed!"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Python3 is not installed!"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "Docker is not installed!"; exit 1; }
	@# 安装 Python 依赖
	cd agent && pip install -r requirements.txt
	@# 下载 Go 依赖
	cd backend && go mod download
	@# 生成 proto
	$(MAKE) proto
	@echo "Development environment initialized!"

# 数据库迁移
db-migrate:
	@echo "Running database migrations..."
	@# TODO: Add migration tool
	@echo "Migrations complete!"

# Kubernetes 部署
k8s-deploy-agent:
	@echo "Deploying agent..."
	kubectl apply -f k8s/agent-deployment.yaml
	@echo "Agent deployed!"


k8s-deploy-backend:
	@echo "Deploying backend..."
	kubectl apply -f k8s/backend-deployment.yaml
	@echo "Backend deployed!"

k8s-deploy-frontend:
	@echo "Deploying frontend..."
	kubectl apply -f k8s/frontend-deployment.yaml
	@echo "Frontend deployed!"


k8s-deploy-config:
	@echo "Deploying config..."
	kubectl apply -f k8s/secrets.yaml 
	kubectl apply -f k8s/configmap.yaml
	@echo "Config deployed!"

k8s-deploy-infra:
	@echo "Deploying infrastructure (Postgres, Redis, Milvus, etcd, MinIO)..."
	kubectl apply -f k8s/infra.yaml
	@echo "Infrastructure deployed!"

k8s-deploy-services:
	@echo "Deploying applications..."
	kubectl apply -f k8s/services.yaml
	kubectl apply -f k8s/agent-deployment.yaml
	kubectl apply -f k8s/backend-deployment.yaml
	kubectl apply -f k8s/frontend-deployment.yaml
	@echo "Applications deployed!"

k8s-deploy-all:
	@echo "Deploying all services..."
	$(MAKE) k8s-deploy-config
	$(MAKE) k8s-deploy-infra
	$(MAKE) k8s-deploy-services
	@echo "All services deployed!"

