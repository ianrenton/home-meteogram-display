# Static definitions for use with Home Meteogram Display Script

# Mapping of Met Office significant weather code (index 0-30) to icon file we will use to display it.
WEATHER_ICON_LOOKUP = ["weather-clear-night.png", "weather-clear.png", "weather-few-clouds-night.png",
                       "weather-few-clouds.png", "", "weather-fog.png", "weather-fog.png", "weather-overcast.png",
                       "weather-overcast.png", "weather-showers-scattered.png", "weather-showers-scattered.png",
                       "weather-showers-scattered.png", "weather-showers-scattered.png", "weather-showers.png",
                       "weather-showers.png", "weather-showers.png", "weather-showers-scattered.png",
                       "weather-showers-scattered.png", "weather-showers.png", "weather-storm.png", "weather-storm.png",
                       "weather-storm.png", "weather-snow.png", "weather-snow.png", "weather-snow.png",
                       "weather-snow.png", "weather-snow.png", "weather-snow.png", "weather-storm.png",
                       "weather-storm.png", "weather-storm.png"]

# Datetime format string used in the API
MET_OFFICE_DATE_TIME_FORMAT_STRING = "%Y-%m-%dT%H:%MZ"

# Dots per inch used to render Matplotlib figures (which deal in inches) to the pixel size
# we actually want. Pretty arbitrary as we will be using this figure to convert from the pixel
# size we want to inches when creating the plot, then back again to write it to an image file.
DPI = 100.0
