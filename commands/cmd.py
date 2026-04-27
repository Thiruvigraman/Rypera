# file: commands/cmd.py

from bot import send_message


def handle_cmd(chat_id):
    text = (
        "📜 *Available Commands*\n\n"

        "🎬 /generate_link - Generate access link for a movie\n"
        "🗑 /delete_movie - Delete a movie from database\n"
        "✏️ /rename_file - Rename an uploaded file\n"
        "📢 /announce - Send announcement to all users\n"
        "📊 /stats - Show bot usage stats\n"
        "🏆 /top_movies - Show most accessed movies\n"
        "❤️ /health - Check bot health status\n"
        "📚 /list_movies - List all movies\n"

        "🧊 /freeze_logs [min] - Freeze logs (default 60 min)\n"
        "🔥 /unfreeze_logs - Resume logs\n"
        "⏸ /pause_logs - Disable logging\n"
        "▶️ /resume_logs - Enable logging\n"
        "📦 /log_status - Show logging status\n"
        "🧹 /clear_logs - Clear queue & failed logs\n"

        "🧾 /cmd - Show this help menu\n"
    )

    send_message(chat_id, text, parse_mode="Markdown")