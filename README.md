# 🎬 Telegram Movie Bot  

This is a **Telegram bot** that automates movie file sharing via a **main channel** and a **private storage channel**.  
Users click a movie link in the main channel, visit **ModijiURL**, and receive the correct movie file automatically.  

---

## 🚀 Features  
✅ **Auto-detects movie uploads** in the private channel and stores message IDs.  
✅ **Sends the correct movie file** when a user clicks the main channel link.  
✅ **Deletes the file** from the user's chat after **30 minutes**.  
✅ **Admin-only movie management** (edit/delete).  
✅ **Runs 24/7** on **Render** with **BetterStack monitoring**.  

---

## 📂 Files in This Repository  
| File Name       | Description |
|----------------|-------------|
| `main.py`       | Main bot script |
| `movies.json`   | Stores movie message IDs |
| `requirements.txt` | Python dependencies |
| `README.md`    | This documentation |

---

## 🔧 How to Deploy on Render  
### 1️⃣ **Upload Your Bot to GitHub**  
- Clone this repo:  
  ```bash
  git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
  cd YOUR_REPO