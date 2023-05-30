import glob
import json
import os
from datetime import datetime

if __name__ == "__main__":
    # check the folders in results
    states = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]

    suburbs = []
    for state in states:
        for file in glob.glob(f"results/{state}/*.geojson"):
            filename, _ = os.path.splitext(os.path.basename(file))
            with open(file, "r", encoding="utf-8") as infile:
                result = json.load(infile)

            # fixup any missing generated dates
            if "generated" not in result:
                result["generated"] = datetime.now().isoformat()
                with open(file, "w", encoding="utf-8") as outfile:
                    json.dump(result, outfile, indent=1)  # indent=1 is to minimise size increase

            suburbs.append({
                "internal": filename.replace("-", " ").upper(),
                "state": state,
                "name": filename.replace("-", " ").title(),
                "file": filename,
                "date": datetime.fromisoformat(result["generated"]).strftime("%d-%m-%Y"),
            })

    # sort by state + name
    suburb_record = {
        "suburbs": sorted(suburbs, key=lambda k: (k["state"], k["name"]))
    }

    with open("results/results.json", "w") as outfile:
        json.dump(suburb_record, outfile, indent=4)