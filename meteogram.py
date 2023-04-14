# Python Met Office Meteogram Script
# by Ian Renton, April 2023
# https://github.com/ianrenton/python-metoffice-meteogram
# See README for instructions.

import datetime
import json
import os
import pathlib
import sys
import urllib.request

import PIL.Image
import dotenv
import plotly.graph_objects as go
import plotly.subplots
import suntime

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
DISPLAY_PRECIP_PROB = os.getenv("DISPLAY_PRECIP_PROB") == "True"
DISPLAY_HUMIDITY = os.getenv("DISPLAY_HUMIDITY") == "True"
WEATHER_ON_X_AXIS = os.getenv("WEATHER_ON_X_AXIS") == "True"
WEATHER_FONT_SIZE = int(os.getenv("WEATHER_FONT_SIZE"))
MAX_TEMP = float(os.getenv("MAX_TEMP"))
FROST_WARNING_TEMP = float(os.getenv("FROST_WARNING_TEMP"))
MIN_TEMP = float(os.getenv("MIN_TEMP"))
MAX_WIND_SPEED = float(os.getenv("MAX_WIND_SPEED"))
CACHE_FILE_NAME = os.getenv("CACHE_FILE_NAME")
OUTPUT_FILE_NAME = os.getenv("OUTPUT_FILE_NAME")
WEATHER_ICON_FOLDER = os.getenv("WEATHER_ICON_FOLDER")
TEMP_COLOR = os.getenv("TEMP_COLOR")
PRECIP_COLOR = os.getenv("PRECIP_COLOR")
WIND_COLOR = os.getenv("WIND_COLOR")
HUMIDITY_COLOR = os.getenv("HUMIDITY_COLOR")
DAYTIME_COLOR = os.getenv("DAYTIME_COLOR")
DAYTIME_OPACITY = float(os.getenv("DAYTIME_OPACITY"))
NOW_LINE_COLOR = os.getenv("NOW_LINE_COLOR")
DATE_AXIS_COLOR = os.getenv("DATE_AXIS_COLOR")
FROST_LINE_COLOR = os.getenv("FROST_LINE_COLOR")
FROST_LINE_STYLE = os.getenv("FROST_LINE_STYLE")
ICE_LINE_COLOR = os.getenv("ICE_LINE_COLOR")
FROST_LINE_OPACITY = float(os.getenv("FROST_LINE_OPACITY"))
BACKGROUND_COLOR = os.getenv("BACKGROUND_COLOR")

# Build API URL
api_url = "http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/" + LOCATION_CODE \
          + "?res=3hourly&key=" + API_KEY

# Check if we already fetched data recently
readFromFile = False
data_json = ""
cacheFile = pathlib.Path(CACHE_FILE_NAME)
if cacheFile.exists() and datetime.datetime.fromtimestamp(cacheFile.stat().st_mtime) > \
        datetime.datetime.now() - datetime.timedelta(minutes=10):
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
    date = datetime.datetime.strptime(day["value"], "%Y-%m-%dZ")
    dates.append(date)
    rep_list = day["Rep"]
    for rep in rep_list:
        time_mins = rep["$"]
        dateTime = date + datetime.timedelta(minutes=int(time_mins))
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

# Create plots
print("Plotting data...")
# noinspection PyTypeChecker
temp_trace = go.Scatter(x=date_times, y=(feels_likes if USE_FEELS_LIKE_TEMP else temperatures),
                        name="Temperature", yaxis="y1", line_shape='spline',
                        marker=dict(color=TEMP_COLOR), line=dict(color=TEMP_COLOR, width=4))
# noinspection PyTypeChecker
precip_trace = go.Scatter(x=date_times, y=precip_probs, name="Precipitation Probability", yaxis="y2",
                          line_shape='spline', marker=dict(color=PRECIP_COLOR), line=dict(color=PRECIP_COLOR, width=4))
# noinspection PyTypeChecker
wind_trace = go.Scatter(x=date_times, y=wind_speeds, name="Wind Speed", yaxis="y3", line_shape='spline',
                        marker=dict(color=WIND_COLOR), line=dict(color=WIND_COLOR, width=4))
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
if DISPLAY_HUMIDITY:
    traces.append(humidity_trace)

# Assemble figure
fig = plotly.subplots.make_subplots()
fig.add_traces(traces)

# Configure layout
fig["layout"].update(height=PLOT_HEIGHT, width=PLOT_WIDTH,
                     paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor=BACKGROUND_COLOR,
                     showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                     xaxis=dict(domain=[0, 0.97], visible=False, showgrid=False, zeroline=False),
                     yaxis1=dict(domain=[0.08, 1.0], side="right", anchor="free", position=0.98,
                                 tickfont=dict(color=TEMP_COLOR, size=16),
                                 showgrid=False, zeroline=False, range=[MIN_TEMP, MAX_TEMP]),
                     yaxis2=dict(domain=[0.08, 1.0], side="right", anchor="free", position=0.98,
                                 tickfont=dict(color=PRECIP_COLOR, size=16),
                                 showgrid=False, zeroline=False, showticklabels=False, overlaying="y",
                                 range=[0.0, 100.0]),
                     yaxis3=dict(domain=[0.08, 1.0], side="right", anchor="free", position=1.00,
                                 tickfont=dict(color=WIND_COLOR, size=16),
                                 showgrid=False, zeroline=False, overlaying="y", range=[0.0, MAX_WIND_SPEED]),
                     yaxis4=dict(domain=[0.08, 1.0], side="right", anchor="free", position=1.00,
                                 tickfont=dict(color=HUMIDITY_COLOR, size=16),
                                 showgrid=False, zeroline=False, showticklabels=False, overlaying="y",
                                 range=[0.0, 100.0])
)

# If we're displaying weather symbols, add them to the plot
if WEATHER_ON_X_AXIS:
    for i in range(0, len(date_times)):
        image = PIL.Image.open(WEATHER_ICON_FOLDER + "/" + WEATHER_ICON_LOOKUP[weather_codes[i]])
        fig.add_layout_image(
            source=image,
            x=date_times[i],
            y=0.07,
            xref="x",
            yref="paper",
            xanchor="center",
            sizex=8000000,
            sizey=1
        )

# If we have frosty temperatures, add horizontal lines at the appropriate temperatures
if frosty_temp:
    fig.add_hline(y=FROST_WARNING_TEMP, line_color=FROST_LINE_COLOR, opacity=FROST_LINE_OPACITY, line_width=1,
                  line_dash=FROST_LINE_STYLE, layer="below")
    fig.add_hline(y=0, line_color=ICE_LINE_COLOR, opacity=FROST_LINE_OPACITY, line_width=2,
                  line_dash=FROST_LINE_STYLE, layer="below")

# Annotate figure with daytime blocks
sun = suntime.Sun(latitude, longitude)
for day in dates:
    daytime_start = sun.get_local_sunrise_time(day.date()).timestamp() * 1000
    daytime_end = sun.get_local_sunset_time(day.date()).timestamp() * 1000
    fig.add_vrect(x0=daytime_start, x1=daytime_end, fillcolor=DAYTIME_COLOR, opacity=DAYTIME_OPACITY,
                  annotation_text=day.strftime("%A"), annotation_position="inside top",
                  annotation_font_color=DAYTIME_COLOR, annotation_font_size=16, layer="below")

# We may have drawn a daytime block before the start of data, so go back and update the x-axis range, so it starts at
# the datetime of the first data point.
fig["layout"].update(xaxis=dict(range=[date_times[0], date_times[len(date_times) - 1]]))

# Mark "now" time
# noinspection PyTypeChecker
fig.add_vline(x=datetime.datetime.now(), line_color=NOW_LINE_COLOR)

# Write to disk
print("Writing output file...")
fig.write_image(OUTPUT_FILE_NAME)

print("Done.")
