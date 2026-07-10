import address_compiler as ac
import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.pool import NullPool

load_dotenv()

password = os.getenv("SUPABASE_KEY")

SUPABASE_HOST = os.getenv("SUPABASE_HOST")       # e.g. aws-0-us-east-1.pooler.supabase.com
SUPABASE_PORT = os.getenv("SUPABASE_PORT", "5432")
SUPABASE_DB   = os.getenv("SUPABASE_NAME", "postgres")
SUPABASE_USER = os.getenv("SUPABASE_USER")       # e.g. postgres.<project-ref>
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")

DATE_COLUMNS = ["DateUpdate", "Date_Acq"]
DB_URL = (
    f"postgresql+psycopg2://{SUPABASE_USER}:{SUPABASE_PASSWORD}"
    f"@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}"
    f"?sslmode=require"
)
# gets engine
def get_engine():
    return create_engine(
        DB_URL,
        poolclass=NullPool,  # important if you're using the pgbouncer/transaction pooler port (6543)
    )

def ensure_postgis(engine):
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

# gets loaded counties to skip
def get_loaded_counties(engine):
    if not inspect(engine).has_table("addresses"):
        return set()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT county FROM addresses"))
        return {row[0] for row in result}

# loads all counties
def load_all_counties(counties, limit=254):
    engine = get_engine()
    ensure_postgis(engine)
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