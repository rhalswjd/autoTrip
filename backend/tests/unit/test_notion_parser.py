import pytest
from utils.notion_parser import extract_notion_page_id

def test_extract_pure_32_char_id():
    # 1. 순수 32자리 Page ID 추출
    assert extract_notion_page_id("11111111111111111111111111111111") == "11111111111111111111111111111111"

def test_extract_hyphen_uuid_id():
    # 2. 하이픈 UUID Page ID 추출
    assert extract_notion_page_id("11111111-1111-1111-1111-111111111111") == "11111111111111111111111111111111"

def test_extract_url_with_title():
    # 3. 제목이 포함된 Notion URL에서 ID 추출
    assert extract_notion_page_id("https://www.notion.so/여행계획-11111111111111111111111111111111") == "11111111111111111111111111111111"
    # With workspace
    assert extract_notion_page_id("https://www.notion.so/my-workspace/여행계획-11111111111111111111111111111111") == "11111111111111111111111111111111"

def test_extract_url_with_query_string():
    # 4. query string이 붙은 URL
    assert extract_notion_page_id("https://www.notion.so/여행계획-11111111111111111111111111111111?pvs=4") == "11111111111111111111111111111111"

def test_extract_url_with_fragment():
    # 5. fragment가 붙은 URL
    assert extract_notion_page_id("https://www.notion.so/여행계획-11111111111111111111111111111111#section-id") == "11111111111111111111111111111111"
    
def test_extract_url_with_query_and_fragment():
    assert extract_notion_page_id("https://www.notion.so/여행계획-11111111111111111111111111111111?pvs=4#section-id") == "11111111111111111111111111111111"

def test_invalid_url():
    # 6. 잘못된 URL (Notion 도메인이지만 ID가 없음)
    with pytest.raises(ValueError):
        extract_notion_page_id("https://www.notion.so/my-workspace")

def test_non_notion_url():
    # 7. 일반 웹사이트 URL
    with pytest.raises(ValueError):
        extract_notion_page_id("https://www.google.com/11111111111111111111111111111111")

def test_empty_string():
    # 8. 빈 문자열
    assert extract_notion_page_id("") is None
    assert extract_notion_page_id(None) is None

def test_invalid_id_format():
    # Invalid ID
    with pytest.raises(ValueError):
        extract_notion_page_id("11111111-1111")

def test_app_notion_com_url():
    # app.notion.com with /p/
    assert extract_notion_page_id("https://app.notion.com/p/Example-11111111111111111111111111111111?source=copy_link") == "11111111111111111111111111111111"
    
def test_app_notion_com_no_protocol():
    # app.notion.com without protocol
    assert extract_notion_page_id("app.notion.com/p/Example-11111111111111111111111111111111?source=copy_link") == "11111111111111111111111111111111"

def test_notion_so_no_protocol():
    assert extract_notion_page_id("notion.so/여행계획-11111111111111111111111111111111") == "11111111111111111111111111111111"

def test_app_notion_com_invalid():
    # app.notion.com domain without path
    with pytest.raises(ValueError):
        extract_notion_page_id("app.notion.com")
        
    with pytest.raises(ValueError):
        extract_notion_page_id("https://app.notion.com/")
        
    with pytest.raises(ValueError):
        extract_notion_page_id("app.notion.com/p/invalid")
