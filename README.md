# 🎬 Telegram Movie Bot

This is a Telegram bot that automates movie file sharing using MongoDB and Flask. Designed for Terabox and Telegram workflows, this bot allows admins to manage movies, generate file links, and auto-delete sent files after 30 minutes.

---

## 🚀 Features

✅ Auto-detects and stores movie uploads from a private channel  
✅ Sends movie files only when a user clicks a link from the main channel  
✅ Automatically deletes sent movie files after 30 minutes (anti-copyright)  
✅ Admin-only access for uploading, editing, or deleting movies  
✅ MongoDB Atlas used to store movie metadata  
✅ Logs activity to Discord via webhooks  
✅ Flask-based server, deployable 24/7 on Render or Replit  

---

## 🛠️ Admin Commands

| Command                    | Description                            |
|----------------------------|----------------------------------------|
| Upload a movie file + name | Saves file message ID to MongoDB      |
| `/list_files`              | Lists all uploaded movies              |
| `/rename_file old new`     | Renames a movie                        |
| `/delete_file name`        | Deletes a movie entry                  |
| `/get_movie_link name`     | Generates clickable movie link         |

