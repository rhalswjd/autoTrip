from typing import Dict, Any, Optional

def build_title(text: str) -> Dict[str, Any]:
    return {"title": [{"text": {"content": text}}]}

def build_rich_text(text: str) -> Dict[str, Any]:
    return {"rich_text": [{"text": {"content": text}}]}

def build_select(name: str) -> Dict[str, Any]:
    return {"select": {"name": name}}

def build_number(value: int) -> Dict[str, Any]:
    return {"number": value}

def build_checkbox(checked: bool) -> Dict[str, Any]:
    return {"checkbox": checked}

def build_date(start_date: str, end_date: Optional[str] = None) -> Dict[str, Any]:
    date_obj = {"start": start_date}
    if end_date:
        date_obj["end"] = end_date
    return {"date": date_obj}
