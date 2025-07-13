🎬 Telegram Movie Bot

A private Telegram bot built for streamlined movie sharing and management using MongoDB, Flask, and Discord logging. Hosted on Render, this bot is designed for personal use with admin-only controls, automated cleanup, and real-time activity monitoring.


---

🚀 Features

✅ Upload and manage movie files stored in MongoDB
✅ Generate private access links via /start Movie_Name
✅ Automatically delete sent files after 15 minutes
✅ Cleans up messages after restarts (post-restart cleanup)
✅ Logs movie access with usernames to Discord (blue embed)
✅ Logs admin actions like upload, delete, and rename (green embed)
✅ Logs bot status and crashes (red embed)
✅ Health check with uptime, memory, and CPU usage
✅ Broadcast announcements to all users with rate-limiting


---

🛠️ Admin Commands

Command	Description

Upload + Name	Upload a file and assign a movie name
/list_files	Lists all stored movies
/rename_file <old> <new>	Renames a movie
/delete_file <name>	Deletes a movie
/get_movie_link <name>	Generates a shareable movie link
/health	Shows bot uptime, memory, and CPU usage
/stats	Displays total movie and user count
/announce <message>	Sends a message to all users



---
