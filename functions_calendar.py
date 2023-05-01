# Calendar event functions for use with Home Meteogram Display Script

from datetime import timedelta
from icalevents.icalevents import events


# Generate event bar data from the events on the calendars provided by config.
def generate_event_bars(config, sun, first_time, last_time):
    print("Fetching calendar events...")
    event_bars = []
    for calendar in config["calendars"]:
        event_list = events(url=calendar["url"], start=first_time, end=last_time)
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
            # centrally-positioned text is off-screen. We actually allow a few more hours either way so that it's
            # obvious it goes off the end, but not the full event range.
            if start < first_time:
                start = first_time - timedelta(hours=3)
            if end > last_time:
                end = last_time + timedelta(hours=3)
            # Build up the list
            event_bars.append(dict(text=event.summary, start=start, end=end, color=calendar["color"]))
    return event_bars
