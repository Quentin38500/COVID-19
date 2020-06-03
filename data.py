import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import datetime
import csv

date = datetime.datetime.now()

# On configure Google Sheets
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("COVID 19").sheet1

# On configure Requests
url = "https://api.covid19api.com/summary"
url_rea = 'https://www.data.gouv.fr/fr/datasets/r/08c18e08-6780-452d-9b8c-ae244ad529b3'
url_france = "https://api.apify.com/v2/datasets/QBiS7pd57KVmFfgZM/items?format=json&clean=1"

# On récupère les données

# Données John Hopkins
r = requests.get(url)
datas = json.loads(r.content)
countries = ["Italy", "Spain", "United Kingdom", "Germany", "Sweden"]
total_confirmed = {}
total_deaths = {}
population = {"France": 67000000, "Italy": 60000000, "Spain": 47000000, "United Kingdom": 67000000, "Germany": 83000000, "Sweden": 10000000}
for data in datas["Countries"]:
    if data["Country"] in countries:
        total_confirmed[data["Country"]] = data["TotalConfirmed"]
        total_deaths[data["Country"]] = data["TotalDeaths"]

# Données Auvergne Rhone Alpes
with requests.get(url_rea, stream=True) as r:
    lines = (line.decode('utf-8') for line in r.iter_lines())
    for row in csv.reader(lines):
        for item in row:
            item = item.replace(";", ",")
            item = item.replace('"', "")
            item = item.split(",")
            if date.month < 10:
                month = str(f"0{date.month}")
            else:
                month = date.month
            if date.day < 10:
                day_minus_one = str(f"0{date.day - 1}")
                day_minus_two = str(f"0{date.day - 2}")
            else:
                day_minus_one = date.day - 1
                day_minus_two = date.day - 2
            if item[0] == "84" and item[1] == "0" and item[2] == f"{date.year}-{month}-{day_minus_one}":
                rea_auvergne_rhone_alpes = item[4]
                hosp_auvergne_rhone_alpes = item[3]
                dc_auvergne_rhone_alpes = item[6]

# Données France
r = requests.get(url_france)
datas = json.loads(r.content)
for data in datas:
    if data["lastUpdatedAtSource"] == f"{date.year}-{month}-{day_minus_one}T00:00:00.000Z":
        total_confirmed["France"] = data["infected"]
        total_deaths["France"] = data["deceased"]
    if data["lastUpdatedAtSource"] == f"{date.year}-{month}-{day_minus_two}T00:00:00.000Z":
        cases_before = data["infected"]
        deaths_before = data["deceased"]
try:
    new_cases = total_confirmed["France"] - cases_before
except:
    new_cases = "?"
try:
    new_deaths = total_deaths["France"] - deaths_before
except:
    new_deaths = "?"

#  On actualise les données sur Google Sheets
x = 3
for country in total_confirmed:
    sheet.update_cell(4, x, total_confirmed[country])
    try:
        sheet.update_cell(5, x, (total_confirmed[country] * 100000) / population[country])
    except:
        print("Certaines données n'ont pas été mises à jour !")
    x += 1

x = 3
for country in total_deaths:
    sheet.update_cell(6, x, total_deaths[country])
    try:
        sheet.update_cell(7, x, (total_deaths[country] * 100000) / population[country])
    except:
        print("Certaines données n'ont pas été mises à jour !")
    x += 1

if sheet.cell(12, 2).value != f"{day_minus_one}/{date.month}/{date.year}":
    insert_row = ["", f"{day_minus_one}/{date.month}/{date.year}", new_cases, new_deaths, "", rea_auvergne_rhone_alpes, hosp_auvergne_rhone_alpes, dc_auvergne_rhone_alpes]
    sheet.insert_row(insert_row, 12)
