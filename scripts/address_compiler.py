import geopandas as gpd
import os
from remotezip import RemoteZip
import requests
import shapely
import sys

collection_id = "f9bfd25d-cf2c-4e2f-9b44-43d4bb915390"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SHP_FOLDER_PREFIX = "shp/"
SHP_COMPONENT_EXTS = {".shp", ".shx", ".dbf", ".prj", ".cpg"}

count = 252

# fetches data
def retrieve_data():
    response = requests.get(
        "https://api.tnris.org/api/v1/resources",
        params = { "collection_id" : collection_id }
    )
    resources = response.json()
    results = resources.get("results")

    return results

# retrieve wanted members of folder only
def _wanted_members(namelist):
    wanted = []

    for name in namelist:
        normalized = name.replace("\\", "/")
        if not normalized.lower().startswith(SHP_FOLDER_PREFIX):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in SHP_COMPONENT_EXTS:
            wanted.append(name)

    return wanted

# get all valid file paths
def _walk_files(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            yield os.path.join(dirpath, fn)

# finds shape files
def _find_shp(out_dir):
    for path in _walk_files(out_dir):
        if path.lower().endswith(".shp"):
            return path
    return None

# download shapefile contents only
def download_layer_files(county):
    county_name = county.get("area_type_name")
    url = county.get("resource")
    out_dir = f"data/address_points/{county_name}"

    os.makedirs(out_dir, exist_ok = True)

    # skip downloading if .shp file already exists
    if any(f.lower().endswith(".shp") for f in _walk_files(out_dir)):
        return out_dir

    try:
        with RemoteZip(url, headers = HEADERS) as rz:
            print(f"Downloading {county_name}...")
            members = _wanted_members(rz.namelist())
            if not members:
                print(f"  [!] No shp/ folder contents found in zip for {county_name}")
                return out_dir
            for member in members:
                rz.extract(member, path=out_dir)
                print(f"  extracted {member}")
    except Exception as e:
        print(f"  [!] Range-based extraction failed for {county_name}: {e}")
        raise

    return out_dir

# read address points
def read_layers(out_dir, county_name, target_crs = "EPSG:4326"):
    result = {}

    shp_path = _find_shp(out_dir)
    if shp_path:
        addresses = gpd.read_file(shp_path)
        if addresses.crs is not None:
            addresses = addresses.to_crs(target_crs)

        addresses["geometry"] = addresses["geometry"].apply(shapely.force_2d)
        addresses["county"] = county_name
        result["addresses"] = addresses
    else:
        print(f"  [!] No .shp found for {county_name} in {out_dir}")

    return result

# compiles addresses
def compile_data(data):
    final_data = {}
    index = 0

    for entry in data:
        if entry.get("area_type") == "county":
            index += 1
            sys.stdout.flush()
            county_name = entry.get("area_type_name")
            final_data[county_name] = entry

            print(f"{county_name} loaded ({index}/{count} counties complete.)")
    
    print("Addresses of all counties downloaded successfully.")
    return {k : v for k, v in sorted(final_data.items(), key = lambda item: item[0])}