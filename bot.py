import os
import re
import asyncio
import instaloader
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from keep_alive import keep_alive


# Try fetching from environment first, or replace the "" with your actual strings
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
IG_USERNAME = os.getenv("IG_USERNAME", "YOUR_IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD", "YOUR_IG_PASSWORD")

L = instaloader.Instaloader(
    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    request_timeout=30.0,
    max_connection_attempts=1,
)

# Instagram login
if IG_USERNAME and IG_PASSWORD and IG_USERNAME != "YOUR_IG_USERNAME":
    try:
        print(f"Loading session for {IG_USERNAME}...")
        L.load_session_from_file(IG_USERNAME)
        print("Session loaded successfully!")
    except FileNotFoundError:
        try:
            print(f"No session found. Logging in to Instagram as {IG_USERNAME}...")
            L.login(IG_USERNAME, IG_PASSWORD)
            L.save_session_to_file()
            print("Login successful and session saved!")
        except Exception as e:
            print(f"Instagram Login Failed: {e}")
    except Exception as e:
        print(f"Could not load session: {e}")



def escape_html(text: str) -> str:
    """Escape special HTML characters for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetch_profile(username: str):
    """Synchronous function to fetch an Instagram profile (runs in a thread)."""
    profile = instaloader.Profile.from_username(L.context, username)
    return profile.biography


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me Instagram usernames (one per line) and I'll extract emails & phone numbers from their bios."
    )


async def handle_usernames(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Split by lines and remove empty strings/whitespace, strip @ prefix
    usernames = [u.strip().lstrip("@") for u in text.splitlines() if u.strip()]

    if not usernames:
        await update.message.reply_text("No valid usernames found. Please try again.")
        return

    # Notify user that processing has started
    status_msg = await update.message.reply_text(
        f"⏳ Processing {len(usernames)} username(s)... This might take a while."
    )

    result = ""
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_regex = r'\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}'

    for i, username in enumerate(usernames):
        safe_username = escape_html(username)
        try:
            # Run blocking instaloader call in a thread so the bot doesn't freeze
            bio = await asyncio.to_thread(fetch_profile, username)
            safe_bio = escape_html(bio) if bio else ""

            emails = list(set(re.findall(email_regex, bio)))
            phones = list(set(re.findall(phone_regex, bio)))

            result += f"👤 <b>{safe_username}</b>\n"

            if emails or phones:
                if emails:
                    result += f"📧 Emails: {', '.join(escape_html(e) for e in emails)}\n"
                if phones:
                    result += f"📞 Phones: {', '.join(escape_html(p) for p in phones)}\n"
            else:
                result += "⚠️ No contact info found in bio.\n"

            result += "\n"

        except instaloader.exceptions.ProfileNotExistsException:
            result += f"❌ <b>{safe_username}</b> — Profile does not exist.\n\n"
        except instaloader.exceptions.ConnectionException as e:
            result += f"❌ <b>{safe_username}</b> — Rate-limited or connection error.\n\n"
            print(f"Connection error for {username}: {e}")
        except Exception as e:
            result += f"❌ <b>{safe_username}</b> — Could not fetch (private or error).\n\n"
            print(f"Error fetching {username}: {e}")

        # Sleep between requests to reduce rate-limiting risk
        # Increased to 7 seconds to prevent 429 blocks from Instagram
        if i < len(usernames) - 1:
            await asyncio.sleep(7)

    # Clean up status message
    try:
        await status_msg.delete()
    except Exception:
        pass  # Ignore if we can't delete (permissions etc.)

    # Handle empty result
    if not result.strip():
        await update.message.reply_text("No results to display.")
        return

    # Send in chunks to avoid Telegram's 4096 character limit
    max_length = 4000
    for i in range(0, len(result), max_length):
        chunk = result[i:i + max_length]
        await update.message.reply_text(chunk, parse_mode="HTML")


def main():
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or not BOT_TOKEN:
        print("CRITICAL: You must provide a valid BOT_TOKEN.")
        print("Set BOT_TOKEN as an environment variable or edit the script directly.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_usernames))

    print("✅ Telegram bot is running polling...")
    app.run_polling()


if __name__ == "__main__":
    keep_alive()
    main()
