"""
Yahoo Transit 시간표 파싱용 Selector
"""
YAHOO_SELECTORS = {
    "route_item": "div.routeSummary",
    "departure_time": "li.time > span:nth-of-type(1)",
    "arrival_time": "li.time > span:nth-of-type(2)",
    "train_name": "ul.transport > li > span.mark",
    "direction": "span.dest"
}
