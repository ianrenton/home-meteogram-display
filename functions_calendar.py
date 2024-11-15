# Calendar event functions for use with Home Meteogram Display Script

import re
import urllib.request
from datetime import timedelta
from icalevents.icalevents import events


# Generate event bar data from the events on the calendars provided by config.
def generate_event_bars(config, sun, first_time, last_time):
    event_bars = []
    for calendar in config["calendars"]:
        # Fetch the iCal data
        with urllib.request.urlopen(calendar["url"]) as response:
            ical_content = response.read().decode("utf-8")

            # Fudge the "UNTIL" timezone to UTC if it's missing, in certain Nextcloud calendars.
            if "nextcloud_until_timezone_fix" in calendar and calendar["nextcloud_until_timezone_fix"] :
                ical_content = re.sub(r'(UNTIL=[0-9]{8}T[0-9]{6})', "\1Z", ical_content, flags=re.MULTILINE)
            ical_content_bytes = ical_content.encode("utf-8")

            # Extract events from the iCal data
            event_list = events(string_content=ical_content_bytes, start=first_time, end=last_time + timedelta(days=1))
            for event in event_list:
                start = event.start
                end = event.end
                # For all-day events, constrain to sunrise/sunset time. Silly but it makes it look nicer when it lines up.
                # We subtract an hour from the end date because it will come through as 00:00 (next day) and we don't want
                # the event to span an extra day.
                if event.all_day:
                    start = sun.get_sunrise_time(event.start.date())
                    end = sun.get_sunset_time((event.end - timedelta(hours=1)).date())
                # Constrain events to the scope of the meteogram, so that long-running events aren't so wide that their
                # centrally-positioned text is off-screen.
                start = max(start, first_time)
                end = min(end, last_time)
                # Build up the list. Ignore any events that are currently off the chart.
                if start < last_time and end > first_time:
                    event_bars.append(dict(text=event.summary, start=start, end=end, color=calendar["color"]))
    return event_bars
