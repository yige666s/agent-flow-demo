"""
Template Retriever Implementation
支持基于向量相似度的模版检索
"""

import os
import json
import math
from typing import List, Dict, Any, Optional
from openai import OpenAI

class TemplateRetriever:
    """模版检索器"""
    
    def __init__(self, data_path: str = "agent/data/templates.json"):
        """
        初始化检索器
        
        Args:
            data_path: 模版数据文件路径
        """
        self.data_path = data_path
        self.templates = self._load_templates()
        self.embeddings = {}  # In-memory vector store: {id: vector}
        
        # 初始化 OpenAI Client 用于生成 Embedding
        # 注意: 这里简化处理，直接使用环境变量中的 KEY
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if api_key:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            print("Warning: OPENAI_API_KEY not found, retriever will likely fail to generate embeddings.")
            self.client = None
            
        # 预计算或加载模版 Embedding (Demo 简化: 懒加载或启动时计算)
        # 实际生产中应存储在 Vector DB
        pass

    def _load_templates(self) -> List[Dict]:
        """加载模版数据"""
        try:
            # 优先使用绝对路径，或者相对于当前文件的路径
            if os.path.isabs(self.data_path) and os.path.exists(self.data_path):
                target_path = self.data_path
            else:
                # 假设 data_path 是相对于 agent/ 目录的，或者是 agent/data/templates.json
                # 如果代码在 agent/core/retriever.py
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # agent/core/../data/templates.json -> agent/data/templates.json
                # 尝试解析相对于 agent/core/ 的路径
                
                # Check if path provided is like "agent/data/templates.json"
                # If we are in agent/core, we want to go up to agent root
                
                # Try 1: Relative to CWD (keep existing behavior as fallback)
                target_path = os.path.abspath(self.data_path)
                
                if not os.path.exists(target_path):
                    # Try 2: Relative to this file's parent (agent/)
                    # self.data_path might be "agent/data/..." or "data/..."
                    
                    # If data_path starts with "agent/", strip it? 
                    # Simpler: just construct the standard path
                    if "templates.json" in self.data_path:
                         target_path = os.path.join(current_dir, "..", "data", "templates.json")
                
            if not os.path.exists(target_path):
                print(f"Warning: Template file not found at {target_path}")
                return []
            
            with open(target_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading templates: {e}")
            return []

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本 Embedding"""
        if not self.client:
            raise ValueError("OpenAI Client not initialized (missing API Key)")
            
        text = text.replace("\n", " ")
        try:
            response = self.client.embeddings.create(
                input=[text],
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度 (Pure Python)"""
        if not v1 or not v2:
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(a * a for a in v1))
        norm_v2 = math.sqrt(sum(b * b for b in v2))
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
            
        return dot_product / (norm_v1 * norm_v2)

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        检索最相似的模版
        
        Args:
            query: 用户查询
            k: 返回结果数量
            
        Returns:
            相似模版列表 (包含 score)
        """
        if not self.templates:
            return []
            
        try:
            query_vec = self._get_embedding(query)
            if not query_vec:
                return []
        except ValueError as e:
            print(f"Search failed: {e}")
            return []
            
        # 简单的线性扫描 (Brute-force)
        scored_templates = []
        
        for tmpl in self.templates:
            content = f"{tmpl.get('name', '')} {tmpl.get('description', '')} {' '.join(tmpl.get('tags', []))}"
            
            tmpl_id = tmpl.get('id')
            if tmpl_id not in self.embeddings:
                # 注意: 搜索时才按需计算，此时很慢。
                # 实际场景应该预先计算好存在本地。
                vec = self._get_embedding(content)
                if vec:
                    self.embeddings[tmpl_id] = vec
            
            tmpl_vec = self.embeddings.get(tmpl_id)
            if tmpl_vec:
                score = self._cosine_similarity(query_vec, tmpl_vec)
                
                result_item = tmpl.copy()
                result_item['score'] = score
                scored_templates.append(result_item)
            
        scored_templates.sort(key=lambda x: x['score'], reverse=True)
        return scored_templates[:k]
