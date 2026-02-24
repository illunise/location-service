import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
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

    print("🤖 Tracker Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
