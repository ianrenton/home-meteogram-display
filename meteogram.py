# Python Met Office Meteogram Script
# by Ian Renton, April 2023
# https://github.com/ianrenton/python-metoffice-meteogram
# See README for instructions.

# ## IMPORTS

import json
import os
import pathlib
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta

import PIL.Image
import dotenv
import plotly.graph_objects as go
import plotly.subplots
import pytz
import suntime

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

# Load .env
print("Loading configuration...")

cacheFile = pathlib.Path(".env")
if not cacheFile.exists():
    print("The .env file does not exist. You will need to create this by copying .env.example and filling "
          "in the required parameters. See the README for more information.")
    sys.exit(1)

dotenv.load_dotenv()

if not os.getenv("API_KEY"):
    print("Your Met Office Datapoint API key is not set. Copy the '.env.example' file to '.env' and insert your key. "
          "Then try running this software again.")
    sys.exit(1)

API_KEY = os.getenv("API_KEY")
LOCATION_CODE = os.getenv("LOCATION_CODE")
PLOT_WIDTH = int(os.getenv("PLOT_WIDTH"))
PLOT_HEIGHT = int(os.getenv("PLOT_HEIGHT"))
DISPLAY_TEMP = os.getenv("DISPLAY_TEMP") == "True"
USE_FEELS_LIKE_TEMP = os.getenv("USE_FEELS_LIKE_TEMP") == "True"
DISPLAY_WIND = os.getenv("DISPLAY_WIND") == "True"
DISPLAY_GUSTS = os.getenv("DISPLAY_GUSTS") == "True"
DISPLAY_PRECIP_PROB = os.getenv("DISPLAY_PRECIP_PROB") == "True"
DISPLAY_HUMIDITY = os.getenv("DISPLAY_HUMIDITY") == "True"
WEATHER_ICONS_ON_X_AXIS = os.getenv("WEATHER_ICONS_ON_X_AXIS") == "True"
CONDITION_BARS_ON_X_AXIS = os.getenv("CONDITION_BARS_ON_X_AXIS") == "True"
CONDITION_BARS_FONT_SIZE = int(os.getenv("CONDITION_BARS_FONT_SIZE"))
MAX_TEMP = float(os.getenv("MAX_TEMP"))
FROST_WARNING_TEMP = float(os.getenv("FROST_WARNING_TEMP"))
MIN_TEMP = float(os.getenv("MIN_TEMP"))
MAX_WIND_SPEED = float(os.getenv("MAX_WIND_SPEED"))
STORM_WARNING_GUST_SPEED = float(os.getenv("STORM_WARNING_GUST_SPEED"))
STORM_WARNING_PRECIP_PROB = float(os.getenv("STORM_WARNING_PRECIP_PROB"))
LAUNDRY_DAY_HANG_OUT_TIME = float(os.getenv("LAUNDRY_DAY_HANG_OUT_TIME"))
LAUNDRY_DAY_ABOVE_HOURS_DAYLIGHT = float(os.getenv("LAUNDRY_DAY_ABOVE_HOURS_DAYLIGHT"))
LAUNDRY_DAY_ABOVE_AVERAGE_TEMP = float(os.getenv("LAUNDRY_DAY_ABOVE_AVERAGE_TEMP"))
LAUNDRY_DAY_BELOW_AVERAGE_HUMIDITY = float(os.getenv("LAUNDRY_DAY_BELOW_AVERAGE_HUMIDITY"))
LAUNDRY_DAY_BELOW_PRECIP_PROB = float(os.getenv("LAUNDRY_DAY_BELOW_PRECIP_PROB"))
CACHE_FILE_NAME = os.getenv("CACHE_FILE_NAME")
OUTPUT_FILE_NAME = os.getenv("OUTPUT_FILE_NAME")
WEATHER_ICON_FOLDER = os.getenv("WEATHER_ICON_FOLDER")
TEMP_COLOR = os.getenv("TEMP_COLOR")
PRECIP_COLOR = os.getenv("PRECIP_COLOR")
WIND_COLOR = os.getenv("WIND_COLOR")
GUST_COLOR = os.getenv("GUST_COLOR")
GUST_LINE_STYLE = os.getenv("GUST_LINE_STYLE")
HUMIDITY_COLOR = os.getenv("HUMIDITY_COLOR")
DAYTIME_COLOR = os.getenv("DAYTIME_COLOR")
DAYTIME_OPACITY = float(os.getenv("DAYTIME_OPACITY"))
CONDITION_BARS_OPACITY = float(os.getenv("CONDITION_BARS_OPACITY"))
NOW_LINE_COLOR = os.getenv("NOW_LINE_COLOR")
DATE_AXIS_COLOR = os.getenv("DATE_AXIS_COLOR")
FROST_COLOR = os.getenv("FROST_COLOR")
ICE_COLOR = os.getenv("ICE_COLOR")
STORM_COLOR = os.getenv("STORM_COLOR")
LAUNDRY_DAY_COLOR = os.getenv("LAUNDRY_DAY_COLOR")
FROST_LINE_STYLE = os.getenv("FROST_LINE_STYLE")
FROST_LINE_OPACITY = float(os.getenv("FROST_LINE_OPACITY"))
BACKGROUND_COLOR = os.getenv("BACKGROUND_COLOR")

# Build API URL
api_url = "http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/" + LOCATION_CODE + "?res=3hourly&key=" + \
          API_KEY

# Check if we already fetched data recently
readFromFile = False
data_json = ""
cacheFile = pathlib.Path(CACHE_FILE_NAME)
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
for day in day_list:
    date = pytz.utc.localize(datetime.strptime(day["value"], "%Y-%m-%dZ"))
    dates.append(date)
    rep_list = day["Rep"]
    for rep in rep_list:
        time_mins = rep["$"]
        dateTime = date + timedelta(minutes=int(time_mins))
        date_times.append(dateTime)
        temp = rep["T"]
        temperatures.append(int(temp))
        if int(temp) <= FROST_WARNING_TEMP:
            frosty_temp = True
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

# Create a suntime object, we will need this later
sun = suntime.Sun(latitude, longitude)

# Create plots
print("Plotting data...")
# noinspection PyTypeChecker
temp_trace = go.Scatter(x=date_times, y=(feels_likes if USE_FEELS_LIKE_TEMP else temperatures), name="Temperature",
                        yaxis="y1", line_shape='spline', marker=dict(color=TEMP_COLOR),
                        line=dict(color=TEMP_COLOR, width=4))
# noinspection PyTypeChecker
precip_trace = go.Scatter(x=date_times, y=precip_probs, name="Precipitation Probability", yaxis="y2",
                          line_shape='spline', marker=dict(color=PRECIP_COLOR), line=dict(color=PRECIP_COLOR, width=4))
# noinspection PyTypeChecker
wind_trace = go.Scatter(x=date_times, y=wind_speeds, name="Wind Speed", yaxis="y3", line_shape='spline',
                        marker=dict(color=WIND_COLOR), line=dict(color=WIND_COLOR, width=4))
# noinspection PyTypeChecker
gust_trace = go.Scatter(x=date_times, y=wind_gusts, name="Gust Speed", yaxis="y3", line_shape='spline',
                        marker=dict(color=WIND_COLOR), line=dict(color=GUST_COLOR, width=4, dash=GUST_LINE_STYLE))
# noinspection PyTypeChecker
humidity_trace = go.Scatter(x=date_times, y=humidities, name="Humidity", yaxis="y4", line_shape='spline',
                            marker=dict(color=HUMIDITY_COLOR), line=dict(color=HUMIDITY_COLOR, width=4))
traces = []
if DISPLAY_TEMP:
    traces.append(temp_trace)
if DISPLAY_PRECIP_PROB:
    traces.append(precip_trace)
if DISPLAY_WIND:
    traces.append(wind_trace)
if DISPLAY_GUSTS:
    traces.append(gust_trace)
if DISPLAY_HUMIDITY:
    traces.append(humidity_trace)

# Assemble figure
fig = plotly.subplots.make_subplots()
fig.add_traces(traces)

# Calculate how much space we need to leave below the X axis for displaying other things
space_below_x_axis = 0
if WEATHER_ICONS_ON_X_AXIS:
    space_below_x_axis += 0.08
if CONDITION_BARS_ON_X_AXIS:
    space_below_x_axis += 0.12

# Configure layout
print("Configuring layout...")
fig["layout"].update(height=PLOT_HEIGHT, width=PLOT_WIDTH, paper_bgcolor=BACKGROUND_COLOR,
                     plot_bgcolor=BACKGROUND_COLOR, showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                     xaxis=dict(domain=[0, 0.97], visible=False, showgrid=False, zeroline=False),
                     yaxis1=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=0.98,
                                 tickfont=dict(color=TEMP_COLOR, size=16), showgrid=False, zeroline=False,
                                 range=[MIN_TEMP, MAX_TEMP]),
                     yaxis2=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=0.98,
                                 tickfont=dict(color=PRECIP_COLOR, size=16), showgrid=False, zeroline=False,
                                 showticklabels=False, overlaying="y", range=[0.0, 100.0]),
                     yaxis3=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=1.00,
                                 tickfont=dict(color=WIND_COLOR, size=16), showgrid=False, zeroline=False,
                                 overlaying="y", range=[0.0, MAX_WIND_SPEED]),
                     yaxis4=dict(domain=[space_below_x_axis, 1.0], side="right", anchor="free", position=1.00,
                                 tickfont=dict(color=HUMIDITY_COLOR, size=16), showgrid=False, zeroline=False,
                                 showticklabels=False, overlaying="y", range=[0.0, 100.0]))

# If we're displaying weather symbols, add them to the figure
weather_icon_y_pos = 0.19 if CONDITION_BARS_ON_X_AXIS else 0.07
if WEATHER_ICONS_ON_X_AXIS:
    print("Adding weather icons...")
    # For each forecast point, look up the icon for its weather code, and add it to the display
    for i in range(0, len(date_times)):
        image = PIL.Image.open(WEATHER_ICON_FOLDER + "/" + WEATHER_ICON_LOOKUP[weather_codes[i]])
        fig.add_layout_image(source=image, x=date_times[i], y=weather_icon_y_pos, xref="x",
                             yref="paper", xanchor="center", sizex=8000000, sizey=1)

# If we're displaying condition bars, calculate where they should be and add them to the figure
if CONDITION_BARS_ON_X_AXIS:
    print("Adding condition bars...")
    # Extract regions of the forecast that correspond to frosty or stormy conditions
    frosty_indices = [i for i in range(len(temperatures)) if temperatures[i] <= FROST_WARNING_TEMP]
    wet_indices = [i for i in range(len(precip_probs)) if precip_probs[i] >= STORM_WARNING_PRECIP_PROB]
    windy_indices = [i for i in range(len(wind_gusts)) if wind_gusts[i] >= STORM_WARNING_GUST_SPEED]
    # Stormy = wet + windy
    stormy_indices = [i for i in wet_indices if i in windy_indices]
    # Storminess takes precedence so remove any frosty indices that are also stormy
    frosty_indices = [i for i in frosty_indices if i not in stormy_indices]

    # Cluster them into date/time blocks
    frosty_cluster_datetimes = cluster_and_get_start_end_times(frosty_indices, date_times)
    stormy_cluster_datetimes = cluster_and_get_start_end_times(stormy_indices, date_times)

    # Display the date/time blocks on the figure
    for c in frosty_cluster_datetimes:
        # noinspection PyTypeChecker
        fig.add_shape(type="rect", x0=c[0], x1=c[1], y0=-0.03, y1=0.07, xref="x", yref="paper",
                      label=dict(text="FROST", font=dict(color=FROST_COLOR, size=CONDITION_BARS_FONT_SIZE)),
                      fillcolor=FROST_COLOR, opacity=CONDITION_BARS_OPACITY,
                      layer="below")
    for c in stormy_cluster_datetimes:
        # noinspection PyTypeChecker
        fig.add_shape(type="rect", x0=c[0], x1=c[1], y0=-0.03, y1=0.07, xref="x", yref="paper",
                      label=dict(text="STORM", font=dict(color=STORM_COLOR, size=CONDITION_BARS_FONT_SIZE)),
                      fillcolor=STORM_COLOR, opacity=CONDITION_BARS_OPACITY,
                      layer="below")

    # Calculate good laundry days
    for day in dates:
        # Start time for laundry is sunrise or our "hanging out" time, whichever is later.
        # End time is sunset.
        laundry_start_time = max(sun.get_sunrise_time(day.date()), day + timedelta(hours=LAUNDRY_DAY_HANG_OUT_TIME))
        laundry_end_time = sun.get_sunset_time(day.date())

        if laundry_end_time - laundry_start_time >= timedelta(hours=LAUNDRY_DAY_ABOVE_HOURS_DAYLIGHT):
            # Enough hours daylight, extract indices during the drying period
            daytime_indices = [i for i in range(len(date_times)) if
                               laundry_start_time <= date_times[i] <= laundry_end_time]
            mean_temp = statistics.mean([temperatures[i] for i in daytime_indices])
            mean_humidity = statistics.mean([humidities[i] for i in daytime_indices])
            max_precip_prob = max([precip_probs[i] for i in daytime_indices])

            # Check logic for being a good laundry day. If so, add the condition bar
            if mean_temp >= LAUNDRY_DAY_ABOVE_AVERAGE_TEMP and mean_humidity <= LAUNDRY_DAY_BELOW_AVERAGE_HUMIDITY \
                    and max_precip_prob <= LAUNDRY_DAY_BELOW_PRECIP_PROB:
                # noinspection PyTypeChecker
                fig.add_shape(type="rect", x0=sun.get_sunrise_time(day.date()).timestamp() * 1000,
                              x1=sun.get_sunset_time(day.date()).timestamp() * 1000,
                              y0=-0.03, y1=0.07, xref="x", yref="paper",
                              label=dict(text="LAUNDRY DAY", font=dict(color=LAUNDRY_DAY_COLOR,
                                                                       size=CONDITION_BARS_FONT_SIZE)),
                              fillcolor=LAUNDRY_DAY_COLOR, opacity=CONDITION_BARS_OPACITY, layer="below")

# If we have frosty temperatures, add horizontal lines at the appropriate temperatures
if frosty_temp:
    print("Adding frost lines...")
    fig.add_hline(y=FROST_WARNING_TEMP, line_color=FROST_COLOR, opacity=FROST_LINE_OPACITY, line_width=1,
                  line_dash=FROST_LINE_STYLE, layer="below")
    fig.add_hline(y=0, line_color=ICE_COLOR, opacity=FROST_LINE_OPACITY, line_width=2, line_dash=FROST_LINE_STYLE,
                  layer="below")

# Annotate figure with daytime blocks
print("Adding daytime regions...")
for day in dates:
    daytime_start = sun.get_sunrise_time(day.date()).timestamp() * 1000
    daytime_end = sun.get_sunset_time(day.date()).timestamp() * 1000
    fig.add_vrect(x0=daytime_start, x1=daytime_end, fillcolor=DAYTIME_COLOR, opacity=DAYTIME_OPACITY,
                  annotation_text=day.strftime("%A"), annotation_position="inside top",
                  annotation_font_color=DAYTIME_COLOR, annotation_font_size=16, layer="below")

# We may have drawn a daytime block or laundry day block before the start of data, or a laundry day block past the end
# of the data, so go back and update the x-axis range to constrain it to the datetimes of the first and last data points
fig["layout"].update(xaxis=dict(range=[date_times[0], date_times[len(date_times) - 1]]))

# Mark "now" time
# noinspection PyTypeChecker
fig.add_vline(x=datetime.utcnow(), line_color=NOW_LINE_COLOR)

# Write to disk
print("Writing output file...")
fig.write_image(OUTPUT_FILE_NAME)

print("Done.")
