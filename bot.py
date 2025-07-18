#############################################################################
# bot.py – Telegram bot that sends gplink links for a requested range
#############################################################################
import re, asyncio, os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ──────────── CONFIG ────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")          # set later in Render
BASE_URL  = "https://gplink.com/post/"      # change if you use a different site
MAX_POST  = 10000                           # highest post number allowed
# ────────────────────────────────

RANGE_CMD = re.compile(r"^/postnumber(\d+)-(\d+)$")  # e.g. /postnumber00001-00200

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Respond to /start with usage instructions."""
    await update.message.reply_text(
        "Welcome! Send a command like:\n"
        "/postnumber00001-00010\n"
        "and I will return the matching gplink URLs."
    )

def make_link(n: int) -> str:
    """Convert 42 → https://gplink.com/post/00042 (always 5 digits)."""
    return f"{BASE_URL}{n:05d}"

async def postnumber_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /postnumber00001-00050."""
    text = update.message.text.strip()
    m = RANGE_CMD.match(text)
    if not m:
        await update.message.reply_text("❌ Wrong format. Try /postnumber00001-00010")
        return

    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        start, end = end, start            # swap so we always count up
    if end > MAX_POST:
        await update.message.reply_text(f"❌ Max allowed is {MAX_POST}.")
        return

    # Build links in safe-size chunks (Telegram hard limit 4096 chars / message)
    chunk, length = [], 0
    for n in range(start, end + 1):
        link = make_link(n)
        if length + len(link) + 1 > 4000:
            await update.message.reply_text("\n".join(chunk))
            chunk, length = [], 0
        chunk.append(link)
        length += len(link) + 1
    if chunk:
        await update.message.reply_text("\n".join(chunk))

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("postnumber", postnumber_cmd))
    print("✅ Bot is running (polling).")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
