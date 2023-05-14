# Plotting functions for use with Home Meteogram Display Script
import matplotlib.ticker
import matplotlib.transforms
import numpy
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import PIL.Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from scipy.interpolate import make_interp_spline

from defines import WEATHER_ICON_LOOKUP, DPI
from functions_condition_bars import find_row_for_new_bar
from functions_weather import get_date_times, get_feels_likes, get_temperatures, get_precip_probs, get_wind_speeds, \
    get_wind_gust_speeds, get_humidities, get_precip_amounts


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
def configure_layout(fig, forecast, config, lines_on_lower_subplot):
    # Set figure dimensions and remove unnecessary space
    fig.set_figwidth(config["plot_size"]["width"] / DPI)
    fig.set_figheight(config["plot_size"]["height"] / DPI)
    fig.tight_layout(pad=0)
    plt.subplots_adjust(wspace=0, hspace=0)

    # Set background color
    fig.patch.set_facecolor(config["style"]["background_color"])
    fig.axes[0].set_facecolor(config["style"]["background_color"])
    fig.axes[1].set_facecolor(config["style"]["background_color"])

    # Duplicate the default axes on the main subplot, maintaining a common x-axis but new y-axes for each because there
    # will be different ranges for temperature, wind, precip prob etc.
    main_subplot_default_axis = fig.axes[0]
    lower_subplot_default_axis = fig.axes[1]
    temp_axis = main_subplot_default_axis.twinx()
    precip_prob_axis = main_subplot_default_axis.twinx()
    precip_amount_axis = main_subplot_default_axis.twinx()
    wind_axis = main_subplot_default_axis.twinx()
    humidity_axis = main_subplot_default_axis.twinx()

    # Configure the new axes
    temp_axis.margins(x=0.0, y=0.0)
    temp_axis.set_ylim(config["scale"]["min_temp"], config["scale"]["max_temp"])
    temp_axis.tick_params(which="both", length=0, colors=config["style"]["temp_color"])
    temp_axis.patch.set_facecolor(config["style"]["background_color"])
    temp_axis.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=10.0))
    temp_axis.set_visible(config["enable_plots"]["temp"])

    precip_prob_axis.margins(x=0.0, y=0.0)
    # Set precip prob y-axis limits. Data is 0-100, but we give it 3 either side so that spline curves don't go
    # outside the plot
    precip_prob_axis.set_ylim(-3, 103)
    precip_prob_axis.yaxis.set_ticks([])
    precip_prob_axis.set_facecolor(config["style"]["background_color"])
    precip_prob_axis.set_visible(config["enable_plots"]["precip_prob"])

    precip_amount_axis.margins(x=0.0, y=0.0)
    precip_amount_axis.set_ylim(0, config["scale"]["max_precip_amount"])
    precip_amount_axis.yaxis.set_ticks([])
    precip_amount_axis.set_facecolor(config["style"]["background_color"])
    precip_amount_axis.set_visible(config["enable_plots"]["precip_amount"])

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
    # Set humidity y-axis limits. Data is 0-100, but we give it 3 either side so that spline curves don't go
    # outside the plot
    humidity_axis.set_ylim(-3, 103)
    humidity_axis.yaxis.set_ticks([])
    humidity_axis.set_facecolor(config["style"]["background_color"])
    humidity_axis.set_visible(config["enable_plots"]["humidity"])

    # Remove margins and hide the default axis for each subplot, to avoid displaying anything apart from what's
    # covered above
    main_subplot_default_axis.margins(x=0.0, y=0.0)
    main_subplot_default_axis.xaxis.set_ticks([])
    main_subplot_default_axis.yaxis.set_ticks([])
    lower_subplot_default_axis.margins(x=0.0, y=0.0)
    lower_subplot_default_axis.xaxis.set_ticks([])
    lower_subplot_default_axis.yaxis.set_ticks([])

    # Set default axis for the top subplot to have a y-axis spanning 0 to 1. We don't use this for plotting data, but we
    # can use knowledge of its range to arrange things like the day names relative to the top
    main_subplot_default_axis.set_ylim([0, 1])

    # Bottom subplot axis doesn't display any data, so it needs its limits set manually. x-axis has datetimes to match
    # the top. For convenience, we set its y-axis to be from zero to -(1 - the number of lines of information we want
    # to display on it); we can therefore use the y-axis to lay out those lines.
    date_times = numpy.array(list(map(lambda dt: dt.timestamp() * 1000, get_date_times(forecast))))
    lower_subplot_default_axis.set_xlim([date_times[0], date_times[len(date_times) - 1]])
    lower_subplot_default_axis.set_ylim([-lines_on_lower_subplot, 0])


# Creates the required traces for the plot
def add_traces(fig, forecast, config):
    # Get the date times of the forecast points, which will be used as the x-axis for all plots.
    # Interpolate 1000 points to give us a basis for spline calculation
    date_times = numpy.array(list(map(lambda dt: dt.timestamp() * 1000, get_date_times(forecast))))
    date_times_interpolated = numpy.linspace(date_times[0], date_times[len(date_times) - 1], 1000)

    # Go through each plot type. If it's enabled, find the appropriate axes, create a spline to
    # show the data as a curve rather than straight lines, then plot it.
    # Indices into the axes list start at 2, because we have a default unused axis on both subplots in [0] and [1].
    # Start with precipitation amount (the bar graph) so that everything else renders on top.
    if config["enable_plots"]["precip_amount"]:
        precip_amount_axis = fig.axes[4]
        precip_amounts = get_precip_amounts(forecast)
        # Calculate the widths of the bars, some will be an hour but further along the forecast they will be three hours
        widths = list(map(lambda dp: (1 if dp.contains_hourly_data else 3) * 3600000, forecast))
        # Ignore the first and last points to make sure the end widths don't exceed the limits of the plot
        precip_amount_axis.bar(date_times[1:-1], precip_amounts[1:-1], width=widths[1:-1], bottom=0,
                               color=config["style"]["precip_amount_color"])

    if config["enable_plots"]["temp"]:
        temp_axis = fig.axes[2]
        temps = numpy.array(get_feels_likes(forecast) if config["use_feels_like_temp"] else get_temperatures(forecast))
        spline = make_interp_spline(date_times, temps)
        temp_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                       color=config["style"]["temp_color"],
                       linewidth=3)

    if config["enable_plots"]["precip_prob"]:
        precip_prob_axis = fig.axes[3]
        precip_probs = numpy.array(get_precip_probs(forecast))
        spline = make_interp_spline(date_times, precip_probs)
        precip_prob_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                              color=config["style"]["precip_prob_color"],
                              linewidth=3)

    if config["enable_plots"]["wind"]:
        wind_axis = fig.axes[5]
        wind_speeds = numpy.array(get_wind_speeds(forecast))
        spline = make_interp_spline(date_times, wind_speeds)
        wind_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                       color=config["style"]["wind_color"],
                       linewidth=3)

    if config["enable_plots"]["gust"]:
        wind_axis = fig.axes[5]  # Same axis as wind
        wind_gust_speeds = numpy.array(get_wind_gust_speeds(forecast))
        spline = make_interp_spline(date_times, wind_gust_speeds)
        wind_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                       color=config["style"]["wind_color"],
                       linestyle=config["style"]["gust_line_style"],
                       linewidth=3)

    if config["enable_plots"]["humidity"]:
        humidity_axis = fig.axes[6]
        humidities = numpy.array(get_humidities(forecast))
        spline = make_interp_spline(date_times, humidities)
        humidity_axis.plot(date_times_interpolated, spline(date_times_interpolated),
                           color=config["style"]["humidity_color"],
                           linewidth=3)


# Annotate figure with units
def add_units(fig, config, y_pos_fraction):
    if config["enable_plots"]["temp"]:
        fig.axes[0].annotate("C", (1.008, y_pos_fraction),
                             xycoords="figure fraction", color=config["style"]["temp_color"],
                             ha="center", va="bottom", annotation_clip=False)
    if config["enable_plots"]["wind"]:
        fig.axes[0].annotate("kt", (1.024, y_pos_fraction),
                             xycoords="figure fraction", color=config["style"]["wind_color"],
                             ha="center", va="bottom", annotation_clip=False)


# Annotate figure with daytime blocks
def add_daytime_regions(fig, config, dates, sun, first_time, last_time):
    for day in dates:
        start = sun.get_sunrise_time(day)
        end = sun.get_sunset_time(day)
        midday_timestamp = (start.timestamp() * 1000 + end.timestamp() * 1000) / 2.0
        # Ensure the regions don't end up outside the plot area
        start = max(start, first_time)
        end = min(end, last_time)
        fig.axes[0].axvspan(start.timestamp() * 1000, end.timestamp() * 1000,
                            color=config["style"]["daytime_color"],
                            alpha=config["style"]["daytime_opacity"])
        fig.axes[0].annotate(day.strftime("%A"), (midday_timestamp, 0.97),
                             xycoords="data",
                             color=config["style"]["daytime_color"],
                             ha="center", va="top", clip_box=fig.axes[1].clipbox, clip_on=True)


# Annotate figure with frost lines
def add_frost_lines(fig, config):
    fig.axes[2].axhline(y=config["frost_storm_warning"]["frost_temp"],
                        color=config["style"]["frost_color"],
                        alpha=config["style"]["frost_line_opacity"],
                        linewidth=2, linestyle=config["style"]["frost_line_style"])
    fig.axes[2].axhline(y=0,
                        color=config["style"]["ice_color"],
                        alpha=config["style"]["frost_line_opacity"],
                        linewidth=2, linestyle=config["style"]["frost_line_style"])


# Annotate figure with weather icons
def add_weather_icons(fig, forecast, config):
    # For each forecast point from the *three hourly* forecast, look up the icon for its weather code, and add it to the
    # display. We only use the three hourly forecast so that the images are equally spaced, and omit the first and last
    # to avoid overrunning the edge of the plot.
    for dp in forecast[1:-1]:
        if dp.contains_three_hourly_data:
            image = PIL.Image.open(config["files"]["weather_icon_folder"] + "/" + WEATHER_ICON_LOOKUP[dp.weather_code])
            imagebox = OffsetImage(image, zoom=0.4)
            imagebox.image.axes = fig.axes[1]
            ab = AnnotationBbox(imagebox,
                                (dp.time.timestamp() * 1000, -0.5), xycoords="data",
                                frameon=False)
            fig.axes[1].add_artist(ab)


# Annotate figure with condition bars
def add_condition_bars(fig, config, condition_bars, show_weather_icons):
    for bar in condition_bars:
        # Calculate positions on the bottom subplot. y-axis position depends on whether we have weather icons above it
        # or not
        y_pos = -2 if show_weather_icons else -1
        x_pos = bar["start"].timestamp() * 1000
        y_height = 0.9
        x_width = (bar["end"].timestamp() - bar["start"].timestamp()) * 1000
        rect = patches.Rectangle((x_pos, y_pos), x_width, y_height,
                                 facecolor=bar["color"], alpha=config["style"]["condition_bars_opacity"])
        fig.axes[1].add_patch(rect)
        fig.axes[1].text(x_pos + x_width / 2.0, y_pos + y_height / 2.0 - 0.05, bar["text"],
                         color=bar["color"], ha="center", va="center", clip_box=fig.axes[1].clipbox, clip_on=True)


# Annotate figure with calendar event bars
def add_calendar_events(fig, config, event_bars, show_weather_icons, show_condition_bars):
    already_added_event_bars = []
    for bar in event_bars:
        # Calculate positions on the bottom subplot. y-axis position depends on whether we have weather icons and/or
        # condition bars above it, and if multiple event rows are being used, which row it is on.
        add_to_row = find_row_for_new_bar(already_added_event_bars, bar)
        y_pos = -1 - (1 if show_weather_icons else 0) - (1 if show_condition_bars else 0) - add_to_row
        x_pos = bar["start"].timestamp() * 1000
        y_height = 0.9
        x_width = (bar["end"].timestamp() - bar["start"].timestamp()) * 1000
        rect = patches.Rectangle((x_pos, y_pos), x_width, y_height,
                                 facecolor=bar["color"], alpha=config["style"]["calendar_event_bars_opacity"])
        fig.axes[1].add_patch(rect)
        fig.axes[1].text(x_pos + x_width / 2.0, y_pos + y_height / 2.0 - 0.05, bar["text"],
                         color=bar["color"], ha="center", va="center", clip_box=fig.axes[1].clipbox, clip_on=True)

        # Store which row the bar was added to, and add it to the list for checking next time around the loop.
        bar["row"] = add_to_row
        already_added_event_bars.append(bar)
