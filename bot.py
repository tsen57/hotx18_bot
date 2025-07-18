#!/usr/bin/env python3
"""
Telegram gplink bot

• Anyone:  /postno00042  → receives the link
• Admin-only (ID 7655961867):  /upload <post> <url>  → adds/overrides link
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─── Configuration ──────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")                    # required
ADMIN_IDS = {7655961867}                              # <<<< your ID here
# (You can still add more admins via ENV: EXTRA_ADMINS="123,456")
EXTRA_ADMINS = os.getenv("EXTRA_ADMINS", "")
ADMIN_IDS.update(int(x) for x in EXTRA_ADMINS.split(",") if x.isdigit())

BASE_URL = os.getenv("BASE_URL", "https://gplink.com/post/")
MAX_POST = int(os.getenv("MAX_POST", "10000"))
DATA_FILE = Path("links.json")                        # persistent file
# ────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# ---- load overrides ----
try:
    LINKS: dict[int, str] = {
        int(k): v for k, v in json.loads(DATA_FILE.read_text()).items()
    }
except Exception:
    LINKS = {}


def save_links() -> None:
    DATA_FILE.write_text(json.dumps({str(k): v for k, v in LINKS.items()}, indent=2))


def default_link(n: int) -> str:
    return f"{BASE_URL}{n:05d}"


# ---- handlers ----
POSTNO_RE = re.compile(r"^/postno(\d{1,5})$")  # 1–5 digits


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi!\n"
        "• Anyone: /postno00001  → get link\n"
        "• Admin:  /upload <post> <url>  → set/override link"
    )


async def handle_postno(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    m = POSTNO_RE.match(update.message.text.strip())
    if not m:
        return
    num = int(m.group(1).lstrip("0") or 0)
    if not (1 <= num <= MAX_POST):
        await update.message.reply_text(f"❌ Post must be 1–{MAX_POST}.")
        return
    await update.message.reply_text(LINKS.get(num, default_link(num)))


async def upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 You are not authorised.")
        return
    if len(ctx.args) != 2:
        await update.message.reply_text("Usage: /upload <postNumber> <full_url>")
        return
    try:
        num = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("First arg must be digits."); return
    if not (1 <= num <= MAX_POST):
        await update.message.reply_text(f"❌ Post must be 1–{MAX_POST}."); return
    LINKS[num] = ctx.args[1]
    save_links()
    await update.message.reply_text(f"✅ Saved custom link for post {num:05d}.")


# ---- tiny web server (for Render free plan) ----
def _start_health_server() -> None:
    port = int(os.getenv("PORT", "8080"))

    class Ping(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *_):  # silence default logging
            return

    logging.info("Health server listening on port %s", port)
    HTTPServer(("0.0.0.0", port), Ping).serve_forever()


# ---- main ----
def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env variable missing.")

    # background health-check server
    threading.Thread(target=_start_health_server, daemon=True).start()

    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(MessageHandler(filters.Regex(POSTNO_RE), handle_postno))

    logging.info("Bot running – polling …")
    app.run_polling()              # blocks forever


if __name__ == "__main__":
    main()
