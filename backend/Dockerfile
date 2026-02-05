# Golang API服务 Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 安装依赖
COPY backend/go.mod backend/go.sum ./
RUN go mod download

# 复制源代码
COPY backend/ .

# 编译
RUN CGO_ENABLED=0 GOOS=linux go build -o /api-server ./cmd/api

# 运行镜像
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

COPY --from=builder /api-server .

# TODO: Copy config file if needed
# COPY config.yaml .

EXPOSE 8080

CMD ["./api-server"]
