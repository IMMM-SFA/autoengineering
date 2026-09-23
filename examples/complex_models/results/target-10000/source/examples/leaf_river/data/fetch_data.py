"""Fetch real hydrology data from USGS and NOAA public APIs.

Downloads and caches daily streamflow (USGS NWIS) and weather (NOAA GHCN)
for the Leaf River near Collins, MS watershed.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_DIR = Path(__file__).parent

# Leaf River near Collins, MS — USGS gage 02472000
# Drainage area: 752 mi² = 1947.7 km²
USGS_SITE = "02472000"
DRAINAGE_AREA_KM2 = 1947.7

# NOAA GHCN station near the watershed
NOAA_STATION = "USW00003940"  # Jackson, MS

START_DATE = "2019-01-01"
END_DATE = "2020-12-31"


def fetch_usgs_streamflow(
    site: str = USGS_SITE,
    start: str = START_DATE,
    end: str = END_DATE,
) -> pd.DataFrame:
    """Fetch daily streamflow from USGS NWIS. Caches to CSV.

    Returns DataFrame with columns: date, flow_cfs, flow_mm_day.
    """
    cache_path = DATA_DIR / "streamflow.csv"
    if cache_path.exists():
        return pd.read_csv(cache_path, parse_dates=["date"])

    url = (
        f"https://waterservices.usgs.gov/nwis/dv/"
        f"?format=json&sites={site}&startDT={start}&endDT={end}"
        f"&parameterCd=00060&siteStatus=all"
    )
    print(f"Fetching USGS streamflow for site {site}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    ts = data["value"]["timeSeries"][0]
    values = ts["values"][0]["value"]

    records = []
    for v in values:
        date = v["dateTime"][:10]
        flow_cfs = float(v["value"])
        # Convert ft³/s to mm/day over drainage area
        # 1 ft³/s = 0.0283168 m³/s
        # mm/day = (m³/s * 86400) / (area_km² * 1e6) * 1000
        flow_m3s = flow_cfs * 0.0283168
        flow_mm_day = flow_m3s * 86400 / (DRAINAGE_AREA_KM2 * 1e6) * 1000
        records.append({"date": date, "flow_cfs": flow_cfs, "flow_mm_day": flow_mm_day})

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df.to_csv(cache_path, index=False)
    print(f"  Cached {len(df)} days to {cache_path}")
    return df


def fetch_noaa_weather(
    station: str = NOAA_STATION,
    start: str = START_DATE,
    end: str = END_DATE,
) -> pd.DataFrame:
    """Fetch daily precip + temp from NOAA GHCN. Caches to CSV.

    Returns DataFrame with columns: date, precip_mm, tmax_c, tmin_c, tmean_c.
    """
    cache_path = DATA_DIR / "weather.csv"
    if cache_path.exists():
        return pd.read_csv(cache_path, parse_dates=["date"])

    url = (
        f"https://www.ncei.noaa.gov/access/services/data/v1"
        f"?dataset=daily-summaries&dataTypes=PRCP,TMAX,TMIN"
        f"&stations={station}&startDate={start}&endDate={end}"
        f"&format=json&units=metric"
    )
    print(f"Fetching NOAA weather for station {station}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    records = []
    for d in data:
        prcp = float(d.get("PRCP", 0))
        tmax = float(d.get("TMAX", np.nan))
        tmin = float(d.get("TMIN", np.nan))
        tmean = (tmax + tmin) / 2 if not (np.isnan(tmax) or np.isnan(tmin)) else np.nan
        records.append({
            "date": d["DATE"],
            "precip_mm": prcp,
            "tmax_c": tmax,
            "tmin_c": tmin,
            "tmean_c": tmean,
        })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df.to_csv(cache_path, index=False)
    print(f"  Cached {len(df)} days to {cache_path}")
    return df


if __name__ == "__main__":
    flow = fetch_usgs_streamflow()
    weather = fetch_noaa_weather()
    print(f"\nStreamflow: {len(flow)} days, mean={flow['flow_mm_day'].mean():.2f} mm/day")
    print(f"Weather: {len(weather)} days, mean precip={weather['precip_mm'].mean():.1f} mm/day")
