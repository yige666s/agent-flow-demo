"""
ReAct Agent 测试脚本
用于验证 ReAct 模式是否正常工作
"""

import os
import sys

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from tools import register_all_tools
from llm_client import init_llm_client, load_config_from_file
from react_agent import ReActAgent


def test_react_agent():
    """测试 ReAct Agent"""
    
    print("=" * 60)
    print("ReAct Agent 测试")
    print("=" * 60)
    
    # 加载配置
    try:
        config = load_config_from_file("config.yaml")
        print(f"✓ 加载配置: {config.get('provider', 'unknown')}")
        init_llm_client(config=config)
    except FileNotFoundError:
        print("✗ 未找到 config.yaml，请确保配置文件存在")
        return
    
    # 注册工具
    register_all_tools()
    print("✓ 工具注册完成")
    
    # 创建 ReAct Agent
    agent = ReActAgent(max_iterations=5)
    print(f"✓ ReAct Agent 创建完成 (最大迭代: {agent.max_iterations})")
    
    # 测试任务
    test_tasks = [
        {
            "task_id": "test_001",
            "user_input": "请读取当前目录下的 config.yaml 文件内容",
            "description": "测试文件读取工具"
        },
        # 可以添加更多测试用例
    ]
    
    for task in test_tasks:
        print(f"\n{'='*60}")
        print(f"任务: {task['description']}")
        print(f"输入: {task['user_input']}")
        print(f"{'='*60}")
        
        result = agent.run(
            task_id=task["task_id"],
            user_input=task["user_input"]
        )
        
        print(f"\n{'='*60}")
        print("执行结果:")
        print(f"  状态: {result.status}")
        print(f"  迭代次数: {result.total_iterations}")
        if result.final_answer:
            print(f"  最终答案: {result.final_answer[:200]}...")
        if result.error:
            print(f"  错误: {result.error}")
        print(f"{'='*60}")


if __name__ == "__main__":
    test_react_agent()
