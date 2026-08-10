import re
from typing import Optional
from urllib.parse import urlparse
from core.logger import logger

def extract_notion_page_id(input_string: Optional[str]) -> Optional[str]:
    """
    Extracts a 32-character Notion Page ID from a given URL or raw ID string.
    Returns the ID without hyphens.
    Raises ValueError if the string is invalid or not a Notion URL.
    """
    if not input_string:
        return None
        
    input_string = input_string.strip()
    logger.debug(f"[NotionParser] Input URL: {input_string}")
    
    # 32-char hex, optionally separated by hyphens (UUID format)
    id_pattern = r'([a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12})'
    
    valid_domains = ['notion.so', 'notion.site', 'app.notion.com']
    if any(domain in input_string for domain in valid_domains):
        if not input_string.startswith('http://') and not input_string.startswith('https://'):
            input_string = 'https://' + input_string
            
    if input_string.startswith('http://') or input_string.startswith('https://'):
        parsed = urlparse(input_string)
        if not any(domain in parsed.netloc for domain in valid_domains):
            raise ValueError("올바른 Notion 페이지 링크가 아닙니다. (유효한 도메인 포함 안됨)")
            
        path = parsed.path
        parts = [p for p in path.split('/') if p]
        if not parts:
            raise ValueError("올바른 Notion 페이지 링크가 아닙니다. (ID 없음)")
            
        last_part = parts[-1]
        
        match = re.search(id_pattern, last_part)
        if match:
            extracted = match.group(1).replace('-', '')
            logger.debug(f"[NotionParser] Extracted Page ID: {extracted}")
            return extracted
        else:
            raise ValueError("Notion 페이지 링크에서 올바른 Page ID를 찾을 수 없습니다.")
            
    else:
        # Check if it's just a raw ID
        match = re.match(f'^{id_pattern}$', input_string)
        if match:
            extracted = match.group(1).replace('-', '')
            logger.debug(f"[NotionParser] Extracted Page ID: {extracted}")
            return extracted
        else:
            raise ValueError("입력값이 올바른 Notion URL이거나 Page ID 형태가 아닙니다.")
