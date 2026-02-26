import asyncio
import requests
from datetime import datetime, timezone, timedelta
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gmplot
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ==========================
# CONFIG
# ==========================
BOT_TOKEN = "8162737192:AAGnlssEXx-Q4O9r4dcAtgMUCqW3m81jBrc"
API_BASE = "http://195.35.8.129:8000"
DEFAULT_DEVICE = "family_default3:device_946e72"
# ==========================


def calculate_status(timestamp_str):
    """Returns status and "updated x seconds/minutes ago" text"""
    try:
        device_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = (now - device_time).total_seconds()

        status = "🟢 Online" if diff <= 30 else "🔴 Offline"

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
    """Format timestamp in IST"""
    dt = datetime.fromisoformat(ts)
    ist = dt + timedelta(hours=5, minutes=30)
    return ist.strftime("%d-%b-%Y %I:%M:%S %p IST")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 Family Tracker Bot\n\n"
        "Commands:\n"
        "/track [device] - Latest location\n"
        "/history [device] [minutes] - Show route history map"
    )


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = "context.args[0] if context.args else DEFAULT_DEVICE"
    try:
        data = await asyncio.to_thread(
            lambda: requests.get(f"{API_BASE}/latest-location/{user_id}", timeout=10).json()
        )

        if "latitude" not in data:
            await update.message.reply_text("❌ No location found.")
            return

        lat = data["latitude"]
        lon = data["longitude"]
        battery = data.get("battery", "N/A")
        timestamp = data["timestamp"]

        status, time_text = calculate_status(timestamp)

        # Battery icon
        try:
            battery_val = int(battery)
        except:
            battery_val = -1

        if battery_val >= 70:
            battery_icon = "🟢"
        elif battery_val >= 30:
            battery_icon = "🟡"
        elif battery_val >= 0:
            battery_icon = "🔴"
        else:
            battery_icon = "❌"

        # Send location pin
        await update.message.reply_location(latitude=lat, longitude=lon)

        # Send device info
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


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.args[0] if context.args else DEFAULT_DEVICE
    minutes = int(context.args[1]) if len(context.args) > 1 else 60

    try:
        r = await asyncio.to_thread(
            lambda: requests.get(f"{API_BASE}/history/{user_id}?minutes={minutes}", timeout=10).json()
        )

        if "status" in r or not r.get("points"):
            await update.message.reply_text(f"No route data for {user_id} in last {minutes} minutes")
            return

        points = r["points"]
        lats = [p["latitude"] for p in points]
        lngs = [p["longitude"] for p in points]

        # Generate GMPlot map
        gmap = gmplot.GoogleMapPlotter(lats[0], lngs[0], 15)
        gmap.plot(lats, lngs, "blue", edge_width=3)
        for i, (lat, lng, p) in enumerate(zip(lats, lngs, points)):
            time_str = format_time(p["timestamp"])
            color = "green" if i == len(lats) - 1 else "red"
            gmap.marker(lat, lng, color=color, title=time_str)

        html_file = f"{user_id}_map.html"
        img_file = f"{user_id}_map.png"
        gmap.draw(html_file)

        # Convert HTML to PNG using Selenium headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1200,800")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f"file://{os.path.abspath(html_file)}")
        await asyncio.sleep(2)  # wait for map to render
        driver.save_screenshot(img_file)
        driver.quit()

        # Send PNG to Telegram
        await update.message.reply_photo(photo=InputFile(img_file))

        # Cleanup
        os.remove(html_file)
        os.remove(img_file)

    except Exception as e:
        await update.message.reply_text(f"⚠ Error generating history map: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(CommandHandler("history", history))

    print("🤖 Tracker Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
