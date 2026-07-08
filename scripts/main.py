import address_matcher as am
import parcels
import os
from pathlib import Path
from datetime import datetime

# main
if __name__ == '__main__':
    succ, addr, confidence, start_input = am.get_address()
    if succ and confidence >= 0.1:
        # displays info
        conf_format = str(round(confidence * 1000) / 10)
        latitude, longitude, geometry = parcels.get_data(addr)
        match_success = False

        if latitude != None and longitude != None and geometry != None:
            match_success = True
            geometry = geometry.replace("\"", "")

            print("\nADDRESS FOUND:\n=====================================\n" + addr + f"({latitude:.5f}, {longitude:.5f})", ("\n\nConfidence: " + conf_format + "%\n"))

            parcels.draw_plot(addr, geometry)
        else:
            print(f"Unable to match address to \"{start_input}\".")

        # logs to file
        formatted_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(BASE_DIR, "logs.txt")

        try:
            with open(log_path, "a", encoding="utf-8") as file:
                if match_success:
                    file.write(f"\n{formatted_ts}\nINPUT: {start_input} \n\n{addr}\nCOORDINATES: ({latitude:.5f}, {longitude:.5f})\nPLOT SHAPE: {geometry}\nCONFIDENCE: {conf_format}%\n=================== [[]] ===================")
                else:
                    file.write(f"\n{formatted_ts}\nINPUT: {start_input} \n\nFailed to return address with input.\n=================== [[]] ===================")
            print("Logged to file.")
        except Exception as e:
            print(f"Logging failed: {e}")
    else:
        print(f"Unable to match address to \"{start_input}\".")