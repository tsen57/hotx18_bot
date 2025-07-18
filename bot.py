async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    # …add handlers…
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
That block is what creates the Application, starts polling, and is wrapped in the usual
if __name__ == "__main__": … guard.
Because it used asyncio.run(), it caused the “Cannot close a running event loop” error.

The fix was to replace that entire snippet with the synchronous version:

def main() -> None:
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )
    # …add handlers…
    application.run_polling()      # blocking, no await

if __name__ == "__main__":
    main()                         # plain call, no asyncio.run
So whenever the instructions said “replace the bottom section,” they referred to everything from async def main(): down to the final if __name__ == "__main__": … block.
write me whole code fixing the runtime error
Thought for 1s
Here is a single, self-contained bot.py that eliminates the event-loop error and adds a simple, robust implementation of your bot.

Save it as bot.py (replace any existing file), keep requirements.txt with
python-telegram-bot==20.8 (or newer), push to GitHub, and redeploy on Render.

#!/usr/bin/env python3
"""
Telegram gplink bot
────────────────────────────────────────
• Anyone can send  /postno00042   (1–5 digits) and receive the link.
• Admin(s) – IDs taken from the ADMIN_IDS environment variable – can
  run        /upload <post-number> <url>
  to add or override a link.  Overrides are kept in links.json and
  survive restarts on Render.
"""

from __future__ import annotations

import json
import logging
import os
import re
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

# ─────────────── Configuration ───────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")               # required
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}                                               # "765...,123..." → {765…,123…}
BASE_URL = os.getenv("BASE_URL", "https://gplink.com/post/")
MAX_POST = int(os.getenv("MAX_POST", "10000"))   # highest post number allowed
DATA_FILE = Path("links.json")                   # persistent storage
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------- load any saved overrides ----------
try:
    LINKS: dict[int, str] = {
        int(k): v for k, v in json.loads(DATA_FILE.read_text()).items()
    }
except Exception:
    LINKS = {}


def save_links() -> None:
    """Write the LINKS dict to disk."""
    DATA_FILE.write_text(json.dumps({str(k): v for k, v in LINKS.items()}, indent=2))


def default_link(n: int) -> str:
    """Build the default gplink URL with leading zeros (5 digits)."""
    return f"{BASE_URL}{n:05d}"


# ---------- Handlers ----------
POSTNO_RE = re.compile(r"^/postno(\d{1,5})$")  # matches /postno1 … /postno99999


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi!\n"
        "• Anyone: /postno00001  → get link\n"
        "• Admin:  /upload <post> <url>  → set or override a link"
    )


async def handle_postno(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    match = POSTNO_RE.match(update.message.text.strip())
    if not match:  # should never happen; regex filter already checks the pattern
        return

    num = int(match.group(1).lstrip("0") or 0)
    if not (1 <= num <= MAX_POST):
        await update.message.reply_text(f"❌ Post number must be 1 – {MAX_POST}.")
        return

    link = LINKS.get(num, default_link(num))
    await update.message.reply_text(link)


async def cmd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 You are not authorised.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /upload <postNumber> <full_url>")
        return

    try:
        num = int(context.args[0])
    except ValueError:
        await update.message.reply_text("First argument must be digits only.")
        return

    if not (1 <= num <= MAX_POST):
        await update.message.reply_text(f"❌ Post number must be 1 – {MAX_POST}.")
        return

    LINKS[num] = context.args[1]
    save_links()
    await update.message.reply_text(f"✅ Saved custom link for post {num:05d}.")


# ---------- Main ----------
def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(MessageHandler(filters.Regex(POSTNO_RE), handle_postno))
    application.add_handler(CommandHandler("upload", cmd_upload))

    logger.info("Bot starting – polling …")
    application.run_polling()          # blocking call, no asyncio.run()


if __name__ == "__main__":
    main()
