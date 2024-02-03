# Config-related functions for use with Home Meteogram Display Script

import pathlib
import sys

import yaml


# Load config. Exit if it cannot be found or is improperly set up.
def load_config():
    config_file = pathlib.Path("config.yml")
    if not config_file.exists():
        print(
            "The config.yml file does not exist. You will need to create this by copying config.yml.example and filling"
            "in the required parameters. See the README for more information.")
        sys.exit(1)
    with open('config.yml', 'r') as file:
        config = yaml.safe_load(file)
    if not config["met_office_datahub_api_key"]:
        print("Your Met Office DataHub API key is not set. Copy the 'config.yml.example' file to 'config.yml' and"
              " insert your API key. Then try running this software again.")
        sys.exit(1)
    return config
