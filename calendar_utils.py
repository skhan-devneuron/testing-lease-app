from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import os
import pickle
from pytz import timezone, utc
from config import TOKEN_FILE, CREDENTIALS_FILE, DEFAULT_TIMEZONE, WORKING_HOURS, SLOT_DURATION, GOOGLE_CALENDAR_SCOPES
import abc

class BaseCalendar(abc.ABC):
    @abc.abstractmethod
    def create_event(self, start_time_str, summary, email):
        pass

    @abc.abstractmethod
    def is_time_available(self, start_time_str):
        pass

    @abc.abstractmethod
    def get_free_slots(self, date_str, tz_str=None):
        pass

class GoogleCalendar(BaseCalendar):
    def get_calendar_service(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("User not authenticated. Please visit /authorize.")
        return build("calendar", "v3", credentials=creds)

    def create_event(self, start_time_str, summary, email,description="Apartment Visit Booking"):
        service = self.get_calendar_service()
        tz = timezone(DEFAULT_TIMEZONE)
        if isinstance(start_time_str, datetime):
            start_time = start_time_str
        else:
            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")  # 24-hour
            except ValueError:
                try:
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %I:%M %p")  # 12-hour with AM/PM
                except ValueError:
                    raise ValueError(
                        "Invalid date format. Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM AM/PM'"
                    )



        start_time = tz.localize(start_time)
        end_time = start_time + timedelta(minutes=30)
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': DEFAULT_TIMEZONE,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': DEFAULT_TIMEZONE,
            },
            'attendees': [{'email': email}],
        }
        event = service.events().insert(calendarId='primary', body=event,sendUpdates='all').execute()
        print("Event URL:", event.get("htmlLink"))
        return event

    def is_time_available(self, start_time_str):
        service = self.get_calendar_service()
        tz = timezone(DEFAULT_TIMEZONE)
        if isinstance(start_time_str, datetime):
            start_time = start_time_str
        else:
            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")  # 24-hour
            except ValueError:
                try:
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %I:%M %p")  # 12-hour with AM/PM
                except ValueError:
                    raise ValueError(
                        "Invalid date format. Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM AM/PM'"
                    )
            start_time = tz.localize(start_time)
        start_utc = start_time.astimezone(utc)
        end_utc = (start_time + timedelta(minutes=30)).astimezone(utc)
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_utc.isoformat(),
            timeMax=end_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return len(events) == 0

    def get_free_slots(self, date_str, tz_str=None):
        if tz_str is None:
            tz_str = DEFAULT_TIMEZONE
        service = self.get_calendar_service()
        tz = timezone(tz_str)
        date = datetime.strptime(date_str, "%Y-%m-%d")
        start = tz.localize(date.replace(hour=WORKING_HOURS["start"], minute=0))
        end = tz.localize(date.replace(hour=WORKING_HOURS["end"], minute=0))
        body = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "timeZone": tz_str,
            "items": [{"id": "primary"}]
        }
        events = service.freebusy().query(body=body).execute()
        busy_times = events["calendars"]["primary"].get("busy", [])
        slots = []
        current = start
        while current < end:
            next_slot = current + timedelta(minutes=SLOT_DURATION)
            overlap = any(
                datetime.fromisoformat(b["start"]).astimezone(tz) < next_slot and
                datetime.fromisoformat(b["end"]).astimezone(tz) > current
                for b in busy_times
            )
            if not overlap:
                slots.append(current.strftime("%I:%M %p"))
            current = next_slot
        return slots

