from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi.responses import HTMLResponse

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
    battery: int


@app.post("/update-location")
def update_location(loc: Location):
    timestamp = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "INSERT INTO locations (user_id, latitude, longitude, timestamp, battery) VALUES (?, ?, ?, ?, ?)",
        (loc.user_id, loc.latitude, loc.longitude, timestamp, loc.battery)
    )
    conn.commit()

    return {"status": "success"}


@app.get("/latest-location/{user_id}")
def get_latest_location(user_id: str):
    cursor.execute(
        """
        SELECT latitude, longitude, timestamp, battery
        FROM locations
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        return {
            "latitude": row[0],
            "longitude": row[1],
            "timestamp": row[2],
            "battery": row[3]
        }

    return {"status": "not found"}


@app.get("/locations")
def get_locations():
    cursor.execute("""
        SELECT user_id, latitude, longitude, timestamp, battery
        FROM locations
        ORDER BY id DESC
    """)

    result = cursor.fetchall()
    latest = {}

    for row in result:
        user_id, latitude, longitude, timestamp, battery = row

        if user_id not in latest:
            latest[user_id] = {
                "user_id": user_id,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": timestamp,
                "battery": battery
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
    
    async function loadHistory() {

    const response = await fetch("/history/manish_phone?minutes=60");
    const data = await response.json();

    if (!data.points) return;

    const path = data.points.map(p => ({
        lat: p.latitude,
        lng: p.longitude
    }));

    const routeLine = new google.maps.Polyline({
        path: path,
        geodesic: true,
        strokeColor: "#007bff",
        strokeOpacity: 1.0,
        strokeWeight: 4,
    });

    routeLine.setMap(map);
}

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
                            const marker = new google.maps.Marker({
                                position: position,
                                map: map,
                                title: device.user_id
                            });

                            const dateObj = new Date(device.timestamp);
const now = new Date();

loadHistory();


// Calculate difference in seconds
const diffSeconds = Math.floor((now - dateObj) / 1000);

let timeText;
if (diffSeconds < 60) {
    timeText = diffSeconds + " seconds ago";
} else if (diffSeconds < 3600) {
    timeText = Math.floor(diffSeconds / 60) + " minutes ago";
} else {
    timeText = Math.floor(diffSeconds / 3600) + " hours ago";
}

// Device status logic
let statusText;
let statusColor;

if (diffSeconds <= 30) {
    statusText = "Online";
    statusColor = "green";
} else {
    statusText = "Offline";
    statusColor = "red";
}

const infoWindow = new google.maps.InfoWindow({
    content: `
        <b>${device.user_id}</b><br>
        Status: <span style="color:${statusColor}; font-weight:bold;">
            ${statusText}
        </span><br>
        Battery: 🔋 ${device.battery}%<br>
        Updated: ${timeText}
    `
});


marker.addListener("click", function() {
    infoWindow.open(map, marker);
});

markers[device.user_id] = marker;

                        }
                    });
                });
        }

        window.onload = initMap;
    </script>
</body>
</html>
"""

@app.get("/history/{user_id}")
def get_history(user_id: str, minutes: int = 60):

    cursor.execute(
        """
        SELECT latitude, longitude, timestamp
        FROM locations
        WHERE user_id = ?
        AND timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
        """,
        (user_id, f'-{minutes} minutes')
    )

    rows = cursor.fetchall()

    if not rows:
        return {"status": "no data"}

    return {
        "points": [
            {
                "latitude": r[0],
                "longitude": r[1],
                "timestamp": r[2]
            }
            for r in rows
        ]
    }