import datetime
import glob
import json
import os

if __name__ == "__main__":
    # check the folders in results
    states = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]

    suburbs = []
    for state in states:
        for file in glob.glob(f"results/{state}/*.geojson"):
            filename, _ = os.path.splitext(os.path.basename(file))
            suburbs.append({
                "internal": filename.replace("-", " ").upper(),
                "state": state,
                "name": filename.replace("-", " ").title(),
                "file": filename,
                "date": datetime.datetime.fromtimestamp(os.path.getmtime(file)).strftime("%d-%m-%Y"),
            })

    # sort by state + name
    suburb_record = {
        "suburbs": sorted(suburbs, key=lambda k: (k["state"], k["name"]))
    }

    with open("results/results.json", "w") as outfile:
        json.dump(suburb_record, outfile, indent=4)