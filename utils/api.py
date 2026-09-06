import aiohttp
import ssl
import json
from datetime import datetime

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

TIMETABLE_URL = "https://iot.spyc.hk/timetable"
EVENTS_URL = "https://iot.spyc.hk/event-schedule"

class SPYCAPI:
    def __init__(self):
        self.session = None
        self._timetable_cache = None
        self._events_cache = None
        self._cache_time = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_timetable(self):
        """Fetch timetable data from SPYC IoT"""
        try:
            session = await self._get_session()
            async with session.get(TIMETABLE_URL, ssl=SSL_CONTEXT) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._timetable_cache = data
                    return data
                else:
                    return None
        except Exception as e:
            print(f"Error fetching timetable: {e}")
            return self._timetable_cache  # Return cached if available

    async def fetch_events(self):
        """Fetch events data from SPYC IoT"""
        try:
            session = await self._get_session()
            async with session.get(EVENTS_URL, ssl=SSL_CONTEXT) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        self._events_cache = data["rows"]
                        return data["rows"]
                    return None
                else:
                    return None
        except Exception as e:
            print(f"Error fetching events: {e}")
            return self._events_cache

    async def get_today_info(self):
        """Get today's cycle day from events"""
        events = await self.fetch_events()
        if not events:
            return None

        today = datetime.now().strftime("%-d/%-m/%Y")  # e.g. "5/9/2026"
        # Try different date formats
        today_alt = datetime.now().strftime("%d/%m/%Y")
        today_alt2 = datetime.now().strftime("%-d/%-m/%Y")

        for date_key in events:
            if date_key in [today, today_alt, today_alt2]:
                return events[date_key]

        # If exact match fails, try to find closest date
        return None

    async def get_class_timetable(self, class_name, day):
        """Get timetable for specific class and day"""
        timetable = await self.fetch_timetable()
        if not timetable:
            return None

        class_name = class_name.upper()
        day = day.upper()

        if class_name not in timetable:
            return None

        if day not in timetable[class_name]:
            return None

        return timetable[class_name][day]

    async def get_day_events(self, date_str=None):
        """Get events for a specific date"""
        events = await self.fetch_events()
        if not events:
            return None

        if date_str is None:
            date_str = datetime.now().strftime("%-d/%-m/%Y")

        return events.get(date_str)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
