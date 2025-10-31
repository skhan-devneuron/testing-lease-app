import os,json
from config import CHAT_SESSIONS_FILE
def load_chat_sessions():
    if os.path.exists(CHAT_SESSIONS_FILE):
        with open(CHAT_SESSIONS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# Save chat sessions to file
def save_chat_sessions(chat_sessions):
    with open(CHAT_SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_sessions, f, indent=2)
