"""
Adott város időjárás adatainak megjelenítése Streamlit applikációban
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st

# API végpont URL-ek
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# --------------------------------------------------------------------------------

def fetch_data(url: str, params: dict, result_field_name: str = None) -> dict | list[dict]:
    """
    URL-re irányuló API hívás végrehajtása. Hibakezelés, eredmények visszaadása dictionary-ben vagy list of dictionary-ben
    """
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        response = response.json()
        if result_field_name:
            if result_field_name in response:
                return response[result_field_name]
        else:
            return response
    except requests.exceptions.RequestException as e:
        st.error(f"Reuqest failed: {e}")
    except ValueError as e:
        st.error(f"Invalid JSON response: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

# --------------------------------------------------------------------------------

@st.cache_data(ttl=86400)
def fetch_geo_data(city_name: str) -> list[dict]:
    """
    Keresés településnév alapján a Geocoding adatbázisban.
    Az API hívás és az eredmények kiszolgálása cache használatával történik.
    """
    if city_name:
        return fetch_data(url=GEOCODING_URL, params={"name": city_name, "count": 100}, result_field_name="results")

# --------------------------------------------------------------------------------

def concat_weather_param(api_res: dict, name: str) -> str:
    """
    KPI/key metric megjelenítéséhez a függvény összefűzi az API által visszaadott időjárási jellemző mennyiségét és mértékegységét
    """
    return f"{api_res['current'][name]} {api_res['current_units'][name]}"

# --------------------------------------------------------------------------------

@st.cache_data(ttl=86400)
def fetch_current_weather(latitude: float, longitude: float) -> dict:
    """
    Latitude és longitude alapján az aktuális hőmrséklet, páratartalom és szélesbesség letöltése az Open Meteo végpontról, és az eredmények visszaadása egy 
    három mezőt tartalmazó dictionary-ben.
    Az API hívás és az eredmények kiszolgálása cache használatával történik.
    """
    weather_params = {"latitude": latitude,
                      "longitude": longitude,
                      "current": "temperature_2m,relative_humidity_2m,wind_speed_10m"}
    response = fetch_data(url=OPEN_METEO_URL, params=weather_params) # Open meteo URL-ről a három időjárási jellemző lekérése
    if response is not None:
        # Az egyes jellemzőkre vonatkozó eredményeket stringként adjuk vissza, amelyben a mennyiség és mértékegység konkatenálva van.
        weather_data = {"temperature": concat_weather_param(name="temperature_2m", api_res=response),
                        "humidity": concat_weather_param(name="relative_humidity_2m", api_res=response),
                        "wind_speed": concat_weather_param(name="wind_speed_10m", api_res=response)}
    return weather_data

# --------------------------------------------------------------------------------

@st.cache_data(ttl=86400)
def fetch_weather_forecast(latitude: float, longitude: float, forecast_days) -> pd.DataFrame:
    """
    Latitude és longitude alapján órás gyakoriságú hőmérséklet előrejelzési adatok letöltése az Open Meteo végpontról, és az eredmények betöltése egy pandas dataframe-be
    Az API hívás és az eredmények kiszolgálása cache használatával történik.
    """
    forecast_params = {"latitude": latitude,
                       "longitude": longitude,
                       "hourly": "temperature_2m",
                       "forecast_days": forecast_days}
    response = fetch_data(url=OPEN_METEO_URL, params=forecast_params) # Open meteo URL-ről a hőmérséklet előrejelzési adatok lekérése
    if response is not None:
        # Az API válaszból egy dictionary of lists létrehozása
        dict_of_list = {"datetime": pd.to_datetime(response["hourly"]["time"]),
                        "temperature": response["hourly"]["temperature_2m"]}
        df = pd.DataFrame(dict_of_list) # A dictionary of lists betöltése egy dataframe-be
        return df

# --------------------------------------------------------------------------------

def city_chooser(df: pd.DataFrame) -> dict:
    """
    Segédfüggény a get_city_geo_data függvényhez. Ha a település keresés több találatot eredményezett, akkor megjeleníti a kiválasztó listát, és az abból választott település adatait
    adja vissza.
    Továbbiakat lásd a get_city_geo_data függvénynél!
    """
    # A keresési eredményeket dataframbe rendezve kapja meg a függvény
    if df is not None:
        if len(df) == 1:
            # Ha df-ben csak egy sor van, akkor pontos a találat, Ennek a településnek az adatait adjuk vissza egy dictionary-ben.
            return df.iloc[0].to_dict()
        else:
            # Ha a df-ben több sor van, akkor kiválasztó lista jelenik meg, és abból egy konkrét települést választ ki a felhasználó
            df["is_foreign_country"] = df["country_code"] != "HU" # A kiválasztó lista elején a magyar településeket szeretnénk látni. A megfelelő sorrend képzéséhez kiegészítjük a df-et egy új oszloppal. 
            df.sort_values(["is_foreign_country", "name"], inplace=True) # Név alapján sorba rendezzük a településeket úgy, hogy a lista elején a magyar települések legyenek
            df.reset_index(drop=True, inplace=True) #  Frissítjük az indexet
            # Kiválasztó lista megjelenítése a df alapján
            city_index = st.selectbox(label=f"There are {len(df)} matches.", # Felirat
                                      index=None,   # Alapértelmezetten ne legyen semmi se kiválasztva
                                      options=df.index, # Ha a felhasználó választott, azt szeretnénk visszakapni, hogy hányadik sort választotta (0-val kezdődően)
                                      accept_new_options=False, # Csak a listából lehet választani, és nem lehet új értéket beírni
                                      format_func=lambda x: (f"{df.loc[x, 'name']} - {df.loc[x, 'country_code']} ({df.loc[x, 'country']})") # A sorokban megjelenő adattartalom (Ebben az AI segített!) 
                                     )
            if city_index is not None:
                # A felhasználó a city_index -edik sort válaszotta. Visszaadjuk az ebben a sorban lévő település adatait egy dictionary-ben.
                return df.iloc[city_index].to_dict()

# --------------------------------------------------------------------------------

def get_city_geo_data(city_name: str) -> dict:
    """
    Elvégzi a településnév szerinti keresést a Geocoding adatbázisban, és visszaadja a megtalált vagy kiválaszott település adatait, köztük a földrajzi koordinátákat.
    A név alapján történő keresés nemcsak 0 vagy 1 találatot eredményezhet, mert az API adott esetben több lehetséges találatot szolgáltat.
    A függvény a találatok számától függően három dolgot hajt végre:
        - Ha nincs egyetlen találat sem, akkor kiír egy figyelmeztetést a sikertelen keresésre.
        - Ha pontosan egy találat van, akkor sikerült megtalálni a települést. Ebben az esetben visszadja a település adatait.
        - Ha több találat van, akkor megjelenít egy legördülő listát, amelyből a felhasználónak ki kell választania egy települést, és annak az adatait adja vissza.
    """
    if city_name:
        city_geo_data = None
        geo_data_found = False
        geo_data = fetch_geo_data(city_name) # Keresés település névre a Geocoding adatbázisban
        if geo_data is not None:
            df = pd.DataFrame(geo_data, columns=["id", "name", "latitude", "longitude", "feature_code", "country_code", "country"]) # Az API által szoláltatott adatokat betöltjük egy dataframe-be
            # A dateframe-nek csak azokat a sorait tartjuk meg, amelyekben a "feature_code" PPL-lel kezdődik. A találatok között ugyanis sokféle lokáció szerepelhet. Olyanok is, amelyek nem települést jelentenek. (pl. park neve, stb.)
            df = df[df["feature_code"].str.upper().str.startswith("PPL")] 
            # Ha a leszürt df-ben egynél több sor van, akkor tekinthető eredményesnek a keresés
            if len(df) > 0:
                geo_data_found = True # Ha ebbe az ágba belefut, akkor nem fog megjelenni a keresés eredménytelenségét jelző figyelmeztetés
                city_geo_data = city_chooser(df=df) # Az előkészített dataframet megkapja a city_chooser függvény, amely - ha szükséges - kiválasztó listát jelenít meg. Ebból visszaérkezik egy konkrét település
        if not geo_data_found:
            # Figyelmeztető üzenet jelenik meg, ha a felhasználó által begépelt településnév alapján a keresés nem eredményezett találatot
            st.warning("There are no city with that name.")
        else:
            return city_geo_data

# --------------------------------------------------------------------------------

def main():

    # Feliratok megjelenítése
    st.title("Robot Dreams Python - Weather Map & Data Visualization App")
    st.subheader("(by Sándor Szőke)")

    # Begépelős telpülésnév mezőben bekérünk egy nevet
    city_name_input = st.text_input("Enter city name:").strip()

    # A név alapján visszakapunk egy konkrét település adatait tartalmazó dictionary-t (Ha szükséges, település kiválasztó jelenik meg.)
    city = get_city_geo_data(city_name_input)

    if city is not None:
        # Település név, ország, és aktuális időjárási adatok megjelenítése
        st.header(f"Current weather in {city['name']}, {city['country']}")
        # A "city" földrajzi koordináták alapján az aktuális időjárási adatok lekérése és megjelenítése
        weather = fetch_current_weather(city["latitude"], city["longitude"])
        if weather is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Temperature", value=weather["temperature"])
            with col2:
                st.metric(label="Humidity", value=weather["humidity"])
            with col3:
                st.metric(label="Wind Speed", value=weather["wind_speed"])

        # A település elhelyezkedését mutató térkép        
        map_df = pd.DataFrame(city, columns=["latitude", "longitude"], index=[0])
        st.map(map_df)

        # 5 napos hőmérséklet előrejelzési grafikon készül
        forecast_days = 5
        # A "city" földrajzi koordináták alapján az órás gyakoriságú hőmérséklet előrejelzési adatok lekérése
        chart_df = fetch_weather_forecast(city["latitude"], city["longitude"], forecast_days)
        if chart_df is not None:
            # Előrejelző grafikon fejléce
            st.subheader(f"Hourly Temperature Forecast for {city['name']} (Next {forecast_days} Days)")
            # Előrejelző grafikon megjelenítése
            chart_df["timestr"] = chart_df["datetime"].dt.strftime("%m.%d %H:%M") # A df egy új oszloppal egészül ki, amely a megfelelően formázott időpontokat tartalmazza
            st.line_chart(data=chart_df, x="timestr", x_label="", y="temperature", y_label="Temperature °C")

# --------------------------------------------------------------------------------
#
# Main
#
# --------------------------------------------------------------------------------

if __name__ == "__main__":
    main()