# "Data Point" class for use with Home Meteogram Display Script
# Used to hold a single forecasted data point, and abstract away the differences between the
# data returned by the "hourly" and "three-hourly" API calls, which do not contain the same
# data!

from datetime import datetime
import pytz
from defines import MET_OFFICE_DATE_TIME_FORMAT_STRING


class DataPoint:
    time = None
    air_temp_C = None
    feels_like_temp_C = None
    dew_point_C = None
    wind_speed_knots = None
    wind_direction_deg = None
    wind_gust_knots = None
    wind_max_gust_knots = None
    weather_code = None
    visibility_miles = None
    humidity = None
    pressure_mbar = None
    uv_index = None
    probability_of_precipitation = None
    probability_of_snow = None
    probability_of_heavy_snow = None
    probability_of_rain = None
    probability_of_heavy_rain = None
    probability_of_hail = None
    probability_of_thunder = None
    precipitation_rate_mm_per_hour = None
    total_precipitation_amount_mm = None
    total_snow_amount_mm = None
    contains_hourly_data = False
    contains_three_hourly_data = False

    # Load this object with a data point from the time series of an *hourly* API call
    def load_hourly_data(self, data):
        self.contains_hourly_data = True
        self.load_data(data)

    # Load this object with a data point from the time series of a *three hourly* API call
    def load_three_hourly_data(self, data):
        self.contains_three_hourly_data = True
        self.load_data(data)

    # Load this object with data from either API call
    def load_data(self, data):
        if "time" in data:
            self.time = pytz.utc.localize(datetime.strptime(data["time"], MET_OFFICE_DATE_TIME_FORMAT_STRING))
        if "screenTemperature" in data:
            self.air_temp_C = data["screenTemperature"]
        elif "minScreenAirTemp" in data and "maxScreenAirTemp" in data:
            self.air_temp_C = (data["maxScreenAirTemp"] + data["minScreenAirTemp"]) / 2.0
        if "feelsLikeTemp" in data:
            self.feels_like_temp_C = data["feelsLikeTemp"]
        if "feelsLikeTemperature" in data:
            self.feels_like_temp_C = data["feelsLikeTemperature"]
        if "screenDewPointTemperature" in data:
            self.dew_point_C = data["screenDewPointTemperature"]
        if "windSpeed10m" in data:
            self.wind_speed_knots = data["windSpeed10m"] * 1.944
        if "windDirectionFrom10m" in data:
            self.wind_direction_deg = data["windDirectionFrom10m"]
        if "windGustSpeed10m" in data:
            self.wind_gust_knots = data["windGustSpeed10m"] * 1.944
        if "max10mWindGust" in data:
            self.wind_max_gust_knots = data["max10mWindGust"] * 1.944
        if "significantWeatherCode" in data:
            self.weather_code = data["significantWeatherCode"]
        if "visibility" in data:
            self.visibility_miles = data["visibility"] / 1609.0
        if "screenRelativeHumidity" in data:
            self.humidity = data["screenRelativeHumidity"]
        if "mslp" in data:
            self.pressure_mbar = data["mslp"] / 100.0
        if "uvIndex" in data:
            self.uv_index = data["uvIndex"]
        if "precipitationRate" in data:
            self.precipitation_rate_mm_per_hour = data["precipitationRate"]
        if "totalPrecipAmount" in data:
            self.total_precipitation_amount_mm = data["totalPrecipAmount"]
        if "totalSnowAmount" in data:
            self.total_snow_amount_mm = data["totalSnowAmount"]
        if "probOfPrecipitation" in data:
            self.probability_of_precipitation = data["probOfPrecipitation"]
        if "probOfSnow" in data:
            self.probability_of_snow = data["probOfSnow"]
        if "probOfHeavySnow" in data:
            self.probability_of_heavy_snow = data["probOfHeavySnow"]
        if "probOfRain" in data:
            self.probability_of_rain = data["probOfRain"]
        if "probOfHeavyRain" in data:
            self.probability_of_heavy_rain = data["probOfHeavyRain"]
        if "probOfHail" in data:
            self.probability_of_hail = data["probOfHail"]
        if "probOfSferics" in data:
            self.probability_of_thunder = data["probOfSferics"]

    # Returns whether this data point is considered "stormy" based on config
    def is_stormy(self, config):
        return self.probability_of_precipitation and self.wind_gust_knots and \
            self.probability_of_precipitation >= config["frost_storm_warning"]["storm_precip_prob"] \
            and self.wind_gust_knots >= config["frost_storm_warning"]["storm_gust_speed"]

    # Returns whether this data point is considered "frosty" based on config
    def is_frosty(self, config):
        # Storminess takes precedence so return false if this datapoint is stormy
        return self.air_temp_C and self.air_temp_C <= config["frost_storm_warning"]["frost_temp"] \
            and not self.is_stormy(config)
