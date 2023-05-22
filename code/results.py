import datetime
import sys
import json

if __name__ == "__main__":
    target_suburb = sys.argv[1]
    target_state = sys.argv[2]
    target_location = [target_suburb, target_state]
    target_suburb_display = target_suburb.title()
    target_suburb_file = target_suburb.lower().replace(" ", "-")

    suburb_record = open("results/results.json", "r")
    suburb_record = json.load(suburb_record)

    flag = False
    for suburb in suburb_record["suburbs"]:
        if suburb["internal"] == target_suburb:
            suburb["date"] = datetime.datetime.now().strftime("%d-%m-%Y")
            flag = True
            break
    if not flag:
        suburb_record["suburbs"].append({
            "internal": target_suburb,
            "name": target_suburb_display,
            "file": target_suburb_file,
            "date": datetime.datetime.now().strftime("%d-%m-%Y")
        })
    with open("results/results.json", "w") as outfile:
        json.dump(suburb_record, outfile, indent=4)