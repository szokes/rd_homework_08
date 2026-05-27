"""
Adatok kinyerése a CoinGecko public API-járól, és azok elemzése Python segítségével.

"""

import requests
import pandas as pd
import numpy as np

# ----------------------------------------------------------
#
# Adatok letöltése a CoinGecko public API-járól
#  
# ----------------------------------------------------------

URL = "https://api.coingecko.com/api/v3/coins/markets"

params = {"vs_currency": "usd",       # USD -ben kifejezett összegeket kérünk
          "order": "market_cap_desc", # A coin-okat market cap szerint csökkenő sorrendben kérjük. A leírás szerint ez az alapértelmezett, de biztos ami ziher, paraméterként megadjuk
          "page": 1,                  # Egy page-t kérünk
          "per_page": 250}            # Egy page-re 250 coin kerüljön. (Ennyi a max ami megengedett.)

is_api_response_ok = False
try:
    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()
    is_api_response_ok = True
except requests.exceptions.RequestException as e:
    print(f"Reuqest failed: {e}")
except ValueError as e:
    print("Invalid JSON response")
except Exception as e:
    print(f"Unexpected error: {e}")

# ----------------------------------------------------------
#
# Adatok feldolgozása dataframe használatával 
#  
# ----------------------------------------------------------

# Szépészeti elem kinyomtatása az eredmények megjelenítéséhez
def print_separator(): 
    print()
    print("-------------------------------------------")
    print()

# Csak akkor fut le a következő feldolgozás, ha az API hívásnál nem volt hiba 

if is_api_response_ok:

    # Az API request eredményeit json-re alakítjuk, és betöltjük egy dataframe-be

    df = pd.DataFrame(response.json()) 

    # 1. Határozd meg, hogy a dataframe egyes oszlopaiban hány üres cella található és printeld ki:

    print()
    print("Number of empty cells in each column:")
    print(df.isna().sum())
    print_separator()

    # 2. Határozd meg a teljes dataframe-re a market_cap összegét és printeld ki:

    print(f"Total market capitalization: {df["market_cap"].sum()} USD")
    print_separator()

    # 3.​ Készíts egy új dataframe-et top50_df néven, itt csak az első 50 kriptovalutát tárold current_price alapján:

    top50_df = (df.sort_values("current_price", ascending=True)
                .head(50)
                .reset_index(drop=True))
    print("Top 50 cheapest cryptocurrencies:")
    print(top50_df[["id","symbol","current_price"]])
    print_separator()

    # 4.​ Rendezd a top50_df-et price_change_percentage_24h alapján csökkenő sorrendbe:

    top50_df.sort_values("price_change_percentage_24h", ascending=False, inplace=True)
    top50_df.reset_index(drop=True, inplace=True) # Az index a current_price szerinti sorrendet tartalmazta. Itt ezt lecseréljük, hogy a price_change_percentage_24h szerinti sorrendet mutassa.

    # 5.​ Hozz létre egy új oszlopot a top50_df-be change_direction néven amelynek 3 értéke lehet:
    #      a. Ha a price_change_percentage_24h értéke nagyobb mint 0, az oszlop értéke legyen "+"
    #      b. Ha negatív, az oszlop értéke legyen "-"
    #      c.​ Ha kereken 0, az érték legyen "0"

    top50_df["change_direction"] = np.where(top50_df["price_change_percentage_24h"] > 0, "+",
                                            np.where(top50_df["price_change_percentage_24h"] < 0, "-", "0")
                                            )
    
    # Végeredmény printelése:
    print("24h price change %:")
    print(top50_df[["id","symbol","current_price","price_change_percentage_24h","change_direction"]])
    print()
