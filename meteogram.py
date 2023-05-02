# Home Meteogram Display Script
# by Ian Renton, April 2023
# https://github.com/ianrenton/python-metoffice-meteogram
# See README for instructions.

from datetime import datetime, timedelta

import plotly.subplots
import suntime

from functions_calendar import generate_event_bars
from functions_condition_bars import count_max_bars_at_time, generate_frost_condition_bars, \
    generate_storm_condition_bars, generate_laundry_day_condition_bars
from functions_config import load_config
from functions_plotting import create_traces, add_units, add_daytime_regions, add_frost_lines, configure_layout, \
    add_weather_icons, add_condition_bars, add_calendar_events
from functions_weather import get_live_or_cached_weather_data, print_weather_metadata, build_forecast_datapoint_list, \
    get_temperatures

# Load config
print("Loading configuration...")
config = load_config()

# Build API URLs. We query twice - once for the hourly data for the next two days, then again
# for the three-hourly data for the next week.
hourly_api_url = "https://api-metoffice.apiconnect.ibmcloud.com/v0/forecasts/point/hourly?latitude=" \
                 + str(config["location"]["lat"]) + "&longitude=" + str(config["location"]["lon"]) \
                 + "&includeLocationName=true"
three_hourly_api_url = "https://api-metoffice.apiconnect.ibmcloud.com/v0/forecasts/point/three-hourly?latitude=" \
                       + str(config["location"]["lat"]) + "&longitude=" + str(config["location"]["lon"]) \
                       + "&includeLocationName=true"

# Fetch the data from the API (or cache files)
# See https://metoffice.apiconnect.ibmcloud.com/metoffice/production/site-specific-api-documentation
# for format data and examples.
hourly_data = get_live_or_cached_weather_data(hourly_api_url, config["files"]["cache_file_hourly"],
                                              config["met_office_datahub_api"]["client_key"],
                                              config["met_office_datahub_api"]["client_secret"])
three_hourly_data = get_live_or_cached_weather_data(three_hourly_api_url, config["files"]["cache_file_three_hourly"],
                                                    config["met_office_datahub_api"]["client_key"],
                                                    config["met_office_datahub_api"]["client_secret"])

print("Extracting weather metadata...")
print_weather_metadata(hourly_data)
print("Extracting weather forecast data...")
forecast = build_forecast_datapoint_list(hourly_data, three_hourly_data)
print("Forecast contains " + str(len(forecast)) + " data points between " + str(forecast[0].time) + " and " + str(
    forecast[len(forecast) - 1].time))

# Limit the forecast to only the number of days we want to show on screen
first_time = forecast[0].time
forecast_days_limit = config["show_forecast_days"]
print("Limiting forecast to " + str(forecast_days_limit) + " days...")
forecast = [x for x in forecast if x.time <= first_time + timedelta(days=forecast_days_limit)]
last_time = forecast[len(forecast) - 1].time

# Calculate a list of *days* spanned by the forecast, which we will use for getting sunrise/sunset
# times, calendar events etc.
dates = [first_time.date() + timedelta(days=x) for x in range((last_time.date() - first_time.date()).days + 1)]

# Create a suntime object, we will need this later
sun = suntime.Sun(config["location"]["lat"], config["location"]["lon"])

# Figure out which extra lines should be enabled
show_weather_icons = config["enable_features"]["weather_icons"]
show_condition_bars = config["enable_features"]["condition_bars"]
show_calendar_events = config["enable_features"]["calendar_events"]
max_calendar_event_bar_rows = config["style"]["max_calendar_event_bar_rows"]

# If we're displaying condition bars, calculate them now. We need to do this early because if
# we have some we will need to size the rest of the figure to allow space for them.
condition_bars = []
if show_condition_bars:
    print("Finding frosts...")
    condition_bars.extend(generate_frost_condition_bars(forecast, config))
    print("Finding storms...")
    condition_bars.extend(generate_storm_condition_bars(forecast, config))
    print("Finding good laundry days...")
    condition_bars.extend(generate_laundry_day_condition_bars(forecast, config, dates, sun))

# If we're displaying calendar events, fetch from the internet. We need to do this early because if
# we have events (and particularly events at overlapping times) we will need to size the rest of
# the figure to allow space for them.
event_bars = []
if show_calendar_events:
    print("Fetching calendar events...")
    event_bars = generate_event_bars(config, sun, first_time, last_time)

# Find the maximum number of conflicting events
event_lines_required = min(count_max_bars_at_time(event_bars), max_calendar_event_bar_rows)

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

# Create plot traces & assemble figure
print("Plotting data...")
fig = plotly.subplots.make_subplots()
fig.add_traces(create_traces(forecast, config))

# Configure layout
print("Configuring layout...")
configure_layout(fig, config, plot_bottom_y_pos)

if show_weather_icons:
    print("Adding weather icons...")
    add_weather_icons(fig, forecast, config, weather_icon_y_pos)

if show_condition_bars:
    print("Adding condition bars...")
    add_condition_bars(fig, config, condition_bars, condition_y0_pos, condition_y1_pos)

if show_calendar_events:
    print("Adding calendar events...")
    add_calendar_events(fig, config, event_bars, events_y0_pos, events_y1_pos, event_lines_required,
                        max_calendar_event_bar_rows)

if min(get_temperatures(forecast)) <= config["frost_storm_warning"]["frost_temp"]:
    print("Adding frost lines...")
    add_frost_lines(fig, config)

print("Adding daytime regions...")
add_daytime_regions(fig, config, dates, sun)

print("Adding units...")
add_units(fig, config, condition_y1_pos)

print("Adding \"now\" line...")
fig.add_vline(x=pytz.utc.localize(datetime.utcnow()).timestamp() * 1000, line_color=config["style"]["now_line_color"])

# We may have drawn a daytime block or laundry day block before the start of data, or a laundry day block past the end
# of the data, so go back and update the x-axis range to constrain it to the datetimes of the first and last data points
fig["layout"].update(xaxis=dict(range=[first_time, last_time]))

# Write to disk
print("Writing output file...")
fig.write_image(config["files"]["output_file_name"])

print("Done.")
