"""
AgentFlow Python Agent Service
Flask API 实现 - 支持多种 Agent 模式：
- legacy: Plan-and-Execute 模式（先规划后执行）
- react: ReAct 模式（Reason + Act 循环）
- langgraph: LangGraph 状态机模式
"""

from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

app = Flask(__name__)

# 全局实例
planner = None
executor = None
langgraph_agent = None
react_agent = None

# Agent 模式: "legacy" (Plan-Execute) / "react" (ReAct循环) / "langgraph" (LangGraph)
AGENT_MODE = os.getenv("AGENT_MODE", "legacy")


def init_legacy_mode():
    """初始化原有模式"""
    global planner, executor
    
    from core.models import Plan
    from core.planner import Planner
    from core.executor import Executor
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
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            init_llm_client(provider_type="claude", api_key=api_key)
        else:
            raise ValueError("No configuration found. Please create config.yaml or set ANTHROPIC_API_KEY")
    
    # 注册工具
    register_all_tools()
    
    # 创建 Planner 和 Executor
    planner = Planner()
    executor = Executor()
    
    llm_provider = get_llm_client()
    print(f"Agent service initialized in LEGACY mode with {llm_provider}")


def init_react_mode():
    """初始化 ReAct 模式"""
    global react_agent
    
    from core.react_agent import ReActAgent
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
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        provider = "claude" if os.getenv("ANTHROPIC_API_KEY") else "openai"
        if api_key:
            init_llm_client(provider_type=provider, api_key=api_key)
        else:
            raise ValueError("No configuration found. Please create config.yaml or set API keys")
    
    # 注册工具
    register_all_tools()
    
    # 创建 ReAct Agent
    max_iterations = int(os.getenv("REACT_MAX_ITERATIONS", "10"))
    react_agent = ReActAgent(max_iterations=max_iterations)
    
    llm_provider = get_llm_client()
    print(f"Agent service initialized in REACT mode with {llm_provider}")
    print(f"Max iterations: {max_iterations}")


def init_langgraph_mode():
    """初始化 LangGraph 模式"""
    global langgraph_agent
    
    from core.agent_frame.langgraph_agent import LangGraphAgent
    
    # 读取 LLM 配置
    llm_config = {
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "model": os.getenv("LLM_MODEL", "gpt-4"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
    }
    
    langgraph_agent = LangGraphAgent(llm_config=llm_config)
    print(f"Agent service initialized in LANGGRAPH mode")
    print(f"LLM Provider: {llm_config['provider']}, Model: {llm_config['model']}")


def init_app():
    """初始化应用"""
    global AGENT_MODE
    
    print(f"Initializing AgentFlow in {AGENT_MODE.upper()} mode...")
    
    if AGENT_MODE == "langgraph":
        init_langgraph_mode()
    elif AGENT_MODE == "react":
        init_react_mode()
    else:
        init_legacy_mode()


# ==================== API 路由 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    if AGENT_MODE == "langgraph":
        return jsonify({
            "status": "healthy",
            "version": "2.0.0",
            "mode": "langgraph",
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL", "gpt-4"),
        })
    elif AGENT_MODE == "react":
        from tools.base import ToolRegistry
        from core.llm_client import get_llm_client
        
        llm_provider = get_llm_client()
        
        return jsonify({
            "status": "healthy",
            "version": "2.1.0",
            "mode": "react",
            "llm_provider": llm_provider.provider_name,
            "llm_model": llm_provider.model,
            "tools_loaded": len(ToolRegistry.list_tools()),
            "max_iterations": react_agent.max_iterations if react_agent else 10
        })
    else:
        from tools.base import ToolRegistry
        from core.llm_client import get_llm_client
        
        llm_provider = get_llm_client()
        
        return jsonify({
            "status": "healthy",
            "version": "1.0.0",
            "mode": "legacy",
            "llm_provider": llm_provider.provider_name,
            "llm_model": llm_provider.model,
            "tools_loaded": len(ToolRegistry.list_tools())
        })


@app.route('/agent/plan', methods=['POST'])
def create_plan():
    """任务拆解"""
    if AGENT_MODE == "langgraph":
        # LangGraph 模式下，plan 和 execute 合并
        return jsonify({
            "status": "info",
            "message": "LangGraph mode uses /agent/run endpoint for combined planning and execution"
        })
    
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        user_input = data.get('user_input')
        
        if not task_id or not user_input:
            return jsonify({
                "status": "error",
                "error": "task_id and user_input are required"
            }), 400
        
        plan = planner.create_plan(task_id, user_input)
        
        return jsonify({
            "status": "success",
            "task_id": task_id,
            "plan": plan.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "task_id": data.get('task_id', 'unknown'),
            "error": str(e)
        }), 500


@app.route('/agent/execute', methods=['POST'])
def execute_plan():
    """任务执行"""
    if AGENT_MODE == "langgraph":
        return jsonify({
            "status": "info",
            "message": "LangGraph mode uses /agent/run endpoint for combined planning and execution"
        })
    
    try:
        from core.models import Plan
        
        data = request.get_json()
        task_id = data.get('task_id')
        plan_data = data.get('plan')
        context_data = data.get('context', {})
        
        if not task_id or not plan_data:
            return jsonify({
                "status": "error",
                "error": "task_id and plan are required"
            }), 400
        
        plan = Plan.from_dict(plan_data)
        
        result = executor.execute_plan(
            plan=plan,
            user_input="",
            initial_context=context_data.get('variables', {})
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "status": "failed",
            "task_id": data.get('task_id', 'unknown'),
            "error": str(e)
        }), 500


@app.route('/agent/run', methods=['POST'])
def run_agent():
    """
    统一执行入口，支持三种模式：
    - legacy: Plan-and-Execute 模式
    - react: ReAct 循环模式
    - langgraph: LangGraph 状态机模式
    """
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        user_input = data.get('user_input')
        
        if not task_id or not user_input:
            return jsonify({
                "status": "error",
                "error": "task_id and user_input are required"
            }), 400
        
        if AGENT_MODE == "langgraph":
            # LangGraph 模式
            result = langgraph_agent.run(task_id, user_input)
            
            return jsonify({
                "status": "completed" if result.get("success") else "failed",
                "task_id": task_id,
                "result": result.get("result"),
                "error": result.get("error"),
                "mode": "langgraph"
            })
        
        elif AGENT_MODE == "react":
            # ReAct 循环模式
            result = react_agent.run(
                task_id=task_id,
                user_input=user_input,
                initial_context=data.get('context', {})
            )
            
            return jsonify({
                "status": result.status,
                "task_id": task_id,
                "result": result.final_answer,
                "steps": [s.to_dict() for s in result.steps],
                "total_iterations": result.total_iterations,
                "error": result.error,
                "mode": "react"
            })
        
        else:
            # Legacy 模式：先规划再执行
            plan = planner.create_plan(task_id, user_input)
            result = executor.execute_plan(plan=plan, user_input=user_input)
            
            return jsonify({
                "status": result.get("status", "completed"),
                "task_id": task_id,
                "plan": plan.to_dict(),
                "result": result.get("result"),
                "error": result.get("error"),
                "mode": "legacy"
            })
    
    except Exception as e:
        return jsonify({
            "status": "failed",
            "task_id": data.get('task_id', 'unknown'),
            "error": str(e)
        }), 500


@app.route('/agent/stream', methods=['POST'])
def stream_agent():
    """
    流式执行任务（仅 LangGraph 模式支持）
    """
    if AGENT_MODE != "langgraph":
        return jsonify({
            "status": "error",
            "error": "Streaming is only supported in LangGraph mode"
        }), 400
    
    from flask import Response
    import json
    
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
