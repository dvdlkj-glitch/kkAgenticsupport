"""Telegram bot front-end for kkAgentic Support.

Every message is sent through the same pipeline (router -> answer).
The last routed project per chat is remembered so follow-up questions stay
on the same project.

Run:
    python -m telegram_bot.bot
"""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core import db, pipeline
from core.config import settings

WELCOME = (
    "👋 Hi! I'm your project support assistant.\n\n"
    "Just ask a question and I'll figure out which project it's about, then answer it.\n"
    "Commands:\n"
    "/projects — list the projects I support\n"
    "/reset — forget the current project context"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)


async def list_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        projects = db.get_active_projects()
    except Exception as e:  # pragma: no cover
        await update.message.reply_text(f"Couldn't load projects: {e}")
        return
    if not projects:
        await update.message.reply_text("No projects are configured yet.")
        return
    lines = [f"• *{p['name']}* — {p['description']}" for p in projects]
    await update.message.reply_text(
        "I currently support:\n" + "\n".join(lines), parse_mode="Markdown"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data.pop("project_key", None)
    await update.message.reply_text("Context cleared. Ask me anything.")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = update.message.text
    chat_id = str(update.effective_chat.id)
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    last_project = context.chat_data.get("project_key")
    try:
        result = pipeline.handle_question(
            question,
            channel="telegram",
            user_ref=chat_id,
            context_project_key=last_project,
        )
    except Exception as e:  # pragma: no cover
        await update.message.reply_text(f"⚠️ Something went wrong: {e}")
        return

    if result["project_key"]:
        context.chat_data["project_key"] = result["project_key"]

    text = result["answer"]
    if result["project_name"] and not result["needs_clarification"]:
        text = f"*{result['project_name']}*\n\n{text}"
        if result["sources"]:
            text += "\n\n_Sources: " + ", ".join(result["sources"]) + "_"

    await update.message.reply_text(text, parse_mode="Markdown")


def main() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("projects", list_projects))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("kkAgentic Support — Telegram bot running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
