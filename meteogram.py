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


# ## MAIN PROGRAM CODE

# Load config
print("Loading configuration...")

cacheFile = pathlib.Path("config.yml")
if not cacheFile.exists():
    print("The config.yml file does not exist. You will need to create this by copying config.yml.example and filling "
          "in the required parameters. See the README for more information.")
    sys.exit(1)

with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

if not config["met_office_api"]["key"]:
    print("Your Met Office Datapoint API key is not set. Copy the 'config.yml.example' file to 'config.yml' and "
          "insert your key. Then try running this software again.")
    sys.exit(1)

# Build API URL
api_url = "http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/" \
          + str(config["met_office_api"]["location_code"]) + "?res=3hourly&key=" + config["met_office_api"]["key"]

# Check if we already fetched data recently
readFromFile = False
data_json = ""
cacheFile = pathlib.Path(config["files"]["cache_file_name"])
if cacheFile.exists() and datetime.fromtimestamp(
        cacheFile.stat().st_mtime) > datetime.now() - timedelta(minutes=10):
    # Already got recent data, so use it if possible
    print("Cache file was updated less than 10 minutes ago, re-using that to spare the API...")
    data_json = cacheFile.read_text()
    if data_json:
        readFromFile = True
    else:
        print("Tried and failed to read cache file, will query API instead.")

if not readFromFile:
    # Didn't have recent cached data so query the API for new data
    print("Querying API...")
    data_json = urllib.request.urlopen(api_url).read()
    if data_json:
        print("Writing local cache file...")
        cacheFile.write_text(json.dumps(json.loads(data_json)))
    else:
        print("Could not query the Met Office Datapoint API. Check your API key is correct and that you have internet "
              "connectivity.")
        sys.exit(1)

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

# Parse data into useful forms for plotting.
# See https://www.metoffice.gov.uk/binaries/content/assets/metofficegovuk/pdf/data/datapoint_api_reference.pdf
# for format data and examples.
print("Extracting data...")
data = json.loads(data_json)
latitude = float(data["SiteRep"]["DV"]["Location"]["lat"])
longitude = float(data["SiteRep"]["DV"]["Location"]["lon"])
day_list = data["SiteRep"]["DV"]["Location"]["Period"]
frosty_temp = False
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

# Record whether we have any frosty temperatures in the forecast, this will cause the frost & ice lines to display
# on the plot later on
if min(temperatures) <= config["frost_storm_warning"]["frost_temp"]:
    frosty_temp = True

# Create a suntime object, we will need this later
sun = suntime.Sun(latitude, longitude)

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

# Calculate how much space we need to leave below the X axis for displaying other things
space_below_x_axis = 0
if config["enable_features"]["weather_icons"]:
    space_below_x_axis += 0.08
if config["enable_features"]["condition_bars"]:
    space_below_x_axis += 0.12
if config["enable_features"]["calendar_events"]:
    space_below_x_axis += 0.12

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
                     yaxis1=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=0.98,
                                 range=[config["scale"]["min_temp"], config["scale"]["max_temp"]],
                                 tickfont=dict(color=config["style"]["temp_color"], size=16),
                                 showgrid=False, zeroline=False),
                     yaxis2=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=0.98,
                                 range=[0.0, 100.0],
                                 tickfont=dict(color=config["style"]["precip_color"], size=16),
                                 showgrid=False, zeroline=False, showticklabels=False, overlaying="y"),
                     yaxis3=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=1.00,
                                 range=[0.0, config["scale"]["max_wind_speed"]],
                                 tickfont=dict(color=config["style"]["wind_color"], size=16),
                                 showgrid=False, zeroline=False, overlaying="y"),
                     yaxis4=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=1.00,
                                 range=[0.0, 100.0],
                                 tickfont=dict(color=config["style"]["humidity_color"], size=16),
                                 showgrid=False, zeroline=False, showticklabels=False, overlaying="y"))

# If we're displaying weather symbols, add them to the figure
if config["enable_features"]["weather_icons"]:
    print("Adding weather icons...")
    weather_icon_y_pos = 0.07
    if config["enable_features"]["condition_bars"]:
        weather_icon_y_pos += 0.12
    if config["enable_features"]["calendar_events"]:
        weather_icon_y_pos += 0.12

    # For each forecast point, look up the icon for its weather code, and add it to the display
    for i in range(0, len(date_times)):
        image = PIL.Image.open(config["files"]["weather_icon_folder"] + "/" + WEATHER_ICON_LOOKUP[weather_codes[i]])
        fig.add_layout_image(source=image, x=date_times[i], y=weather_icon_y_pos, xref="x",
                             yref="paper", xanchor="center", sizex=8000000, sizey=1)

# If we're displaying condition bars, calculate where they should be and add them to the figure
if config["enable_features"]["condition_bars"]:
    print("Adding condition bars...")
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

    # Display the date/time blocks on the figure
    condition_y0_pos = -0.03
    condition_y1_pos = 0.07
    if config["enable_features"]["calendar_events"]:
        condition_y0_pos += 0.12
        condition_y1_pos += 0.12
    for c in frosty_cluster_datetimes:
        # noinspection PyTypeChecker
        fig.add_shape(type="rect",
                      x0=c[0], x1=c[1], xref="x",
                      y0=condition_y0_pos, y1=condition_y1_pos, yref="paper",
                      label=dict(text="FROST", font=dict(color=config["style"]["frost_color"],
                                                         size=config["style"]["condition_bars_font_size"])),
                      fillcolor=config["style"]["frost_color"],
                      opacity=config["style"]["condition_bars_opacity"],
                      layer="below")
    for c in stormy_cluster_datetimes:
        # noinspection PyTypeChecker
        fig.add_shape(type="rect",
                      x0=c[0], x1=c[1], xref="x",
                      y0=condition_y0_pos, y1=condition_y1_pos, yref="paper",
                      label=dict(text="STORM", font=dict(color=config["style"]["storm_color"],
                                                         size=config["style"]["condition_bars_font_size"])),
                      fillcolor=config["style"]["storm_color"],
                      opacity=config["style"]["condition_bars_opacity"],
                      layer="below")

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
                    mean_humidity <= config["laundry_day"]["max_average_humidity"] \
                    and max_precip_prob <= config["laundry_day"]["max_precip_prob"]:
                # noinspection PyTypeChecker
                fig.add_shape(type="rect",
                              x0=sun.get_sunrise_time(day.date()).timestamp() * 1000,
                              x1=sun.get_sunset_time(day.date()).timestamp() * 1000, xref="x",
                              y0=condition_y0_pos, y1=condition_y1_pos, yref="paper",
                              label=dict(text="LAUNDRY DAY", font=dict(color=config["style"]["laundry_day_color"],
                                                                       size=config["style"][
                                                                           "condition_bars_font_size"])),
                              fillcolor=config["style"]["laundry_day_color"],
                              opacity=config["style"]["condition_bars_opacity"],
                              layer="below")

# If we're displaying calendar events, fetch from the internet, calculate where they should be placed,
# and add them to the figure
if config["enable_features"]["calendar_events"]:
    print("Adding calendar events...")
    event_y0_pos = -0.03
    event_y1_pos = 0.07

    for calendar in config["calendars"]:
        eventList = events(calendar["url"])
        for event in eventList:
            # For all-day events, constrain to sunrise/sunset time. Silly but it makes it look nicer when it lines up
            start = event.start
            end = event.end
            if event.all_day:
                start = sun.get_sunrise_time(start.date())
                end = sun.get_sunset_time(start.date())

            # Add to figure
            fig.add_shape(type="rect",
                          x0=start.timestamp() * 1000, x1=end.timestamp() * 1000, xref="x",
                          y0=event_y0_pos, y1=event_y1_pos, yref="paper",
                          label=dict(text=event.summary,
                                     font=dict(color=calendar["color"],
                                               size=config["style"]["calendar_event_bars_font_size"])),
                          fillcolor=calendar["color"], opacity=config["style"]["calendar_event_bars_opacity"],
                          layer="below")

# If we have frosty temperatures, add horizontal lines at the appropriate temperatures
if frosty_temp:
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
fig["layout"].update(xaxis=dict(range=[date_times[0], date_times[len(date_times) - 1]]))

# Mark "now" time
# noinspection PyTypeChecker
fig.add_vline(x=datetime.utcnow(), line_color=config["style"]["now_line_color"])

# Write to disk
print("Writing output file...")
fig.write_image(config["files"]["output_file_name"])

print("Done.")
