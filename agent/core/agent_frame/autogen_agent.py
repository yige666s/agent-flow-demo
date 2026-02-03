"""
AutoGen Agent 实现示例
展示如何使用 AutoGen 框架构建 AI Agent 系统

AutoGen 是微软开发的多智能体对话框架，支持：
- 多 Agent 协作
- 人机交互
- 代码执行
- 工具调用
"""

import os
import json
from typing import Dict, Any, Optional, List, Annotated
from dotenv import load_dotenv

# AutoGen 核心导入
from autogen import ConversableAgent, AssistantAgent, UserProxyAgent
from autogen import register_function
from autogen.coding import LocalCommandLineCodeExecutor

import requests
from bs4 import BeautifulSoup

load_dotenv()


# ==================== 1. 配置 LLM ====================

def get_llm_config(provider: str = "openai") -> Dict[str, Any]:
    """
    获取 LLM 配置
    AutoGen 使用 config_list 格式配置多个模型
    """
    if provider == "openai":
        return {
            "config_list": [
                {
                    "model": "gpt-4",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                }
            ],
            "temperature": 0.7,
        }
    elif provider == "anthropic":
        return {
            "config_list": [
                {
                    "model": "claude-sonnet-4-20250514",
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "api_type": "anthropic",
                }
            ],
            "temperature": 0.7,
        }
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# ==================== 2. 定义工具函数 ====================

def http_request(
    url: Annotated[str, "请求的 URL 地址，必须包含完整的查询参数"],
    method: Annotated[str, "HTTP 方法: GET/POST/PUT/DELETE"] = "GET",
    headers: Annotated[Optional[Dict[str, str]], "请求头"] = None,
    body: Annotated[Optional[str], "请求体"] = None,
    timeout: Annotated[int, "超时时间（秒）"] = 10
) -> Dict[str, Any]:
    """
    发起 HTTP 请求，获取网页或 API 数据。
    返回包含 status_code、body 和 json（如果是 JSON 响应）的结果。
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
            "body": response.text[:5000],  # 限制长度
            "success": 200 <= response.status_code < 300
        }
        
        # 尝试解析 JSON
        try:
            result["json"] = response.json()
        except:
            pass
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def file_write(
    filename: Annotated[str, "文件名"],
    content: Annotated[str, "要写入的内容"]
) -> Dict[str, Any]:
    """
    将内容写入文件，保存到 data/user 目录。
    """
    try:
        user_dir = os.path.join(os.path.dirname(__file__), "..", "data", "user")
        os.makedirs(user_dir, exist_ok=True)
        
        filepath = os.path.join(user_dir, os.path.basename(filename))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {"success": True, "path": filepath, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def file_read(
    filename: Annotated[str, "文件名"]
) -> Dict[str, Any]:
    """
    读取文件内容。
    """
    try:
        user_dir = os.path.join(os.path.dirname(__file__), "..", "data", "user")
        filepath = os.path.join(user_dir, os.path.basename(filename))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


def web_scraper(
    html: Annotated[str, "HTML 字符串"],
    extract_type: Annotated[str, "提取类型: text/links/tables/title"]
) -> Dict[str, Any]:
    """
    从 HTML 中提取指定内容。
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        if extract_type == "text":
            return {"success": True, "data": soup.get_text(strip=True)[:5000]}
        elif extract_type == "title":
            title = soup.find('title')
            return {"success": True, "data": title.string if title else None}
        elif extract_type == "links":
            links = [{"text": a.get_text(strip=True), "href": a['href']} 
                     for a in soup.find_all('a', href=True)[:50]]
            return {"success": True, "data": links}
        elif extract_type == "tables":
            tables = []
            for table in soup.find_all('table')[:5]:
                rows = [[cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                        for row in table.find_all('tr')]
                tables.append(rows)
            return {"success": True, "data": tables}
        else:
            return {"success": False, "error": f"Unknown extract_type: {extract_type}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 3. 创建 AutoGen Agent ====================

class AutoGenAgent:
    """
    AutoGen Agent 封装类
    
    核心概念：
    1. AssistantAgent: AI 助手，负责推理和决策
    2. UserProxyAgent: 用户代理，负责执行代码和工具调用
    3. 两者通过对话协作完成任务
    """
    
    def __init__(self, llm_config: Dict[str, Any] = None):
        """初始化 AutoGen Agent"""
        
        self.llm_config = llm_config or get_llm_config("openai")
        
        # 创建 Assistant Agent（AI 助手）
        self.assistant = AssistantAgent(
            name="TaskAssistant",
            system_message="""你是一个智能任务执行助手。你需要根据用户的任务，使用可用的工具来完成任务。

可用工具：
1. http_request: 发起 HTTP 请求获取网页或 API 数据
2. file_write: 将内容写入文件
3. file_read: 读取文件内容
4. web_scraper: 从 HTML 中提取结构化数据

执行原则：
1. 分析任务，确定需要的步骤
2. 按顺序调用工具执行每个步骤
3. 处理工具返回的结果
4. 完成任务后，用 "TERMINATE" 结束对话

注意：
- URL 必须完整，包含所有查询参数
- 处理数据时注意格式转换
- 写入文件时使用 JSON 格式""",
            llm_config=self.llm_config,
        )
        
        # 创建 User Proxy Agent（用户代理/执行器）
        self.user_proxy = UserProxyAgent(
            name="TaskExecutor",
            human_input_mode="NEVER",  # 不需要人工输入
            max_consecutive_auto_reply=10,  # 最多自动回复 10 次
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config=False,  # 不执行代码（使用工具代替）
        )
        
        # 注册工具到两个 Agent
        self._register_tools()
    
    def _register_tools(self):
        """注册工具函数"""
        
        # 注册 http_request
        register_function(
            http_request,
            caller=self.assistant,  # Assistant 决定何时调用
            executor=self.user_proxy,  # UserProxy 负责执行
            name="http_request",
            description="发起 HTTP 请求获取网页或 API 数据"
        )
        
        # 注册 file_write
        register_function(
            file_write,
            caller=self.assistant,
            executor=self.user_proxy,
            name="file_write",
            description="将内容写入文件"
        )
        
        # 注册 file_read
        register_function(
            file_read,
            caller=self.assistant,
            executor=self.user_proxy,
            name="file_read",
            description="读取文件内容"
        )
        
        # 注册 web_scraper
        register_function(
            web_scraper,
            caller=self.assistant,
            executor=self.user_proxy,
            name="web_scraper",
            description="从 HTML 中提取结构化数据"
        )
    
    def run(self, task: str) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 用户任务描述
        
        Returns:
            执行结果
        """
        try:
            # 发起对话，UserProxy 向 Assistant 发送任务
            chat_result = self.user_proxy.initiate_chat(
                self.assistant,
                message=task,
                clear_history=True,  # 清除之前的对话历史
            )
            
            return {
                "success": True,
                "chat_history": chat_result.chat_history,
                "cost": chat_result.cost,
                "summary": chat_result.summary,
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# ==================== 4. 多 Agent 协作示例 ====================

class MultiAgentTeam:
    """
    多 Agent 协作团队示例
    
    展示 AutoGen 的多 Agent 协作能力：
    - Planner: 负责任务拆解
    - Executor: 负责执行工具
    - Critic: 负责检查结果
    """
    
    def __init__(self, llm_config: Dict[str, Any] = None):
        self.llm_config = llm_config or get_llm_config("openai")
        
        # 规划者 Agent
        self.planner = AssistantAgent(
            name="Planner",
            system_message="""你是一个任务规划专家。
你的职责是将用户的任务拆解为具体的执行步骤。
每个步骤应该包含：步骤编号、描述、需要使用的工具、预期结果。
输出 JSON 格式的计划。""",
            llm_config=self.llm_config,
        )
        
        # 执行者 Agent
        self.executor = AssistantAgent(
            name="Executor",
            system_message="""你是一个任务执行专家。
你的职责是按照计划执行每个步骤，调用相应的工具。
执行完成后报告结果。""",
            llm_config=self.llm_config,
        )
        
        # 评审者 Agent
        self.critic = AssistantAgent(
            name="Critic",
            system_message="""你是一个质量检查专家。
你的职责是检查执行结果是否符合预期。
如果有问题，指出问题并建议改进。
如果满意，回复 "APPROVED"。""",
            llm_config=self.llm_config,
        )
        
        # 用户代理
        self.user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=5,
            is_termination_msg=lambda x: "APPROVED" in x.get("content", ""),
        )
    
    def run(self, task: str) -> Dict[str, Any]:
        """
        执行多 Agent 协作任务
        
        流程: User -> Planner -> Executor -> Critic -> (循环或结束)
        """
        from autogen import GroupChat, GroupChatManager
        
        # 创建群聊
        groupchat = GroupChat(
            agents=[self.user_proxy, self.planner, self.executor, self.critic],
            messages=[],
            max_round=12,  # 最多 12 轮对话
        )
        
        # 创建群聊管理器
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self.llm_config,
        )
        
        # 发起群聊
        chat_result = self.user_proxy.initiate_chat(
            manager,
            message=task,
        )
        
        return {
            "success": True,
            "chat_history": chat_result.chat_history,
            "summary": chat_result.summary,
        }


# ==================== 5. 代码执行示例 ====================

class CodeExecutionAgent:
    """
    支持代码执行的 Agent
    
    AutoGen 可以让 LLM 生成代码并自动执行
    """
    
    def __init__(self, llm_config: Dict[str, Any] = None):
        self.llm_config = llm_config or get_llm_config("openai")
        
        # 创建代码执行器（在本地执行）
        self.code_executor = LocalCommandLineCodeExecutor(
            timeout=60,  # 执行超时
            work_dir="./workspace",  # 工作目录
        )
        
        # 创建 Assistant
        self.assistant = AssistantAgent(
            name="CodeAssistant",
            system_message="""你是一个编程助手。
你可以编写 Python 代码来完成用户的任务。
代码会被自动执行，你会收到执行结果。
根据结果决定下一步行动。""",
            llm_config=self.llm_config,
        )
        
        # 创建可执行代码的 UserProxy
        self.user_proxy = UserProxyAgent(
            name="CodeExecutor",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={
                "executor": self.code_executor,
            },
        )
    
    def run(self, task: str) -> Dict[str, Any]:
        """执行需要代码的任务"""
        chat_result = self.user_proxy.initiate_chat(
            self.assistant,
            message=task,
        )
        
        return {
            "success": True,
            "chat_history": chat_result.chat_history,
        }


# ==================== 6. 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("AutoGen Agent 示例")
    print("=" * 60)
    
    # 创建基础 Agent
    agent = AutoGenAgent()
    
    # 测试任务
    task = """
    访问 https://api.github.com/users/torvalds 获取用户信息，
    提取 login、name、public_repos 字段，
    保存到 linus.json 文件中。
    """
    
    print(f"\n任务: {task}")
    print("\n开始执行...")
    
    result = agent.run(task)
    
    if result["success"]:
        print("\n✅ 任务完成!")
        print(f"对话轮数: {len(result['chat_history'])}")
        print(f"摘要: {result.get('summary', 'N/A')}")
    else:
        print(f"\n❌ 任务失败: {result['error']}")
