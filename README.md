To use, run scripts\main.py through your operating system's terminal.

## Modules:
**address_compiler.py**: Pulls from TxGIO, downloads all readable files from ZIP files of all supported counties.
**address_matcher.py**: Takes input from user and attempts to match to closest address.
**database_compiler.py**: Originally meant to upload all data to local PSQL databse. Should not have to use otherwise, given this repo uses Supabase.
**main.py**: Initializes program and all its modules.
**parcels.py**: Matches address (post-database-comparison) to information provided by RealEstateAPI.com, returns coordinates and parcel boundaries.

Made with Python 3.14.6.
