"""
网页爬取工具
"""

from typing import Any, Dict, List
from bs4 import BeautifulSoup
import requests
from .base import BaseTool, ToolSchema, ToolParameter


class WebScraperTool(BaseTool):
    """网页内容提取工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="web_scraper",
            description="从 HTML 中提取指定内容（标题、链接、文本、表格等）",
            parameters={
                "html": ToolParameter(
                    name="html",
                    type="string",
                    description="HTML 字符串",
                    required=True
                ),
                "extract": ToolParameter(
                    name="extract",
                    type="array",
                    description="要提取的内容类型列表: title, links, text, headings, images, tables",
                    required=True
                )
            },
            timeout=10
        )
    
    def execute(self, html: str, extract: List[str]) -> Dict[str, Any]:
        """提取网页内容"""
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
                            headings.append({
                                "level": i,
                                "text": h_tag.get_text(strip=True)
                            })
                    result["headings"] = headings
                
                elif item == "images":
                    images = []
                    for img_tag in soup.find_all('img', src=True):
                        images.append({
                            "src": img_tag['src'],
                            "alt": img_tag.get('alt', '')
                        })
                    result["images"] = images
                
                elif item == "tables":
                    tables = []
                    for table in soup.find_all('table'):
                        table_data = []
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            if row_data:  # 只添加非空行
                                table_data.append(row_data)
                        if table_data:
                            tables.append(table_data)
                    result["tables"] = tables
            
            return {
                "success": True,
                "data": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
