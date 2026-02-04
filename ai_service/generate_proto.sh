#!/bin/bash

# Script to generate gRPC code from protobuf definitions

# TODO: Install grpcio-tools if not already installed
# pip install grpcio-tools

python -m grpc_tools.protoc \
    -I../proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ../proto/ai_service.proto

echo "gRPC code generated successfully"
