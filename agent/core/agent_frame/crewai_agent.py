"""
CrewAI Agent Implementation for AgentFlow

CrewAI 是一个多 Agent 协作框架，核心概念：
- Agent: 具有特定角色和目标的智能体
- Task: 分配给 Agent 的具体任务
- Crew: Agent 团队，协调多个 Agent 完成复杂任务
- Tool: Agent 可使用的工具

与 AutoGen 的区别：
- CrewAI 更强调角色扮演和团队协作
- 使用"船员"隐喻，每个 Agent 有明确的角色定位
- 支持顺序执行和层级执行模式
"""

import os
import json
import requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================================
# CrewAI 核心组件
# ============================================================

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("Warning: crewai not installed. Run: pip install crewai")


# ============================================================
# 自定义工具定义 (使用 Pydantic 模型)
# ============================================================

if CREWAI_AVAILABLE:
    
    # ----- HTTP 请求工具 -----
    class HttpRequestInput(BaseModel):
        """HTTP 请求工具的输入参数"""
        url: str = Field(description="请求的完整 URL")
        method: str = Field(default="GET", description="HTTP 方法: GET, POST, PUT, DELETE")
        headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
        body: Optional[Dict[str, Any]] = Field(default=None, description="请求体")

    class HttpRequestTool(BaseTool):
        name: str = "http_request"
        description: str = "发送 HTTP 请求获取数据。支持 GET/POST/PUT/DELETE 方法。"
        args_schema: type[BaseModel] = HttpRequestInput

        def _run(self, url: str, method: str = "GET", 
                 headers: Optional[Dict] = None, body: Optional[Dict] = None) -> str:
            """执行 HTTP 请求"""
            try:
                method = method.upper()
                req_headers = headers or {}
                
                if method == "GET":
                    response = requests.get(url, headers=req_headers, timeout=30)
                elif method == "POST":
                    response = requests.post(url, headers=req_headers, json=body, timeout=30)
                elif method == "PUT":
                    response = requests.put(url, headers=req_headers, json=body, timeout=30)
                elif method == "DELETE":
                    response = requests.delete(url, headers=req_headers, timeout=30)
                else:
                    return f"不支持的 HTTP 方法: {method}"
                
                # 尝试解析 JSON
                try:
                    data = response.json()
                    return json.dumps(data, ensure_ascii=False, indent=2)
                except:
                    # 返回文本内容（截断）
                    content = response.text[:5000]
                    return content
                    
            except Exception as e:
                return f"HTTP 请求失败: {str(e)}"


    # ----- 文件操作工具 -----
    class FileOpsInput(BaseModel):
        """文件操作工具的输入参数"""
        action: str = Field(description="操作类型: read 或 write")
        filename: str = Field(description="文件名")
        content: Optional[str] = Field(default=None, description="写入的内容（write 时必需）")

    class FileOpsTool(BaseTool):
        name: str = "file_ops"
        description: str = "读写本地文件。action='read' 读取文件，action='write' 写入文件。"
        args_schema: type[BaseModel] = FileOpsInput

        def _run(self, action: str, filename: str, content: Optional[str] = None) -> str:
            """执行文件操作"""
            # 使用 data/user 目录
            base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "user")
            os.makedirs(base_dir, exist_ok=True)
            filepath = os.path.join(base_dir, filename)
            
            try:
                if action == "read":
                    with open(filepath, "r", encoding="utf-8") as f:
                        return f.read()
                elif action == "write":
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content or "")
                    return f"文件已保存: {filepath}"
                else:
                    return f"不支持的操作: {action}"
            except Exception as e:
                return f"文件操作失败: {str(e)}"


    # ----- 网页抓取工具 -----
    class WebScraperInput(BaseModel):
        """网页抓取工具的输入参数"""
        url: str = Field(description="要抓取的网页 URL")
        selector: Optional[str] = Field(default=None, description="CSS 选择器")

    class WebScraperTool(BaseTool):
        name: str = "web_scraper"
        description: str = "抓取网页内容，可选 CSS 选择器提取特定元素。"
        args_schema: type[BaseModel] = WebScraperInput

        def _run(self, url: str, selector: Optional[str] = None) -> str:
            """抓取网页"""
            try:
                from bs4 import BeautifulSoup
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.get(url, headers=headers, timeout=30)
                soup = BeautifulSoup(response.text, "html.parser")
                
                if selector:
                    elements = soup.select(selector)
                    results = [elem.get_text(strip=True) for elem in elements[:50]]
                    return json.dumps(results, ensure_ascii=False, indent=2)
                else:
                    # 返回纯文本
                    text = soup.get_text(separator="\n", strip=True)
                    return text[:5000]
                    
            except Exception as e:
                return f"网页抓取失败: {str(e)}"


    # ----- Python 代码执行工具 -----
    class PythonExecInput(BaseModel):
        """Python 代码执行工具的输入参数"""
        code: str = Field(description="要执行的 Python 代码")

    class PythonExecTool(BaseTool):
        name: str = "python_exec"
        description: str = "执行 Python 代码并返回结果。可用于数据处理和计算。"
        args_schema: type[BaseModel] = PythonExecInput

        def _run(self, code: str) -> str:
            """执行 Python 代码"""
            try:
                # 创建安全的执行环境
                local_vars = {}
                exec(code, {"__builtins__": __builtins__}, local_vars)
                
                # 返回 result 变量或最后的输出
                if "result" in local_vars:
                    result = local_vars["result"]
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, ensure_ascii=False, indent=2)
                    return str(result)
                return "代码执行完成（无返回值）"
                
            except Exception as e:
                return f"代码执行错误: {str(e)}"


# ============================================================
# CrewAI Agent 定义
# ============================================================

def create_agents(llm_config: Dict[str, Any] = None) -> List["Agent"]:
    """
    创建 Crew 成员（Agent 团队）
    
    CrewAI 的角色设计理念：
    - 每个 Agent 有明确的角色、目标和背景故事
    - 角色定位影响 Agent 的行为和决策
    - 团队成员各司其职，协作完成任务
    """
    if not CREWAI_AVAILABLE:
        raise ImportError("crewai not installed")
    
    # 创建工具实例
    http_tool = HttpRequestTool()
    file_tool = FileOpsTool()
    scraper_tool = WebScraperTool()
    python_tool = PythonExecTool()
    
    # ----- 研究员 Agent -----
    researcher = Agent(
        role="数据研究员",
        goal="收集和分析来自网络的数据和信息",
        backstory="""你是一名资深数据研究员，擅长从各种网络来源收集信息。
        你精通 HTTP 请求和网页抓取技术，能够高效获取所需数据。
        你注重数据的准确性和完整性。""",
        tools=[http_tool, scraper_tool],
        verbose=True,
        allow_delegation=False,  # 不允许委派任务给其他 Agent
    )
    
    # ----- 数据分析师 Agent -----
    analyst = Agent(
        role="数据分析师",
        goal="处理和分析数据，提取有价值的洞察",
        backstory="""你是一名专业的数据分析师，擅长使用 Python 处理数据。
        你能够对原始数据进行清洗、转换和分析。
        你的分析结果总是清晰、准确且可操作的。""",
        tools=[python_tool],
        verbose=True,
        allow_delegation=False,
    )
    
    # ----- 报告撰写员 Agent -----
    writer = Agent(
        role="报告撰写员",
        goal="将分析结果整理成清晰的报告并保存",
        backstory="""你是一名技术写作专家，擅长将复杂的技术内容转化为易懂的文档。
        你注重文档的结构化和可读性。
        你熟练使用文件系统保存工作成果。""",
        tools=[file_tool],
        verbose=True,
        allow_delegation=False,
    )
    
    return [researcher, analyst, writer]


def create_tasks(agents: List["Agent"], user_request: str) -> List["Task"]:
    """
    创建任务列表
    
    CrewAI 的任务设计：
    - 每个任务有明确的描述和期望输出
    - 任务分配给特定的 Agent
    - 任务可以有依赖关系（context）
    """
    if not CREWAI_AVAILABLE:
        raise ImportError("crewai not installed")
    
    researcher, analyst, writer = agents
    
    # ----- 任务 1: 数据收集 -----
    research_task = Task(
        description=f"""
        根据以下用户请求收集数据:
        
        {user_request}
        
        使用 http_request 或 web_scraper 工具获取所需数据。
        确保收集到完整、准确的原始数据。
        """,
        expected_output="收集到的原始数据，格式为 JSON 或结构化文本",
        agent=researcher,
    )
    
    # ----- 任务 2: 数据分析 -----
    analysis_task = Task(
        description=f"""
        分析研究员收集到的数据:
        
        原始请求: {user_request}
        
        使用 python_exec 工具对数据进行:
        1. 数据清洗和格式化
        2. 按照用户需求筛选和排序
        3. 提取关键信息
        """,
        expected_output="处理后的数据分析结果，格式清晰",
        agent=analyst,
        context=[research_task],  # 依赖研究任务的输出
    )
    
    # ----- 任务 3: 报告生成 -----
    report_task = Task(
        description=f"""
        将分析结果整理成报告:
        
        原始请求: {user_request}
        
        使用 file_ops 工具:
        1. 将结果格式化为可读的报告
        2. 保存到适当的文件（如 report.md 或 result.json）
        3. 返回保存结果的确认信息
        """,
        expected_output="报告文件的保存确认和内容摘要",
        agent=writer,
        context=[analysis_task],  # 依赖分析任务的输出
    )
    
    return [research_task, analysis_task, report_task]


# ============================================================
# CrewAI 执行引擎
# ============================================================

def run_crew(user_request: str, 
             process: str = "sequential",
             verbose: bool = True) -> str:
    """
    创建并运行 Crew 完成任务
    
    Args:
        user_request: 用户请求
        process: 执行模式
            - "sequential": 顺序执行（默认），任务按顺序一个接一个执行
            - "hierarchical": 层级执行，需要 manager Agent 协调
        verbose: 是否显示详细日志
    
    Returns:
        执行结果
    """
    if not CREWAI_AVAILABLE:
        return "Error: crewai not installed. Run: pip install crewai"
    
    print(f"\n{'='*60}")
    print(f"CrewAI 任务执行")
    print(f"{'='*60}")
    print(f"用户请求: {user_request}")
    print(f"执行模式: {process}")
    print(f"{'='*60}\n")
    
    try:
        # 创建 Agent 团队
        agents = create_agents()
        
        # 创建任务
        tasks = create_tasks(agents, user_request)
        
        # 组建 Crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential if process == "sequential" else Process.hierarchical,
            verbose=verbose,
        )
        
        # 执行任务
        result = crew.kickoff()
        
        print(f"\n{'='*60}")
        print("任务完成！")
        print(f"{'='*60}")
        
        return str(result)
        
    except Exception as e:
        error_msg = f"Crew 执行失败: {str(e)}"
        print(error_msg)
        return error_msg


# ============================================================
# 单 Agent 模式（简化版）
# ============================================================

def run_single_agent(user_request: str) -> str:
    """
    使用单个全能 Agent 执行任务（简化模式）
    
    适用于简单任务，不需要多 Agent 协作
    """
    if not CREWAI_AVAILABLE:
        return "Error: crewai not installed"
    
    # 创建全部工具
    tools = [
        HttpRequestTool(),
        FileOpsTool(),
        WebScraperTool(),
        PythonExecTool(),
    ]
    
    # 创建全能 Agent
    agent = Agent(
        role="AI 助手",
        goal="帮助用户完成各种任务",
        backstory="你是一个全能的 AI 助手，可以处理网络请求、数据分析和文件操作。",
        tools=tools,
        verbose=True,
    )
    
    # 创建任务
    task = Task(
        description=f"完成以下用户请求:\n\n{user_request}",
        expected_output="任务完成的结果和确认",
        agent=agent,
    )
    
    # 创建并运行 Crew
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )
    
    return str(crew.kickoff())


# ============================================================
# Flask 集成示例
# ============================================================

def create_crewai_blueprint():
    """
    创建 Flask Blueprint 用于 CrewAI 集成
    
    可以添加到现有的 Flask 应用中
    """
    from flask import Blueprint, request, jsonify
    
    bp = Blueprint('crewai', __name__, url_prefix='/crewai')
    
    @bp.route('/run', methods=['POST'])
    def run_task():
        """运行 CrewAI 任务"""
        data = request.get_json()
        user_request = data.get('request', '')
        mode = data.get('mode', 'crew')  # 'crew' 或 'single'
        
        if mode == 'single':
            result = run_single_agent(user_request)
        else:
            result = run_crew(user_request)
        
        return jsonify({
            "status": "success",
            "result": result
        })
    
    return bp


# ============================================================
# 主程序入口
# ============================================================

if __name__ == "__main__":
    # 示例：运行 Crew 完成任务
    
    # 测试请求
    test_request = """
    获取 GitHub 上 Python 相关的热门项目信息，
    筛选出 star 数最多的前 5 个项目，
    并将结果保存到 github_trending.json 文件中。
    """
    
    print("=" * 60)
    print("CrewAI Agent 测试")
    print("=" * 60)
    
    if CREWAI_AVAILABLE:
        # 运行多 Agent 协作模式
        result = run_crew(test_request)
        print("\n最终结果:")
        print(result)
    else:
        print("请先安装 crewai: pip install crewai")
        print("\n以下是 CrewAI 的核心概念演示（无需安装）:")
        print("""
        CrewAI 工作流程:
        
        1. 定义 Agent（船员）:
           - Researcher: 负责数据收集
           - Analyst: 负责数据分析  
           - Writer: 负责报告撰写
        
        2. 定义 Task（任务）:
           - 每个任务分配给特定 Agent
           - 任务可以有依赖关系
        
        3. 组建 Crew（团队）:
           - 将 Agent 和 Task 组合
           - 选择执行模式（顺序/层级）
        
        4. 执行 kickoff():
           - Crew 协调各 Agent 完成任务
           - 自动传递上下文和结果
        """)
