# Template Recommendation System

基于 Golang + Python (LangGraph) 混合架构的模版推荐系统，使用 AI Agent 进行智能推荐。

## 技术栈

### Backend (Golang)
- **Web框架**: Gin
- **数据库**: PostgreSQL + GORM
- **向量数据库**: Milvus
- **缓存**: Redis
- **RPC**: gRPC

### AI Service (Python)
- **Agent框架**: LangGraph
- **LLM**: OpenAI GPT-4 / Claude
- **Embedding**: OpenAI / BGE (本地)
- **RPC**: gRPC

## 项目结构

```
.
├── backend/                 # Golang后端服务
│   ├── cmd/api/            # 主程序入口
│   ├── internal/
│   │   ├── config/         # 配置管理
│   │   ├── database/       # 数据库初始化
│   │   ├── models/         # 数据模型
│   │   ├── repository/     # 数据访问层
│   │   ├── service/        # 业务逻辑层
│   │   ├── handler/        # HTTP处理器
│   │   └── client/         # gRPC客户端
│   ├── config.yaml         # 配置文件
│   └── Dockerfile
│
├── ai_service/             # Python AI服务
│   ├── agent.py            # LangGraph Agent实现
│   ├── embedding.py        # Embedding服务
│   ├── server.py           # gRPC服务器
│   ├── config.py           # 配置管理
│   ├── proto/              # gRPC生成代码
│   ├── requirements.txt
│   └── Dockerfile
│
├── proto/                  # Protobuf定义
│   └── ai_service.proto
│
├── scripts/                # 脚本和初始化SQL
│   └── init_db.sql
│
└── docker-compose.yml      # Docker Compose配置
```

## 快速开始

### 前置要求

- Docker & Docker Compose
- Go 1.21+ (本地开发)
- Python 3.11+ (本地开发)
- OpenAI API Key

### 1. 配置环境变量

创建 `.env` 文件:

```bash
# TODO: 设置你的 OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here
```

### 2. 使用 Docker Compose 启动

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

服务端口:
- API Gateway: http://localhost:8080
- AI Service (gRPC): localhost:50051
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Milvus: localhost:19530
- MinIO: http://localhost:9001

### 3. 测试API

```bash
# 健康检查
curl http://localhost:8080/health

# 推荐模版
curl -X POST http://localhost:8080/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我需要一张简约风格的产品发布会海报",
    "user_id": "user123",
    "top_k": 5
  }'

# 获取模版列表
curl http://localhost:8080/api/v1/templates?limit=10
```

## 本地开发

### Backend (Golang)

```bash
cd backend

# 安装依赖
go mod download

# TODO: 配置 config.yaml

# 运行
go run cmd/api/main.go
```

### AI Service (Python)

```bash
cd ai_service

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# TODO: 设置环境变量
export OPENAI_API_KEY=sk-your-key

# 生成 gRPC 代码
bash generate_proto.sh

# 运行服务
python -m ai_service.server
```

## 核心功能

### 1. 智能推荐流程

```
用户查询 → Golang API
    ↓
Python AI Agent (LangGraph)
    ↓
意图理解 + 特征提取
    ↓
并行检索:
- Milvus 向量检索
- PostgreSQL 标签过滤
- PostgreSQL 关键词搜索
    ↓
结果融合 (RRF算法)
    ↓
生成推荐理由
    ↓
返回结果
```

### 2. 核心组件

- **LangGraph Agent**: 使用 LangGraph 实现的智能 Agent，负责意图理解和特征提取
- **Milvus 向量检索**: 基于语义相似度的向量检索
- **多路召回融合**: RRF 算法融合多个检索结果
- **智能缓存**: Redis 缓存热点查询结果

## 配置说明

### TODO 列表

以下配置需要根据实际环境调整:

1. **OpenAI API Key** (ai_service/config.py, .env)
   - 设置你的 OpenAI API Key
   - 或配置使用本地模型

2. **数据库连接** (backend/config.yaml)
   - PostgreSQL 连接参数
   - Redis 连接参数
   - Milvus 连接参数

3. **Embedding 模型** (ai_service/config.py)
   - 选择 OpenAI API 或本地 BGE 模型
   - 配置 embedding 维度

4. **LLM 模型** (ai_service/agent.py)
   - 选择 GPT-4 或 Claude
   - 配置模型参数

5. **生产环境安全**
   - 修改默认密码
   - 启用 SSL/TLS
   - 配置防火墙规则

## API 文档

### POST /api/v1/recommend

推荐模版

**请求体:**
```json
{
  "query": "用户查询",
  "user_id": "用户ID (可选)",
  "top_k": 5
}
```

**响应:**
```json
{
  "status": "success",
  "query": "用户查询",
  "recommendations": [
    {
      "template_id": "tmpl_001",
      "name": "模版名称",
      "description": "模版描述",
      "tags": ["标签1", "标签2"],
      "score": 0.95
    }
  ],
  "explanation": "推荐理由说明",
  "response_time_ms": 1250
}
```

### GET /api/v1/templates

获取模版列表

**查询参数:**
- `limit`: 返回数量 (默认: 20)
- `offset`: 偏移量 (默认: 0)

## 性能优化

1. **Redis 缓存**: 缓存热点查询，命中率 50%+
2. **并行检索**: 使用 errgroup 并行执行多路召回
3. **连接池**: 数据库和 Redis 连接池优化
4. **异步日志**: 异步记录用户交互数据

## 监控和日志

- 使用结构化日志 (zap)
- Prometheus 指标暴露 (TODO)
- 分布式追踪 (TODO)

## 扩展建议

1. **添加更多检索策略**: 协同过滤、内容过滤等
2. **个性化推荐**: 基于用户历史行为
3. **多轮对话**: 支持对话式精确需求
4. **A/B 测试**: 推荐策略 A/B 测试框架

## License

MIT
