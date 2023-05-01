# Plotting functions for use with Home Meteogram Display Script

from plotly import graph_objects as go
from functions_weather import get_date_times, get_feels_likes, get_temperatures, get_precip_probs, get_wind_speeds, \
    get_wind_gust_speeds, get_humidities


# Creates the required traces for the plot
def create_traces(forecast, config):
    print("Plotting data...")
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
