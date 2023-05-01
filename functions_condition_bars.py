# Condition bar calculation functions for use with Home Meteogram Display Script
import statistics
from datetime import timedelta, datetime
import pytz
from functions_weather import get_date_times, get_temperatures, get_humidities, get_precip_probs


# Cluster function used to find stormy and frosty parts of the forecast
def cluster(indices):
    if len(indices) > 0:
        groups = [[indices[0]]]
        for x in indices[1:]:
            if x - groups[-1][-1] <= 1:
                groups[-1].append(x)
            else:
                groups.append([x])
        return groups
    else:
        return []


# Given a set of indices and the full set of datetimes that the indices index, cluster the indices, then calculate an
# effective start and end time for each cluster. This goes halfway to the previous and next timestamp.
# For example, given input indices [1,2,3,7,8,9] and for simplicity, date_times [0,1,2,3,4,5,6,7,8,9,10,11]
# this function should return [{start=0.5, end=3.5}, {start=6.5, end=9.5}]
def cluster_and_get_start_end_times(indices, all_date_times):
    output = []
    clusters = cluster(indices)
    for cl in clusters:
        start_time_step = all_date_times[cl[0]] - all_date_times[cl[0] - 1] if (cl[0] != 0) else 0
        start_time = all_date_times[cl[0]] - (start_time_step / 2.0)
        end_time_step = all_date_times[cl[len(cl) - 1]] - all_date_times[cl[len(cl) - 1] + 1] if (
                cl[len(cl) - 1] < len(all_date_times) - 1) else 0
        end_time = all_date_times[cl[len(cl) - 1]] + (end_time_step / 2.0)
        output.append(dict(start=start_time, end=end_time))
    return output


# Given a set of event bars, and a new bar, count how many of the set are overlapped by the new one
def count_overlapping_bars(bars, new_bar):
    count = 0
    for test_bar in bars:
        latest_start = max(new_bar["start"], test_bar["start"])
        earliest_end = min(new_bar["end"], test_bar["end"])
        if earliest_end - latest_start > timedelta(0):
            count += 1
    return count


# Given a set of event bars, calculate how many of them are present at the given time
def count_bars_at_time(bars, time):
    return sum(1 for b in bars if b["start"] < time < b["end"])


# Given a set of event bars, calculate the maximum number of simultaneous ones, i.e. the number of
# lines that would be required to display them all without overlap
def count_max_bars_at_time(bars):
    first_event_start = min(map(lambda b: b["start"], bars))
    first_event_end = max(map(lambda b: b["end"], bars))
    duration = first_event_end - first_event_start
    hour_count = duration.days * 24 + duration.seconds // 3600
    max_simultaneous_events = 0
    for test_time in (first_event_start + timedelta(hours=n) for n in range(hour_count)):
        simultaneous_events = count_bars_at_time(bars, test_time)
        max_simultaneous_events = max(max_simultaneous_events, simultaneous_events)
    return max_simultaneous_events


# Get a list of datetime blocks that are considered stormy. A list will be returned where each
# entry is a dict with "start" and "end" datetimes provided.
def get_stormy_blocks(forecast, config):
    stormy_indices = [i for i in range(len(forecast)) if forecast[i].is_stormy(config)]
    return cluster_and_get_start_end_times(stormy_indices, get_date_times(forecast))


# Get a list of datetime blocks that are considered frosty. A list will be returned where each
# entry is a dict with "start" and "end" datetimes provided.
def get_frosty_blocks(forecast, config):
    frosty_indices = [i for i in range(len(forecast)) if forecast[i].is_frosty(config)]
    return cluster_and_get_start_end_times(frosty_indices, get_date_times(forecast))


# Generate a list of condition bars representing frosty conditions
def generate_frost_condition_bars(forecast, config):
    condition_bars = []
    for c in get_frosty_blocks(forecast, config):
        condition_bars.append(dict(text="Frost", start=c.start, end=c.end,
                                   color=config["style"]["frost_color"]))
    return condition_bars


# Generate a list of condition bars representing stormy conditions
def generate_storm_condition_bars(forecast, config):
    condition_bars = []
    for c in get_stormy_blocks(forecast, config):
        condition_bars.append(dict(text="Storm", start=c.start, end=c.end,
                                   color=config["style"]["storm_color"]))
    return condition_bars


# Generate a list of condition bars representing good laundry days
def generate_laundry_day_condition_bars(forecast, config, dates, sun):
    condition_bars = []
    print("Calculating good laundry days...")
    for day in dates:
        # Start time for laundry is sunrise or our "hanging out" time, whichever is later.
        # End time is sunset.
        laundry_start_time = max(sun.get_sunrise_time(day),
                                 pytz.utc.localize(datetime.combine(day, datetime.min.time()))
                                 + timedelta(hours=config["laundry_day"]["hang_out_time"]))
        laundry_end_time = sun.get_sunset_time(day)

        if laundry_end_time - laundry_start_time >= timedelta(hours=config["laundry_day"]["min_hours_daylight"]):
            # Enough hours daylight, extract indices during the drying period
            daytime_indices = [i for i in range(len(forecast)) if
                               laundry_start_time <= forecast[i].time <= laundry_end_time]
            if len(daytime_indices) > 0:
                mean_temp = statistics.mean([get_temperatures(forecast)[i] for i in daytime_indices])
                mean_humidity = statistics.mean([get_humidities(forecast)[i] for i in daytime_indices])
                max_precip_prob = max([get_precip_probs(forecast)[i] for i in daytime_indices])

                # Check logic for being a good laundry day. If so, add the condition bar
                if mean_temp >= config["laundry_day"]["min_average_temp"] and \
                        mean_humidity <= config["laundry_day"]["max_average_humidity"] and \
                        max_precip_prob <= config["laundry_day"]["max_precip_prob"]:
                    # Build up the list
                    condition_bars.append(dict(text="Laundry Day",
                                               start=sun.get_sunrise_time(day),
                                               end=sun.get_sunset_time(day),
                                               color=config["style"]["laundry_day_color"]))
    return condition_bars