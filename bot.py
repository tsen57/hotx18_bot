##########################################################################
# bot.py – Public gplink bot / anyone gets links, admins can /upload
##########################################################################
import os, json, re, asyncio, logging
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

# ───────────── reachable through ENV VARIABLES ─────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")           # REQUIRED – your BotFather token
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}                                            # admins, e.g. "7655961867"
BASE_URL  = os.getenv("BASE_URL", "https://gplink.com/post/")
MAX_POST  = int(os.getenv("MAX_POST", "10000"))
DATA_FILE = Path("links.json")               # local file for overrides
# ───────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

# –– helpers ––
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def load_links() -> dict[int, str]:
    if DATA_FILE.exists():
        try:
            return {int(k): str(v) for k, v in json.load(DATA_FILE.open()) .items()}
        except Exception as e:
            logging.error("Error loading links.json: %s", e)
    return {}

def save_links(store: dict[int, str]) -> None:
    try:
        json.dump(store, DATA_FILE.open("w"), ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error("Error saving links.json: %s", e)

LINKS_CACHE = load_links()

# –– regex patterns ––
POSTNO_RE = re.compile(r"^/postno(\d+)$")            # public
UPLOAD_RE = re.compile(r"^/upload\s+(\d+)\s+(\S+)$") # admin

# –– commands ––
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Public:\n"
        "  /postno00042  → link of post 00042\n\n"
        "Admin only:\n"
        "  /upload <post> <url> → override a link"
    )

async def postno_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = POSTNO_RE.match(update.message.text.strip())
    if not m:
        return
    num = int(m.group(1))
    if not (1 <= num <= MAX_POST):
        await update.message.reply_text(f"❌ Post number must be 1-{MAX_POST}.")
        return
    link = LINKS_CACHE.get(num) or f"{BASE_URL}{num:05d}"
    await update.message.reply_text(link)

async def upload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorised to upload.")
        return
    m = UPLOAD_RE.match(update.message.text.strip())
    if not m:
        await update.message.reply_text(
            "Format: /upload <postNumber> <full_url>\n"
            "Example: /upload 15 https://gplink.com/abc"
        )
        return
    num, url = int(m.group(1)), m.group(2)
    if not (1 <= num <= MAX_POST):
        await update.message.reply_text(f"❌ Post number must be 1-{MAX_POST}.")
        return
    LINKS_CACHE[num] = url
    save_links(LINKS_CACHE)
    await update.message.reply_text(f"✅ Saved custom link for post {num:05d}.")

# –– main ––
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var missing!")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("upload", upload_cmd))
    app.add_handler(MessageHandler(filters.Regex(POSTNO_RE), postno_handler))
    logging.info("Bot online.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
