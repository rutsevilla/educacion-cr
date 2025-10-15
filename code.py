# code.py
import json
import unicodedata
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
import math, numpy as _np
import plotly.express as px
from funciones import *    

import folium
from folium import GeoJson, GeoJsonTooltip
from folium.plugins import MarkerCluster
import branca.colormap as cm
from streamlit_folium import st_folium
import plotly.io as pio
import streamlit.components.v1 as components

# ================== CONFIG (solo una vez y lo 1º) ==================
st.set_page_config(
    page_title="Dashboard Educación – Costa Rica 2026",
    page_icon="/share/home/ruts/visualizacion/logos/circle-white.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ================== RUTAS ==================
CSV_PATH = r"/share/home/ruts/notebooks/costa-rica/eduacion/nivel-eduacion-region-sexo-edad.csv"
CENTROS_GEOJSON_PATH = r"/share/home/ruts/notebooks/costa-rica/eduacion/centros-educativos-CR.geojson"  # puntos
REGIONES_SHP_PATH = r"/share/home/ruts/notebooks/costa-rica/geometry/Unidad Geoestadística Regional 2024.shp"  # polígonos

# ================== ESTILOS ==================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');

/* Fondo global */
html, body, [data-testid="stAppViewContainer"] {
  height: 100%;
  margin: 0;
  background: linear-gradient(90deg, #175CA1, #07A9E0 140%);
  background-attachment: fixed;
  font-family: 'Poppins', system-ui, -apple-system, Segoe UI, Roboto, sans-serif !important;
}

/* ===== Cabecera (logo + título) ===== */
.header-box { padding: 0 0 0 0; }
.header-row { display:flex; align-items:center; gap:1vh; }
.header-row h1 { margin:0; font-size:4vh ; font-weight:500; color:#fff;}
.header-row img { height:5vh; width:auto; }

/* Sin márgenes arriba */
.block-container { padding-top: 0 !important; margin-top: 0 !important; }

/* Ocultar sidebar, header, footer */
[data-testid="stSidebar"], header[data-testid="stHeader"], MainMenu { display: none !important; }
footer { visibility: hidden; }

/* Contenedor principal */
.container-box {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 1rem 1.5rem;
  box-shadow: 0 4px 20px rgba(0,0,0,.2);
  backdrop-filter: blur(4px);
}

/* Selectores compactos */
.small-select label,
.small-select [data-baseweb="select"] div,
.small-select select,
.small-select input,
.small-select button,
.small-select span { font-size: 0.8rem !important; }
.small-select [data-baseweb="select"] { min-height: 34px !important; }
.small-select [data-baseweb="select"],
.stSelectbox div[data-baseweb="select"] {
  min-height: clamp(34px, 4.8vh, 42px) !important;
  display: flex !important;
  align-items: center !important;
}
.small-select [data-baseweb="select"] div[role="combobox"],
.stSelectbox div[data-baseweb="select"] div[role="combobox"]{
  padding-top: 0.2rem !important;
  padding-bottom: 0.2rem !important;
  display: flex; align-items: center;
}

/* Etiquetas */
.small-select label, .stSelectbox label {
  line-height: 1.2 !important; display: inline-block !important;
}

/* Mapa */
.map-wrapper iframe {
  width: 100% !important;
  height: 30vh !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 2px 10px rgba(0,0,0,.25);
  transition: height 0.3s ease;
  prefer_canvas: true;
}
/* Quitar logos Leaflet */
.leaflet-control-attribution, .leaflet-control-scale { display: none !important; }

/* Usa con cuidado: afecta a todos los stacks verticales */
div[data-testid="stVerticalBlock"] {
  gap: 0.4rem !important;
  row-gap: 0.4rem !important;
}

.small-select label,
.small-select [data-baseweb="select"] div,
.small-select select,
.small-select input,
.small-select button,
.small-select span,
.stSelectbox label,
.stSelectbox div[data-baseweb="select"] {
  font-size: clamp(0.7rem, 1.5vh, 0.95rem) !important;
}


.small-checkbox div[data-testid="stCheckbox"] label {
  font-size: 0.5rem !important;
  line-height: 1 !important;
}

/* ===== Sliders adaptativos ===== */
[data-testid="stSlider"] label { font-size: clamp(0.7rem, 1.4vh, 0.9rem) !important; }
[data-testid="stSlider"] .stSlider { height: clamp(20px, 2.8vh, 28px) !important; }

/* ===== Ajustes generales ===== */
.block-container label:empty { margin:0; padding:0; }
.main .block-container { padding-top: 1.2rem; }
section[data-testid="stSidebar"] { display:none !important; }
main blockquote, .block-container { padding-top: 0.6rem; padding-bottom: 0.6rem; }
html, body, [data-testid="stAppViewContainer"] { height: 100%; overflow: hidden; }

</style>
""", unsafe_allow_html=True)


def _fix_misencoded(s: Optional[str]) -> Optional[str]:
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s
        
def _normalize_str_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.strip()
         .str.lower()
         .apply(lambda x: unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii"))
    )

# ================== CARGA Y PROCESADO CSV ==================
df_wide = load_csv(CSV_PATH)
df_wide.rename(columns={"Secunadia academica Completa": "Secundaria academica Completa"}, inplace=True)

COL_REGION = "Region de planificacion"
COL_SEXO   = "Sexo"
COL_EDAD   = "Edad"

# Corrige nombre mal escrito
df_wide.rename(columns={"Secunadia academica Completa": "Secundaria academica Completa"}, inplace=True)

for col in (COL_REGION, COL_SEXO, COL_EDAD):
    if col not in df_wide.columns:
        st.error(f"Falta la columna '{col}' en el CSV. Columnas disponibles: {list(df_wide.columns)}")
        st.stop()

fixed_cols = {COL_REGION, COL_SEXO, COL_EDAD}
var_cols = [c for c in df_wide.columns if c not in fixed_cols]
for c in var_cols:
    s = (
        df_wide[c].astype(str)
        .str.replace("-", "0", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df_wide[c] = pd.to_numeric(s, errors="coerce").fillna(0)

# Ancho -> largo (valor absoluto)
df_long = df_wide.melt(
    id_vars=[COL_REGION, COL_SEXO, COL_EDAD],
    value_vars=var_cols,
    var_name="variable",
    value_name="valor_abs"
)

# Totales por (Región, Sexo, Edad) y % relativo
totals = (
    df_long[df_long["variable"] == "Total"]
    .rename(columns={"valor_abs": "total"})
    [[COL_REGION, COL_SEXO, COL_EDAD, "total"]]
)
df_long = df_long.merge(totals, on=[COL_REGION, COL_SEXO, COL_EDAD], how="left")
df_long["pct"] = np.where(df_long["total"] > 0, 100 * df_long["valor_abs"] / df_long["total"], np.nan)

# Dimensiones (excluye 'Total' para trabajar en %)
variables = sorted([v for v in df_long["variable"].unique() if v not in ["Total", 'Ignorado']])
sexos     = sorted(df_long[COL_SEXO].dropna().astype(str).unique().tolist())
edades    = sorted(df_long[COL_EDAD].dropna().astype(str).unique().tolist())

# ================== CABECERA ==================
LOGO_PATH = "/share/www/projects/js-dir/img/logos/svg/circle-white.svg"
logo_data_uri = img_to_data_uri(LOGO_PATH)
st.markdown(
    f"""
    <div class="header-box">
      <div class="header-row">
        <img src="{logo_data_uri}" alt="Logo" />
        <h1>Educación en Costa Rica</h1>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ================== LAYOUT ==================
row1_col1, row1_col2 = st.columns([1, 0.9])
with row1_col1:
    col1, col2 = st.columns([0.7, 0.6])
    with col1:
        # ================== MAPA EN CONTENEDOR ==================
        with st.container(border=True):
            # ---------- SELECTORES ----------
            c1, c2, c3 = st.columns([1.7, 1, 1.2])
            with c1:
                var_sel = st.selectbox("Variables", options=variables, index=0)
            with c2:
                sexo_sel = st.selectbox("Sexo", options=["Todos"] + sexos, index=0)
            with c3:
                edad_sel = st.selectbox("Rango de edad", options=["Todos"] + edades, index=0)

            # ---------- FILTROS ----------
            dmap = df_long.copy()
            if sexo_sel != "Todos":
                dmap = dmap[dmap[COL_SEXO].astype(str) == sexo_sel]
            if edad_sel != "Todos":
                dmap = dmap[dmap[COL_EDAD].astype(str) == edad_sel]
            dmap = dmap[dmap["variable"] == var_sel]
            dmap_reg = dmap.groupby(COL_REGION, as_index=False)["pct"].mean().rename(columns={"pct": "valor_plot"})

            # ---------- GEOMETRÍAS (rápidas) ----------
            gdf_regions = load_regions(REGIONES_SHP_PATH)
            gdf_regions["NOMB_UGER"] = gdf_regions["NOMB_UGER"].apply(_fix_misencoded)
            gdf_regions["__region_norm"] = _normalize_str_series(gdf_regions["NOMB_UGER"])

            dmap = df_long.copy()
            if sexo_sel != "Todos":
                dmap = dmap[dmap[COL_SEXO].astype(str) == sexo_sel]
            if edad_sel != "Todos":
                dmap = dmap[dmap[COL_EDAD].astype(str) == edad_sel]
            dmap = dmap[dmap["variable"] == var_sel]

            dmap_reg = (
                dmap.groupby(COL_REGION, as_index=False)["pct"]
                .mean()
                .rename(columns={"pct": "valor_plot"})
            )
            dmap_reg["__region_norm"] = _normalize_str_series(dmap_reg[COL_REGION])

            gplot = gdf_regions.merge(
                dmap_reg[["__region_norm", "valor_plot"]],
                on="__region_norm",
                how="left"
            )
            gplot["valor_plot"] = gplot["valor_plot"].fillna(0.0).round(1)

            # Mantener sólo columnas necesarias
            gplot = gplot[["NOMB_UGER", "valor_plot", "geometry"]].copy()

            # Simplificar geometrías para acelerar (ajusta tolerancia si hace falta)
            # Tolerancia ~0.001º ≈ 100 m; sube/baja según calidad deseada
            gplot["geometry"] = gplot["geometry"].simplify(tolerance=0.001, preserve_topology=True)

            # ---------- MAPA ----------
            # Colormap robusto
            vmin = float(np.nanmin(gplot["valor_plot"])) if len(gplot) else 0.0
            vmax = float(np.nanmax(gplot["valor_plot"])) if len(gplot) else 1.0
            if np.isclose(vmin, vmax):
                vmax = vmin + 1.0
            COLOR_PALETTE = ["#DB2E0B", "#F7FF03", "#1BB315"]
            colormap = cm.LinearColormap(COLOR_PALETTE, vmin=vmin, vmax=vmax)


            center_lat, center_lon = 9.974522, -84.100133 
            sw, ne = [8.1, -85.8], [11.3, -82.2]
            def style_fn(feature):
                val = feature["properties"].get("valor_plot", 0)
                color = colormap(val) if val is not None else "#cccccc"
                return {"fillColor": color, "color": "#333", "weight": 0.6, "fillOpacity": 0.6}
            
            # ---------- MAPA ----------
            m = folium.Map(
                location=[center_lat, center_lon],
                tiles="OpenStreetMap",
                control_scale=False,
                prefer_canvas=True,
                zoom_control=False
            )
            m.get_root().header.add_child(folium.Element("""
            <style>
            .leaflet-control-attribution, .leaflet-control-scale, .leaflet-control-zoom { display:none !important; }
            </style>
            """))

            tooltip = GeoJsonTooltip(
                fields=["NOMB_UGER", "valor_plot"],
                aliases=["Región:", f"{var_sel} (%):"],
                localize=True,
                sticky=False,
                labels=True,
                style=(
                    "background-color:white; color:#111; font-size:12px; "
                    "padding:6px; border-radius:4px;"
                ),
            )
            
            # ---------- POLÍGONOS ----------
            GeoJson(
                data=json.loads(gplot.to_json()),
                style_function=style_fn,
                tooltip=tooltip,
                highlight_function=lambda x: {"weight": 2, "color": "#000", "fillOpacity": 1},
                name="Indicador por región"
            ).add_to(m)

            # ---------- PUNTOS (FeatureGroup único) ----------
            st.markdown('<div class="small-checkbox">', unsafe_allow_html=True)
            mostrar_centros = st.checkbox("Mostrar centros educativos", value=False)
            st.markdown('</div>', unsafe_allow_html=True)

            
            fg_centros = folium.FeatureGroup(name="Centros educativos", show=True)

            try:
                gdf_centros = load_points(CENTROS_GEOJSON_PATH)
                name_col = "CENTRO_EDU" if "CENTRO_EDU" in gdf_centros.columns else None

                # Detecta la columna de tipo
                tipo_col = None
                for c in gdf_centros.columns:
                    if c.lower() in ("tipo", "tipo_insti", "tipoedu", "sector"):
                        tipo_col = c
                        break

                # Normaliza el tipo (público/privado) y crea orden categórico
                if tipo_col:
                    tipo_norm = (
                        gdf_centros[tipo_col]
                        .astype(str).str.strip().str.lower()
                        .replace({"público": "publico"})  # resuelve acento
                    )
                else:
                    tipo_norm = "desconocido"

                gdf_centros["__tipo_norm"] = pd.Categorical(
                    tipo_norm,
                    categories=["publico", "privado", "desconocido"],  # ← públicos primero
                    ordered=True
                )

                # 🔹 Ordena: públicos → privados → desconocidos
                gdf_centros = gdf_centros.sort_values("__tipo_norm")

                # Colores por tipo
                COLOR_MAP = {
                    "publico": "#619AD0",      # azul
                    "privado": "#190C8D",      # naranja
                    "desconocido": "#999999",  # gris por si acaso
                }

                # Un solo bucle: al estar ordenado, los privados se dibujan después (quedan encima)
                for _, row in gdf_centros.iterrows():
                    geom = row.geometry
                    if geom is None or geom.is_empty:
                        continue

                    tipo = str(row["__tipo_norm"]) if tipo_col else "desconocido"
                    color = COLOR_MAP.get(tipo, "#999999")

                    tooltip_text = f"{row[name_col]}" if name_col else "Centro educativo"
                    if tipo_col:
                        tooltip_text += f" ({row.get(tipo_col)})"

                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=3,
                        color=color,
                        weight=1,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.6,
                        tooltip=tooltip_text,
                    ).add_to(fg_centros)

            except Exception as e:
                st.warning(f"No se pudieron cargar los centros educativos: {e}")

            # Añade la capa si está marcado y mete la leyenda
            if mostrar_centros:
                fg_centros.add_to(m)
                legend_html = """
                <div style="position: fixed; bottom: 20px; left: 20px;
                            background-color: rgba(255, 255, 255, 0.85);
                            border-radius: 8px; padding: 8px 12px; font-size: 13px;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.3); line-height: 1.3;">
                    <b>Tipo de centro educativo</b><br>
                    <span style="color:#004E98;">●</span> Público<br>
                    <span style="color:#F7B538;">●</span> Privado
                </div>
                """
                m.get_root().html.add_child(folium.Element(legend_html))

            # Ajuste de vista y render
            m.fit_bounds([sw, ne])
            st_folium(m, width=None, height=300)

    with col2:
        with st.container(border=True):
            st.markdown("**Pirámide educativa**")
            colum1, colum2 = st.columns([0.5, 1])
            with colum1:  
                # ===== Selectores =====
                regiones_opts = sorted(df_wide[COL_REGION].dropna().astype(str).unique().tolist())
                region_pyr_sel = st.selectbox("Región", options=["Todas"] + regiones_opts, index=0)
            with colum2:
                # Orden de edades (usa la lista 'edades' ya creada)
                def _edad_key(s):
                    import re
                    s = str(s)
                    m = re.search(r"\d+", s)
                    return int(m.group(0)) if m else 0

                edades_sorted = sorted(edades, key=_edad_key)
                edad_min, edad_max = st.select_slider(
                    "Rango de edad",
                    options=edades_sorted,
                    value=(edades_sorted[0], edades_sorted[-1]),
                )
                i0, i1 = edades_sorted.index(edad_min), edades_sorted.index(edad_max)
                edades_elegidas = set(edades_sorted[min(i0, i1) : max(i0, i1) + 1])

                # ===== Datos base en ancho (más directo para sumar) =====
                niveles = [c for c in var_cols if c not in ("Total", "Ignorado")]

                sub = df_wide[df_wide[COL_EDAD].astype(str).isin(edades_elegidas)].copy()
                if region_pyr_sel != "Todas":
                    sub = sub[sub[COL_REGION].astype(str) == region_pyr_sel]

                # Normaliza etiquetas de sexo a Hombre/Mujer
                def _sexo_std(x: str) -> str:
                    x = str(x).strip().lower()
                    if x.startswith(("h", "masc")):
                        return "Hombre"
                    if x.startswith(("m", "fem")):
                        return "Mujer"
                    return x.title()  # fallback

                sub["Sexo_std"] = sub[COL_SEXO].apply(_sexo_std)

                # Total absoluto para el denominador
                tot_abs = pd.to_numeric(sub.get("Total", 0), errors="coerce").fillna(0).sum()

                # A formato largo y pivot -> filas = Nivel, columnas = Sexo_std
                long = sub.melt(
                    id_vars=[COL_REGION, "Sexo_std", COL_EDAD],
                    value_vars=niveles,
                    var_name="Nivel",
                    value_name="Valor",
                )
                piv = (
                    long.groupby(["Nivel", "Sexo_std"], as_index=False)["Valor"].sum()
                        .pivot(index="Nivel", columns="Sexo_std", values="Valor")
                        .fillna(0.0)
                )

            # Asegura columnas presentes
            if "Hombre" not in piv.columns: piv["Hombre"] = 0.0
            if "Mujer"  not in piv.columns: piv["Mujer"]  = 0.0

            # Reordena niveles como en la tabla original
            piv = piv.reindex(niveles)

            # Pasa a porcentaje respecto al total seleccionado
            if tot_abs > 0:
                piv_pct = piv / float(tot_abs) * 100.0
            else:
                piv_pct = piv.copy() * 0.0

            # Prepara para pirámide: hombres negativos (izquierda)
            piv_pct_plot = piv_pct.copy()
            piv_pct_plot["Hombre"] = -piv_pct_plot["Hombre"]

            # Para Plotly: a largo
            piramide = (
                piv_pct_plot.reset_index()
                    .melt(id_vars="Nivel", value_vars=["Hombre", "Mujer"],
                        var_name="Sexo", value_name="valor_plot")
            )

            # Límite simétrico bonito
            vmax = float(_np.nanmax(_np.abs(piramide["valor_plot"]))) if len(piramide) else 5.0
            lim  = max(5.0, math.ceil(vmax / 5.0) * 5.0)

            # Gráfico
            fig = px.bar(
                piramide,
                x="valor_plot",
                y="Nivel",
                color="Sexo",
                orientation="h",
                color_discrete_map={"Hombre": "#BDBEFF", "Mujer": "#BDFFC8"},
                height=319,
                labels={"valor_plot": "Porcentaje (%)", "Nivel": "Nivel educativo"},
            )
            fig.update_layout(
                bargap=0.15,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend_title_text="Sexo",
                xaxis=dict(
                    title="Porcentaje (%)",
                    range=[-lim, lim],
                    tickvals=[-lim, -lim/2, 0, lim/2, lim],
                    ticktext=[f"{abs(v):.0f}" for v in [-lim, -lim/2, 0, lim/2, lim]],
                    zeroline=True, zerolinewidth=2, zerolinecolor="black",
                ),
                yaxis=dict(
                    categoryorder="array",
                    categoryarray=niveles[::-1],  # de abajo hacia arriba como en tu ejemplo
                    title=None,
                ),
                font=dict(family="Poppins", size=11),
                margin=dict(l=0, r=0, t=0, b=0),
            )
            # Pie dinámico
            st.plotly_chart(fig, use_container_width=True)
    
    with st.container(border=True):
        st.markdown("**Heatmap por región de planificación**")

        # Selectores
        c1, c2 = st.columns(2)
        with c1:
            sexo_hm = st.selectbox("Sexo", options=["Todos"] + sexos, index=0, key="hm_sexo")
        with c2:
            edad_hm = st.selectbox("Rango de edad", options=["Todos"] + edades, index=0, key="hm_edad")

        # Filtrado
        d = df_long.copy()
        if sexo_hm != "Todos":
            d = d[d[COL_SEXO].astype(str) == sexo_hm]
        if edad_hm != "Todos":
            d = d[d[COL_EDAD].astype(str) == edad_hm]

        # Solo variables “reales” (sin Total / Ignorado)
        d = d[d["variable"].isin(variables)]

        # Tabla pivote: media % por región-variable
        piv = (d
                .pivot_table(index=COL_REGION, columns="variable", values="pct", aggfunc="mean")
                .reindex(columns=variables))  # asegura orden de columnas

        # Si no hay datos tras el filtrado
        if piv.empty:
            st.info("No hay datos para el filtro seleccionado.")
        else:
            # Altura dinámica según número de regiones para que se lea bien
            height = 323

            # Heatmap
            fig = px.imshow(
                piv.values,
                x=piv.columns,
                y=piv.index,
                aspect="auto",
                color_continuous_scale=COLOR_PALETTE,
                zmin=0, zmax=80,                # escala 0–100 %
                origin="upper",
                text_auto=".1f"                  # anota valores (opcional)
            )
            fig.update_traces(
                hovertemplate="Región: %{y}<br>Indicador: %{x}<br>%: %{z:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=height,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=8, b=0),
                coloraxis_colorbar=dict(title="%")
            )

            st.plotly_chart(fig, use_container_width=True)
    
with row1_col2:
    with st.container(border=True):
        st.markdown("**Evolución temporal**")
        # --- Ruta y carga del CSV de series temporales ---
        CSV_SERIES_PATH = "/share/home/ruts/visualizacion/eduacion-cr/educacion-cr-1990-2023.csv"  # <- cámbiala
        @st.cache_data(show_spinner=False)
        def load_series(path: str) -> pd.DataFrame:
            df = pd.read_csv(path)
            # Normaliza nombres
            df.columns = [c.strip() for c in df.columns]
            # Año a numérico
            if "Año" not in df.columns:
                raise ValueError("El CSV debe tener una columna 'Año'")
            df["Año"] = pd.to_numeric(df["Año"], errors="coerce")
            # Resto a numérico cuando sea posible
            for c in df.columns:
                if c == "Año": 
                    continue
                df[c] = pd.to_numeric(df[c], errors="coerce")
            # Orden por año
            df = df.sort_values("Año")
            return df

        df_series = load_series(CSV_SERIES_PATH)

        # --- Variables disponibles (todas menos Año) ---
        metricas = [c for c in df_series.columns if c != "Año"]

        # Selección de variables (multiselect con búsqueda)
        sel = st.multiselect(
            "Variables a visualizar",
            options=metricas,
            default=[
                "Asistencia a la educación en personas de 7 a 12 años (porcentaje)",
                "Asistencia a la educación en personas de 13 a 17 años (porcentaje)",
            ],
            label_visibility="collapsed",       # <- oculta el label
            key="ts_vars",
        )

        if not sel:
            st.info("Selecciona al menos una variable.")
        else:
            # Prepara datos en formato largo para px.line
            dlong = df_series[["Año"] + sel].melt(id_vars="Año", var_name="Variable", value_name="Valor")

            # Gráfico
            fig = px.line(
                dlong,
                x="Año", y="Valor",
                color="Variable",
                markers=True,
                labels={"Valor": "Valor", "Año": "Año"},
            )
            # Rango y estilo
            fig.update_xaxes(rangeslider_visible=False, showgrid=False, zeroline=False)
            fig.update_yaxes(showgrid=True, zeroline=False)
            fig.update_layout(
                height=349,
                margin=dict(l=0, r=0, t=10, b=40),
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.5,
                    xanchor="right",
                    x=1,
                ),
                legend_title_text=None,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ================== Comparador por edad y sexo  ==================
    with st.container(border=True):
        st.markdown("**Comparador de variables y región**")

        import re
        def _edad_key(s: str) -> int:
            m = re.search(r"\d+", str(s))
            return int(m.group(0)) if m else 0
        edades_sorted = sorted(edades, key=_edad_key)

        def render_sex_age_bars(key_prefix: str):
            # — Selectores —
            regiones_opts = sorted(df_wide[COL_REGION].dropna().astype(str).unique().tolist())
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                region_sel = st.selectbox(
                    "Región",
                    options=regiones_opts,
                    index=0,
                    key=f"{key_prefix}_region",
                )
            with col_sel2:
                var_sel_bar = st.selectbox(
                    "Variable",
                    options=[v for v in variables if v not in ("Total", "Ignorado")],
                    index=0,
                    key=f"{key_prefix}_var",
                )

            # — Datos —
            d = df_long.copy()
            d = d[(d[COL_REGION].astype(str) == region_sel) & (d["variable"] == var_sel_bar)]

            def _sexo_std(x: str) -> str:
                x = str(x).strip().lower()
                if x.startswith(("h", "masc")): return "Hombre"
                if x.startswith(("m", "fem")):  return "Mujer"
                return x.title()
            d["Sexo_std"] = d[COL_SEXO].apply(_sexo_std)

            d_grp = (
                d.groupby([COL_EDAD, "Sexo_std"], as_index=False)["pct"]
                .mean()
                .rename(columns={"pct": "valor_pct"})
            )

            all_idx = pd.MultiIndex.from_product(
                [edades_sorted, ["Hombre", "Mujer"]],
                names=[COL_EDAD, "Sexo_std"]
            )
            d_full = (
                d_grp.set_index([COL_EDAD, "Sexo_std"])
                    .reindex(all_idx)
                    .reset_index()
            )

            # — Gráfico —
            fig = px.bar(
                d_full,
                x=COL_EDAD,
                y="valor_pct",
                color="Sexo_std",
                barmode="group",
                category_orders={COL_EDAD: edades_sorted, "Sexo_std": ["Hombre", "Mujer"]},
                color_discrete_map={"Hombre": "#BDBEFF", "Mujer": "#BDFFC8"},
                labels={COL_EDAD: "Rango de edad", "valor_pct": "%"},
                height=320,
            )

            # — Estilo de la leyenda: arriba a la izquierda dentro del gráfico —
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(
                    title=None,
                    orientation="v",
                    x=0.02,   # posición horizontal dentro del gráfico
                    y=0.98,   # parte superior
                    xanchor="left",
                    yanchor="top",
                    bgcolor="rgba(255,255,255,0.1)",
                    bordercolor="rgba(0,0,0,0)",
                    borderwidth=0.5,
                    font=dict(size=10)
                ),
                xaxis=dict(tickangle=0, title=None),
                yaxis=dict(title="Porcentaje (%)", rangemode="tozero"),
                font=dict(family="Poppins", size=11),
            )
            st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_plot")

        # — Dos columnas iguales —
        c_left, c_right = st.columns(2)
        with c_left:
            render_sex_age_bars("bars_left")
        with c_right:
            render_sex_age_bars("bars_right")



            
        