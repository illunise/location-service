from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from fastapi.responses import HTMLResponse
from sqlalchemy import text

app = FastAPI()

# Create DB
conn = sqlite3.connect("locations.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    latitude REAL,
    longitude REAL,
    timestamp TEXT
)
""")
conn.commit()


class Location(BaseModel):
    user_id: str
    latitude: float
    longitude: float


@app.post("/update-location")
def update_location(loc: Location):
    timestamp = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO locations (user_id, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)",
        (loc.user_id, loc.latitude, loc.longitude, timestamp)
    )
    conn.commit()

    return {"status": "success"}


@app.get("/latest-location/{user_id}")
def get_latest_location(user_id: str):
    cursor.execute(
        "SELECT latitude, longitude, timestamp FROM locations WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        return {
            "latitude": row[0],
            "longitude": row[1],
            "timestamp": row[2]
        }

    return {"status": "not found"}

@app.get("/locations")
def get_locations():
    query = text("""
        SELECT user_id, latitude, longitude, created_at
        FROM locations
        ORDER BY created_at DESC
    """)

    result = cursor.execute(query).fetchall()

    latest = {}
    for row in result:
        if row.user_id not in latest:
            latest[row.user_id] = {
                "user_id": row.user_id,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "created_at": str(row.created_at)
            }

    return list(latest.values())


@app.get("/map", response_class=HTMLResponse)
def map_view():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Family Safety Map</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://maps.googleapis.com/maps/api/js"></script>
    </head>
    <body>
        <h2>Live Location Tracking</h2>
        <div id="map" style="height: 90vh; width: 100%;"></div>

        <script>
            let map;
            let markers = {};

            function initMap() {
                map = new google.maps.Map(document.getElementById("map"), {
                    zoom: 15,
                    center: { lat: 20.5937, lng: 78.9629 }
                });

                fetchLocations();
                setInterval(fetchLocations, 5000);
            }

            function fetchLocations() {
                fetch("/locations")
                    .then(response => response.json())
                    .then(data => {
                        data.forEach(device => {
                            const position = {
                                lat: device.latitude,
                                lng: device.longitude
                            };

                            if (markers[device.user_id]) {
                                markers[device.user_id].setPosition(position);
                            } else {
                                markers[device.user_id] = new google.maps.Marker({
                                    position: position,
                                    map: map,
                                    title: device.user_id
                                });
                            }

                            map.setCenter(position);
                        });
                    });
            }

            window.onload = initMap;
        </script>
    </body>
    </html>
    """
