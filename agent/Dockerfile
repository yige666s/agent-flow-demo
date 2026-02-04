# 使用官方Python镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖，添加更好的错误处理
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "First install failed, retrying with compatibility flags..." && \
    pip install --no-cache-dir --no-build-isolation -r requirements.txt)

# 复制应用代码
COPY . .

# 创建软链接以简化导入（core 模块在 /app/core 目录下）
RUN cd /app && \
    for module in core/models.py core/llm_client.py core/planner.py core/executor.py core/react_agent.py; do \
        [ -f "$module" ] && ln -sf "$module" "$(basename $module)" || true; \
    done

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/core

# 暴露端口
EXPOSE 8000

# 运行应用
CMD ["python", "app.py"]
