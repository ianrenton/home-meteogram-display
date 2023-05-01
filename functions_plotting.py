# Plotting functions for use with Home Meteogram Display Script
import PIL.Image
from plotly import graph_objects as go

from defines import WEATHER_ICON_LOOKUP
from functions_condition_bars import count_overlapping_bars
from functions_weather import get_date_times, get_feels_likes, get_temperatures, get_precip_probs, get_wind_speeds, \
    get_wind_gust_speeds, get_humidities


# Creates the required traces for the plot
def create_traces(forecast, config):
    date_times = get_date_times(forecast)
    # noinspection PyTypeChecker
    temp_trace = go.Scatter(x=date_times,
                            y=(get_feels_likes(forecast) if config["use_feels_like_temp"] else get_temperatures(
                                forecast)),
                            name="Temperature",
                            yaxis="y1",
                            line_shape='spline',
                            marker=dict(color=config["style"]["temp_color"]),
                            line=dict(color=config["style"]["temp_color"], width=4))
    # noinspection PyTypeChecker
    precip_trace = go.Scatter(x=date_times,
                              y=get_precip_probs(forecast),
                              name="Precipitation Probability",
                              yaxis="y2",
                              line_shape='spline',
                              marker=dict(color=config["style"]["precip_color"]),
                              line=dict(color=config["style"]["precip_color"], width=4))
    # noinspection PyTypeChecker
    wind_trace = go.Scatter(x=date_times,
                            y=get_wind_speeds(forecast),
                            name="Wind Speed",
                            yaxis="y3",
                            line_shape='spline',
                            marker=dict(color=config["style"]["wind_color"]),
                            line=dict(color=config["style"]["wind_color"], width=4))
    # noinspection PyTypeChecker
    gust_trace = go.Scatter(x=date_times,
                            y=get_wind_gust_speeds(forecast),
                            name="Gust Speed",
                            yaxis="y3",
                            line_shape='spline',
                            marker=dict(color=config["style"]["gust_color"]),
                            line=dict(color=config["style"]["gust_color"], width=4,
                                      dash=config["style"]["gust_line_style"]))
    # noinspection PyTypeChecker
    humidity_trace = go.Scatter(x=date_times,
                                y=get_humidities(forecast),
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
    return traces


# Configure layout
def configure_layout(fig, config, plot_bottom_y_pos):
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


# Annotate figure with units
def add_units(fig, config, y_pos):
    if config["enable_plots"]["temp"]:
        fig.add_annotation(text="C",
                           xref="paper", yref="paper",
                           x=0.99 if config["enable_plots"]["wind"] else 1.0, y=y_pos,
                           font=dict(color=config["style"]["temp_color"], size=16), showarrow=False)
    if config["enable_plots"]["wind"]:
        fig.add_annotation(text="kt",
                           xref="paper", yref="paper",
                           x=1.01, y=y_pos,
                           font=dict(color=config["style"]["wind_color"], size=16), showarrow=False)


# Annotate figure with daytime blocks
def add_daytime_regions(fig, config, dates, sun):
    for day in dates:
        daytime_start = sun.get_sunrise_time(day).timestamp() * 1000
        daytime_end = sun.get_sunset_time(day).timestamp() * 1000
        fig.add_vrect(x0=daytime_start, x1=daytime_end,
                      fillcolor=config["style"]["daytime_color"],
                      opacity=config["style"]["daytime_opacity"],
                      line_width=0,
                      annotation_text=day.strftime("%A"), annotation_position="inside top",
                      annotation_font_color=config["style"]["daytime_color"], annotation_font_size=16,
                      layer="below")


# Annotate figure with frost lines
def add_frost_lines(fig, config):
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


# Annotate figure with weather icons
def add_weather_icons(fig, forecast, config, weather_icon_y_pos):
    # For each forecast point from the *three hourly* forecast, look up the icon for its weather code, and add it to the
    # display. We only use the three hourly forecast so that the images are equally spaced.
    for dp in forecast:
        if dp.contains_three_hourly_data:
            image = PIL.Image.open(config["files"]["weather_icon_folder"] + "/" + WEATHER_ICON_LOOKUP[dp.weather_code])
            fig.add_layout_image(source=image, x=dp.time, y=weather_icon_y_pos, xref="x",
                                 yref="paper", xanchor="center", sizex=8000000, sizey=1)


# Annotate figure with condition bars
def add_condition_bars(fig, config, condition_bars, condition_y0_pos, condition_y1_pos):
    for bar in condition_bars:
        fig.add_shape(type="rect",
                      x0=bar["start"].timestamp() * 1000, x1=bar["end"].timestamp() * 1000, xref="x",
                      y0=condition_y0_pos, y1=condition_y1_pos, yref="paper",
                      label=dict(text=bar["text"], font=dict(color=bar["color"],
                                                             size=config["style"]["condition_bars_font_size"])),
                      fillcolor=bar["color"],
                      opacity=config["style"]["condition_bars_opacity"],
                      line_width=0,
                      layer="below")


# Annotate figure with calendar event bars
def add_calendar_events(fig, config, event_bars, events_y0_pos, events_y1_pos, event_lines_required,
                        max_calendar_event_bar_rows):
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
                          line_width=0,
                          layer="below")
        already_added_event_bars.append(bar)
