import requests
import pandas as pd
import numpy as np
import streamlit as st

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_data(url: str, params: dict, result_field_name: str) -> list[dict]:
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        response = response.json()
        if result_field_name in response:
            return response[result_field_name]
    except requests.exceptions.RequestException as e:
        st.error(f"Reuqest failed: {e}")
    except ValueError as e:
        st.error("Invalid JSON response")
    except Exception as e:
        st.error(f"Unexpected error: {e}")


def fetch_geo_data(city_name: str) -> dict:
    if city_name:
        if (
            "city_name" not in st.session_state
            or city_name != st.session_state.city_name
        ):
            api_result_list = fetch_data(
                url=GEOCODING_URL,
                params={"name": city_name, "count": 100},
                result_field_name="results",
            )
            if api_result_list:
                df = pd.DataFrame(
                    api_result_list,
                    columns=[
                        "id",
                        "name",
                        "latitude",
                        "longitude",
                        "feature_code",
                        "country_code",
                        "country",
                    ],
                )
                df = df[df["feature_code"].str.upper().str.startswith("PPL")]
                st.dataframe(df)
                if len(df) == 1:
                    st.session_state.city_geo_data = df.iloc[0].to_dict()
                else:
                    df["foreign_country"] = df["country_code"] != "HU"
                    df.sort_values(["foreign_country", "name"], inplace=True)
                    kivalasztott_index = st.selectbox(
                        label="Válassz ki egy elemet:",
                        index=None,
                        options=df.index,
                        accept_new_options=False,
                        format_func=lambda x: (
                            f"{df.loc[x, 'name']} - {df.loc[x, 'country_code']} ({df.loc[x, 'country']})"
                        ),
                    )
                    st.dataframe(df)
                    st.session_state.city_geo_data = df.iloc[0].to_dict()
                    print(kivalasztott_index)
            else:
                st.warning("There are no city with that name.")
                st.session_state.city_geo_data = None
            st.session_state.city_name = city_name
    if "city_geo_data" in st.session_state:
        return st.session_state.city_geo_data


def main():
    st.title("Robot Dreams Python - Weather Map & Data Visualization App")
    st.subheader("(by Sándor Szőke)")
    city_name_input = st.text_input("Enter city name:").strip()
    city = fetch_geo_data(city_name_input)
    if city:
        st.json(city)
    else:
        print(type(city))


if __name__ == "__main__":
    main()
