#!/bin/bash
# Generate protobuf code for Python (virtual environment aware)

# Set project root
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_ROOT" || exit 1

# Check for venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: virtual environment not activated."
    echo "Please activate your venv first, e.g.:"
    echo "  source venv/bin/activate"
    exit 1
fi

# Check for python3 in venv
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found."
    exit 1
fi

# Ensure output directory exists
mkdir -p agent/proto
touch agent/proto/__init__.py

echo "Generating Python code in virtual environment: $VIRTUAL_ENV"

# Check if grpcio-tools is installed in venv
if ! python3 -c "import grpc_tools.protoc" 2>/dev/null; then
    echo "grpcio-tools not found in virtual environment."
    echo "Installing grpcio-tools in venv..."
    if ! python3 -m pip install --upgrade pip; then
        echo "Failed to upgrade pip in venv."
        exit 1
    fi
    if ! python3 -m pip install grpcio-tools; then
        echo "Failed to install grpcio-tools in venv."
        exit 1
    fi
fi

# Generate code
# -I. sets the include path to project root, so proto/agent.proto creates agent/proto/agent_pb2.py
python3 -m grpc_tools.protoc \
    -I. \
    --python_out=agent \
    --grpc_python_out=agent \
    proto/agent.proto

if [ $? -eq 0 ]; then
    echo "Python code generated successfully in venv."
else
    echo "Error generating Python code."
    exit 1
fi
