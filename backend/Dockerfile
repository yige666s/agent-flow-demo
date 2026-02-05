# Golang API服务 Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 安装依赖及 protoc 工具
RUN apk add --no-cache protobuf protobuf-dev
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.32.0 && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0

COPY backend/go.mod backend/go.sum ./
RUN go mod download

# 复制协议文件和源代码
COPY proto/ ./proto/
COPY backend/ .

# 生成 Go gRPC 代码
ENV PATH="$PATH:$(go env GOPATH)/bin"
RUN protoc --proto_path=. \
       --go_out=. \
       --go_opt=module=template-recommend \
       --go-grpc_out=. \
       --go-grpc_opt=module=template-recommend \
       proto/agent.proto

# 编译
RUN CGO_ENABLED=0 GOOS=linux go build -o /api-server ./cmd/api

# 运行镜像
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

COPY --from=builder /api-server .

EXPOSE 8080

CMD ["./api-server"]
