import asyncio
import json
import ssl
from urllib.request import Request, urlopen
from datetime import datetime, timedelta

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

TIMETABLE_URL = "https://iot.spyc.hk/timetable"
EVENTS_URL = "https://iot.spyc.hk/event-schedule"

def _fmt_date(dt):
    """Format date as D/M/YYYY (cross-platform)"""
    return f"{dt.day}/{dt.month}/{dt.year}"

class SPYCAPI:
    def __init__(self):
        self.session = None
        self._timetable_cache = None
        self._events_cache = None
        self._cache_time = None
    
    async def _get_session(self):
        return self.session

    async def _get_json(self, url):
        def request():
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, context=SSL_CONTEXT) as response:
                if response.status != 200:
                    return None
                return json.loads(response.read().decode("utf-8"))

        return await asyncio.to_thread(request)
    
    async def fetch_timetable(self):
        """Fetch timetable data from SPYC IoT"""
        try:
            data = await self._get_json(TIMETABLE_URL)
            if data is not None:
                self._timetable_cache = data
            return data
        except Exception as e:
            print(f"Error fetching timetable: {e}")
            return self._timetable_cache
    
    async def fetch_events(self):
        """Fetch events data from SPYC IoT"""
        try:
            data = await self._get_json(EVENTS_URL)
            if isinstance(data, dict) and data.get("success") and "rows" in data:
                self._events_cache = data["rows"]
                return self._events_cache
            return self._events_cache
        except Exception as e:
            print(f"Error fetching events: {e}")
            return self._events_cache
    
    async def get_date_info(self, date_str):
        """Get info for a specific date string (D/M/YYYY)"""
        events = await self.fetch_events()
        if not events:
            return None
        return events.get(date_str)
    
    async def get_today_info(self):
        """Get today's cycle day from events"""
        today = _fmt_date(datetime.now())
        return await self.get_date_info(today)
    
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
        if date_str is None:
            date_str = _fmt_date(datetime.now())
        
        events = await self.fetch_events()
        if not events:
            return None
        
        return events.get(date_str)
    
    async def close(self):
        self.session = None