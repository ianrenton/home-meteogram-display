# Python Met Office Meteogram Script
# by Ian Renton, April 2023
# https://github.com/ianrenton/python-metoffice-meteogram
# See README for instructions.

# ## IMPORTS

import json
import pathlib
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta

import PIL.Image
import plotly.graph_objects as go
import plotly.subplots
import pytz
import suntime
import yaml
from icalevents.icalevents import events

# ## DEFINES

# Mapping of Met Office weather code (index 0-30) to icon file we will use to display it.
WEATHER_ICON_LOOKUP = ["weather-clear-night.png", "weather-clear.png", "weather-few-clouds-night.png",
                       "weather-few-clouds.png", "", "weather-fog.png", "weather-fog.png", "weather-overcast.png",
                       "weather-overcast.png", "weather-showers-scattered.png", "weather-showers-scattered.png",
                       "weather-showers-scattered.png", "weather-showers-scattered.png", "weather-showers.png",
                       "weather-showers.png", "weather-showers.png", "weather-showers-scattered.png",
                       "weather-showers-scattered.png", "weather-showers.png", "weather-storm.png", "weather-storm.png",
                       "weather-storm.png", "weather-snow.png", "weather-snow.png", "weather-snow.png",
                       "weather-snow.png", "weather-snow.png", "weather-snow.png", "weather-storm.png",
                       "weather-storm.png", "weather-storm.png"]


# ## FUNCTION DEFINITIONS

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
# effective start and end time for each cluster. This goes halfway to the previous and next clusters.
# For example, given input indices [1,2,3,7,8,9] and for simplicity, date_times [0,1,2,3,4,5,6,7,8,9,10,11]
# this function should return [[0.5,3.5], [6.5,9.5]]
def cluster_and_get_start_end_times(indices, all_date_times):
    output = []
    time_step = all_date_times[1] - all_date_times[0]
    clusters = cluster(indices)
    for cl in clusters:
        start_time = all_date_times[cl[0]] - (time_step / 2.0)
        end_time = all_date_times[cl[len(cl) - 1]] + (time_step / 2.0)
        output.append([start_time, end_time])
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


# ## MAIN PROGRAM CODE

# Prepare data storage
dates = []
date_times = []
temperatures = []
feels_likes = []
precip_probs = []
wind_speeds = []
wind_gusts = []
wind_dirs = []
humidities = []
weather_codes = []
condition_bars = []
event_bars = []

# Load config
print("Loading configuration...")
config_file = pathlib.Path("config.yml")
if not config_file.exists():
    print(
        "The config.yml file does not exist. You will need to create this by copying config.yml.example and filling"
        "in the required parameters. See the README for more information.")
    sys.exit(1)

with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

if not config["met_office_api"]["key"]:
    print("Your Met Office Datapoint API key is not set. Copy the 'config.yml.example' file to 'config.yml' and "
          "insert your key. Then try running this software again.")
    sys.exit(1)

# Build API URL
api_url = "http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/" + str(
    config["met_office_api"]["location_code"]) + "?res=3hourly&key=" + config["met_office_api"]["key"]

# Check if we already fetched data recently
read_from_file = False
data_json = ""
cache_file = pathlib.Path(config["files"]["cache_file_name"])
if cache_file.exists() and datetime.fromtimestamp(
        cache_file.stat().st_mtime) > datetime.now() - timedelta(minutes=10):
    # Already got recent data, so use it if possible
    print("Weather cache file was updated less than 10 minutes ago, re-using that to spare the API...")
    data_json = cache_file.read_text()
    if data_json:
        read_from_file = True
    else:
        print("Tried and failed to read cache file, will query API instead.")
if not read_from_file:
    # Didn't have recent cached data so query the API for new data
    print("Querying weather API...")
    data_json = urllib.request.urlopen(api_url).read()
    if data_json:
        print("Writing local cache file...")
        cache_file.write_text(json.dumps(json.loads(data_json)))
    else:
        print(
            "Could not query the Met Office Datapoint API. Check your API key is correct and that you have internet"
            "connectivity.")
        sys.exit(1)
weather_data = json.loads(data_json)

# Parse weather API data into useful forms for plotting.
# See https://www.metoffice.gov.uk/binaries/content/assets/metofficegovuk/pdf/data/datapoint_api_reference.pdf
# for format data and examples.
print("Extracting weather data...")
latitude = float(weather_data["SiteRep"]["DV"]["Location"]["lat"])
longitude = float(weather_data["SiteRep"]["DV"]["Location"]["lon"])
day_list = weather_data["SiteRep"]["DV"]["Location"]["Period"]

# Iterate over the days in the data
for day in day_list:
    date = pytz.utc.localize(datetime.strptime(day["value"], "%Y-%m-%dZ"))
    dates.append(date)
    # Iterate over the reported forecast points in the day's data
    rep_list = day["Rep"]
    for rep in rep_list:
        time_mins = rep["$"]
        dateTime = date + timedelta(minutes=int(time_mins))
        date_times.append(dateTime)
        temp = rep["T"]
        temperatures.append(int(temp))
        feels_like = rep["F"]
        feels_likes.append(int(temp))
        precip_prob = rep["Pp"]
        precip_probs.append(int(precip_prob))
        wind_speed = rep["S"]
        wind_speeds.append(int(wind_speed))
        wind_gust = rep["G"]
        wind_gusts.append(int(wind_gust))
        wind_dir = rep["D"]
        wind_dirs.append(wind_dir)
        humidity = rep["H"]
        humidities.append(int(humidity))
        weather_code = rep["W"]
        weather_codes.append(int(weather_code))

first_time = date_times[0]
last_time = date_times[len(date_times) - 1]

# Create a suntime object, we will need this later
sun = suntime.Sun(latitude, longitude)

# Figure out which extra lines should be enabled
show_weather_icons = config["enable_features"]["weather_icons"]
show_condition_bars = config["enable_features"]["condition_bars"]
show_calendar_events = config["enable_features"]["calendar_events"]
max_calendar_event_bar_rows = config["style"]["max_calendar_event_bar_rows"]

# If we're displaying condition bars, calculate them now. We need to do this early because if
# we have some we will need to size the rest of the figure to allow space for them.
if show_condition_bars:
    print("Calculating condition bars...")
    # Extract regions of the forecast that correspond to frosty or stormy conditions
    frosty_indices = [i for i in range(len(temperatures))
                      if temperatures[i] <= config["frost_storm_warning"]["frost_temp"]]
    wet_indices = [i for i in range(len(precip_probs))
                   if precip_probs[i] >= config["frost_storm_warning"]["storm_precip_prob"]]
    windy_indices = [i for i in range(len(wind_gusts))
                     if wind_gusts[i] >= config["frost_storm_warning"]["storm_gust_speed"]]
    # Stormy = wet + windy
    stormy_indices = [i for i in wet_indices if i in windy_indices]
    # Storminess takes precedence so remove any frosty indices that are also stormy
    frosty_indices = [i for i in frosty_indices if i not in stormy_indices]

    # Cluster them into date/time blocks
    frosty_cluster_datetimes = cluster_and_get_start_end_times(frosty_indices, date_times)
    stormy_cluster_datetimes = cluster_and_get_start_end_times(stormy_indices, date_times)

    # Build up the list
    for c in frosty_cluster_datetimes:
        condition_bars.append(dict(text="Frost", start=c[0], end=c[1],
                                   color=config["style"]["frost_color"]))
    for c in stormy_cluster_datetimes:
        condition_bars.append(dict(text="Storm", start=c[0], end=c[1],
                                   color=config["style"]["storm_color"]))

    # Calculate good laundry days
    print("Calculating good laundry days...")
    for day in dates:
        # Start time for laundry is sunrise or our "hanging out" time, whichever is later.
        # End time is sunset.
        laundry_start_time = max(sun.get_sunrise_time(day.date()),
                                 day + timedelta(hours=config["laundry_day"]["hang_out_time"]))
        laundry_end_time = sun.get_sunset_time(day.date())

        if laundry_end_time - laundry_start_time >= timedelta(hours=config["laundry_day"]["min_hours_daylight"]):
            # Enough hours daylight, extract indices during the drying period
            daytime_indices = [i for i in range(len(date_times)) if
                               laundry_start_time <= date_times[i] <= laundry_end_time]
            mean_temp = statistics.mean([temperatures[i] for i in daytime_indices])
            mean_humidity = statistics.mean([humidities[i] for i in daytime_indices])
            max_precip_prob = max([precip_probs[i] for i in daytime_indices])

            # Check logic for being a good laundry day. If so, add the condition bar
            if mean_temp >= config["laundry_day"]["min_average_temp"] and \
                    mean_humidity <= config["laundry_day"]["max_average_humidity"] and \
                    max_precip_prob <= config["laundry_day"]["max_precip_prob"]:
                # Build up the list
                condition_bars.append(dict(text="Laundry Day",
                                           start=sun.get_sunrise_time(day.date()),
                                           end=sun.get_sunset_time(day.date()),
                                           color=config["style"]["laundry_day_color"]))

# If we're displaying calendar events, fetch from the internet. We need to do this early because if
# we have events (and particularly events at overlapping times) we will need to size the rest of
# the figure to allow space for them.
if show_calendar_events:
    print("Fetching calendar events...")
    for calendar in config["calendars"]:
        event_list = events(url=calendar["url"], start=first_time, end=last_time)
        for event in event_list:
            # For all-day events, constrain to sunrise/sunset time. Silly but it makes it look nicer when it lines up
            start = sun.get_sunrise_time(event.start.date()) if event.all_day else event.start
            end = sun.get_sunset_time(event.start.date()) if event.all_day else event.end
            # Build up the list
            event_bars.append(dict(text=event.summary, start=start, end=end, color=calendar["color"]))

# Find the maximum number of conflicting events
event_lines_required = min(count_max_bars_at_time(event_bars), max_calendar_event_bar_rows)
print(event_lines_required)

# Disable extra lines if there's nothing to display on them
if not len(condition_bars):
    show_condition_bars = False
if not len(event_bars):
    show_calendar_events = False

# Calculate the vertical alignment of various components based on what is enabled
plot_bottom_y_pos = 0
weather_icon_y_pos = 0.07
condition_y0_pos = -0.03
condition_y1_pos = 0.07
events_y0_pos = -0.03
events_y1_pos = 0.07
if show_weather_icons:
    plot_bottom_y_pos += 0.08
if show_condition_bars:
    plot_bottom_y_pos += 0.12
    weather_icon_y_pos += 0.12
if show_calendar_events:
    plot_bottom_y_pos += 0.12 * event_lines_required
    weather_icon_y_pos += 0.12 * event_lines_required
    condition_y0_pos += 0.12 * event_lines_required
    condition_y1_pos += 0.12 * event_lines_required

# Create plots
print("Plotting data...")
# noinspection PyTypeChecker
temp_trace = go.Scatter(x=date_times,
                        y=(feels_likes if config["use_feels_like_temp"] else temperatures),
                        name="Temperature",
                        yaxis="y1",
                        line_shape='spline',
                        marker=dict(color=config["style"]["temp_color"]),
                        line=dict(color=config["style"]["temp_color"], width=4))
# noinspection PyTypeChecker
precip_trace = go.Scatter(x=date_times,
                          y=precip_probs,
                          name="Precipitation Probability",
                          yaxis="y2",
                          line_shape='spline',
                          marker=dict(color=config["style"]["precip_color"]),
                          line=dict(color=config["style"]["precip_color"], width=4))
# noinspection PyTypeChecker
wind_trace = go.Scatter(x=date_times,
                        y=wind_speeds,
                        name="Wind Speed",
                        yaxis="y3",
                        line_shape='spline',
                        marker=dict(color=config["style"]["wind_color"]),
                        line=dict(color=config["style"]["wind_color"], width=4))
# noinspection PyTypeChecker
gust_trace = go.Scatter(x=date_times,
                        y=wind_gusts,
                        name="Gust Speed",
                        yaxis="y3",
                        line_shape='spline',
                        marker=dict(color=config["style"]["gust_color"]),
                        line=dict(color=config["style"]["gust_color"], width=4,
                                  dash=config["style"]["gust_line_style"]))
# noinspection PyTypeChecker
humidity_trace = go.Scatter(x=date_times,
                            y=humidities,
                            name="Humidity",
                            yaxis="y4",
                            line_shape='spline',
                            marker=dict(color=config["style"]["humidity_color"]),
                            line=dict(color=config["style"]["humidity_color"], width=4))
traces = []
if config["enable_plots"]["temp"]:
    traces.append(temp_trace)
if config["enable_plots"]["precip_prob"]:
    traces.append(precip_trace)
if config["enable_plots"]["wind"]:
    traces.append(wind_trace)
if config["enable_plots"]["gust"]:
    traces.append(gust_trace)
if config["enable_plots"]["humidity"]:
    traces.append(humidity_trace)

# Assemble figure
fig = plotly.subplots.make_subplots()
fig.add_traces(traces)

# Configure layout
print("Configuring layout...")
fig["layout"].update(height=config["plot_size"]["height"],
                     width=config["plot_size"]["width"],
                     paper_bgcolor=config["style"]["background_color"],
                     plot_bgcolor=config["style"]["background_color"],
                     showlegend=False,
                     margin=dict(l=0, r=5, t=0, b=10),
                     xaxis=dict(domain=[0, 0.97],
                                visible=False, showgrid=False, zeroline=False),
                     yaxis1=dict(domain=[plot_bottom_y_pos, 1.0], side="right", anchor="free", position=0.98,
                                 range=[config["scale"]["min_temp"], config["scale"]["max_temp"]],
                                 tickfont=dict(color=config["style"]["temp_color"], size=16),
                                 showgrid=False, zeroline=False),
                     yaxis2=dict(domain=[plot_bottom_y_pos, 1.0], side="right", anchor="free", position=0.98,
                                 range=[0.0, 100.0],
                                 tickfont=dict(color=config["style"]["precip_color"], size=16),
                                 showgrid=False, zeroline=False, showticklabels=False, overlaying="y"),
                     yaxis3=dict(domain=[plot_bottom_y_pos, 1.0], side="right", anchor="free", position=1.00,
                                 range=[0.0, config["scale"]["max_wind_speed"]],
                                 tickfont=dict(color=config["style"]["wind_color"], size=16),
                                 showgrid=False, zeroline=False, overlaying="y"),
                     yaxis4=dict(domain=[plot_bottom_y_pos, 1.0], side="right", anchor="free", position=1.00,
                                 range=[0.0, 100.0],
                                 tickfont=dict(color=config["style"]["humidity_color"], size=16),
                                 showgrid=False, zeroline=False, showticklabels=False, overlaying="y"))

# If we're displaying weather symbols, add them to the figure
if show_weather_icons:
    print("Adding weather icons...")
    # For each forecast point, look up the icon for its weather code, and add it to the display
    for i in range(0, len(date_times)):
        image = PIL.Image.open(config["files"]["weather_icon_folder"] + "/" + WEATHER_ICON_LOOKUP[weather_codes[i]])
        fig.add_layout_image(source=image, x=date_times[i], y=weather_icon_y_pos, xref="x",
                             yref="paper", xanchor="center", sizex=8000000, sizey=1)

# If we're displaying condition bars, calculate where they should be and add them to the figure
if show_condition_bars:
    print("Adding condition bars...")
    # Display the date/time blocks on the figure
    for bar in condition_bars:
        # noinspection PyTypeChecker
        fig.add_shape(type="rect",
                      x0=bar["start"].timestamp() * 1000, x1=bar["end"].timestamp() * 1000, xref="x",
                      y0=condition_y0_pos, y1=condition_y1_pos, yref="paper",
                      label=dict(text=bar["text"], font=dict(color=bar["color"],
                                                             size=config["style"]["condition_bars_font_size"])),
                      fillcolor=bar["color"],
                      opacity=config["style"]["condition_bars_opacity"],
                      layer="below")

# If we're displaying calendar events, fetch from the internet, calculate where they should be placed,
# and add them to the figure
if show_calendar_events:
    print("Adding calendar events...")
    already_added_event_bars = []
    for bar in event_bars:
        add_to_row = count_overlapping_bars(already_added_event_bars, bar)
        if add_to_row < max_calendar_event_bar_rows:
            y0_pos = events_y0_pos + 0.12 * (max_calendar_event_bar_rows - add_to_row - 1)
            y1_pos = events_y1_pos + 0.12 * (max_calendar_event_bar_rows - add_to_row - 1)
            fig.add_shape(type="rect",
                          x0=bar["start"].timestamp() * 1000, x1=bar["end"].timestamp() * 1000, xref="x",
                          y0=y0_pos, y1=y1_pos, yref="paper",
                          label=dict(text=bar["text"],
                                     font=dict(color=bar["color"],
                                               size=config["style"]["calendar_event_bars_font_size"])),
                          fillcolor=bar["color"], opacity=config["style"]["calendar_event_bars_opacity"],
                          layer="below")
        already_added_event_bars.append(bar)

# If we have frosty temperatures, add horizontal lines at the appropriate temperatures
if min(temperatures) <= config["frost_storm_warning"]["frost_temp"]:
    print("Adding frost lines...")
    fig.add_hline(y=config["frost_storm_warning"]["frost_temp"],
                  line_color=config["style"]["frost_color"],
                  opacity=config["style"]["frost_line_opacity"],
                  line_width=1, line_dash=config["style"]["frost_line_style"],
                  layer="below")
    fig.add_hline(y=0,
                  line_color=config["style"]["ice_color"],
                  opacity=config["style"]["frost_line_opacity"],
                  line_width=2, line_dash=config["style"]["frost_line_style"],
                  layer="below")

# Annotate figure with daytime blocks
print("Adding daytime regions...")
for day in dates:
    daytime_start = sun.get_sunrise_time(day.date()).timestamp() * 1000
    daytime_end = sun.get_sunset_time(day.date()).timestamp() * 1000
    fig.add_vrect(x0=daytime_start, x1=daytime_end,
                  fillcolor=config["style"]["daytime_color"],
                  opacity=config["style"]["daytime_opacity"],
                  annotation_text=day.strftime("%A"), annotation_position="inside top",
                  annotation_font_color=config["style"]["daytime_color"], annotation_font_size=16,
                  layer="below")

# We may have drawn a daytime block or laundry day block before the start of data, or a laundry day block past the end
# of the data, so go back and update the x-axis range to constrain it to the datetimes of the first and last data points
fig["layout"].update(xaxis=dict(range=[first_time, last_time]))

# Mark "now" time
# noinspection PyTypeChecker
fig.add_vline(x=datetime.utcnow(), line_color=config["style"]["now_line_color"])

# Write to disk
print("Writing output file...")
fig.write_image(config["files"]["output_file_name"])

print("Done.")
