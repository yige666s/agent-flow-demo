# AWS EKS 部署指南

本项目包含完整的 AWS EKS 部署配置，参考 aws_cicd_workflow 项目配置。

## 📁 项目结构

```
agent-flow-demo/
├── .github/workflows/
│   └── deploy.yml          # GitHub Actions CI/CD 配置
├── agent/
│   └── Dockerfile          # Python Agent 服务镜像
├── backend/
│   └── Dockerfile          # Go Backend 服务镜像
├── frontend/
│   └── Dockerfile          # Frontend 服务镜像
├── k8s/                    # Kubernetes 配置文件
│   ├── agent-deployment.yaml
│   ├── agent-service.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   └── frontend-service.yaml
├── Makefile                # 便捷部署命令
└── .dockerignore           # Docker 构建忽略文件
```

## 🚀 快速开始

### 前置要求

1. **AWS CLI** 已配置并有权限访问 EKS 集群
2. **Docker** 已安装
3. **kubectl** 已安装
4. **make** 已安装（macOS 自带）

### 环境配置

在 [Makefile](Makefile) 中修改以下变量以匹配你的 AWS 环境：

```makefile
AWS_REGION := us-east-1
ECR_REGISTRY := 483739914637.dkr.ecr.us-east-1.amazonaws.com
EKS_CLUSTER := ferocious-rock-goose
```

## 📋 使用说明

### 1. 查看所有可用命令

```bash
make help
```

### 2. 本地开发

```bash
# 安装依赖
make install-agent
make install-backend

# 运行服务
make run-agent      # 启动 Agent 服务 (端口 8000)
make run-backend    # 启动 Backend 服务 (端口 8080)
make run-frontend   # 启动 Frontend 服务 (端口 8000)
```

### 3. 本地 Docker 测试

```bash
# 构建所有镜像
make docker-build-all

# 运行容器
make docker-run-agent
make docker-run-backend
make docker-run-frontend

# 停止所有容器
make docker-stop-all
```

### 4. 部署到 AWS EKS

#### 方式一：使用 Makefile 一键部署

```bash
# 创建 ECR 仓库（首次部署时）
make ecr-create-repos

# 一键构建、推送、部署
make deploy-to-aws
```

这个命令会：
- 构建所有 Docker 镜像
- 推送镜像到 ECR
- 部署到 EKS 集群
- 显示 LoadBalancer URL

#### 方式二：分步部署

```bash
# 1. 构建镜像
make docker-build-all

# 2. 推送到 ECR
make docker-push-all

# 3. 部署到 K8s
make k8s-deploy-all

# 4. 查看状态
make k8s-status
```

### 5. GitHub Actions 自动部署

当代码推送到 `main` 分支时，GitHub Actions 会自动：

1. 构建三个服务的 Docker 镜像
2. 推送到 AWS ECR
3. 更新 EKS 集群部署

**配置步骤：**

1. 在 GitHub 仓库设置中配置 AWS 凭证（使用 OIDC）
2. 确保 GitHub Actions 有权限访问你的 AWS 账户
3. 修改 [.github/workflows/deploy.yml](.github/workflows/deploy.yml) 中的 IAM role ARN

### 6. 查看日志

```bash
# 查看各服务日志
make k8s-logs-agent
make k8s-logs-backend
make k8s-logs-frontend
```

### 7. 清理资源

```bash
# 删除 K8s 资源
make k8s-delete-all

# 清理本地 Docker 镜像
make clean-docker
```

## 🏗️ 架构说明

### 服务架构

```
Internet
    ↓
[LoadBalancer] → [Frontend (Nginx:80)]
                      ↓
                 [Backend (Go:8080)]
                      ↓
                 [Agent (Python:8000)]
```

### 服务说明

- **Frontend**: Nginx 提供静态文件，反向代理 API 请求到 Backend
- **Backend**: Go 服务，编排任务并调用 Agent 服务
- **Agent**: Python 服务，执行 AI Agent 任务

### Kubernetes 资源

每个服务包含：
- **Deployment**: 2 副本，滚动更新策略
- **Service**: 
  - Frontend: LoadBalancer 类型（对外暴露）
  - Backend/Agent: ClusterIP 类型（集群内部访问）

### 健康检查

所有服务都配置了 liveness 和 readiness probes：
- Liveness: 检查服务是否存活
- Readiness: 检查服务是否准备好接收流量

## 🔧 自定义配置

### 修改副本数

编辑 `k8s/*-deployment.yaml` 文件中的 `replicas` 字段：

```yaml
spec:
  replicas: 3  # 修改为所需副本数
```

### 修改资源限制

在 deployment 文件中调整 `resources` 配置：

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
```

### 添加环境变量

在 deployment 文件中的 `env` 部分添加：

```yaml
env:
  - name: CUSTOM_VAR
    value: "custom_value"
```

## 📊 监控和故障排查

### 查看 Pod 状态

```bash
kubectl get pods
kubectl describe pod <pod-name>
```

### 查看服务状态

```bash
kubectl get services
kubectl describe service agent-flow-frontend
```

### 获取 LoadBalancer URL

```bash
kubectl get service agent-flow-frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### 进入容器调试

```bash
kubectl exec -it <pod-name> -- /bin/sh
```

## 🔐 安全最佳实践

1. **使用 IAM Roles**: 通过 IRSA (IAM Roles for Service Accounts) 授予 Pod 权限
2. **镜像扫描**: 在 ECR 中启用镜像扫描
3. **网络策略**: 使用 Network Policies 限制 Pod 间通信
4. **Secret 管理**: 使用 AWS Secrets Manager 或 K8s Secrets
5. **最小权限原则**: 确保 GitHub Actions role 只有必要的权限

## 💡 常用命令速查

```bash
# 本地开发
make run-agent              # 运行 Agent 服务
make run-backend            # 运行 Backend 服务

# Docker 操作
make docker-build-all       # 构建所有镜像
make docker-push-all        # 推送所有镜像到 ECR

# Kubernetes 操作
make k8s-deploy-all         # 部署所有服务
make k8s-status             # 查看部署状态
make k8s-logs-agent         # 查看 Agent 日志

# 完整部署
make deploy-to-aws          # 构建、推送、部署一键完成
```

## 📚 参考资源

- [AWS EKS 文档](https://docs.aws.amazon.com/eks/)
- [Kubernetes 文档](https://kubernetes.io/docs/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [参考项目: aws_cicd_workflow](../aws_cicd_workflow/)

## 🆘 常见问题

### Q: ImagePullBackOff 错误
A: 检查 ECR 权限和镜像标签是否正确

### Q: LoadBalancer 一直处于 Pending 状态
A: 检查 AWS Load Balancer Controller 是否正确安装

### Q: Pod 无法启动
A: 使用 `kubectl logs <pod-name>` 查看日志，检查应用配置

---

**注意**: 首次部署前，请确保：
1. AWS EKS 集群已创建并运行
2. ECR 仓库已创建（或运行 `make ecr-create-repos`）
3. kubectl 已正确配置连接到集群
4. GitHub Actions 的 IAM role 已配置
