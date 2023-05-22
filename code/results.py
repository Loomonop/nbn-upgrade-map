import datetime
import json
import os

if __name__ == "__main__":
    suburb_record = {"suburbs": []}

    # check the folders in results
    states = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]

    for state in states:
        # check if the folder exists
        if not os.path.exists("results/" + state):
            continue
        for file in os.listdir("results/" + state):
            if file.endswith(".geojson"):
                suburb_record["suburbs"].append({
                    "internal": file.split(".")[0].replace("-", " ").upper(),
                    "state": state,
                    "name": file.split(".")[0].replace("-", " ").title(),
                    "file": file.split(".")[0],
                    "date": datetime.datetime.fromtimestamp(os.path.getmtime("results/" + state + "/" + file)).strftime("%d-%m-%Y")
                })

    with open("results/results.json", "w") as outfile:
        json.dump(suburb_record, outfile, indent=4)