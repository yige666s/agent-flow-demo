"""
AgentFlow Python Agent Service
Flask API 实现 - 使用 LangGraph 状态机模式
"""

from flask import Flask, request, jsonify, Response
import os
import json
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

app = Flask(__name__)

# 全局实例
langgraph_agent = None


def init_app():
    """初始化应用"""
    global langgraph_agent
    
    print("Initializing AgentFlow in LANGGRAPH mode...")
    
    from core.langgraph_agent import LangGraphAgent
    from tools import register_all_tools
    from core.llm_client import init_llm_client, get_llm_client, load_config_from_file
    
    # 加载配置文件
    try:
        config = load_config_from_file("config.yaml")
        print(f"Loaded configuration from config.yaml")
        print(f"LLM Provider: {config.get('provider', 'not specified')}")
    except FileNotFoundError:
        print("config.yaml not found, using environment variables")
        config = None
    
    # 初始化 LLM 客户端
    if config:
        init_llm_client(config=config)
    else:
        init_llm_client()
    
    llm_provider = get_llm_client()
    print(f"LLM client initialized: {llm_provider}")
    
    # 注册所有工具
    register_all_tools()
    
    # 创建 LangGraph Agent
    langgraph_agent = LangGraphAgent()
    
    print(f"Agent service initialized in LANGGRAPH mode with {llm_provider}")


# ==================== API 路由 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    from tools.base import ToolRegistry
    from core.llm_client import get_llm_client
    
    llm_provider = get_llm_client()
    
    return jsonify({
        "status": "healthy",
        "version": "3.0.0",
        "mode": "langgraph",
        "llm_provider": llm_provider.provider_name,
        "llm_model": llm_provider.model,
        "tools_loaded": len(ToolRegistry.list_tools())
    })


@app.route('/agent/run', methods=['POST'])
def run_agent():
    """执行 Agent 任务"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        user_input = data.get('user_input')
        
        if not task_id or not user_input:
            return jsonify({
                "status": "error",
                "error": "task_id and user_input are required"
            }), 400
        
        result = langgraph_agent.run(task_id, user_input)
        
        return jsonify({
            "status": result.get("status", "completed"),
            "task_id": task_id,
            "plan": result.get("plan"),
            "result": result.get("result"),
            "step_results": result.get("step_results", []),
            "error": result.get("error"),
            "mode": "langgraph"
        })
    
    except Exception as e:
        return jsonify({
            "status": "failed",
            "task_id": data.get('task_id', 'unknown'),
            "error": str(e)
        }), 500


@app.route('/agent/stream', methods=['POST'])
def stream_agent():
    """流式执行任务"""
    data = request.get_json()
    task_id = data.get('task_id')
    user_input = data.get('user_input')
    
    if not task_id or not user_input:
        return jsonify({
            "status": "error",
            "error": "task_id and user_input are required"
        }), 400
    
    def generate():
        for event in langgraph_agent.stream(task_id, user_input):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    init_app()
    port = int(os.getenv('PORT', 8000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
