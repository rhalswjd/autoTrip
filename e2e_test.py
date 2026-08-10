import urllib.request
import json
import uuid

# 1. Search Route
url = "http://localhost:8000/api/v1/search?departure_station=Shin-Osaka&arrival_station=Tsuwano&departure_time=06:06&departure_date=2026-08-11"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    routes = json.loads(response.read().decode())
    
route = routes[0]
print("Route ID:", route["id"])
legs = []
for i, s in enumerate(route["segments"]):
    print(f"Segment {i}: {s['railway_name']} | Platform: {s['departure_platform']}")
    legs.append({
        "segment_index": i,
        "departure_station": route["stations"][i]["name"],
        "arrival_station": route["stations"][i+1]["name"],
        "departure_time": "10:00",
        "arrival_time": "11:00",
        "transport_name": s["railway_name"],
        "platform": int(s["departure_platform"]) if s.get("departure_platform") else None,
        "base_fare": s.get("base_fare"),
        "express_fare": s.get("express_fare")
    })

# 2. Save Movement
movement_req = {
    "route_id": route["id"],
    "selected_departure_time": "06:06",
    "selected_arrival_time": "10:00",
    "departure_station": "Shin-Osaka",
    "arrival_station": "Tsuwano",
    "notion_page_url": "https://app.notion.com/p/Suma-3b65bbf7e7bd8011974febee06cf4970?source=copy_link",
    "legs": legs
}

print("Saving Movement to Notion...")
save_req = urllib.request.Request(
    "http://localhost:8000/api/v1/movements", 
    data=json.dumps(movement_req).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(save_req) as response:
        res = json.loads(response.read().decode())
        print("Success:", res)
except urllib.error.HTTPError as e:
    print("Error:", e.read().decode())
