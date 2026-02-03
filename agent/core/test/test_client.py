#!/usr/bin/env python3
"""
AgentFlow 测试客户端
用于测试完整的任务执行流程
"""

import requests
import time
import json


BASE_URL = "http://localhost:8000"


def create_task(user_input: str):
    """创建任务"""
    print(f"\n{'='*60}")
    print(f"创建任务: {user_input}")
    print(f"{'='*60}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/tasks",
        json={"user_input": user_input}
    )
    
    if response.status_code == 201:
        data = response.json()
        print(f"✓ 任务创建成功")
        print(f"  Task ID: {data['task_id']}")
        print(f"  Status: {data['status']}")
        return data['task_id']
    else:
        print(f"✗ 任务创建失败: {response.text}")
        return None


def get_task(task_id: str):
    """查询任务"""
    response = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"✗ 查询任务失败: {response.text}")
        return None


def wait_for_completion(task_id: str, timeout: int = 120):
    """等待任务完成"""
    print(f"\n等待任务完成...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        task = get_task(task_id)
        
        if not task:
            return None
        
        status = task['status']
        print(f"  状态: {status}", end='\r')
        
        if status in ['completed', 'failed', 'cancelled']:
            print()  # 换行
            return task
        
        time.sleep(2)
    
    print("\n✗ 任务超时")
    return None


def print_task_result(task):
    """打印任务结果"""
    print(f"\n{'='*60}")
    print(f"任务执行结果")
    print(f"{'='*60}")
    print(f"Task ID: {task['id']}")
    print(f"Status: {task['status']}")
    
    if task.get('plan'):
        print(f"\n执行计划:")
        for step in task['plan']['steps']:
            print(f"  Step {step['step_id']}: {step['description']}")
            print(f"    Tool: {step['tool']}")
    
    if task.get('result'):
        print(f"\n执行结果:")
        print(json.dumps(task['result'], indent=2, ensure_ascii=False))
    
    if task.get('error'):
        print(f"\n错误信息: {task['error']}")
    
    print(f"{'='*60}\n")


def run_test_case(user_input: str):
    """运行测试用例"""
    task_id = create_task(user_input)
    
    if not task_id:
        return
    
    task = wait_for_completion(task_id)
    
    if task:
        print_task_result(task)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("AgentFlow 测试客户端")
    print("="*60)
    
    # 测试用例 1：HTTP 请求 + 网页分析
    run_test_case("帮我获取 https://example.com 的网页标题和链接")
    
    # 测试用例 2：文件操作
    run_test_case("创建一个文本文件 test.txt，内容是 'Hello AgentFlow'")
    
    # 可以添加更多测试用例...
    
    print("\n所有测试完成！")
