from csv import DictReader
import pathlib
import glob
import json
import requests
from collections import defaultdict
import shutil
import os

ROOT_PATH = pathlib.Path(__file__).parent.absolute()
INVALID = "AMANDA_EVANS_IS_THE_COOLEST"

# Your custom GSCRIPT URL must go here
GSCRIPT_URL = "https://script.google.com/macros/s/AKfycbx6rGudqIPIf0I6RoE4syneJEehSdYshZq7jpiPs67VC6WILojdd82lLZCa1pQ0bxUbuQ/exec"
YEAR = INVALID

GSB_HONORS_IGNITE = "GSB Honors Ignite"

ATTRIBUTE_KEYS = {
    GSB_HONORS_IGNITE: "Honors / Ignite",
    "Felt Testing Required": "International ESL FELT Placement",
    "Manresa": "Manresa",
    "Deans": "Deans",
    "Higher Ed Opportunity Program": "HEOP",
    "National Merit Finalist": "National Merit Finalist",
}

HIGH_ACHIEVER_KEYS = ["Deans", "National Merit Finalist"]

AP_ATTRIBUTE_KEYS = {"Y": "Claim"}

AP_KEYS = [
    "AP ECON MACRO",
    "AP CALC BC",
    "AP CALC AB",
    "AP ECON MICRO",
    "AP STAT",
    "IB ECON",
    "IB MATH",
    "IB THEA",
    "AP ART",
]

SURVEY_KEY_TO_ATTRIBUTE_KEY = {
    "FIDN": "FIDN",
    "FIRST": "First",
    "LAST": "Last",
    "PERSONAL EMAIL": "Personal Email",
    "FORDHAM EMAIL": "Fordham Email",
    "LIST AP/IB EXAMS": "AP Classes",
    "LANGUAGE CHOICE": "LANGUAGE CHOICE",
    "CALCULUS IN HIGH SCHOOL": "CALCULUS IN HIGH SCHOOL",
}

ATTRIBUTE_KEYS_TO_POSSIBLE_VALUES = {}

for AP_KEY in AP_KEYS:
    UPPER_KEY = AP_KEY.upper()
    SURVEY_KEY_TO_ATTRIBUTE_KEY[UPPER_KEY] = UPPER_KEY
    ATTRIBUTE_KEYS_TO_POSSIBLE_VALUES[UPPER_KEY] = AP_ATTRIBUTE_KEYS

ATTRIBUTE_START = 1  # Inclusive
ATTRIBUTE_STOP = 11  # Exclusive
for index in range(ATTRIBUTE_START, ATTRIBUTE_STOP):
    SURVEY_KEY_TO_ATTRIBUTE_KEY[f"ATTR{index}"] = ATTRIBUTE_KEYS

ATTRIBUTE_KEYS_TO_MANDATORY_VALUES = {
    "International ESL FELT Placement": "International",
    "Honors / Ignite": {
        GSB_HONORS_IGNITE: GSB_HONORS_IGNITE,
        "GSB Honors GPHP": "GPHP",
    },
}


def get_csv_contents(path):
    rows = []
    with open(path, "r") as f:
        reader = DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def survey_to_attributes(people):
    output = defaultdict(dict)
    for person in people:
        myOutput = {}
        myId = None
        high_achiever = False
        for survey_key, survey_value in person.items():
            if survey_key == "FIDN":
                myId = survey_value
            attribute_key = SURVEY_KEY_TO_ATTRIBUTE_KEY.get(survey_key)
            if attribute_key is None or survey_value == "":
                continue
            if isinstance(attribute_key, dict):
                attribute_key = attribute_key.get(survey_value)
                if attribute_key is None:
                    continue
            attribute_value = ATTRIBUTE_KEYS_TO_MANDATORY_VALUES.get(
                attribute_key,
                ATTRIBUTE_KEYS_TO_POSSIBLE_VALUES.get(attribute_key, survey_value),
            )
            if isinstance(attribute_value, dict):
                attribute_value = attribute_value.get(survey_value)
                if attribute_value is None:
                    continue
            if not high_achiever and attribute_key in HIGH_ACHIEVER_KEYS:
                high_achiever = True
                myOutput["High Achiever"] = "Y"
            myOutput[attribute_key] = attribute_value
        output[myId] = myOutput
    return output


def send_to_script(year, headers, people):
    print(
        f"Uploading {len(people.keys())} items for the year {year}\nHeaders:\n{headers}"
    )
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    response = requests.post(
        GSCRIPT_URL,
        json.dumps(people),
        params={"year": year, "headers": headers},
        headers=headers,
    )
    print(response.content)
    if response.status_code == 200:
        print("Successfully updated the sheet")
        return response
    else:
        print(f"{response.status_code}\n{response.body}")


if __name__ == "__main__":
    print(f"This program will ingest all CSV files found in the following folder.\n {ROOT_PATH}/new/\n Converted files can be found in {ROOT_PATH}/conversions/ and finishied files in {ROOT_PATH}/conversions/ in case there is an issue uploading them after conversion.")
    input(f"Press enter to continue...")
    if YEAR is INVALID:
        print("You must input a year to use, this will be matched with the name of a tab in Google Sheets")
        USER_INPUT = input("Year (Ex: 2023): ")
        while YEAR is INVALID:
            try:
                int(USER_INPUT.strip())
                YEAR = USER_INPUT.strip()
            except Exception:
                USER_INPUT = input("That was not a valid year. Must be a whole integer. Try again: ")
    
    # Create folders in case they don't exist
    os.makedirs(f"{ROOT_PATH}/new", exist_ok=True) 
    os.makedirs(f"{ROOT_PATH}/conversions", exist_ok=True)
    os.makedirs(f"{ROOT_PATH}/finished", exist_ok=True)

    # Begin processing CSVs one by one.
    csvs = glob.glob(f"{ROOT_PATH}/new/*.csv")
    total_csvs = len(csvs)
    print(f"Processing {total_csvs} CSV{'s' if total_csvs != 1 else ''}")
    for index, path in enumerate(csvs, start=1):
        people = survey_to_attributes(get_csv_contents(path))
        filename = os.path.basename(path)
        unique_keys = defaultdict(bool)
        print(f"Got data for {len(people.keys())} students")
        for id, person in people.items():
            for key in person.keys():
                unique_keys[key] = True
        unique_keys = list(unique_keys.keys())
        typeless_path = path.replace(".csv", "").replace(f"{ROOT_PATH}/new", f"{ROOT_PATH}/conversions")
        with open(f"{typeless_path}.json", "w") as f:
            json.dump(people, f, indent=4)
        shutil.move(path, f"{ROOT_PATH}/finished")
        print(f"Finished processing CSV: {index}/{total_csvs}\nSaved to {ROOT_PATH}/finished/{filename}")
        print(f"Now sending to Google Script")
        try:
            send_to_script(YEAR, unique_keys, people)
        except Exception as e:
            print("Failed to upload converted output. Fix your issues and try again for this file.", e)
    

    input("Press Enter to exit...")
    # for personId, person in people.items():
    #     print(person)
