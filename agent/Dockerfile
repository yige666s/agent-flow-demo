# Python AI服务 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY agent/ ./agent/
COPY proto/ ./proto/

# 生成gRPC代码
RUN mkdir -p agent/proto && python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./agent/proto \
    --grpc_python_out=./agent/proto \
    ./proto/agent.proto

ENV PYTHONPATH=/app

EXPOSE 50051

CMD ["python", "-m", "agent.server"]
