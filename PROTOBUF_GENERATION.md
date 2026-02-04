# 生成 protobuf 代码

## Golang

```bash
# 安装 protoc 和 Go 插件
# macOS
brew install protobuf
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# 生成代码
cd proto
protoc --go_out=../backend/proto --go_opt=paths=source_relative \
    --go-grpc_out=../backend/proto --go-grpc_opt=paths=source_relative \
    ai_service.proto
```

## Python

```bash
cd ai_service
bash generate_proto.sh
```

或手动执行:

```bash
python -m grpc_tools.protoc \
    -I../proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ../proto/ai_service.proto
```

## 注意事项

生成的代码需要在 `proto/__init__.py` 中导出或直接使用完整路径导入。
