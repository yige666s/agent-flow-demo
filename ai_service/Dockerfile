# Python AI服务 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY ai_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY ai_service/ ./ai_service/
COPY proto/ ./proto/

# 生成gRPC代码
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./ai_service/proto \
    --grpc_python_out=./ai_service/proto \
    ./proto/ai_service.proto

# TODO: Set environment variables
ENV PYTHONPATH=/app
ENV OPENAI_API_KEY=""

EXPOSE 50051

CMD ["python", "-m", "ai_service.server"]
