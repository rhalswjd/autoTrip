"""Synthetic Yahoo route pages for deterministic parser and discovery tests."""
import json


def route_page(route_specs, *, start, end, count, next_url=None):
    route_html = []
    feature_info = []
    for index, spec in enumerate(route_specs, start=1):
        route_html.append(f"""
        <div id="route0{index}">
          <div class="routeSummary">
            <span class="time">{spec['departure']}発 {spec['arrival']}着 {spec['elapsed']}（乗車 {spec['onboard']}）</span>
            <span class="fare">乗換：{spec['transfers']}回 {spec['fare']:,}円</span>
          </div>
          <div class="routeDetail">
            <div class="station"><dt>{spec['from']}</dt></div>
            <div class="transport"><div>{spec['train']}</div></div>
            <div class="station"><dt>{spec['to']}</dt></div>
          </div>
        </div>
        """)
        feature_info.append({
            "summaryInfo": {
                "departureTime": spec["departure"],
                "arrivalTime": spec["arrival"],
                "totalTime": spec["elapsed"],
                "timeOnBoard": spec["onboard"],
                "totalPrice": str(spec["fare"]),
                "transferCount": str(spec["transfers"]),
            },
            "edgeInfoList": [],
        })

    pager = {"start": start, "end": end, "count": count}
    if next_url:
        pager["prevNextThreeUrl"] = next_url
    payload = {
        "props": {"pageProps": {"naviSearchParam": {
            "featureInfoList": feature_info,
            "pagerInfo": pager,
        }}}
    }
    return "".join(route_html) + (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script>"
    )


def route_spec(name, departure, arrival, elapsed="2時間39分", onboard="2時間13分", transfers=1):
    return {
        "from": "新大阪",
        "to": "敦賀",
        "train": name,
        "departure": departure,
        "arrival": arrival,
        "elapsed": elapsed,
        "onboard": onboard,
        "transfers": transfers,
        "fare": 2310,
    }
