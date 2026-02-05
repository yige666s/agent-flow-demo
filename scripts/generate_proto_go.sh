#!/bin/bash
# Generate protobuf code for Go

# Set project root
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_ROOT"

# Check for protoc
if ! command -v protoc &> /dev/null; then
    echo "Error: protoc could not be found. Please install protobuf-compiler."
    exit 1
fi

# Install Go plugins if not present
if ! command -v protoc-gen-go &> /dev/null; then
    echo "Installing protoc-gen-go..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
fi

if ! command -v protoc-gen-go-grpc &> /dev/null; then
    echo "Installing protoc-gen-go-grpc..."
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
fi

# Create output directory
mkdir -p backend/proto

echo "Generating Go code..."

# Generate code
# --go_out and --go-grpc_out are relative to the project root
# module=template-recommend ensures the generated files include the correct package path
protoc --proto_path=. \
       --go_out=backend \
       --go_opt=module=template-recommend \
       --go-grpc_out=backend \
       --go-grpc_opt=module=template-recommend \
       proto/agent.proto

echo "Go code generated successfully."
