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