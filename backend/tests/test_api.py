def test_search_api(client):
    response = client.get("/api/v1/search?departure_station=Tokyo&arrival_station=Kyoto")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "dummy_123"

def test_timetable_api(client):
    response = client.get("/api/v1/routes/dummy_123/timetable")
    assert response.status_code == 200
    data = response.json()
    assert data["route_id"] == "dummy_123"
    assert data["first_train"] == "05:00"

def test_movements_api(client):
    payload = {
        "route_id": "dummy_123",
        "departure_station": "Tokyo",
        "arrival_station": "Kyoto",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "12:00"
    }
    response = client.post("/api/v1/movements", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["route_id"] == "dummy_123"
    assert data["search_mode"] == "ROUTE_ONLY"

def test_station_search_api(client):
    response = client.get("/api/v1/stations/search?q=Tokyo")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
