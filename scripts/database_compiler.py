import address_compiler as ac
import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text

load_dotenv()

password = os.getenv("DB_PASSWORD")

DATE_COLUMNS = ["DateUpdate", "Date_Acq"]
DB_URL = f"postgresql+psycopg2://postgres:{password}@localhost:5432/tx_addrs"

# gets engine
def get_engine():
    return create_engine(DB_URL)

# gets loaded counties to skip
def get_loaded_counties(engine):
    if not inspect(engine).has_table("addresses"):
        return set()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT county FROM addresses"))
        return {row[0] for row in result}

# loads all counties
def load_all_counties(counties, limit = 254):
    engine = get_engine()
    loaded = get_loaded_counties(engine)

    with engine.connect() as conn:
        print("Current database:", conn.execute(text("SELECT current_database()")).scalar())
        print("PostGIS version:", conn.execute(text("SELECT PostGIS_Version()")).scalar())

    processed = 0

    for county_name, county in counties.items():
        if county_name in loaded:
            print(f"Skipping {county_name}, already loaded.")
            continue

        print(f"Processing {county_name}...")
 
        try:
            out_dir = ac.download_layer_files(county)
        except Exception as e:
            print(f"  [!] Skipping {county_name} after error: {e}")
            continue
    
        layers = ac.read_layers(out_dir, county_name)
 
        for layer_name, gdf in layers.items():
            if gdf.empty:
                continue

            for col in DATE_COLUMNS:
                if col in gdf.columns:
                    gdf[col] = pd.to_datetime(
                        gdf[col].astype(str),
                        format="%Y%m%d%H%M%S",
                        errors="coerce"
                    )

            gdf.to_postgis(
                name=layer_name,
                con=engine,
                if_exists="append",
                index=False,
            )
            print(f"  -> wrote {len(gdf)} rows to '{layer_name}'")
 
        processed += 1
        if limit and processed >= limit:
            break