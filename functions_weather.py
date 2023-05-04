# Weather-related functions for use with Home Meteogram Display Script

import json
import pathlib
import sys
from urllib.request import Request, urlopen
from datetime import datetime, timedelta

import pytz
from datapoint import DataPoint
from defines import MET_OFFICE_DATE_TIME_FORMAT_STRING


# Fetch weather data as JSON, either from the given URL (in which case also save to the given
# cache file) or, if the cache file date is within the last 10 minutes, return the contents of
# the cache file instead.
def get_live_or_cached_weather_data(api_url, cache_file_path, client_key, client_secret):
    read_from_file = False
    data_json = ""
    cache_file = pathlib.Path(cache_file_path)
    # Check if we already fetched data recently
    if cache_file.exists() and datetime.fromtimestamp(
            cache_file.stat().st_mtime) > datetime.now() - timedelta(minutes=10):
        # Already got recent data, so use it if possible
        print("Weather cache file was updated less than 10 minutes ago, re-using that to spare the API...")
        data_json = cache_file.read_text()
        if data_json:
            read_from_file = True
        else:
            print("Tried and failed to read cache file, will query API instead.")
    if not read_from_file:
        # Didn't have recent cached data so query the API for new data
        print("Querying weather API...")
        req = Request(api_url)
        req.add_header("X-IBM-Client-Id", client_key)
        req.add_header("X-IBM-Client-Secret", client_secret)
        req.add_header("accept", "application/json")
        resp = urlopen(req)
        data_json = resp.read()
        if data_json:
            print("Writing local cache file...")
            cache_file.parent.mkdir(exist_ok=True, parents=True)
            cache_file.write_text(json.dumps(json.loads(data_json), indent=2))
        else:
            print(
                "Could not query the Met Office DataHub API. Check your API key is correct and that you have internet"
                "connectivity.")
            sys.exit(1)
    weather_data = json.loads(data_json)
    return weather_data


# Given a set of JSON weather data, print the metadata about forecast location and model time.
def print_weather_metadata(weather_data):
    forecast_location = dict(name=weather_data["features"][0]["properties"]["location"]["name"],
                             lat=weather_data["features"][0]["geometry"]["coordinates"][1],
                             lon=weather_data["features"][0]["geometry"]["coordinates"][0],
                             alt=weather_data["features"][0]["geometry"]["coordinates"][2],
                             distance_from_requested_point=weather_data["features"][0]["properties"][
                                 "requestPointDistance"])
    model_run_datetime = pytz.utc.localize(
        datetime.strptime(weather_data["features"][0]["properties"]["modelRunDate"],
                          MET_OFFICE_DATE_TIME_FORMAT_STRING))
    print("Forecast data modelled at " + str(model_run_datetime))
    print("Forecast location: " + forecast_location["name"] + " (" + str(
        forecast_location["distance_from_requested_point"]) + "m from requested lat/lon point)")


# Combines the hourly and three-hourly JSON datasets from the API, and produces a list of
# DataPoints sorted by time.
def build_forecast_datapoint_list(hourly_data, three_hourly_data):
    # Iterate through the three-hourly data, converting each entry in the time series to
    # a DataPoint, and adding them to a list
    forecast = []
    for point in three_hourly_data["features"][0]["properties"]["timeSeries"]:
        dp = DataPoint()
        dp.load_three_hourly_data(point)
        forecast.append(dp)
    # Now add the hourly data. (We do this second, so it can overwrite anything from the
    # three-hourly data, on the assumption that hourly is better data). If there is no
    # existing DataPoint with the given time, add it, otherwise merge it.
    for point in hourly_data["features"][0]["properties"]["timeSeries"]:
        time = pytz.utc.localize(datetime.strptime(point["time"], MET_OFFICE_DATE_TIME_FORMAT_STRING))
        if time in get_date_times(forecast):
            index_to_update = next(i for i, v in enumerate(forecast) if v.time == time)
            forecast[index_to_update].load_hourly_data(point)
        else:
            dp = DataPoint()
            dp.load_hourly_data(point)
            forecast.append(dp)

    return sorted(forecast, key=lambda dp2: dp2.time)


# Get a set of datetimes to use as the x-axis for chart plots. This is just the list of all
# datetimes in the forecast
def get_date_times(forecast):
    return list(map(lambda dp: dp.time, forecast))


# Get a temperature series to plot on the chart. This provides y-axis values; corresponding
# x-axis values can be retrieved by calling get_date_times
def get_temperatures(forecast):
    return list(map(lambda dp: dp.air_temp_C, forecast))


# Get a "feels like" series to plot on the chart. This provides y-axis values; corresponding
# x-axis values can be retrieved by calling get_date_times
def get_feels_likes(forecast):
    return list(map(lambda dp: dp.feels_like_temp_C, forecast))


# Get a precipitation probability series to plot on the chart. This provides y-axis values; corresponding
# x-axis values can be retrieved by calling get_date_times
def get_precip_probs(forecast):
    return list(map(lambda dp: dp.probability_of_precipitation, forecast))


# Get a wind speed series to plot on the chart. This provides y-axis values; corresponding
# x-axis values can be retrieved by calling get_date_times
def get_wind_speeds(forecast):
    return list(map(lambda dp: dp.wind_speed_knots, forecast))


# Get a wind gust speed series to plot on the chart. This provides y-axis values; corresponding
# x-axis values can be retrieved by calling get_date_times
def get_wind_gust_speeds(forecast):
    return list(map(lambda dp: dp.wind_gust_knots, forecast))


# Get a humidity series to plot on the chart. This provides y-axis values; corresponding
# x-axis values can be retrieved by calling get_date_times
def get_humidities(forecast):
    return list(map(lambda dp: dp.humidity, forecast))
