from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime

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
