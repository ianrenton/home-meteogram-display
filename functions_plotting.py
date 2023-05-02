# Plotting functions for use with Home Meteogram Display Script
import matplotlib.ticker
import matplotlib.transforms
import numpy
import matplotlib.pyplot as plt
import PIL.Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox, DrawingArea, AnchoredText
from matplotlib.patches import Rectangle
from scipy.interpolate import make_interp_spline

from defines import WEATHER_ICON_LOOKUP, DPI
from functions_condition_bars import count_overlapping_bars
from functions_weather import get_date_times, get_feels_likes, get_temperatures, get_precip_probs, get_wind_speeds, \
    get_wind_gust_speeds, get_humidities


# Utility method to get how wide the plot area should be, as a fraction of the overall figure image.
# It will be less than 1 to allow space for axis labels on the right.
def get_plot_width_fraction(config):
    return 0.97 if config["enable_plots"]["wind"] else 0.99


# Gets the horizontal size, in points, spanned by one second of time on the chart. Used for positioning
# and sizing condition & event bars. Will be a very small number.
def get_one_second_point_size(config, first_time, last_time):
    total_width_points = config["plot_size"]["width"] / DPI * 72
    plot_width_points = total_width_points * get_plot_width_fraction(config)
    time_span_seconds = (last_time - first_time).total_seconds()
    return plot_width_points / time_span_seconds


# Configure layout
def configure_layout(fig, config, plot_height_fraction):
    # Set figure dimensions
    fig.set_figwidth(config["plot_size"]["width"] / DPI)
    fig.set_figheight(config["plot_size"]["height"] / DPI)
    fig.tight_layout(pad=0)

    # Set background color
    fig.patch.set_facecolor(config["style"]["background_color"])

    # Duplicate the axes, maintaining a common x-axis but new y-axes.
    # Set axis area height to accomodate plot_bottom_y_pos and width to accomodate right-hand
    # side axis labels.
    default_axis = fig.add_axes([0, 1 - plot_height_fraction,
                                 get_plot_width_fraction(config),
                                 plot_height_fraction])
    temp_axis = default_axis.twinx()
    precip_axis = default_axis.twinx()
    wind_axis = default_axis.twinx()
    humidity_axis = default_axis.twinx()

    # Configure the new axes
    temp_axis.margins(x=0.0, y=0.0)
    temp_axis.set_ylim(config["scale"]["min_temp"], config["scale"]["max_temp"])
    temp_axis.tick_params(which="both", length=0, colors=config["style"]["temp_color"])
    temp_axis.patch.set_facecolor(config["style"]["background_color"])
    temp_axis.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=10.0))
    temp_axis.set_visible(config["enable_plots"]["temp"])

    precip_axis.margins(x=0.0, y=0.0)
    precip_axis.set_ylim(-1, 100)
    precip_axis.yaxis.set_ticks([])
    precip_axis.set_facecolor(config["style"]["background_color"])
    precip_axis.set_visible(config["enable_plots"]["precip_prob"])

    wind_axis.margins(x=0.0, y=0.0)
    wind_axis.set_ylim(0, config["scale"]["max_wind_speed"])
    wind_axis.tick_params(which="both", length=0, colors=config["style"]["wind_color"])
    wind_axis.set_facecolor(config["style"]["background_color"])
    wind_axis.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=10.0))
    wind_axis_label_offset = matplotlib.transforms.ScaledTranslation(15 / 72, 0, fig.dpi_scale_trans)
    for label in wind_axis.yaxis.get_majorticklabels():
        label.set_transform(label.get_transform() + wind_axis_label_offset)
    wind_axis.set_visible(config["enable_plots"]["wind"])

    humidity_axis.margins(x=0.0, y=0.0)
    humidity_axis.set_ylim(0, 100)
    humidity_axis.yaxis.set_ticks([])
    humidity_axis.set_facecolor(config["style"]["background_color"])
    humidity_axis.set_visible(config["enable_plots"]["humidity"])

    # Configure (hide) the default axis
    default_axis.margins(x=0.0, y=0.0)
    default_axis.set_visible(False)


# Creates the required traces for the plot
def add_traces(fig, forecast, config):
    # Get the date times of the forecast points, which will be used as the x-axis for all plots.
    # Interpolate 1000 points to give us a basis for spline calculation
    date_times = numpy.array(list(map(lambda dt: dt.timestamp() * 1000, get_date_times(forecast))))
    date_times_interpolated = numpy.linspace(date_times.min(), date_times.max(), 1000)

    # Go through each plot type. If it's enabled, find the appropriate axes, create a spline to
    # show the data as a curve rather than straight lines, then plot it.
    if config["enable_plots"]["temp"]:
        temp_axis = fig.axes[1]
        temps = numpy.array(get_feels_likes(forecast) if config["use_feels_like_temp"] else get_temperatures(forecast))
        spline = make_interp_spline(date_times, temps)
        temp_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                       color=config["style"]["temp_color"],
                       linewidth=3)

    if config["enable_plots"]["precip_prob"]:
        precip_axis = fig.axes[2]
        precip_probs = numpy.array(get_precip_probs(forecast))
        spline = make_interp_spline(date_times, precip_probs)
        precip_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                         color=config["style"]["precip_color"],
                         linewidth=3)

    if config["enable_plots"]["wind"]:
        wind_axis = fig.axes[3]
        wind_speeds = numpy.array(get_wind_speeds(forecast))
        spline = make_interp_spline(date_times, wind_speeds)
        wind_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                       color=config["style"]["wind_color"],
                       linewidth=3)

    if config["enable_plots"]["gust"]:
        wind_axis = fig.axes[3]
        wind_gust_speeds = numpy.array(get_wind_gust_speeds(forecast))
        spline = make_interp_spline(date_times, wind_gust_speeds)
        wind_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                       color=config["style"]["wind_color"],
                       linestyle=config["style"]["gust_line_style"],
                       linewidth=3)

    if config["enable_plots"]["humidity"]:
        humidity_axis = fig.axes[4]
        humidities = numpy.array(get_humidities(forecast))
        spline = make_interp_spline(date_times, humidities)
        humidity_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                           color=config["style"]["humidity_color"],
                           linewidth=3)


# Annotate figure with units
def add_units(config, y_pos_fraction):
    if config["enable_plots"]["temp"]:
        plt.annotate("C", (0.975 if config["enable_plots"]["wind"] else 1.0, y_pos_fraction),
                     xycoords="figure fraction", color=config["style"]["temp_color"],
                     ha="center", va="center")
    if config["enable_plots"]["wind"]:
        plt.annotate("kt", (0.99, y_pos_fraction),
                     xycoords="figure fraction", color=config["style"]["wind_color"],
                     ha="center", va="center")


# Annotate figure with daytime blocks
def add_daytime_regions(config, dates, sun, first_time, last_time):
    for day in dates:
        start = sun.get_sunrise_time(day)
        end = sun.get_sunset_time(day)
        midday_timestamp = (start.timestamp() * 1000 + end.timestamp() * 1000) / 2.0
        # Ensure the regions don't end up outside the plot area
        start = max(start, first_time)
        end = min(end, last_time)
        plt.axvspan(start.timestamp() * 1000, end.timestamp() * 1000,
                    color=config["style"]["daytime_color"],
                    alpha=config["style"]["daytime_opacity"])
        plt.annotate(day.strftime("%A"), (midday_timestamp, 100),
                     xycoords="data",
                     xytext=(0, -5), textcoords="offset points",
                     color=config["style"]["daytime_color"],
                     ha="center", va="top")


# Annotate figure with frost lines
def add_frost_lines(fig, config):
    fig.axes[1].axhline(y=config["frost_storm_warning"]["frost_temp"],
                        color=config["style"]["frost_color"],
                        alpha=config["style"]["frost_line_opacity"],
                        linewidth=2, linestyle=config["style"]["frost_line_style"])
    fig.axes[1].axhline(y=0,
                        color=config["style"]["ice_color"],
                        alpha=config["style"]["frost_line_opacity"],
                        linewidth=2, linestyle=config["style"]["frost_line_style"])


# Annotate figure with weather icons
def add_weather_icons(fig, forecast, config, weather_icon_points_below_axis):
    # For each forecast point from the *three hourly* forecast, look up the icon for its weather code, and add it to the
    # display. We only use the three hourly forecast so that the images are equally spaced, and omit the first and last
    # to avoid overrunning the edge of the plot.
    for dp in forecast[1:-1]:
        if dp.contains_three_hourly_data:
            image = PIL.Image.open(config["files"]["weather_icon_folder"] + "/" + WEATHER_ICON_LOOKUP[dp.weather_code])
            imagebox = OffsetImage(image, zoom=0.4)
            imagebox.image.axes = fig.axes[1]
            ab = AnnotationBbox(imagebox,
                                (dp.time.timestamp() * 1000, config["scale"]["min_temp"]), xycoords="data",
                                xybox=(0, -weather_icon_points_below_axis), boxcoords="offset points",
                                frameon=False)
            fig.axes[1].add_artist(ab)


# Annotate figure with condition bars
def add_condition_bars(fig, config, condition_bars, first_time, last_time, condition_bar_points_below_axis):
    for bar in condition_bars:
        middle_timestamp = (bar["start"].timestamp() + bar["end"].timestamp()) / 2 * 1000
        width_seconds = bar["end"].timestamp() - bar["start"].timestamp()
        width_points = width_seconds * get_one_second_point_size(config, first_time, last_time)
        da = DrawingArea(width_points, 15)
        background = Rectangle((0, 0), width=width_points, height=15,
                               facecolor=bar["color"], alpha=config["style"]["condition_bars_opacity"])
        da.add_artist(background)
        ab = AnnotationBbox(da,
                            (middle_timestamp, config["scale"]["min_temp"]), xycoords="data",
                            xybox=(0, -condition_bar_points_below_axis), boxcoords="offset points",
                            frameon=False, pad=0)
        fig.axes[1].add_artist(ab)
        plt.annotate(bar["text"],
                     (middle_timestamp, 50), xycoords="data",
                     xytext=(0, -condition_bar_points_below_axis), textcoords="offset points",
                     color=bar["color"],
                     annotation_clip=False,
                     ha="center", va="center")


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
