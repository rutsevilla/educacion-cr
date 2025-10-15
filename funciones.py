import json
from pathlib import Path
import os, base64, mimetypes
from unidecode import unidecode
import altair as alt
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.io as pio
from typing import Optional  # <-- agrégalo al inicio del archivo


@st.cache_data
def load_csv(f):
    df = pd.read_csv(f)
    return df


@st.cache_data
def load_geojson(f):
    # plotly acepta dict
    gj = json.load(f)
    # convertir a GeoDataFrame también para merges si hace falta
    gdf = gpd.GeoDataFrame.from_features(gj["features"]) if isinstance(gj, dict) else gpd.read_file(f)
    return gj, gdf

@st.cache_data
def guess_column(df: pd.DataFrame, candidates: list[str]):
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


def standardize_columns(df: pd.DataFrame):
    mapping = {}
    for k, cands in DEFAULT_COLS.items():
        col = guess_column(df, cands)
        if col is None:
            mapping[k] = None
        else:
            mapping[k] = col
    return mapping

# Normalizar claves (str upper-trim) para el merge
def norm_key(s):
    if pd.isna(s):
        return None
    return str(s).strip().upper()

def img_to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64  = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    df_wide = pd.read_csv(path)
    df_wide.columns = [c.strip() for c in df_wide.columns]
    return df_wide

@st.cache_data(show_spinner=False)
def load_regions(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    else:
        gdf = gdf.to_crs(epsg=4326)
    return gdf

@st.cache_data(show_spinner=False)
def load_points(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    else:
        gdf = gdf.to_crs(epsg=4326)
    return gdf