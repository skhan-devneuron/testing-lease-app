import json
from datetime import datetime
from typing import Dict, Any

class MessageLimiter:
    def __init__(self, limit_file: str = "messageLimits.json", daily_limit: int = 100):
        self.limit_file = limit_file
        self.daily_limit = daily_limit
    
    def load_limits(self) -> Dict[str, Any]:
        """Load message limits from JSON file"""
        try:
            with open(self.limit_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_limits(self, limits: Dict[str, Any]) -> None:
        """Save message limits to JSON file"""
        with open(self.limit_file, "w") as f:
            json.dump(limits, f)
    
    def check_message_limit(self, user_id: str) -> bool:
        """Check if user has exceeded daily message limit"""
        today = datetime.now().date().isoformat()
        limits = self.load_limits()
        
        print("limits",limits)
        
        user_data = limits.get(user_id, {"date": today, "count": 0})
        print("User Data:",user_data)
        
        if user_data["date"] != today:
            user_data = {"date": today, "count": 1}
        else:
            if user_data["count"] >= self.daily_limit:
                return False
            user_data["count"] += 1
        
        limits[user_id] = user_data
        self.save_limits(limits)
        return True
    
    def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current usage statistics for a user"""
        limits = self.load_limits()
        user_data = limits.get(user_id, {"date": datetime.now().date().isoformat(), "count": 0})
        return {
            "current_count": user_data["count"],
            "daily_limit": self.daily_limit,
            "remaining": max(0, self.daily_limit - user_data["count"]),
            "date": user_data["date"]
        } 