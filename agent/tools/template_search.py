"""
Template Search Tool
"""

from typing import Dict, Any, List
from .base import BaseTool, ToolSchema, ToolParameter
from core.retriever import TemplateRetriever

class TemplateSearchTool(BaseTool):
    """模版搜索工具"""
    
    def __init__(self):
        self.retriever = TemplateRetriever()
        
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="search_templates",
            description="Search for image generation templates based on a natural language description. Use this when the user wants to find a style, theme, or specific type of image template.",
            parameters={
                "query": ToolParameter(
                    name="query",
                    type="string",
                    description="The search query describing the desired template or style (e.g., 'cyberpunk city', 'watercolor nature')."
                ),
                "limit": ToolParameter(
                    name="limit",
                    type="number",
                    description="The number of templates to return (default: 3).",
                    required=False,
                    default=3
                )
            }
        )
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """执行搜索"""
        query = kwargs.get("query")
        limit = kwargs.get("limit", 3)
        
        if not query:
            return []
            
        return self.retriever.search(query, k=limit)
