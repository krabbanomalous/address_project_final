from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt
from shapely import wkt

import json
import os
import requests

geolocator = Nominatim(user_agent="tx_addrs")
url = "https://api.realestateapi.com/v1/PropertyParcel"

load_dotenv()

LINE_COLOR = "#00ff84"
FILL_COLOR = "#80ffc2"

PASSWORD = os.getenv("REAPI_KEY")

headers = {
    "x-api-key": PASSWORD,
    "content-type": "application/json"
}

# gets metadata of address
def get_address_info(address):
    payload = {
        "address": address
    }

    response = requests.post(url, json = payload, headers = headers)

    if response.status_code == 200:
        parcel_data = response.json()
        return parcel_data.get("data")
    else:
        raise Exception(f"[!] Failed to get parcel boundary info: Error code [{response.status_code}] ({response.text})")

# gets coordinates
def get_location(data):
    return data.get("latitude"), data.get("longitude"), data.get("geometry")

# gets property boundaries
def get_data(address):
    addr_info = get_address_info(address)
    return addr_info.get("latitude"), addr_info.get("longitude"), json.dumps(addr_info.get("geometry"), indent = 2)

# draws plot
def draw_plot(address, plot):
    polygon = wkt.loads(plot)

    x, y = polygon.exterior.xy

    fig, ax = plt.subplots(figsize = (6, 6))
    ax.plot(x, y, color = LINE_COLOR, linewidth = 2)
    ax.fill(x, y, color = FILL_COLOR, alpha = 1)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(address)
    ax.set_aspect("equal")
    plt.show()