from dotenv import load_dotenv
import os
import sys
import psycopg2
import re

load_dotenv()

DB_KEY = os.getenv("DB_PASSWORD")
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": os.environ.get("PGPORT", "5432"),
    "dbname": os.environ.get("PGDATABASE", "tx_addrs"),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", DB_KEY),
}

NORMALIZED_ROAD_ENDS = {
    "farm road"      : "fm",
    "north"          : "n",
    "south"          : "s",
    "east"           : "e",
    "west"           : "w",
    "road"           : "rd",
    "street"         : "st",
    "drive"          : "dr",
    "avenue"         : "ave",
    "boulevard"      : "blvd",
    "lane"           : "ln",
}

FALLBACK_MIN_SIMILARITY = 0.15

# normalizes address
def normalize_address(addr, invert=False):
    fin_addr = addr.lower()

    for long_form, short_form in NORMALIZED_ROAD_ENDS.items():
        for long_form, short_form in NORMALIZED_ROAD_ENDS.items():
            pattern = short_form if invert else long_form
            replacement = long_form if invert else short_form
            fin_addr = re.sub(rf"\b{re.escape(pattern)}\b", replacement, fin_addr)

    return fin_addr

# connects to database
def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as exc:
        sys.exit(f"Could not connect to the database: {exc}")

# ensures trgm extension is operational
def ensure_trgm_extension(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    conn.commit()

# finds closest address
def find_closest_address(conn, user_input):
    query = """
        SELECT
            "Full_Addr",
            "Post_Comm",
            "County",
            "State",
            "Post_Code",
            similarity("Full_Addr", %(input)s) AS sim
        FROM public.addresses
        WHERE "Full_Addr" %% %(input)s
        ORDER BY sim DESC
        LIMIT 1;
    """

    with conn.cursor() as cur:
        cur.execute(query, {"input": user_input})
        row = cur.fetchone()
    
    if row is not None:
        return row

    # no clear match
    fallback_query = """
        SELECT
            "Full_Addr",
            "Post_Comm",
            "County",
            "State",
            "Post_Code",
            similarity("Full_Addr", %(input)s) AS sim
        FROM public.addresses
        ORDER BY sim DESC
        LIMIT 1;
    """

    with conn.cursor() as cur:
        cur.execute(fallback_query, {"input": user_input})
        row = cur.fetchone()
 
    if row and row[-1] is not None and row[-1] >= FALLBACK_MIN_SIMILARITY:
        return row
    return None

# formats result
def format_result(row):
    full_addr, post_comm, county, state, post_code, sim = row
    city_or_county = post_comm.strip() if post_comm and post_comm.strip() else county

    return (
        f"{full_addr}\n"
        f"{city_or_county}, TX {post_code}\n"
    ), sim

# gets input
def get_address():
    conn = get_connection()
    try:
        ensure_trgm_extension(conn)
        print("Address matcher ready. Type \"quit\" or \"exit\" to abort.\n")

        input_accepted = False
        user_input = ""

        while not input_accepted:
            user_input = input("Please enter address: ").strip()
            input_accepted = any(c.isalpha() for c in user_input) and any(c.isdigit() for c in user_input)
            if input_accepted == False and not user_input.lower() in ("quit", "exit"):
                print("Input must contain at least one (1) number and one (1) letter.")
            else:
                input_accepted = True

        if user_input is not None and not user_input.lower() in ("quit", "exit"):
            is_success = False

            normed = normalize_address(user_input)
            non_normed = user_input

            norm_conf = 0
            non_norm_conf = 0

            # normed address
            row1 = find_closest_address(conn, normed.upper())
            if row1:
                is_success = True
                normed, norm_conf = format_result(row1)
            else:
                normed = user_input

            # non-normed address
            row2 = find_closest_address(conn, non_normed.upper())
            if row2:
                is_success = True
                non_normed, non_norm_conf = format_result(row2)
            else:
                return True, normed, norm_conf, user_input

            return (is_success, normed, norm_conf, user_input) if norm_conf > non_norm_conf else (is_success, non_normed, non_norm_conf, user_input)
        else:
            if user_input.lower() in ("quit", "exit"):
                return False, "User aborted.", 0
    finally:
        conn.close()