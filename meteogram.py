# Home Meteogram Display Script
# by Ian Renton, April 2023
# https://github.com/ianrenton/python-metoffice-meteogram
# See README for instructions.

from datetime import datetime, timedelta
import PIL.Image
import plotly.subplots
import suntime
from functions_calendar import generate_event_bars
from functions_config import load_config
from functions_plotting import create_traces
from functions_weather import get_live_or_cached_weather_data, print_weather_metadata, build_forecast_datapoint_list, \
    get_temperatures
from functions_condition_bars import count_overlapping_bars, \
    count_max_bars_at_time, generate_frost_condition_bars, generate_storm_condition_bars, \
    generate_laundry_day_condition_bars
from defines import WEATHER_ICON_LOOKUP

# Load config
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

print_weather_metadata(hourly_data)
forecast = build_forecast_datapoint_list(hourly_data, three_hourly_data)

# Limit the forecast to only the number of days we want to show on screen
first_time = forecast[0].time
forecast_days_limit = config["show_forecast_days"]
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
    print("Calculating condition bars...")
    condition_bars.extend(generate_frost_condition_bars(forecast, config))
    condition_bars.extend(generate_storm_condition_bars(forecast, config))
    condition_bars.extend(generate_laundry_day_condition_bars(forecast, config, dates, sun))

# If we're displaying calendar events, fetch from the internet. We need to do this early because if
# we have events (and particularly events at overlapping times) we will need to size the rest of
# the figure to allow space for them.
event_bars = generate_event_bars(config, sun, first_time, last_time) if show_calendar_events else []

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
fig = plotly.subplots.make_subplots()
fig.add_traces(create_traces(forecast, config))

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
    # For each forecast point from the *three hourly* forecast, look up the icon for its weather code, and add it to the
    # display. We only use the three hourly forecast so that the images are equally spaced.
    for dp in forecast:
        if dp.contains_three_hourly_data:
            image = PIL.Image.open(config["files"]["weather_icon_folder"] + "/" + WEATHER_ICON_LOOKUP[dp.weather_code])
            fig.add_layout_image(source=image, x=dp.time, y=weather_icon_y_pos, xref="x",
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
            y0_pos = events_y0_pos + 0.12 * (event_lines_required - add_to_row - 1)
            y1_pos = events_y1_pos + 0.12 * (event_lines_required - add_to_row - 1)
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
if min(get_temperatures(forecast)) <= config["frost_storm_warning"]["frost_temp"]:
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
    daytime_start = sun.get_sunrise_time(day).timestamp() * 1000
    daytime_end = sun.get_sunset_time(day).timestamp() * 1000
    fig.add_vrect(x0=daytime_start, x1=daytime_end,
                  fillcolor=config["style"]["daytime_color"],
                  opacity=config["style"]["daytime_opacity"],
                  annotation_text=day.strftime("%A"), annotation_position="inside top",
                  annotation_font_color=config["style"]["daytime_color"], annotation_font_size=16,
                  layer="below")

# Annotate figure with units
if config["enable_plots"]["temp"]:
    fig.add_annotation(text="C",
                       xref="paper", yref="paper",
                       x=0.99 if config["enable_plots"]["wind"] else 1.0, y=condition_y1_pos + 0.003,
                       font=dict(color=config["style"]["temp_color"], size=16), showarrow=False)
if config["enable_plots"]["wind"]:
    fig.add_annotation(text="kt",
                       xref="paper", yref="paper",
                       x=1.01, y=condition_y1_pos,
                       font=dict(color=config["style"]["wind_color"], size=16), showarrow=False)


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
