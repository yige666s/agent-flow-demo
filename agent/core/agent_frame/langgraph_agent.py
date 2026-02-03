"""
LangGraph Agent 实现
使用 LangGraph 构建有状态的 AI Agent 工作流
"""

import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
from operator import add

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

import requests
from bs4 import BeautifulSoup


# ==================== State 定义 ====================

class AgentState(TypedDict):
    """Agent 状态定义"""
    messages: Annotated[Sequence[BaseMessage], add]  # 消息历史
    task_id: str  # 任务 ID
    user_input: str  # 用户输入
    plan: Optional[Dict[str, Any]]  # 执行计划
    current_step: int  # 当前步骤
    step_results: Dict[int, Any]  # 步骤结果
    final_result: Optional[Any]  # 最终结果
    error: Optional[str]  # 错误信息


# ==================== 工具定义 ====================

@tool
def http_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, 
                 body: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
    """
    发起 HTTP 请求，支持 GET、POST、PUT、DELETE 等方法。
    返回包含 status_code、headers、body（文本）和 json（如果响应是 JSON 格式）的结果。
    
    Args:
        url: 请求 URL（必须完整，包含查询参数）
        method: HTTP 方法 (GET/POST/PUT/DELETE)
        headers: 请求头
        body: 请求体
        timeout: 超时时间（秒）
    """
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers or {},
            data=body,
            timeout=timeout
        )
        
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "success": 200 <= response.status_code < 300
        }
        
        # 尝试解析 JSON
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type or response.text.strip().startswith(('{', '[')):
            try:
                json_data = response.json()
                result["json"] = json_data
                # 智能展开 JSON 字段
                if isinstance(json_data, dict):
                    for k, v in json_data.items():
                        if k not in result:
                            result[k] = v
            except ValueError:
                pass
        
        return result
    except requests.RequestException as e:
        return {"status_code": 0, "error": str(e), "success": False}


@tool
def file_ops(operation: str, path: str, content: Optional[str] = None, 
             encoding: str = "utf-8") -> Dict[str, Any]:
    """
    文件读写操作，支持读取和写入文本、JSON 文件。
    写入操作会自动保存到 data/user 目录。
    
    Args:
        operation: 操作类型 (read/write/append)
        path: 文件名（会自动保存到 data/user 目录）
        content: 要写入的内容（write/append 操作必需）
        encoding: 文件编码，默认 utf-8
    """
    user_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "user")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # 获取完整路径
    filename = os.path.basename(path)
    full_path = os.path.join(user_data_dir, filename)
    
    try:
        if operation == "read":
            # 读取时先尝试 user 目录
            if os.path.exists(full_path):
                read_path = full_path
            else:
                read_path = path
            
            with open(read_path, 'r', encoding=encoding) as f:
                file_content = f.read()
            
            result = {"success": True, "content": file_content, "size": len(file_content)}
            try:
                result["json"] = json.loads(file_content)
            except json.JSONDecodeError:
                pass
            return result
        
        elif operation == "write":
            if content is None:
                raise ValueError("Content is required for write operation")
            
            # 处理非字符串内容
            if isinstance(content, (dict, list)):
                content_str = json.dumps(content, ensure_ascii=False, indent=2)
            else:
                content_str = str(content)
            
            with open(full_path, 'w', encoding=encoding) as f:
                f.write(content_str)
            
            return {"success": True, "path": full_path, "size": len(content_str)}
        
        elif operation == "append":
            if content is None:
                raise ValueError("Content is required for append operation")
            
            content_str = str(content) if not isinstance(content, str) else content
            
            with open(full_path, 'a', encoding=encoding) as f:
                f.write(content_str)
            
            return {"success": True, "path": full_path, "appended_size": len(content_str)}
        
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def web_scraper(html: str, extract: List[str]) -> Dict[str, Any]:
    """
    从 HTML 中提取指定内容（标题、链接、文本、表格等）。
    
    Args:
        html: HTML 字符串
        extract: 要提取的内容类型列表: title, links, text, headings, images, tables
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        for item in extract:
            if item == "title":
                title_tag = soup.find('title')
                result["title"] = title_tag.string if title_tag else None
            
            elif item == "links":
                links = []
                for a_tag in soup.find_all('a', href=True):
                    links.append({
                        "text": a_tag.get_text(strip=True),
                        "href": a_tag['href']
                    })
                result["links"] = links
            
            elif item == "text":
                result["text"] = soup.get_text(strip=True)
            
            elif item == "headings":
                headings = []
                for i in range(1, 7):
                    for h_tag in soup.find_all(f'h{i}'):
                        headings.append({"level": i, "text": h_tag.get_text(strip=True)})
                result["headings"] = headings
            
            elif item == "images":
                images = []
                for img_tag in soup.find_all('img', src=True):
                    images.append({"src": img_tag['src'], "alt": img_tag.get('alt', '')})
                result["images"] = images
            
            elif item == "tables":
                tables = []
                for table in soup.find_all('table'):
                    table_data = []
                    for row in table.find_all('tr'):
                        cells = row.find_all(['td', 'th'])
                        row_data = [cell.get_text(strip=True) for cell in cells]
                        if row_data:
                            table_data.append(row_data)
                    if table_data:
                        tables.append(table_data)
                result["tables"] = tables
        
        return {"success": True, "data": result}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def python_exec(code: str, input_data: Optional[Any] = None) -> Dict[str, Any]:
    """
    执行 Python 代码片段进行数据处理和转换。
    代码中可以访问 'input_data' 变量，需要将结果赋值给 'output' 变量。
    
    Args:
        code: 要执行的 Python 代码
        input_data: 传入代码的输入数据
    """
    try:
        import re as re_module
        
        allowed_globals = {
            '__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float,
                'bool': bool, 'list': list, 'dict': dict, 'tuple': tuple,
                'set': set, 'range': range, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter, 'sorted': sorted,
                'max': max, 'min': min, 'sum': sum, 'abs': abs, 'round': round,
                'print': print, 'isinstance': isinstance, 'type': type,
            },
            'json': json,
            're': re_module,
        }
        
        local_vars = {'input_data': input_data, 'output': None}
        exec(code, allowed_globals, local_vars)
        
        return {"success": True, "output": local_vars.get('output')}
    
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


# 工具列表
TOOLS = [http_request, file_ops, web_scraper, python_exec]


# ==================== LLM 初始化 ====================

def get_llm(provider: str = "openai", **kwargs):
    """根据配置获取 LLM 实例"""
    if provider == "openai":
        return ChatOpenAI(
            model=kwargs.get("model", "gpt-4"),
            temperature=kwargs.get("temperature", 0.7),
            api_key=kwargs.get("api_key", os.getenv("OPENAI_API_KEY")),
        )
    elif provider == "anthropic" or provider == "claude":
        return ChatAnthropic(
            model=kwargs.get("model", "claude-sonnet-4-20250514"),
            temperature=kwargs.get("temperature", 0.7),
            api_key=kwargs.get("api_key", os.getenv("ANTHROPIC_API_KEY")),
        )
    else:
        # 默认使用 OpenAI
        return ChatOpenAI(
            model=kwargs.get("model", "gpt-4"),
            temperature=kwargs.get("temperature", 0.7),
        )


# ==================== 图节点定义 ====================

def create_agent_graph(llm_config: Dict[str, Any] = None):
    """
    创建 LangGraph Agent 图
    
    节点结构:
    START -> agent -> should_continue -> tools -> agent -> ... -> END
    """
    
    # 初始化 LLM
    config = llm_config or {}
    llm = get_llm(
        provider=config.get("provider", "openai"),
        model=config.get("model"),
        temperature=config.get("temperature", 0.7),
        api_key=config.get("api_key"),
    )
    
    # 绑定工具到 LLM
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个智能任务执行助手。你需要根据用户的任务，使用可用的工具来完成任务。

可用工具：
1. http_request: 发起 HTTP 请求获取网页或 API 数据
2. file_ops: 读写文件
3. web_scraper: 从 HTML 中提取结构化数据
4. python_exec: 执行 Python 代码进行数据处理

执行原则：
1. 分析任务，确定需要的步骤
2. 按顺序调用工具执行每个步骤
3. 处理工具返回的结果
4. 如果任务完成，返回最终结果
5. URL 必须完整，包含所有查询参数

注意：
- 每次只调用一个工具
- 仔细处理上一步的输出作为下一步的输入
- 如果遇到错误，尝试修正或报告错误原因
"""
    
    def agent_node(state: AgentState) -> Dict[str, Any]:
        """Agent 节点：调用 LLM 决定下一步行动"""
        messages = state.get("messages", [])
        
        # 如果是第一次调用，添加系统消息和用户输入
        if not messages:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=state["user_input"])
            ]
        
        # 调用 LLM
        response = llm_with_tools.invoke(messages)
        
        return {"messages": [response]}
    
    def should_continue(state: AgentState) -> str:
        """决定是否继续执行"""
        messages = state.get("messages", [])
        if not messages:
            return "end"
        
        last_message = messages[-1]
        
        # 如果有工具调用，继续执行工具
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # 否则结束
        return "end"
    
    def extract_result(state: AgentState) -> Dict[str, Any]:
        """提取最终结果"""
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                return {"final_result": last_message.content}
        return {"final_result": None}
    
    # 创建工具节点
    tool_node = ToolNode(TOOLS)
    
    # 构建图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("extract", extract_result)
    
    # 设置入口
    workflow.set_entry_point("agent")
    
    # 添加边
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": "extract"
        }
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("extract", END)
    
    # 编译图
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


# ==================== Agent 类封装 ====================

class LangGraphAgent:
    """LangGraph Agent 封装类"""
    
    def __init__(self, llm_config: Dict[str, Any] = None):
        """
        初始化 Agent
        
        Args:
            llm_config: LLM 配置
                - provider: "openai" | "anthropic" | "claude"
                - model: 模型名称
                - temperature: 温度
                - api_key: API Key
        """
        self.graph = create_agent_graph(llm_config)
        self.llm_config = llm_config or {}
    
    def run(self, task_id: str, user_input: str) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task_id: 任务 ID
            user_input: 用户输入
        
        Returns:
            执行结果
        """
        initial_state = {
            "messages": [],
            "task_id": task_id,
            "user_input": user_input,
            "plan": None,
            "current_step": 0,
            "step_results": {},
            "final_result": None,
            "error": None,
        }
        
        config = {"configurable": {"thread_id": task_id}}
        
        try:
            # 执行图
            result = self.graph.invoke(initial_state, config)
            
            return {
                "success": True,
                "task_id": task_id,
                "result": result.get("final_result"),
                "messages_count": len(result.get("messages", [])),
            }
        
        except Exception as e:
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
            }
    
    async def arun(self, task_id: str, user_input: str) -> Dict[str, Any]:
        """异步执行任务"""
        initial_state = {
            "messages": [],
            "task_id": task_id,
            "user_input": user_input,
            "plan": None,
            "current_step": 0,
            "step_results": {},
            "final_result": None,
            "error": None,
        }
        
        config = {"configurable": {"thread_id": task_id}}
        
        try:
            result = await self.graph.ainvoke(initial_state, config)
            
            return {
                "success": True,
                "task_id": task_id,
                "result": result.get("final_result"),
                "messages_count": len(result.get("messages", [])),
            }
        
        except Exception as e:
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
            }
    
    def stream(self, task_id: str, user_input: str):
        """
        流式执行任务，返回每一步的状态
        
        Yields:
            每一步的状态更新
        """
        initial_state = {
            "messages": [],
            "task_id": task_id,
            "user_input": user_input,
            "plan": None,
            "current_step": 0,
            "step_results": {},
            "final_result": None,
            "error": None,
        }
        
        config = {"configurable": {"thread_id": task_id}}
        
        for event in self.graph.stream(initial_state, config):
            yield event


# ==================== 测试代码 ====================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # 创建 Agent
    agent = LangGraphAgent(llm_config={
        "provider": "openai",
        "model": "gpt-4",
    })
    
    # 测试任务
    result = agent.run(
        task_id="test-001",
        user_input="访问 https://api.github.com/users/torvalds 获取用户信息，提取 login 和 name，保存到 linus.json"
    )
    
    print("执行结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
