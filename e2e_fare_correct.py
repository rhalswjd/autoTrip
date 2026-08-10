import urllib.request
import json
import os

url = "http://localhost:8000/api/v1/search?departure_station=Shin-Osaka&arrival_station=Tsuwano&departure_time=06:06&departure_date=2026-08-11"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    routes = json.loads(response.read().decode())
    
route = routes[0]

# For Shin-Osaka -> Shin-Yamaguchi (Sakura 741)
leg0_dep_time = "06:06" # We know it from the route, wait, the API does not return leg departure time unless we query timetable. Let's just use 06:06 for Leg0 and 08:52 for Leg 1 (Super Oki 2 departs at 08:52!)
leg1_dep_time = "08:52"

legs = []
for i, s in enumerate(route["segments"]):
    d_time = leg0_dep_time if i == 0 else leg1_dep_time
    legs.append({
        "segment_index": i,
        "departure_station": route["stations"][i]["name"],
        "arrival_station": route["stations"][i+1]["name"],
        "departure_time": d_time,
        "arrival_time": "11:00", # Fake arrival is fine
        "transport_name": s["railway_name"],
        "platform": int(s["departure_platform"]) if s.get("departure_platform") else None,
        "base_fare": s.get("base_fare"),
        "express_fare": s.get("express_fare")
    })

movement_req = {
    "route_id": route["id"],
    "selected_departure_time": "06:06",
    "selected_arrival_time": "11:00",
    "departure_station": "Shin-Osaka",
    "arrival_station": "Tsuwano",
    "search_date": "2026-08-11",
    "notion_page_url": "https://app.notion.com/p/Suma-3b65bbf7e7bd8011974febee06cf4970?source=copy_link",
    "legs": legs
}

save_req = urllib.request.Request(
    "http://localhost:8000/api/v1/movements", 
    data=json.dumps(movement_req).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(save_req) as response:
        res = json.loads(response.read().decode())
        print(f"Parent Total Fare: {route['total_fare']}")
        child_ids = res["child_page_ids"]
        for i, c_id in enumerate(child_ids):
            notion_req = urllib.request.Request(
                f"https://api.notion.com/v1/pages/{c_id}",
                headers={
                    "Authorization": f"Bearer {os.environ.get('NOTION_TOKEN')}",
                    "Notion-Version": "2022-06-28"
                }
            )
            with urllib.request.urlopen(notion_req) as notion_res:
                page_data = json.loads(notion_res.read().decode())
                fare_prop = page_data["properties"].get("Fare", {}).get("number")
                print(f"Leg {i+1} ({legs[i]['transport_name']}) independent fare (from Notion):", fare_prop)

except Exception as e:
    print("Error:", e)
