from dotenv import load_dotenv
import os
import sys
import psycopg2
import re
import time

load_dotenv()

DB_KEY = os.getenv("DB_PASSWORD")
DB_CONFIG = {
    "host": os.environ.get("SUPABASE_HOST"),
    "port": os.environ.get("SUPABASE_PORT", "5432"),
    "dbname": os.environ.get("SUPABASE_POSTGRES", "postgres"),
    "user": os.environ.get("SUPABASE_USER", "postgres"),
    "password": os.environ.get("SUPABASE_KEY"),
    "sslmode": "require",
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
def normalize_address(addr: str, invert: bool = False) -> str:
    addr = addr.lower()

    for long_form, short_form in NORMALIZED_ROAD_ENDS.items():
        pattern = short_form if invert else long_form
        replacement = long_form if invert else short_form
        addr = re.sub(
            rf"\b{re.escape(pattern)}\b",
            replacement,
            addr
        )

    return addr.upper()
 
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
    starting_number = re.match(r"\d+", user_input)
    starting_number = starting_number.group()
    street_name = user_input.split()[1]

    query = """
        SELECT
            "Full_Addr",
            "Post_Comm",
            "County",
            "State",
            "Post_Code",
            similarity("full_addr_norm", %(input)s) AS sim
        FROM public.addresses
        WHERE "Add_Number" = %(house_num)s
            AND "Full_Addr" %% %(input)s
            AND "St_Name" %% %(street_name)s
        ORDER BY sim DESC
        LIMIT 1;
    """
 
    with conn.cursor() as cur:
        cur.execute(query, {"input": user_input, "house_num": starting_number, "street_name": street_name})
        row = cur.fetchone()
    
    if row is not None:
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
        contents = user_input.split()
 
        while not input_accepted:
            user_input = input("Please enter address: ").strip()
            starting_number = re.match(r"\d+", user_input)

            input_accepted = any(c.isalpha() for c in user_input) and any(c.isdigit() for c in user_input) and starting_number != None
            if input_accepted == False and not user_input.lower() in ("quit", "exit"):
                if starting_number != None:
                    print("Input must contain at least one (1) number and one (1) letter.")
                else:
                    print("Input must start with a number.")
            else:
                input_accepted = True
 
        if user_input is not None and not user_input.lower() in ("quit", "exit"):
            is_success = False
            search_start = int(time.time() * 1000)
            search_end = int(time.time() * 1000)
 
            addr = normalize_address(user_input)
            conf = 0
 
            # non-normed address
            row = find_closest_address(conn, addr.upper())
            if row:
                is_success = True
                addr, conf = format_result(row)
 
            search_end = int(time.time() * 1000)
            return (is_success, addr, conf, user_input, search_end - search_start)
        else:
            if user_input.lower() in ("quit", "exit"):
                return False, "User aborted.", 0
    finally:
        conn.close()