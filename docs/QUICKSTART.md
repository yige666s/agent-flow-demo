# 快速开始指南

## 前置要求

- Docker & Docker Compose
- Go 1.21+ (可选，本地开发)
- Python 3.11+ (可选，本地开发)
- OpenAI API Key

## 1️⃣ 配置环境变量

创建 `.env` 文件（已提供模板）：

```bash
# TODO: 设置你的 OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here
```

## 2️⃣ 启动服务

### 方式一：使用 Docker Compose（推荐）

```bash
# 启动所有服务
make docker-up

# 或直接使用 docker-compose
docker-compose up -d

# 查看日志
make logs
```

### 方式二：本地开发

#### 启动依赖服务

```bash
# 只启动数据库服务
docker-compose up -d postgres redis milvus etcd minio
```

#### 启动 AI Service

```bash
cd agent

# 安装依赖
pip install -r requirements.txt

# 生成 gRPC 代码
bash generate_proto.sh
# 或使用 make
make proto

# 设置环境变量
export OPENAI_API_KEY=sk-your-key

# 启动服务
python -m ai_service.server
```

#### 启动 Backend

```bash
cd backend

# 安装依赖
go mod download

# 运行
go run cmd/api/main.go
# 或使用 make
make run
```

## 3️⃣ 测试 API

### 健康检查

```bash
curl http://localhost:8080/health
```

### 模版推荐

```bash
curl -X POST http://localhost:8080/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我需要一张简约风格的产品发布会海报",
    "user_id": "user123",
    "top_k": 5
  }'
```

### 获取模版列表

```bash
curl http://localhost:8080/api/v1/templates?limit=10
```

## 4️⃣ 访问管理界面

- **MinIO 控制台**: http://localhost:9001
  - 用户名: `minioadmin`
  - 密码: `minioadmin`

## 5️⃣ 停止服务

```bash
make docker-down
# 或
docker-compose down
```

## 常见问题

### 1. gRPC 连接错误

确保 AI Service 已启动并运行在 50051 端口。

### 2. 数据库连接失败

检查 PostgreSQL 是否正常运行：
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### 3. Milvus 连接失败

Milvus 启动较慢，等待1-2分钟后重试。

### 4. OpenAI API 错误

- 检查 API Key 是否正确
- 检查网络连接
- 考虑使用本地 embedding 模型（修改配置）

## 开发工具

```bash
# 查看所有可用命令
make help

# 生成 protobuf 代码
make proto

# 编译后端
make build

# 运行测试
make test

# 清理构建产物
make clean
```

## 下一步

1. 查看 [README.md](README.md) 了解详细架构
2. 查看 [STRUCTURE.md](STRUCTURE.md) 了解项目结构
3. 阅读 [模版推荐技术方案.md](模版推荐技术方案.md) 了解技术细节
