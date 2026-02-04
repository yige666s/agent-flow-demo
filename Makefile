# Makefile for Agent Flow Demo Project

.PHONY: help build run test clean docker-build docker-run deploy-local k8s-deploy

# 变量定义
AWS_REGION := us-east-1
ECR_REGISTRY := 483739914637.dkr.ecr.us-east-1.amazonaws.com
ECR_REPO_AGENT := agent-flow-agent
ECR_REPO_BACKEND := agent-flow-backend
ECR_REPO_FRONTEND := agent-flow-frontend
EKS_CLUSTER := ferocious-rock-goose
IMAGE_TAG := $(shell git rev-parse --short HEAD)

help: ## 显示帮助信息
	@echo "Agent Flow Demo - 可用的命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ========== 本地开发 ==========
install-agent: ## 安装Agent依赖
	@echo "Installing Agent dependencies..."
	cd agent && pip install -r requirements.txt

install-backend: ## 安装Backend依赖
	@echo "Installing Backend dependencies..."
	cd backend && go mod download

run-agent: ## 运行Agent服务
	@echo "Running Agent service..."
	cd agent && python app.py

run-backend: ## 运行Backend服务
	@echo "Running Backend service..."
	cd backend && go run main.go

run-frontend: ## 运行Frontend服务（需要http-server）
	@echo "Running Frontend service..."
	cd frontend && python -m http.server 8000

test-agent: ## 测试Agent
	@echo "Testing Agent..."
	cd agent && python -m pytest core/test/

test-backend: ## 测试Backend
	@echo "Testing Backend..."
	cd backend && go test -v ./...

# ========== Docker构建 ==========
docker-build-agent: ## 构建Agent Docker镜像
	@echo "Building Agent Docker image..."
	docker build -t $(ECR_REPO_AGENT):$(IMAGE_TAG) -f agent/Dockerfile ./agent
	docker tag $(ECR_REPO_AGENT):$(IMAGE_TAG) $(ECR_REPO_AGENT):latest

docker-build-backend: ## 构建Backend Docker镜像
	@echo "Building Backend Docker image..."
	docker build -t $(ECR_REPO_BACKEND):$(IMAGE_TAG) -f backend/Dockerfile ./backend
	docker tag $(ECR_REPO_BACKEND):$(IMAGE_TAG) $(ECR_REPO_BACKEND):latest

docker-build-frontend: ## 构建Frontend Docker镜像
	@echo "Building Frontend Docker image..."
	docker build -t $(ECR_REPO_FRONTEND):$(IMAGE_TAG) -f frontend/Dockerfile ./frontend
	docker tag $(ECR_REPO_FRONTEND):$(IMAGE_TAG) $(ECR_REPO_FRONTEND):latest

docker-build-all: docker-build-agent docker-build-backend docker-build-frontend ## 构建所有Docker镜像

# ========== Docker本地运行 ==========
docker-run-agent: ## 运行Agent容器
	@echo "Running Agent container..."
	docker run -d --name agent-flow-agent -p 8000:8000 $(ECR_REPO_AGENT):latest

docker-run-backend: ## 运行Backend容器
	@echo "Running Backend container..."
	docker run -d --name agent-flow-backend -p 8080:8080 \
		-e AGENT_SERVICE_URL=http://host.docker.internal:8000 \
		$(ECR_REPO_BACKEND):latest

docker-run-frontend: ## 运行Frontend容器
	@echo "Running Frontend container..."
	docker run -d --name agent-flow-frontend -p 80:80 $(ECR_REPO_FRONTEND):latest

docker-stop-all: ## 停止所有容器
	@echo "Stopping all containers..."
	docker stop agent-flow-agent agent-flow-backend agent-flow-frontend 2>/dev/null || true
	docker rm agent-flow-agent agent-flow-backend agent-flow-frontend 2>/dev/null || true

# ========== AWS ECR ==========
ecr-login: ## 登录到AWS ECR
	@echo "Logging into AWS ECR..."
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ECR_REGISTRY)

ecr-create-repos: ## 创建ECR仓库
	@echo "Creating ECR repositories..."
	aws ecr create-repository --repository-name $(ECR_REPO_AGENT) --region $(AWS_REGION) 2>/dev/null || true
	aws ecr create-repository --repository-name $(ECR_REPO_BACKEND) --region $(AWS_REGION) 2>/dev/null || true
	aws ecr create-repository --repository-name $(ECR_REPO_FRONTEND) --region $(AWS_REGION) 2>/dev/null || true

docker-push-agent: ecr-login ## 推送Agent镜像到ECR
	@echo "Pushing Agent image to ECR..."
	docker tag $(ECR_REPO_AGENT):$(IMAGE_TAG) $(ECR_REGISTRY)/$(ECR_REPO_AGENT):$(IMAGE_TAG)
	docker tag $(ECR_REPO_AGENT):latest $(ECR_REGISTRY)/$(ECR_REPO_AGENT):latest
	docker push $(ECR_REGISTRY)/$(ECR_REPO_AGENT):$(IMAGE_TAG)
	docker push $(ECR_REGISTRY)/$(ECR_REPO_AGENT):latest

docker-push-backend: ecr-login ## 推送Backend镜像到ECR
	@echo "Pushing Backend image to ECR..."
	docker tag $(ECR_REPO_BACKEND):$(IMAGE_TAG) $(ECR_REGISTRY)/$(ECR_REPO_BACKEND):$(IMAGE_TAG)
	docker tag $(ECR_REPO_BACKEND):latest $(ECR_REGISTRY)/$(ECR_REPO_BACKEND):latest
	docker push $(ECR_REGISTRY)/$(ECR_REPO_BACKEND):$(IMAGE_TAG)
	docker push $(ECR_REGISTRY)/$(ECR_REPO_BACKEND):latest

docker-push-frontend: ecr-login ## 推送Frontend镜像到ECR
	@echo "Pushing Frontend image to ECR..."
	docker tag $(ECR_REPO_FRONTEND):$(IMAGE_TAG) $(ECR_REGISTRY)/$(ECR_REPO_FRONTEND):$(IMAGE_TAG)
	docker tag $(ECR_REPO_FRONTEND):latest $(ECR_REGISTRY)/$(ECR_REPO_FRONTEND):latest
	docker push $(ECR_REGISTRY)/$(ECR_REPO_FRONTEND):$(IMAGE_TAG)
	docker push $(ECR_REGISTRY)/$(ECR_REPO_FRONTEND):latest

docker-push-all: docker-push-agent docker-push-backend docker-push-frontend ## 推送所有镜像到ECR

# ========== Kubernetes部署 ==========
k8s-config: ## 配置kubectl访问EKS集群
	@echo "Configuring kubectl for EKS..."
	aws eks update-kubeconfig --region $(AWS_REGION) --name $(EKS_CLUSTER)

k8s-deploy-secrets: k8s-config ## 部署Secrets到K8s
	@echo "Deploying Secrets to Kubernetes..."
	@if [ ! -f k8s/secrets.yaml ]; then \
		echo "⚠️  Warning: k8s/secrets.yaml not found!"; \
		echo "Please copy k8s/secrets.yaml.example to k8s/secrets.yaml and fill in your API keys"; \
		exit 1; \
	fi
	kubectl apply -f k8s/secrets.yaml

k8s-update-secrets: k8s-config ## 更新Secrets并重启服务
	@echo "Updating Secrets..."
	kubectl apply -f k8s/secrets.yaml
	kubectl rollout restart deployment/agent-flow-agent
	kubectl rollout restart deployment/agent-flow-backend

k8s-verify-secrets: k8s-config ## 验证Secrets是否已部署
	@echo "Verifying Secrets..."
	kubectl get secret agent-flow-secrets -o yaml

k8s-deploy-agent: k8s-config ## 部署Agent到K8s
	@echo "Deploying Agent to Kubernetes..."
	sed "s|__AGENT_IMAGE__|$(ECR_REGISTRY)/$(ECR_REPO_AGENT):$(IMAGE_TAG)|g" k8s/agent-deployment.yaml | kubectl apply -f -
	kubectl apply -f k8s/agent-service.yaml

k8s-deploy-backend: k8s-config ## 部署Backend到K8s
	@echo "Deploying Backend to Kubernetes..."
	sed "s|__BACKEND_IMAGE__|$(ECR_REGISTRY)/$(ECR_REPO_BACKEND):$(IMAGE_TAG)|g" k8s/backend-deployment.yaml | kubectl apply -f -
	kubectl apply -f k8s/backend-service.yaml

k8s-deploy-frontend: k8s-config ## 部署Frontend到K8s
	@echo "Deploying Frontend to Kubernetes..."
	sed "s|__FRONTEND_IMAGE__|$(ECR_REGISTRY)/$(ECR_REPO_FRONTEND):$(IMAGE_TAG)|g" k8s/frontend-deployment.yaml | kubectl apply -f -
	kubectl apply -f k8s/frontend-service.yaml

k8s-deploy-all: k8s-deploy-secrets k8s-deploy-agent k8s-deploy-backend k8s-deploy-frontend ## 部署所有服务到K8s
	@echo "All services deployed!"

k8s-status: k8s-config ## 查看K8s部署状态
	@echo "Checking deployment status..."
	kubectl get deployments
	kubectl get services
	kubectl get pods

k8s-logs-agent: k8s-config ## 查看Agent日志
	kubectl logs -l app=agent-flow-agent --tail=100 -f

k8s-logs-backend: k8s-config ## 查看Backend日志
	kubectl logs -l app=agent-flow-backend --tail=100 -f

k8s-logs-frontend: k8s-config ## 查看Frontend日志
	kubectl logs -l app=agent-flow-frontend --tail=100 -f

k8s-delete-all: k8s-config ## 删除所有K8s资源
	@echo "Deleting all Kubernetes resources..."
	kubectl delete -f k8s/ --ignore-not-found=true || true
	kubectl delete secret agent-flow-secrets --ignore-not-found=true || true

# ========== 完整部署流程 ==========
deploy-to-aws: docker-build-all docker-push-all k8s-deploy-all ## 完整部署到AWS（构建、推送、部署）
	@echo "✅ Deployment to AWS completed!"
	@echo "Getting service URL..."
	@kubectl get service agent-flow-frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
	@echo ""

# ========== 清理 ==========
clean: ## 清理本地构建文件
	@echo "Cleaning up..."
	rm -rf agent/__pycache__ agent/**/__pycache__
	rm -rf backend/bin
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

clean-docker: ## 清理Docker镜像
	@echo "Cleaning Docker images..."
	docker rmi $(ECR_REPO_AGENT):$(IMAGE_TAG) $(ECR_REPO_AGENT):latest 2>/dev/null || true
	docker rmi $(ECR_REPO_BACKEND):$(IMAGE_TAG) $(ECR_REPO_BACKEND):latest 2>/dev/null || true
	docker rmi $(ECR_REPO_FRONTEND):$(IMAGE_TAG) $(ECR_REPO_FRONTEND):latest 2>/dev/null || true
