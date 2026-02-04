"""
网页爬取工具 - 增强版
支持更多提取类型、CSS选择器、更好的文本清理
"""

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import re
from .base import BaseTool, ToolSchema, ToolParameter


class WebScraperTool(BaseTool):
    """网页内容提取工具（增强版）"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="web_scraper",
            description=(
                "从 HTML 中提取指定内容。支持提取：\n"
                "- title: 页面标题\n"
                "- text: 纯文本内容（已清理）\n"
                "- links: 所有链接\n"
                "- headings: 标题（h1-h6）\n"
                "- images: 图片\n"
                "- tables: 表格数据\n"
                "- meta: meta 标签信息\n"
                "- css_select: 使用 CSS 选择器提取"
            ),
            parameters={
                "html": ToolParameter(
                    name="html",
                    type="string",
                    description="HTML 字符串内容",
                    required=True
                ),
                "extract": ToolParameter(
                    name="extract",
                    type="array",
                    description="要提取的内容类型列表：title, links, text, headings, images, tables, meta",
                    required=True
                ),
                "css_selector": ToolParameter(
                    name="css_selector",
                    type="string",
                    description="CSS 选择器（可选），用于精确提取特定元素",
                    required=False
                ),
                "clean_text": ToolParameter(
                    name="clean_text",
                    type="boolean",
                    description="是否清理文本（去除多余空白、脚本标签等），默认 True",
                    required=False,
                    default=True
                )
            },
            timeout=15
        )
    
    def _clean_text(self, text: str) -> str:
        """清理文本，去除多余空白"""
        if not text:
            return ""
        # 合并多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()
        return text
    
    def _remove_scripts_styles(self, soup: BeautifulSoup) -> BeautifulSoup:
        """移除脚本和样式标签"""
        for tag in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
            tag.decompose()
        return soup
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """提取标题"""
        # 优先 title 标签
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return self._clean_text(title_tag.string)
        
        # 其次 h1
        h1_tag = soup.find('h1')
        if h1_tag:
            return self._clean_text(h1_tag.get_text())
        
        # 再次 og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return self._clean_text(og_title['content'])
        
        return None
    
    def _extract_links(self, soup: BeautifulSoup, limit: int = 100) -> List[Dict[str, str]]:
        """提取链接"""
        links = []
        seen_hrefs = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if not href or href.startswith(('#', 'javascript:')):
                continue
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            
            text = self._clean_text(a_tag.get_text())
            links.append({
                "text": text or "[无文本]",
                "href": href
            })
            
            if len(links) >= limit:
                break
        
        return links
    
    def _extract_text(self, soup: BeautifulSoup, clean: bool = True) -> str:
        """提取纯文本"""
        # 克隆以避免影响原始 soup
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        if clean:
            soup_copy = self._remove_scripts_styles(soup_copy)
        
        # 获取文本
        text = soup_copy.get_text(separator=' ')
        
        if clean:
            text = self._clean_text(text)
        
        return text
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取标题"""
        headings = []
        for level in range(1, 7):
            for h_tag in soup.find_all(f'h{level}'):
                text = self._clean_text(h_tag.get_text())
                if text:
                    headings.append({
                        "level": level,
                        "text": text
                    })
        return headings
    
    def _extract_images(self, soup: BeautifulSoup, limit: int = 50) -> List[Dict[str, str]]:
        """提取图片"""
        images = []
        seen_srcs = set()
        
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src', '') or img_tag.get('data-src', '')
            if not src or src in seen_srcs:
                continue
            seen_srcs.add(src)
            
            images.append({
                "src": src,
                "alt": img_tag.get('alt', ''),
                "title": img_tag.get('title', '')
            })
            
            if len(images) >= limit:
                break
        
        return images
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[List[List[str]]]:
        """提取表格"""
        tables = []
        
        for table in soup.find_all('table'):
            table_data = []
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                row_data = [self._clean_text(cell.get_text()) for cell in cells]
                if any(row_data):  # 只添加非空行
                    table_data.append(row_data)
            if table_data:
                tables.append(table_data)
        
        return tables
    
    def _extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取 meta 信息"""
        meta_info = {}
        
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property', '')
            content = meta.get('content', '')
            if name and content:
                meta_info[name] = content
        
        return meta_info
    
    def _css_select(self, soup: BeautifulSoup, selector: str) -> List[Dict[str, Any]]:
        """使用 CSS 选择器提取"""
        results = []
        try:
            elements = soup.select(selector)
            for elem in elements:
                results.append({
                    "tag": elem.name,
                    "text": self._clean_text(elem.get_text()),
                    "html": str(elem)[:500],  # 限制 HTML 长度
                    "attrs": dict(elem.attrs) if elem.attrs else {}
                })
        except Exception as e:
            results.append({"error": f"CSS 选择器错误: {str(e)}"})
        
        return results
    
    def execute(
        self,
        html: str,
        extract: List[str],
        css_selector: Optional[str] = None,
        clean_text: bool = True
    ) -> Dict[str, Any]:
        """提取网页内容"""
        # 参数规范化
        if not html:
            return {"success": False, "error": "HTML 内容为空"}
        
        html = str(html)
        if isinstance(extract, str):
            extract = [extract]
        extract = [str(e).lower().strip() for e in extract if e]
        
        if not extract:
            extract = ["text"]  # 默认提取文本
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            result = {"success": True, "data": {}}
            
            for item in extract:
                if item == "title":
                    result["data"]["title"] = self._extract_title(soup)
                
                elif item == "links":
                    result["data"]["links"] = self._extract_links(soup)
                
                elif item == "text":
                    result["data"]["text"] = self._extract_text(soup, clean_text)
                
                elif item == "headings":
                    result["data"]["headings"] = self._extract_headings(soup)
                
                elif item == "images":
                    result["data"]["images"] = self._extract_images(soup)
                
                elif item == "tables":
                    result["data"]["tables"] = self._extract_tables(soup)
                
                elif item == "meta":
                    result["data"]["meta"] = self._extract_meta(soup)
                
                else:
                    result["data"][item] = f"未知的提取类型: {item}"
            
            # CSS 选择器
            if css_selector:
                result["data"]["css_select"] = self._css_select(soup, css_selector)
            
            return result
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
