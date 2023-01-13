#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Earthquake Preparation Tool

@author: DataFarmers 
Grace Kim, Sajujya Gangopadhyay, Michael Rodriguez, Miguel Avila Fuentes

10.12.2022
"""

# Import libraries
import folium.plugins as plugins
import json
import requests
import pandas as pd
import numpy as np
import folium
import webbrowser
import os
from pretty_html_table import build_table
from bs4 import BeautifulSoup

# %% ### EARTHQUAKE DATA ### - from api

# Get earthquakes with magnitude > 5.0
apiURL = 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=33.5&maxlatitude=35.1&minlongitude=-119&maxlongitude=-117.5&starttime=1970-01-01&minmagnitude=5'
headers = {'Content-Type': 'application/json'}
response = requests.get(apiURL, headers=headers)
if response.status_code == 200:
    data = json.loads(response.content.decode('utf-8'))

# properties- list of dicts
properties = []
for item in data['features']:
    properties.append(item)

# 1. Earthquake info - put into a dataframe called quakes
earthquakes = []
for earthquake in properties:
    earthquakes.append(earthquake['properties'])
quakes_df = pd.DataFrame(data=earthquakes)

# Extract just magnitude, time, and place from quakes_df
quakes_df = quakes_df[['mag', 'time', 'place']]

# Convert time column into a year/month/day
quakes_df['time'] = pd.to_datetime(quakes_df['time'], unit='ms')

# Rename columns
quakes_df.rename(columns={"time": "Datetime","mag": "Magnitude", "place": "Place"}, inplace=True)

# 2. Earthquake location - put into dataframe called quakesLoc
geometry = []
for geo in properties:
    geometry.append(geo['geometry'])
quakesLoc_df = pd.DataFrame(data=geometry)

# Parse through lists of coordinates in the column - putting into two lists
eqCoord = quakesLoc_df['coordinates']
lat = []
lon = []
for i in eqCoord:
    lat.append(i[1])
    lon.append(i[0])

# Put lat and lon lists into a dataframe
quakesLoc_df = pd.DataFrame({'Lat': lat, 'Lon': lon})
quakesLoc_df = quakesLoc_df.astype({'Lat': float, 'Lon': float})

# Add zip code list
zipcodeslist = [92821, 91709, 91381, 91383, 91343, 91326, 91381, 93040, 93063,
                93063, 91381, 91344, 91335, 91011, 91711, 91106, 93203, 91776,
                91770, 90292, 91351, 91351, 91351, 91351, 92358]

# Join two dataframes into final dataframe - contains magnitutde, time, place, lat, and lon
earthquakesLA_df = pd.concat([quakes_df, quakesLoc_df], axis=1)

# Add column to front of the dataframe
earthquakesLA_df.insert(loc=0, column='Zipcode', value=zipcodeslist)

# %% ### HOUSING DATA ### - from webscraping

# Read housing units & price data in to a dataframe
housing_df = pd.read_csv("LA_housing_data.csv")

# Drop the null values to calculate median value
dropped_df = housing_df.dropna()

# Data cleaning- remove the $ value and strip commas
dropped_df.iloc[:, 1:3] = dropped_df.iloc[:, 1:3].replace({'\$': '', ',': ''}, regex=True)

# Calculate median home value & fill null values with it
med_home_value = dropped_df["Median Home Value"].median()
housing_df.fillna(med_home_value, inplace=True)

# Data cleaning- remove the $ value and strip commas
housing_df.iloc[:, 1:3] = housing_df.iloc[:, 1:3].replace({'\$': '', ',': ''}, regex=True)

# Change data types to floats for calculation below
housing_df = housing_df.astype({"Zip Code": str, 'Housing Units': float, 'Median Home Value': float})

# 1. Set median cost of insurance to $1,177 -
median_cost_of_insurance = 1177

# 2. Calculate cost of insuring every dollar (med insurance cost / med home value)
cost_of_insuring_every_dollar = median_cost_of_insurance / med_home_value

# 3. Calculate "Raw cost of Insurance per House"
housing_df["Raw cost of Insurance per House"] = housing_df["Median Home Value"] * cost_of_insuring_every_dollar

# 4. Calculate "Cost of insuring 10% of the houses in the ZIP Code"
housing_df["Cost of insuring 10% of the houses in the ZIP Code"] = \
    housing_df["Raw cost of Insurance per House"] * \
    housing_df["Housing Units"] * 0.1

# %% ### INCOME DATA ### - from live webscraping
# Create dataframe just for the bottom 10% median income households

# Median Income Table from laalmanac
httpString = 'http://www.laalmanac.com/employment/em12c.php'
page = requests.get(httpString)
soup = BeautifulSoup(page.content, 'html.parser')
content = soup.find(class_="content-box")
table = content.find_all("table")
data = pd.read_html(str(table))
income_df = data[0]

# Remove "Community" column
income_df.drop(['Community'], axis=1, inplace=True)

# Sort by decreasing median income
income_df.sort_values(by="Estimated Median Income", inplace=True)

# Changing the index in that order
index_now = list(income_df.index)
temp_index = list(range(len(index_now)))
new_index = dict(zip(index_now, temp_index))
income_df.rename(index=new_index, inplace=True)

# Delete the non-numeric values - only 1 non numeric value found for Glendale
income_df = income_df.loc[0:280]

# Data cleaning- remove the $ value and strip commas
income_df["Estimated Median Income"] = income_df["Estimated Median Income"].replace({'\$': '', ',': ''}, regex=True)

# Change data types to floats for calculation below
income_df = income_df.astype({"Zip Code": str, 'Estimated Median Income': float})

# Merge income_df dataframe to housing_df dataframe on ("ZIP")
bottom_10_df = pd.merge(housing_df, income_df, on='Zip Code')
bottom_10_df.sort_values(by="Estimated Median Income", inplace=True)

# Calculation of 10 percentile
bottom_10_percentile = income_df["Estimated Median Income"].quantile(q=0.10)  # 48723

# Go through dataframe and just get the rows with median income less than the bottom_10_percentile
bottom_10_percentile_incomes = []
for item in bottom_10_df["Estimated Median Income"]:
    if item < bottom_10_percentile:
        bottom_10_percentile_incomes.append(item)

bottom_10_df = bottom_10_df.iloc[0: len(bottom_10_percentile_incomes)]
bottom_10_int_df = bottom_10_df.copy()

# %% ### SHELTERS DATA ### - from csv
### POPULATION DATA ### - from csv (this was webscraped)

# Create DataFrame of shelters
shelters_df = pd.read_csv('LA_shelters_data.csv')
shelters_df['ZIP'] = shelters_df['ZIP'].astype(str)

# Group zipcodes and sum the evacuation capacities of shelters in each zipcode
shelterbyzip_df = shelters_df.groupby(['ZIP'], as_index=False)['EVAC_CAP'].sum()

# Create DataFrame of la_pop_df for population info
Cal_pop_df = pd.read_csv("LA_population_data.csv")
# capitalize all column names to be consistent
Cal_pop_df.columns = Cal_pop_df.columns.str.upper()
la_pop_df = Cal_pop_df.loc[Cal_pop_df['COUNTY'] == 'Los Angeles'][['ZIP', 'POP']].copy()
la_pop_df['ZIP'] = la_pop_df['ZIP'].astype(str)

# Merge la_pop_df dataframe to shelterbyzip_df dataframe on ("ZIP")
shelterbyzip_df = shelterbyzip_df.merge(la_pop_df, on='ZIP', how='outer')

# Rename columns
shelterbyzip_df.rename(columns={"ZIP": "Zip Code", "EVAC_CAP": "Shelter Capacity", "POP": "Population"}, inplace=True)

# Add column of percentage to calculate shelter capacity rate
# Only calculate for zip codes that have a population value
for i in range(len(shelterbyzip_df)):
    if shelterbyzip_df['Population'].iloc[i] != 0:
        shelterbyzip_df['Shelter Capacity Percentage'] = round(
            (shelterbyzip_df['Shelter Capacity'] / shelterbyzip_df['Population']) * 100, 2)

# Replace inf to nan
shelterbyzip_df['Shelter Capacity Percentage'] = shelterbyzip_df['Shelter Capacity Percentage'].replace(np.inf, np.nan)

# Merge shelterbyzip_df dataframe to housing_df dataframe on ("ZIP")
final_df = housing_df.merge(shelterbyzip_df, on='Zip Code', how='outer')
final_int_df = final_df.copy()
# %% # ZIP CODE BOUNDARIES DATA ### - from geojson file

# Load GeoJSON
with open('la-zip-code-areas-2012.geojson', 'r') as jsonFile:
    data = json.load(jsonFile)

# Remove zip codes not in our dataset
lazipcodes = []
for i in range(len(data['features'])):
    if data['features'][i]['properties']['name'] in list(shelterbyzip_df['Zip Code'].astype(str).unique()):
        lazipcodes.append(data['features'][i])

# Create new JSON object
new_json = dict.fromkeys(['type', 'features'])
new_json['type'] = 'FeatureCollection'
new_json['features'] = lazipcodes

# Save JSON object as a new file
open('la-county-zipcode-areas.json', "w").write(
    json.dumps(new_json, sort_keys=True, indent=4, separators=(',', ':'))
)

# Read updated GeoJSON file
la_zip = r'la-county-zipcode-areas.json'

# %% ### CREATE MAP ###

# initiate a folium map
la_map = folium.Map(location=[34.0522, -118.2437], zoom_start=11)

# create a choropleth map with shelterbyzip_df
folium.Choropleth(
    geo_data=la_zip,
    data=shelterbyzip_df,
    columns=['Zip Code', 'Shelter Capacity Percentage'],
    key_on='feature.properties.name',
    name='Shelter Capacity',
    nan_fill_color='grey',  # zip codes without shelter information shows in gray
    nan_fill_opacity=0.7,
    fill_color='RdYlGn',
    fill_opacity=0.7,
    line_opacity=0.2,
    line_color='Blue',
    legend_name='Shelter Capacity'
).add_to(la_map)

folium.Choropleth(
    geo_data=la_zip,
    data=final_df,
    columns=['Zip Code', 'Cost of insuring 10% of the houses in the ZIP Code'],
    key_on='feature.properties.name',
    name='Insurance Cost',
    # nan_fill_color='grey', # zip codes without shelter information shows in gray
    # nan_fill_opacity=0.7,
    fill_color='YlOrRd',
    fill_opacity=0.7,
    line_opacity=0.2,
    line_color='Blue',
    legend_name='Insurance Cost',
    show=False
).add_to(la_map)

# Add hover functionality.
def style_function(x): return {'fillColor': '#ffffff',
                               'color': '#000000',
                               'fillOpacity': 0.1,
                               'weight': 0.1}

def highlight_function(x): return {'fillColor': '#000000',
                                   'color': '#000000',
                                   'fillOpacity': 0.50,
                                   'weight': 0.1}

NIL = folium.features.GeoJson(
    data=la_zip,
    style_function=style_function,
    control=False,
    highlight_function=highlight_function,
    tooltip=folium.features.GeoJsonTooltip(
        fields=['external_id'],
        aliases=['ZIP'],
        style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
    )
)

la_map.add_child(NIL)

group1 = folium.FeatureGroup(name='<span style=\\"color: red;\\">Earthquakes</span>')
# Go through each earthquake in set, make circle, and add to map.
for i in range(len(earthquakesLA_df)):
    html = f"""
    <p> Magnitude: {earthquakesLA_df.iloc[i]['Magnitude']}  </p>
    <p> DateTime: {earthquakesLA_df.iloc[i]['Datetime']}  </p>
    """

    iframe = folium.IFrame(html=html, width=200, height=150)
    popup = folium.Popup(iframe, max_width=650)

    folium.Marker(
        location=[earthquakesLA_df.loc[i]['Lat'],
                  earthquakesLA_df.loc[i]['Lon']],
        popup=popup,
        icon=plugins.BeautifyIcon(
            icon="arrow-down", icon_shape="marker",
            number=earthquakesLA_df.iloc[i]['Magnitude'],
            border_color='red',
            background_color='red')
    ).add_to(group1)
group1.add_to(la_map)

group0 = folium.FeatureGroup(name='<span style=\\"color: red;\\">Shelters</span>')
# Go through each shelter in set, make circle, and add to map.
for i in range(len(shelters_df)):
    folium.Circle(
        location=[shelters_df.loc[i]['X'], shelters_df.loc[i]['Y']],
        popup=shelters_df.loc[i, 'EVAC_CAP'],
        radius=int(shelters_df.loc[i, 'EVAC_CAP']) * 0.5,
        weight=1,  # thickness of the border
        color='blue',  # this is the color of the border
        opacity=0.3,  # this is the alpha for the border
        fill_color='blue',  # fill is inside the circle
        fill_opacity=0.5,  # we will make that less opaque so we can see layers
    ).add_to(group0)
group0.add_to(la_map)

folium.LayerControl(collapsed=False).add_to(la_map)

# Save map
la_map.save('LA_earthquake_shelter_map.html')

# %% ### FORMAT OUTPUT ###

# [1] EARTHQUAKE
earthquakesLA_df.drop(['Lat', 'Lon'], axis=1, inplace=True)
earthquakes_html = build_table(earthquakesLA_df, 'blue_light')
with open('LA_past_earthquakes.html', 'w') as f:
    f.write(earthquakes_html)

# [2] HOUSING/SHELTER
# FILL NAN Data
final_df.fillna(0, inplace=True)

# Sort
final_df.sort_values(by="Cost of insuring 10% of the houses in the ZIP Code", inplace=True, ascending=False)

# Housing Units
final_df.iloc[:, 1:2] = final_df.iloc[:, 1:2].applymap(lambda x: "{:,}".format((int(x))))

# Median Home Value
final_df.iloc[:, 2:3] = final_df.iloc[:, 2:3].applymap(lambda x: "${:,}".format((int(x))))

# Raw cost
final_df.iloc[:, 3:5] = final_df.iloc[:, 3:5].applymap(lambda x: "${:,.2f}".format((x)))

# Shelter Capacity, Population
final_df.iloc[:, 5:7] = final_df.iloc[:, 5:7].applymap(lambda x: "{:,}".format((int(x))))

# Shelter Capacity Percentage
final_df.iloc[:, 7:] = final_df.iloc[:, 7:].applymap(lambda x: "{:.2f}%".format((x)))

bottom_10_df.iloc[:, 1:2] = bottom_10_df.iloc[:, 1:2].applymap(lambda x: "{:,}".format((int(x))))
bottom_10_df.iloc[:, 2:3] = bottom_10_df.iloc[:, 2:3].applymap(lambda x: "${:,}".format((int(x))))
bottom_10_df.iloc[:, 3:5] = bottom_10_df.iloc[:, 3:5].applymap(lambda x: "${:,.2f}".format((x)))
bottom_10_df.iloc[:, 5:] = bottom_10_df.iloc[:, 5:].applymap(lambda x: "${:,}".format((int(x))))

# Rearrange bottom_10_df
cols = bottom_10_df.columns.tolist()
cols = cols[0:3] + cols[-1:] + cols[3:5]
bottom_10_df = bottom_10_df[cols]

housing_html = build_table(final_df, 'blue_light')
with open('LA_housing_insurance_cost.html', 'w') as f:
    f.write(housing_html)

bottom_10_housing_html = build_table(bottom_10_df, 'blue_light')
with open('LA_housing_insurance_cost_bottom_10.html', 'w') as f:
    f.write(bottom_10_housing_html)

# Function that opens up a html browser for dataframes and map
def openbrowser(html):
    filename = 'file:///' + os.getcwd() + '/' + html
    webbrowser.open_new_tab(filename)

print("\n\n\n\n\n\n\n\n\n\n\n\n\n")
print("--------------------------Earthquake Preparation Tool--------------------------\n")
print("1) 'LA_past_earthquakes.html' shows you information on past earthquakes of magnitude of 5 and above that occurred in the LA County.\n")

print("2) 'LA_housing_insurance_cost.html' shows you housing insurance cost for each zip code in the LA county.")
print("Median of the insurance mortage in the LA county is: $", median_cost_of_insurance, " (Source: Statista)")
print("Median of the house values in LA county is: $", med_home_value)
print("Cost of insuring every dollar is: $", round(cost_of_insuring_every_dollar, 5))

print("\nThe last 3 columns show you shelter capacity information of all the shelters in each zip code.")
print("'Shelter capacity percentage' shows you the percentage of the zip code population that can be sheltered.")
print("Cells that show a value of 0 means that there are no information available.\n")

print("3) 'LA_housing_insurance_cost_bottom_10.html' shows you housing insurance cost for the lowest 10% median income zip codes.")
print("Total amount required to insure lowest 10% median income zip codes is: $", \
      round(bottom_10_int_df["Cost of insuring 10% of the houses in the ZIP Code"].sum(),2), "\n")

print("4) 'LA_earthquake_shelter_map.html' shows you the LA county map with all of the above information.\n")

print("**If you want specific zip code information, please return to this window and input the zipcode.")

instructions = ""

while instructions != "Go":
    instructions = input("If you have understood, please type in 'Go' to proceed opening the map: ")

    if instructions == "Go":
        openbrowser("LA_past_earthquakes.html")
        openbrowser("LA_housing_insurance_cost.html")
        openbrowser("LA_housing_insurance_cost_bottom_10.html")
        openbrowser("LA_earthquake_shelter_map.html")
        
        # Gets the information of a zip code according to user input
        zipcode = 1
        while zipcode != 0:
            zipcode = input('Enter an LA County zip code to show its information. Enter 0 to exit: ')
            try:
                zipcode = int(zipcode)
                try: 
                    zip_housingunits = final_df[final_df['Zip Code'] == str(zipcode)]['Housing Units'].item()
                    zip_mhv = final_df[final_df['Zip Code'] == str(zipcode)]['Median Home Value'].item()
                    zip_rawinscost = final_df[final_df['Zip Code'] == str(zipcode)]['Raw cost of Insurance per House'].item()
                    zip_inscost_10percent = final_df[final_df['Zip Code'] == str(zipcode)]['Cost of insuring 10% of the houses in the ZIP Code'].item()
                    zip_sheltercap = final_df[final_df['Zip Code'] == str(zipcode)]['Shelter Capacity'].item()
                    zip_pop = final_df[final_df['Zip Code'] == str(zipcode)]['Population'].item()
                    zip_shelterpercent = final_df[final_df['Zip Code'] == str(zipcode)]['Shelter Capacity Percentage'].item()
                    try: # ZIP city name is in another dataframe, some city name values are missing. 
                        zip_city = Cal_pop_df[Cal_pop_df['ZIP'] == zipcode]['CITY'].item()
                        print('Zipcode:', zipcode)
                        print('City:', zip_city)
                    except:
                        zip_city = ''
                        print('Zipcode:', zipcode)
                    print('Housing units:', zip_housingunits)
                    print('Median home value:', zip_mhv)
                    print('Raw cost of Insurance per House:', zip_rawinscost)
                    print('Cost of insuring 10% of the houses in the ZIP Code:', zip_inscost_10percent)
                    print('Shelter capacity:', zip_sheltercap)
                    print('Total population:', zip_pop)
                    print('Shelter capacity percentage:', zip_shelterpercent)
                except:
                    if zipcode == 0:
                        print("End of program")
                    else:
                        print('Zipcode not found')
            except: 
                print('Invalid format. Enter zip code in numeric value')
        
        break
    else:
        print("Please type 'Go' again")
        