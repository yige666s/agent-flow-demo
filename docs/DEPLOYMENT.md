# Kubernetes Secret 使用指南

## 📋 快速开始

### 1. 创建实际的 secrets.yaml 文件

```bash
# 复制示例文件
cp k8s/secrets.yaml.example k8s/secrets.yaml

# 编辑并填入真实的 API keys
vim k8s/secrets.yaml
```

### 2. 部署 Secret 到 Kubernetes

```bash
# 应用 Secret 配置
kubectl apply -f k8s/secrets.yaml

# 验证 Secret 已创建
kubectl get secrets agent-flow-secrets

# 查看 Secret 详情（不会显示真实值）
kubectl describe secret agent-flow-secrets
```

### 3. 部署应用

```bash
# Secret 必须在 deployment 之前创建
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/agent-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
```

## 🔐 Secret 文件结构

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-flow-secrets
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "sk-ant-your-real-key-here"
  OPENAI_API_KEY: "sk-your-real-key-here"
  ZHIPU_API_KEY: "your-real-key-here"
  QWEN_API_KEY: "sk-your-real-key-here"
```

## 🚀 使用 Makefile 部署

已在 Makefile 中集成了 Secret 部署命令：

```bash
# 部署所有资源（包括 secrets）
make k8s-deploy-all

# 单独部署 secrets
make k8s-deploy-secrets

# 更新 secrets
make k8s-update-secrets
```

## 🔄 更新 Secret

### 方法一：使用 kubectl apply

```bash
# 修改 k8s/secrets.yaml 后应用
kubectl apply -f k8s/secrets.yaml

# 重启 pod 以使新的 secret 生效
kubectl rollout restart deployment/agent-flow-agent
kubectl rollout restart deployment/agent-flow-backend
```

### 方法二：直接编辑 Secret

```bash
# 在线编辑 Secret
kubectl edit secret agent-flow-secrets

# 查看当前值（base64 编码）
kubectl get secret agent-flow-secrets -o yaml
```

### 方法三：从环境变量创建

```bash
# 从环境变量创建/更新 Secret
kubectl create secret generic agent-flow-secrets \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=ZHIPU_API_KEY="$ZHIPU_API_KEY" \
  --from-literal=QWEN_API_KEY="$QWEN_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 🔍 调试和验证

### 查看 Pod 中的环境变量

```bash
# 列出 pod
kubectl get pods

# 查看环境变量（不显示 Secret 值）
kubectl exec -it <pod-name> -- env | grep API_KEY

# 进入容器检查
kubectl exec -it <pod-name> -- /bin/sh
echo $ANTHROPIC_API_KEY
```

### 验证 Secret 是否正确挂载

```bash
# 查看 pod 详情
kubectl describe pod <pod-name>

# 查看日志确认应用是否正常读取
kubectl logs <pod-name>
```

## 🛡️ 安全最佳实践

### 1. 不要提交真实的 secrets.yaml

```bash
# 确保 secrets.yaml 在 .gitignore 中
echo "k8s/secrets.yaml" >> .gitignore

# 只提交 secrets.yaml.example
git add k8s/secrets.yaml.example
```

### 2. 使用 RBAC 限制访问

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["agent-flow-secrets"]
    verbs: ["get"]
```

### 3. 使用 AWS Secrets Manager（生产环境推荐）

安装 External Secrets Operator：

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets
```

创建 ExternalSecret：

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: agent-flow-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: agent-flow-secrets
  data:
    - secretKey: ANTHROPIC_API_KEY
      remoteRef:
        key: agent-flow/anthropic-api-key
    - secretKey: OPENAI_API_KEY
      remoteRef:
        key: agent-flow/openai-api-key
```

### 4. 加密 Secret at rest

```bash
# 启用 EKS 加密
aws eks update-cluster-config \
  --name ferocious-rock-goose \
  --encryption-config \
  '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:..."}}]'
```

## 📦 CI/CD 集成

### GitHub Actions 中使用 Secrets

在 `.github/workflows/deploy.yml` 中：

```yaml
- name: Create Kubernetes Secret
  run: |
    kubectl create secret generic agent-flow-secrets \
      --from-literal=ANTHROPIC_API_KEY="${{ secrets.ANTHROPIC_API_KEY }}" \
      --from-literal=OPENAI_API_KEY="${{ secrets.OPENAI_API_KEY }}" \
      --from-literal=ZHIPU_API_KEY="${{ secrets.ZHIPU_API_KEY }}" \
      --from-literal=QWEN_API_KEY="${{ secrets.QWEN_API_KEY }}" \
      --dry-run=client -o yaml | kubectl apply -f -
```

在 GitHub 仓库中设置 Secrets：
- Settings → Secrets and variables → Actions → New repository secret

## 🧪 本地测试

使用 kind 或 minikube 本地测试：

```bash
# 创建本地集群
kind create cluster

# 应用配置
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/

# 测试
kubectl port-forward svc/agent-flow-frontend 8080:80
```

## 🔧 故障排查

### Secret 不存在

```bash
Error: secrets "agent-flow-secrets" not found
```

解决方法：
```bash
kubectl apply -f k8s/secrets.yaml
```

### Pod 无法启动

```bash
# 查看详细错误
kubectl describe pod <pod-name>

# 查看日志
kubectl logs <pod-name>
```

### Secret 更新后未生效

```bash
# 重启部署
kubectl rollout restart deployment/agent-flow-agent
kubectl rollout restart deployment/agent-flow-backend
```

## 📝 相关文件

- [k8s/secrets.yaml.example](secrets.yaml.example) - Secret 模板文件
- [k8s/agent-deployment.yaml](agent-deployment.yaml) - Agent 部署配置
- [k8s/backend-deployment.yaml](backend-deployment.yaml) - Backend 部署配置
- [DEPLOYMENT.md](../DEPLOYMENT.md) - 完整部署文档
