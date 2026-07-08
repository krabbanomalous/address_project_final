import address_matcher as am
import parcels

# main
if __name__ == '__main__':
    succ, addr, confidence = am.get_address()
    if succ and confidence >= 0.1:
        latitude, longitude, geometry = parcels.get_data(addr)
        geometry = geometry.replace("\"", "")
        print("\nADDRESS FOUND:\n=====================================\n" + addr + f"({latitude:.5f}, {longitude:.5f})", ("\n\nConfidence: " + str(round(confidence * 1000) / 10) + "%\n"))
        parcels.draw_plot(addr, geometry)
    else:
        print(f"Unable to match address to \"{addr}\".")