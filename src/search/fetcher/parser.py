"""HTML to Markdown parser."""

import re
from typing import Optional, List


class HTMLParser:
    """Parse HTML to Markdown."""
    
    def __init__(self):
        """Initialize parser."""
        pass
    
    def parse(self, html: str, base_url: Optional[str] = None) -> str:
        """
        Parse HTML to Markdown.
        
        Args:
            html: HTML content
            base_url: Base URL for relative links
            
        Returns:
            Markdown text
        """
        if not html:
            return ""
        
        # Remove scripts and styles
        text = self._remove_scripts(html)
        text = self._remove_styles(text)
        
        # Convert common elements
        text = self._convert_headers(text)
        text = self._convert_links(text)
        text = self._convert_lists(text)
        text = self._convert_code(text)
        text = self._convert_emphasis(text)
        text = self._convert_tables(text)
        text = self._convert_quotes(text)
        
        # Clean up
        text = self._clean_whitespace(text)
        text = self._decode_entities(text)
        
        return text.strip()
    
    def _remove_scripts(self, html: str) -> str:
        """Remove script tags."""
        return re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    def _remove_styles(self, html: str) -> str:
        """Remove style tags."""
        return re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    def _convert_headers(self, html: str) -> str:
        """Convert header tags."""
        # h1
        html = re.sub(
            r'<h1[^>]*>(.*?)</h1>',
            r'\n# \1\n',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        # h2
        html = re.sub(
            r'<h2[^>]*>(.*?)</h2>',
            r'\n## \1\n',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        # h3
        html = re.sub(
            r'<h3[^>]*>(.*?)</h3>',
            r'\n### \1\n',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        # h4
        html = re.sub(
            r'<h4[^>]*>(.*?)</h4>',
            r'\n#### \1\n',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        # h5
        html = re.sub(
            r'<h5[^>]*>(.*?)</h5>',
            r'\n##### \1\n',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        # h6
        html = re.sub(
            r'<h6[^>]*>(.*?)</h6>',
            r'\n###### \1\n',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        return html
    
    def _convert_links(self, html: str) -> str:
        """Convert anchor tags."""
        def replace_link(match):
            href = match.group(1)
            text = match.group(2)
            # Clean up text
            text = re.sub(r'<[^>]+>', '', text)
            return f'[{text}]({href})'
        
        return re.sub(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            replace_link,
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
    
    def _convert_lists(self, html: str) -> str:
        """Convert list tags."""
        # Unordered lists
        def replace_ul(match):
            content = match.group(1)
            items = re.findall(r'<li[^>]*>(.*?)</li>', content, re.DOTALL | re.IGNORECASE)
            return '\n' + '\n'.join(f'- {self._clean_item(item)}' for item in items) + '\n'
        
        html = re.sub(r'<ul[^>]*>(.*?)</ul>', replace_ul, html, flags=re.DOTALL | re.IGNORECASE)
        
        # Ordered lists
        def replace_ol(match):
            content = match.group(1)
            items = re.findall(r'<li[^>]*>(.*?)</li>', content, re.DOTALL | re.IGNORECASE)
            return '\n' + '\n'.join(f'{i+1}. {self._clean_item(item)}' for i, item in enumerate(items)) + '\n'
        
        html = re.sub(r'<ol[^>]*>(.*?)</ol>', replace_ol, html, flags=re.DOTALL | re.IGNORECASE)
        
        # Individual li items (not in ul/ol)
        html = re.sub(
            r'<li[^>]*>(.*?)</li>',
            r'- \1',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        return html
    
    def _clean_item(self, text: str) -> str:
        """Clean list item text."""
        # Remove inner tags but keep content
        text = re.sub(r'<[^>]+>', '', text)
        # Clean whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def _convert_code(self, html: str) -> str:
        """Convert code tags."""
        # Pre/code blocks
        def replace_code_block(match):
            code = match.group(1)
            # Try to detect language
            lang = ''
            class_match = re.search(r'class=["\'][^"\']*language-(\w+)["\']', match.group(0))
            if class_match:
                lang = class_match.group(1)
            
            code = self._clean_code(code)
            return f'\n```{lang}\n{code}\n```\n'
        
        html = re.sub(
            r'<pre[^>]*>\s*(?:<code[^>]*>)?(.*?)(?:</code>)?\s*</pre>',
            replace_code_block,
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Inline code
        html = re.sub(
            r'<code[^>]*>(.*?)</code>',
            r'`\1`',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        return html
    
    def _clean_code(self, code: str) -> str:
        """Clean code block content."""
        # Remove HTML tags
        code = re.sub(r'<[^>]+>', '', code)
        # Decode entities
        code = self._decode_entities(code)
        return code.strip()
    
    def _convert_emphasis(self, html: str) -> str:
        """Convert emphasis tags."""
        # Bold
        html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Italic
        html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)
        
        return html
    
    def _convert_tables(self, html: str) -> str:
        """Convert table tags to simple text."""
        # Simplified table conversion - just extract text
        def replace_table(match):
            content = match.group(1)
            # Extract all cells
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', content, re.DOTALL | re.IGNORECASE)
            return '\n' + ' | '.join(self._clean_item(c) for c in cells) + '\n'
        
        return re.sub(r'<table[^>]*>(.*?)</table>', replace_table, html, flags=re.DOTALL | re.IGNORECASE)
    
    def _convert_quotes(self, html: str) -> str:
        """Convert blockquote tags."""
        def replace_quote(match):
            content = match.group(1)
            # Add > to each line
            lines = content.split('\n')
            quoted = '\n'.join(f'> {line.strip()}' for line in lines if line.strip())
            return f'\n{quoted}\n'
        
        return re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', replace_quote, html, flags=re.DOTALL | re.IGNORECASE)
    
    def _clean_whitespace(self, text: str) -> str:
        """Clean up whitespace."""
        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()
    
    def _decode_entities(self, text: str) -> str:
        """Decode HTML entities."""
        import html
        return html.unescape(text)