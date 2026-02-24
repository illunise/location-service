import gmplot
import requests
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes, CallbackContext,
)

# ==========================
# CONFIG
# ==========================
BOT_TOKEN = "8162737192:AAGnlssEXx-Q4O9r4dcAtgMUCqW3m81jBrc"
API_BASE = "http://195.35.8.129:8000"
DEFAULT_DEVICE = "manish_phone"
# ==========================


def calculate_status(timestamp_str):
    """
    Returns:
        status_text
        time_text
    """
    try:
        device_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        diff = (now - device_time).total_seconds()

        # Online logic
        if diff <= 30:
            status = "🟢 Online"
        else:
            status = "🔴 Offline"

        # Time ago formatting
        if diff < 60:
            time_text = f"{int(diff)} seconds ago"
        elif diff < 3600:
            time_text = f"{int(diff // 60)} minutes ago"
        else:
            time_text = f"{int(diff // 3600)} hours ago"

        return status, time_text

    except Exception:
        return "Unknown", "Unknown"

def format_time(ts: str):
    dt = datetime.fromisoformat(ts)
    # IST timezone (+5:30)
    ist = dt + timedelta(hours=5, minutes=30)
    return ist.strftime("%d-%b-%Y %I:%M:%S %p IST")


def route_map(update: Update, context: CallbackContext):
    user_id = context.args[0] if context.args else None
    minutes = int(context.args[1]) if len(context.args) > 1 else 60

    if not user_id:
        update.message.reply_text("Usage: /historymap <user_id> [minutes]")
        return

    # Fetch history
    r = requests.get(f"{API_BASE}/history/{user_id}?minutes={minutes}").json()
    if "status" in r:
        update.message.reply_text(f"No route data for {user_id} in last {minutes} minutes")
        return

    points = r["points"]

    # Extract coordinates
    lats = [p["latitude"] for p in points]
    lngs = [p["longitude"] for p in points]

    if not lats or not lngs:
        update.message.reply_text("No coordinates found.")
        return

    # Create GMPlot map centered at first point
    gmap = gmplot.GoogleMapPlotter(lats[0], lngs[0], 15)

    # Draw route polyline
    gmap.plot(lats, lngs, "blue", edge_width=3)

    # Add markers
    for i, (lat, lng, p) in enumerate(zip(lats, lngs, points)):
        time_str = format_time(p["timestamp"])
        color = "green" if i == len(lats) - 1 else "red"  # last = current
        gmap.marker(lat, lng, color=color, title=time_str)

    # Save HTML map
    html_file = f"{user_id}_map.html"
    gmap.draw(html_file)

    # Convert HTML map to image (via web rendering)
    # For simplicity, use web browser screenshot or third-party tool
    # Here we just send HTML (can open in browser)
    update.message.reply_text(f"Map generated: open {html_file} in browser")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 Family Tracker Bot\n\n"
        "Use /track to get latest device location."
    )


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Allow: /track or /track device_name
    if context.args:
        user_id = context.args[0]
    else:
        user_id = DEFAULT_DEVICE

    try:
        response = requests.get(
            f"{API_BASE}/latest-location/{user_id}",
            timeout=10
        )
        data = response.json()

        if "latitude" not in data:
            await update.message.reply_text("❌ No location found.")
            return

        lat = data["latitude"]
        lon = data["longitude"]
        battery = data.get("battery", "N/A")
        timestamp = data["timestamp"]

        status, time_text = calculate_status(timestamp)

        # Send live map pin
        await update.message.reply_location(latitude=lat, longitude=lon)

        # Send device info
        if battery >= 70:
            battery_icon = "🟢"
        elif battery >= 30:
            battery_icon = "🟡"
        else:
            battery_icon = "🔴"

        message = (
            "━━━━━━━━━━━━━━━\n"
            "📍 <b>LIVE TRACKING STATUS</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            f"📱 <b>Device:</b> {user_id}\n"
            f"{status}\n"
            f"{battery_icon} <b>Battery:</b> {battery}%\n"
            f"⏱ <b>Updated:</b> {time_text}\n\n"
            "━━━━━━━━━━━━━━━"
        )

        await update.message.reply_text(message, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"⚠ Error: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(CommandHandler("history", route_map()))

    print("🤖 Tracker Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
