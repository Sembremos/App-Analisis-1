# ============================== PARTE 1/4 ==============================
# app.py
# streamlit run app.py

import re
import io
import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="CR | Mapas y Programas", page_icon="🛰️", layout="wide")

# =========================
# ESTILO (MISMA LÍNEA VISUAL)
# =========================
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.0rem; padding-bottom: 2rem;}
      .title{font-size: 28px; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 2px;}
      .subtitle{color:#6b7280; margin-top:0px; margin-bottom: 14px;}
      .kpi-grid{display:flex; gap:14px; flex-wrap:wrap; margin-bottom: 10px;}

      /* KPI con color */
      .kpi{
        border-radius:18px;
        padding:16px 18px;
        box-shadow:0 10px 25px rgba(0,0,0,0.08);
        min-width: 240px; flex:1;
        border:1px solid rgba(255,255,255,0.14);
        color:#0b1220;
      }
      .kpi.kpi-a{
        background: linear-gradient(135deg, rgba(99,102,241,0.22), rgba(59,130,246,0.10));
        border:1px solid rgba(99,102,241,0.35);
      }
      .kpi.kpi-b{
        background: linear-gradient(135deg, rgba(16,185,129,0.22), rgba(34,197,94,0.10));
        border:1px solid rgba(16,185,129,0.35);
      }
      .kpi.kpi-c{
        background: linear-gradient(135deg, rgba(245,158,11,0.22), rgba(251,146,60,0.10));
        border:1px solid rgba(245,158,11,0.35);
      }

      .kpi-label{color:#e5e7eb; font-weight:800; font-size:14px; letter-spacing:0.01em;}
      .kpi-value{color:#ffffff; font-weight:900; font-size:44px; margin-top:6px; line-height:1;}
      .kpi-sub{color:#cbd5e1; font-size:12px; margin-top:6px;}

      .panel{
        background:#ffffff; border:1px solid #e5e7eb; border-radius:18px;
        padding:14px 16px; box-shadow:0 10px 25px rgba(0,0,0,0.05);
      }
      hr {border:none; border-top:1px solid #e5e7eb; margin: 16px 0;}
      .caption{color:#6b7280; font-size:12px;}
      .btnrow{display:flex; gap:10px; align-items:center; margin: 6px 0 10px 0;}
      .mapwrap{border-radius:18px; overflow:hidden;}
      .filterbox{
        background:#0b1220;
        border:1px solid rgba(255,255,255,0.10);
        border-radius:18px;
        padding:12px 12px;
        box-shadow:0 10px 25px rgba(0,0,0,0.25);
      }
      .filtertitle{color:#ffffff; font-weight:900; font-size:14px; margin-bottom:6px;}
      .smallhint{color:#cbd5e1; font-size:12px; margin-top:6px;}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# SESSION STATE
# =========================
if "map_fullscreen" not in st.session_state:
    st.session_state["map_fullscreen"] = {"t1": False, "t2": False, "t3": False, "t4": False}

# =========================
# COLORES POR PROVINCIA (MISMO ESQUEMA)
# =========================
PROV_COLORS = {
    "San Jose":    {"stroke": "#6d28d9", "fill": "#8b5cf6"},  # morado
    "Alajuela":    {"stroke": "#0f766e", "fill": "#14b8a6"},  # teal
    "Cartago":     {"stroke": "#b45309", "fill": "#f59e0b"},  # naranja
    "Heredia":     {"stroke": "#1d4ed8", "fill": "#60a5fa"},  # azul
    "Guanacaste":  {"stroke": "#15803d", "fill": "#4ade80"},  # verde
    "Puntarenas":  {"stroke": "#b91c1c", "fill": "#f87171"},  # rojo
    "Limon":       {"stroke": "#a16207", "fill": "#facc15"},  # amarillo
}

PROV_ORDER = ["San Jose", "Alajuela", "Cartago", "Heredia", "Guanacaste", "Puntarenas", "Limon"]

# =========================
# NORMALIZACIÓN (MISMA LÓGICA)
# - "Diablo" y "Diablo - Alejandro Arias Monge" = MISMA estructura
# =========================
def clean_txt(x: str) -> str:
    if pd.isna(x):
        return ""
    x = str(x).strip()
    x = re.sub(r"\s+", " ", x)
    return x

def normalize_estructura(name: str) -> str:
    name = clean_txt(name)
    if not name:
        return ""
    low = name.lower()
    if low.startswith("diablo"):
        return "Diablo - Alejandro Arias Monge"
    return name

def titlecase_first(s: str) -> str:
    s = clean_txt(s)
    if not s:
        return s
    return s[0].upper() + s[1:]

def safe_int(x):
    if pd.isna(x):
        return 0
    x = str(x).strip()
    if x == "":
        return 0
    # permite "En proceso"
    if re.search(r"[a-zA-Z]", x):
        return 0
    try:
        return int(float(x))
    except:
        return 0

def parse_canton_only(x: str) -> str:
    """
    - Si viene 'Canton / Distrito' => toma el cantón
    - Si viene 'Provincia / Canton ...' => toma lo primero (cantón real en tus datos tipo CPC)
    """
    x = clean_txt(x)
    if not x:
        return ""
    # separadores típicos que mandaste: "Alajuela / Los Cocos", "San José/ Hatillo", "Pococi/ la Sole"
    parts = [p.strip() for p in re.split(r"\s*/\s*", x) if p.strip()]
    if len(parts) >= 1:
        return parts[0]
    return x

# =========================
# COORDENADAS (CENTROIDES APROX. PARA MAPEAR)
# =========================
CANTON_COORDS = {
    # San José
    "San Jose": (9.9326, -84.0790),
    "Escazu": (9.9189, -84.1386),
    "Desamparados": (9.8985, -84.0664),
    "Puriscal": (9.8490, -84.3160),
    "Tarrazu": (9.6580, -84.0130),
    "Aserri": (9.8585, -84.0928),
    "Mora": (9.9095, -84.3405),
    "Goicoechea": (9.9527, -84.0595),
    "Santa Ana": (9.9300, -84.1820),
    "Alajuelita": (9.9060, -84.1050),
    "Vasquez de Coronado": (9.9760, -84.0100),
    "Acosta": (9.8020, -84.3400),
    "Tibas": (9.9560, -84.0800),
    "Moravia": (9.9610, -84.0470),
    "Montes de Oca": (9.9400, -84.0400),
    "Turrubares": (9.9070, -84.4800),
    "Dota": (9.6480, -83.9890),
    "Curridabat": (9.9130, -84.0320),
    "Perez Zeledon": (9.3720, -83.7030),
    "Leon Cortes": (9.6770, -84.0470),

    # Alajuela
    "Alajuela": (10.0163, -84.2147),
    "San Ramon": (10.0880, -84.4700),
    "Grecia": (10.0730, -84.3140),
    "San Mateo": (9.9500, -84.5240),
    "Atenas": (9.9800, -84.3820),
    "Naranjo": (10.0970, -84.3780),
    "Palmares": (10.0600, -84.4330),
    "Poas": (10.1000, -84.2330),
    "Orotina": (9.9100, -84.5220),
    "San Carlos": (10.3300, -84.4300),
    "Zarcero": (10.1860, -84.3920),
    "Sarchi": (10.0930, -84.3440),
    "Upala": (10.9000, -85.0200),
    "Los Chiles": (11.0300, -84.7200),
    "Guatuso": (10.7100, -84.9300),
    "Rio Cuarto": (10.3350, -84.2000),

    # Cartago
    "Cartago": (9.8644, -83.9194),
    "Paraiso": (9.8380, -83.8660),
    "La Union": (9.9190, -83.9890),
    "Jimenez": (9.9790, -83.7100),
    "Turrialba": (9.9040, -83.6840),
    "Alvarado": (9.9800, -83.8000),
    "Oreamuno": (9.8900, -83.8600),
    "El Guarco": (9.8000, -83.9100),

    # Heredia
    "Heredia": (9.9980, -84.1160),
    "Barba": (10.0200, -84.1200),
    "Santo Domingo": (9.9800, -84.0900),
    "Santa Barbara": (10.0400, -84.1500),
    "San Rafael": (10.0500, -84.1100),
    "San Isidro": (10.0600, -84.0900),
    "Belen": (9.9800, -84.1900),
    "Flores": (10.0000, -84.1600),
    "San Pablo": (10.0000, -84.1000),
    "Sarapiqui": (10.4600, -84.0300),

    # Guanacaste
    "Liberia": (10.6340, -85.4370),
    "Nicoya": (10.1490, -85.4520),
    "Santa Cruz": (10.2600, -85.5860),
    "Bagaces": (10.5300, -85.2500),
    "Carrillo": (10.4300, -85.5500),
    "Cañas": (10.4300, -85.1000),
    "Abangares": (10.2200, -84.9000),
    "Tilaran": (10.4700, -84.9700),
    "Nandayure": (9.9200, -85.2900),
    "La Cruz": (11.0700, -85.6300),
    "Hojancha": (10.0600, -85.4200),

    # Puntarenas
    "Puntarenas": (9.9800, -84.8300),
    "Esparza": (9.9900, -84.6600),
    "Buenos Aires": (9.1700, -83.3300),
    "Montes de Oro": (10.1000, -84.7300),
    "Osa": (8.9500, -83.5300),
    "Aguirre": (9.4300, -84.1600),
    "Golfito": (8.6500, -83.1500),
    "Coto Brus": (8.9500, -82.9500),
    "Parrita": (9.5200, -84.3200),
    "Corredores": (8.5800, -82.9500),
    "Garabito": (9.6200, -84.6300),
    "Monteverde": (10.3000, -84.8200),
    "Puerto Jimenez": (8.5300, -83.3000),

    # Limón
    "Limon": (9.9900, -83.0300),
    "Pococi": (10.6200, -83.7400),
    "Siquirres": (10.1000, -83.5100),
    "Talamanca": (9.6200, -82.8500),
    "Matina": (10.0800, -83.3000),
    "Guacimo": (10.2100, -83.6800),
}

# =========================
# CANTÓN -> PROVINCIA (para datasets SIN provincia)
# =========================
CANTON_TO_PROV = {
    # San José
    "San Jose": "San Jose", "Escazu": "San Jose", "Desamparados": "San Jose", "Puriscal": "San Jose",
    "Tarrazu": "San Jose", "Aserri": "San Jose", "Mora": "San Jose", "Goicoechea": "San Jose",
    "Santa Ana": "San Jose", "Alajuelita": "San Jose", "Vasquez de Coronado": "San Jose", "Acosta": "San Jose",
    "Tibas": "San Jose", "Moravia": "San Jose", "Montes de Oca": "San Jose", "Turrubares": "San Jose",
    "Dota": "San Jose", "Curridabat": "San Jose", "Perez Zeledon": "San Jose", "Leon Cortes": "San Jose",

    # Alajuela
    "Alajuela": "Alajuela", "San Ramon": "Alajuela", "Grecia": "Alajuela", "San Mateo": "Alajuela",
    "Atenas": "Alajuela", "Naranjo": "Alajuela", "Palmares": "Alajuela", "Poas": "Alajuela",
    "Orotina": "Alajuela", "San Carlos": "Alajuela", "Zarcero": "Alajuela", "Sarchi": "Alajuela",
    "Upala": "Alajuela", "Los Chiles": "Alajuela", "Guatuso": "Alajuela", "Rio Cuarto": "Alajuela",

    # Cartago
    "Cartago": "Cartago", "Paraiso": "Cartago", "La Union": "Cartago", "Jimenez": "Cartago",
    "Turrialba": "Cartago", "Alvarado": "Cartago", "Oreamuno": "Cartago", "El Guarco": "Cartago",

    # Heredia
    "Heredia": "Heredia", "Barba": "Heredia", "Santo Domingo": "Heredia", "Santa Barbara": "Heredia",
    "San Rafael": "Heredia", "San Isidro": "Heredia", "Belen": "Heredia", "Flores": "Heredia",
    "San Pablo": "Heredia", "Sarapiqui": "Heredia",

    # Guanacaste
    "Liberia": "Guanacaste", "Nicoya": "Guanacaste", "Santa Cruz": "Guanacaste", "Bagaces": "Guanacaste",
    "Carrillo": "Guanacaste", "Cañas": "Guanacaste", "Abangares": "Guanacaste", "Tilaran": "Guanacaste",
    "Nandayure": "Guanacaste", "La Cruz": "Guanacaste", "Hojancha": "Guanacaste",

    # Puntarenas
    "Puntarenas": "Puntarenas", "Esparza": "Puntarenas", "Buenos Aires": "Puntarenas", "Montes de Oro": "Puntarenas",
    "Osa": "Puntarenas", "Aguirre": "Puntarenas", "Golfito": "Puntarenas", "Coto Brus": "Puntarenas",
    "Parrita": "Puntarenas", "Corredores": "Puntarenas", "Garabito": "Puntarenas", "Monteverde": "Puntarenas",
    "Puerto Jimenez": "Puntarenas", "Quepos": "Puntarenas",

    # Limón
    "Limon": "Limon", "Pococi": "Limon", "Siquirres": "Limon", "Talamanca": "Limon", "Matina": "Limon", "Guacimo": "Limon",
}

# =========================
# EXPORT EXCEL ORDENADO (SIN COORDENADAS)
# =========================
def df_to_pretty_excel_bytes(df: pd.DataFrame, sheet_name: str = "Datos") -> bytes:
    df = df.copy()

    # eliminar coords si existen
    for c in ["lat", "lon", "Lat", "Lon", "LAT", "LON"]:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    # encabezados con primera letra mayúscula
    df.columns = [titlecase_first(c) for c in df.columns]

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]

    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    # estilos
    header_fill = PatternFill("solid", fgColor="111827")  # oscuro
    header_font = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="E5E7EB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    ws.freeze_panes = "A2"

    # auto width
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(60, max(12, max_len + 2))

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()

# =========================
# MAP RENDER (REUTILIZABLE)
# =========================
def render_map_points(df_points: pd.DataFrame, height_px: int, popup_builder):
    fm = df_points.dropna(subset=["lat", "lon"]).copy()
    if fm.empty:
        st.warning("No hay puntos con coordenadas para mostrar.")
        return

    center_lat = float(fm["lat"].mean())
    center_lon = float(fm["lon"].mean())

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, control_scale=True, tiles=None)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics, CNES/Airbus DS, USDA, USGS",
        name="ESRI Satélite",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Límites y lugares",
        overlay=True,
        control=True,
        opacity=0.95
    ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    for _, r in fm.iterrows():
        provincia = r["provincia"]
        canton = r["canton"]

        colors = PROV_COLORS.get(provincia, {"stroke": "#111827", "fill": "#9ca3af"})
        tooltip = f"{canton} ({provincia})"

        popup_html, radius = popup_builder(r)

        folium.CircleMarker(
            location=[float(r["lat"]), float(r["lon"])],
            radius=radius,
            weight=2,
            color=colors["stroke"],
            fill=True,
            fill_color=colors["fill"],
            fill_opacity=0.55,
            tooltip=tooltip,
            popup=folium.Popup(popup_html, max_width=450)
        ).add_to(m)

    st.markdown("<div class='mapwrap'>", unsafe_allow_html=True)
    st_folium(m, use_container_width=True, height=height_px)
    st.markdown("</div>", unsafe_allow_html=True)
# ============================== PARTE 2/4 ==============================
# =========================
# DATOS — PESTAÑA 1: ESTRUCTURAS CRIMINALES (TU DATA ORIGINAL)
# =========================
RAW_BY_PROV = {
    "San Jose": [
        ("San Jose", [
            "Los Lara (San Sebastia)", "Los coqueros (Pavas)", "Los Moreco", "Turesky", "Pollo",
            "Indio", "Ojos Bellos", "Los Picudos (Carpio)", "Los Diablos (Pavas)", "Los Polacos (Pavas)"
        ]),
        ("Escazu", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Desamparados", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Puriscal", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Tarrazu", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Aserri", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Mora", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Goicoechea", ["Los Lara", "Mongo", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Santa Ana", ["Los Lara", "La H", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Alajuelita", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Vasquez de Coronado", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Acosta", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Tibas", ["Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Moravia", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Montes de Oca", ["Los Lara", "Cartel de Sinaloa", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Turrubares", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Dota", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Curridabat", ["GaryGery", "Churro y Tauro", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Perez Zeledon", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Leon Cortes", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
    ],
    "Alajuela": [
        ("Alajuela", ["La hyena", "Diablo - Alejandro Arias", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Los Ungas", "Cascaritas (San Antonio y El Roble)", ""]),
        ("San Ramon", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Grecia", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("San Mateo", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Atenas", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Naranjo", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Palmares", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Poas", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Orotina", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("San Carlos", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Diablo", "", ""]),
        ("Zarcero", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Sarchi", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Gordon", "", ""]),
        ("Upala", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Los Chiles", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Guatuso", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Rio Cuarto", ["", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
    ],
    "Cartago": [
        ("Cartago", ["Los Maruja", "", "", "", "", "", "", "Chacales", "Pollo", "Turco"]),
        ("Paraiso", ["Los Maruja", "", "", "", "", "", "", "", "", ""]),
        ("La Union", ["Los Maruja", "", "", "", "", "", "", "Hermanos Gary Gery", "", ""]),
        ("Jimenez", ["Los Maruja", "", "", "", "", "", "", "", "", ""]),
        ("Turrialba", ["Los Maruja", "", "", "", "", "", "", "Diablo", "", ""]),
        ("Alvarado", ["Los Maruja", "", "", "", "", "", "", "", "", ""]),
        ("Oreamuno", ["Los Maruja", "", "", "", "", "", "", "Los Elizondo", "", ""]),
        ("El Guarco", ["Los Maruja", "", "", "", "", "", "", "Hermanos Gary Gery", "Palomo", "Los Maruja"]),
    ],
    "Heredia": [
        ("Heredia", ["Lara", "Myrie", "Polacos", "Hermanos Ga", "Shaggy", "", "", "Pipis (Guararri y Los ...)", "Zepol", ""]),
        ("Barba", ["", "", "", "", "", "", "", "", "", ""]),
        ("Santo Domingo", ["", "", "", "", "", "", "", "", "", ""]),
        ("Santa Barbara", ["", "", "", "", "", "", "", "", "", ""]),
        ("San Rafael", ["", "", "", "", "", "", "", "", "", ""]),
        ("San Isidro", ["", "", "", "", "", "", "", "", "", ""]),
        ("Belen", ["", "", "", "", "", "", "", "", "", ""]),
        ("Flores", ["", "", "", "", "", "", "", "", "", ""]),
        ("San Pablo", ["Diablo - Alejandro Arias Monge", "", "", "", "", "", "", "", "", ""]),
        ("Sarapiqui", ["Diablo - Alejandro Arias Monge", "", "", "", "", "", "", "Diablo", "", ""]),
    ],
    "Guanacaste": [
        ("Liberia",   ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Nicoya",    ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Santa Cruz",["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "Diablo", "Ticachu (Tamarindo)", "Los Porteños"]),
        ("Bagaces",   ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Carrillo",  ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Cañas",     ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "Rata", "", ""]),
        ("Abangares", ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Tilaran",   ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Nandayure", ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("La Cruz",   ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
        ("Hojancha",  ["Diablo - Alejandro Arias Monge", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Cartel de Juárez", "", "", ""]),
    ],
    "Puntarenas": [
        ("Puntarenas", ["Diablo - Alejandro Arias Monge", "Los Picachu-20 de No", "Guayacanes - El Gordo Dan", "Los Buhos -", "El Gordo Ram", "Los Leiner - Barranca", "Los Unga - Barranca", "", "", ""]),
        ("Esparza",      ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "Los Unga - B", "El Gordo Ramos - Barranca", "", "", "", "", "", ""]),
        ("Buenos Aires", ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Montes de Oro",["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Osa",          ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "Diablo", "", ""]),
        ("Aguirre",      ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Golfito",      ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Coto Brus",    ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Parrita",      ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Corredores",   ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Garabito",     ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Monteverde",   ["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
        ("Puerto Jimenez",["Diablo - Alejandro Arias Monge", "Cartel de Juárez", "", "", "", "", "", "", "", ""]),
    ],
    "Limon": [
        ("Limon",     ["La H", "Diablo - Alejandro Arias Monge", "Los Morenco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Tony Peña Russel", "La H", ""]),
        ("Pococi",    ["La H", "Diablo - Alejandro Arias Monge", "Los Morenco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Siquirres", ["La H", "Diablo - Alejandro Arias Monge", "Los Morenco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Talamanca", ["La H", "Diablo - Alejandro Arias Monge", "Los Morenco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""]),
        ("Matina",    ["La H", "Diablo - Alejandro Arias Monge", "Los Morenco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Tony Peña Russel", "La H", ""]),
        ("Guacimo",   ["La H", "Diablo - Alejandro Arias Monge", "Los Morenco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Pechuga", "", ""]),
    ],
}

def build_wide_df_struct() -> pd.DataFrame:
    rows = []
    for prov, items in RAW_BY_PROV.items():
        for canton, structs in items:
            r = {"provincia": prov, "canton": canton}
            for i in range(10):
                r[f"e{i+1}"] = structs[i] if i < len(structs) else ""
            rows.append(r)
    return pd.DataFrame(rows)

def normalize_long_struct(df_wide: pd.DataFrame) -> pd.DataFrame:
    struct_cols = [c for c in df_wide.columns if c.startswith("e")]
    long = df_wide.melt(
        id_vars=["provincia", "canton"],
        value_vars=struct_cols,
        var_name="col",
        value_name="estructura"
    )
    long["estructura"] = long["estructura"].apply(clean_txt).apply(normalize_estructura)
    long = long[long["estructura"].str.len() > 0].copy()
    long.drop(columns=["col"], inplace=True)
    return long.reset_index(drop=True)

def add_coords(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["lat"] = df["canton"].map(lambda c: CANTON_COORDS.get(c, (None, None))[0])
    df["lon"] = df["canton"].map(lambda c: CANTON_COORDS.get(c, (None, None))[1])
    return df

wide_struct = build_wide_df_struct()
long_struct = add_coords(normalize_long_struct(wide_struct))

# =========================
# DATOS — PESTAÑA 2: BANDAS MUSICALES (LO QUE ENVIASTE EN IMÁGENES)
# =========================
BANDAS_ROWS = [
    # Alajuela
    ("Alajuela", "Alajuela", "Banda Municipal de Alajuela", 82),
    ("Alajuela", "Atenas", "Banda Escuela Municipal de Atenas", 50),
    ("Alajuela", "Grecia", "Centro de la Cultura (Academia Edol)", 10),
    ("Alajuela", "Guatuso", "Centro preventivo", 25),
    ("Alajuela", "Guatuso", "Banda Escuela Municipal de Guatuso", 25),
    ("Alajuela", "Los Chiles", "Banda Municipal de Los Chiles", 40),
    ("Alajuela", "Naranjo", "Banda Escuela de Concepción / Colegio La Candelaria / Banda Municipal", 155),
    ("Alajuela", "Orotina", "Banda Comunal de Orotina", 250),
    ("Alajuela", "Palmares", "Banda Escuela Municipal de Palmares", 178),
    ("Alajuela", "Peñas Blancas", "Banda Municipal de Peñas Blancas", 40),
    ("Alajuela", "Rio Cuarto", "Banda Comunal de Rio Cuarto", 50),
    ("Alajuela", "San Carlos", "Banda Municipal de San Carlos", 150),
    ("Alajuela", "San Mateo", "Banda Municipal de San Mateo", 100),
    ("Alajuela", "Upala", "Escuela Música Municipal de Upala", 100),
    ("Alajuela", "Zarcero", "Banda de marcha de Zarcero", 300),

    # Cartago (algunas filas venían sin beneficiarios en la imagen; se dejan como 0 si faltan)
    ("Cartago", "Cartago", "Banda Escuela de Cartago", 0),
    ("Cartago", "Cervantes", "Banda Escuela for Cerva de Cervantes", 0),
    ("Cartago", "Jiménez", "Escuela Municipal de Música de Jiménez", 79),
    ("Cartago", "La Unión", "Escuela de la Música de La Unión", 20),
    ("Cartago", "La Unión", "Banda Municipal de Marca de la Unión", 30),
    ("Cartago", "Tucurrique", "Banda Escuela de Tucurrique", 0),
    ("Cartago", "Turrialba", "Banda Municipal de Turrialba", 42),

    # Guanacaste
    ("Guanacaste", "Abangares", "Banda Melorítmica Lourdes y Pozo Azul (LP)", 32),
    ("Guanacaste", "Bagaces", "Banda Comunitaria", 27),
    ("Guanacaste", "Colorado", "Banda Municipal de Marcha de Colorado", 149),
    ("Guanacaste", "La Cruz", "Escuela de Musica La Cruz", 350),
    ("Guanacaste", "Nicoya", "Banda de marcha municipal", 180),
    ("Guanacaste", "Santa Cruz", "Centro Cívico por la Paz Santa Cruz / Proy. Polic. Comunitario", 0),
    ("Guanacaste", "Tilaran", "Banda Escuela Municipal de Tilaran", 150),

    # Heredia
    ("Heredia", "Barva", "Casa de la música de Barva", 50),
    ("Heredia", "Flores", "Banda Escuela Municipal de Flores", 50),
    ("Heredia", "Heredia", "Banda Escuela for Heredia de Heredia", 100),
    ("Heredia", "San Pablo", "Escuela de Musica", 100),
    ("Heredia", "San Pablo", "Banda estudiantil MAVISA", 150),
    ("Heredia", "Santa Bárbara", "Banda Municipal de Santa Bárbara", 50),
    ("Heredia", "Sarapiquí", "Banda Escuela Piano de Sarapiquí", 25),
    ("Heredia", "Sarapiquí", "Banda Escuela de Sarapiquí", 100),

    # Institución (se asigna provincia por cantón si aplica; si no, se marca Unknown->San Jose por defecto)
    ("San Jose", "Vice Paz", "Centro Cívico por la Paz", 25),

    # Limón
    ("Limon", "Limón", "Kawe Calipso Youth", 30),
    ("Limon", "Matina", "Banda Municipal d Matina", 45),
    ("Limon", "Pococi", "Banda Escuela Municipal de Pococi", 100),
    ("Limon", "Pococi", "Banda Cospnli de for NPA Pococi", 100),
    ("Limon", "Siquirres", "Banda Escuela for Siqui de Siquirres", 50),

    # Puntarenas
    ("Puntarenas", "Cóbano", "Banda Escuela for CMD C de Cóbano", 75),
    ("Puntarenas", "Coto Brus", "Banda Municipal de Coto Brus", 75),
    ("Puntarenas", "Coto Brus", "Colideportivo de Brus", 50),
    ("Puntarenas", "Puntarenas", "Banda de Puntarenas Barranca", 150),
    ("Puntarenas", "Quepos", "Banda Escuela for Munic de Quepos", 120),

    # San José
    ("San Jose", "Acosta", "Banda Escuela Instrumen de Acosta", 50),
    ("San Jose", "Aserri", "Banda Escuela for Aserr de Aserri", 50),
    ("San Jose", "Desamparados", "Banda Municipal de Desamparados", 195),
    ("San Jose", "Desamparados", "Banda Municipal de Desamparados", 0),
    ("San Jose", "Desamparados", "Banda Escuela de Desamparados", 75),
    ("San Jose", "Dota", "Banda Escuela for Dota", 100),
    ("San Jose", "Montes de Oca", "Banda Estudiantil Liceo Anastasio Alfaro", 100),
    ("San Jose", "Montes de Oca", "Banda Estudiantil Liceo Anastasio Alfaro", 0),
    ("San Jose", "Puriscal", "Banda Municipal de Puriscal", 130),
    ("San Jose", "San José", "Banda Municipal de San José", 200),
    ("San Jose", "Goicoechea", "Banda de Marcha de Heredia", 50),
    ("San Jose", "Santa Ana", "Banda Cantonal Municipal de Santa Ana", 115),
    ("San Jose", "Santa Ana", "EMAI", 100),
    ("San Jose", "Tarrazú", "Banda Escuela Municipal de Tarrazú", 30),
    ("San Jose", "Turrubares", "Banda Escuela Municipal de Turrubares", 25),
]

def normalize_prov_name(p: str) -> str:
    p = clean_txt(p)
    # normalizar tildes o variantes
    if p.lower() in ["san josé", "san jose"]:
        return "San Jose"
    if p.lower() in ["limón", "limon"]:
        return "Limon"
    if p.lower() == "tarrazú":
        return "Tarrazu"
    return p

def build_bandas_df() -> pd.DataFrame:
    rows = []
    for prov, canton, nombre, benef in BANDAS_ROWS:
        prov2 = normalize_prov_name(prov)
        c = clean_txt(canton).replace("San José", "San Jose").replace("Limón", "Limon")
        c = c.replace("Tarrazú", "Tarrazu")
        rows.append({
            "provincia": prov2,
            "canton": c,
            "nombre": clean_txt(nombre),
            "beneficiarios": safe_int(benef),
        })
    df = pd.DataFrame(rows)
    df["lat"] = df["canton"].map(lambda x: CANTON_COORDS.get(x, (None, None))[0])
    df["lon"] = df["canton"].map(lambda x: CANTON_COORDS.get(x, (None, None))[1])
    return df

df_bandas = build_bandas_df()

# =========================
# DATOS — PESTAÑA 3: CENTROS PREVENTIVOS COMUNITARIOS (SIN PROVINCIA -> SE ASIGNA)
# =========================
CPC_ROWS = [
    (40, "Alajuela / Vistas de Santamaria", "Centro Preventivo Comunitario"),
    (25, "Alajuela / Los Cocos", "Community Prevention Center"),
    (60, "Alajuelita / San Felipe", "Safe Space"),
    (40, "Alajuelita / Centro", "Casa de Creación Juvenil"),
    (40, "Corredores/ Sabalito", "Safe Space"),
    (40, "Coto Brus", "Safe Space"),
    (100, "Curridabat", "Human Center of Development La Cometa"),
    (50, "Desamparados", "Civic Center of Peace & Desamparados Municipality"),
    (350, "Desamparados/ Los Guido", "Safe Space"),
    (60, "Guatuso", "Safe Space"),
    (100, "Heredia", "Community Prevention Center"),
    (100, "La Cruz Santa Cecilia", "Safe Space"),
    (80, "La Cruz/ Centro", "Safe Space"),
    (30, "Limon/ Pueblo Nuevo", "Community Prevention Center: Youth Center"),
    (150, "Limon/ Cieneguita", "Community Prevention Center/ Safe Space/ Surf Boxing"),
    (15, "Limón/ Limoncito", "Community Prevention Center/ Safe Space"),
    (30, "Limón / Valle de la Estrella", "Colectivo deportivo Valle de la Estrella"),
    (100, "Limon/ Cocos", "Asoc de Futbol Club Atlético Limonense"),
    (150, "Los Chiles / Muelle", "Centro Preventivo Comunitario"),
    (100, "Los Chiles / La Virgen", "Safe Space"),
    (50, "Matina/ Estrada", "Safe Space"),
    (55, "Matina / Luzon", "Safe Space"),
    (75, "Montes de Oca", "Community Prevention Center / Circo Social de Sinaí"),
    (60, "Mora", "Casa de la Juventud/Club House"),
    (45, "Osa/ Bahia Ballena", "Centro Preventivo Comunitario"),
    (20, "Pococi/ la Sole", "ADI Sole, DINADECO, UNICEF, PANI, INL"),
    (100, "Puntarenas/ Barranca", "Centro Preventivo Comunitario / ONG Barranca Sport Club"),
    (15, "Puntarenas/ Chacarita", "Safe Space"),
    (50, "Puntarenas/ Fray Casiano", "Safe Space"),
    (20, "Quepos/ Pies Mojados", "Safe Space"),
    (70, "San Carlos", "Civic Center of Peace"),
    (40, "San José/ Pavas", "Safe Space"),
    (30, "San José/ Hatillo", "Safe Space"),
    (150, "San José / Carpio", "Safe Space"),
    (25, "San Ramón", "Safe Space"),
    (100, "Santa Ana", "Casita de Escucha Corazón de Jesús"),
    (100, "Santa Ana", "Casita de Escucha El Triunfo"),
    (40, "Sarapiquí / llanuras de Gaspar", "Safe Space"),
    (40, "Sarapiquí / puerto Viejo", "Safe Space"),
    (15, "Siquirres/ 3 Cercas", "Safe Space"),
    (25, "Turrialba", "Community Prevention Center"),
    (52, "Turrubares", "Safe Space"),
    (20, "Upala/ Mexico", "Safe Space"),
    (30, "Upala/ La Real", "Safe Space"),
]

def build_cpc_df() -> pd.DataFrame:
    rows = []
    for benef, canton_raw, centro in CPC_ROWS:
        canton = parse_canton_only(canton_raw)
        canton = canton.replace("San José", "San Jose").replace("Limón", "Limon").replace("San Ramón", "San Ramon")
        canton = canton.replace("Sarapiquí", "Sarapiqui")
        prov = CANTON_TO_PROV.get(canton, "San Jose")
        rows.append({
            "provincia": prov,
            "canton": canton,
            "centro": clean_txt(centro),
            "beneficiarios": safe_int(benef),
        })
    df = pd.DataFrame(rows)
    df["lat"] = df["canton"].map(lambda x: CANTON_COORDS.get(x, (None, None))[0])
    df["lon"] = df["canton"].map(lambda x: CANTON_COORDS.get(x, (None, None))[1])
    return df

df_cpc = build_cpc_df()
# ============================== PARTE 3/4 ==============================
# =========================
# DATOS — PESTAÑA 4: PROGRAMAS DE EMPLEABILIDAD (SIN PROVINCIA -> SE ASIGNA)
# =========================
EMP_ROWS = [
    # Canton, Cursos, Matriculadas, Egresadas, H, M
    ("Cartago 1", "Aseo y Limpieza de Espacios Comerciales | Servicio al Cliente | Manejo de Vehículos Pesados", "100", "95", "36", "59"),
    ("Cartago 2", "Aseo y Limpieza de Espacios Comerciales | Servicio al Cliente | Buenas Prácticas de Manufactura BPM | Operario de Construcción", "100", "113", "26", "87"),
    ("Turrialba 1", "Servicio al Cliente y Ventas | Aseo y Limpieza de Espacios Comerciales | Pistero de Gasolinera", "100", "88", "61", "27"),
    ("Turrialba 2", "Servicio al Cliente y Ventas | Aseo y Limpieza de Espacios Comerciales | Pistero de Gasolinera | Buenas Prácticas de Manufactura BPM", "100", "71", "48", "23"),
    ("Puntarenas 1", "Buenas Prácticas de Manufactura BPM | Auxiliar de Bodega | Atención y Servicio al Cliente para Salonero | Pistero de Gasolinera | Aseo y Limpieza en Hotelería", "100", "88", "27", "61"),
    ("Limon 1", "Aseo y Limpieza Cabinas y Hoteles | Servicio al Cliente para Comercio | Auxiliar de Bodega | Pistero de Gasolinera", "100", "89", "20", "69"),
    ("Abangares", "Auxiliar de cocina | Servicio al Cliente y ventas", "30", "31", "6", "25"),
    ("Pococi 1", "Buenas Prácticas de Manufactura con énfasis en industria alimentaria | Auxiliar de Bodega", "100", "97", "52", "45"),
    ("Desamparados", "Servicio al cliente con énfasis en ferretería | Buenas Prácticas de Manufactura con énfasis en industria alimentaria | Auxiliar de Bodega", "100", "83", "30", "53"),
    ("La Unión", "Buenas Prácticas de Manufactura con énfasis en industria alimentaria | Auxiliar de Bodega | Aseo y Limpieza de locales comerciales", "100", "85", "36", "49"),
    ("Curridabat", "Buenas Prácticas de Manufactura con énfasis en industria alimentaria | Auxiliar de Bodega | Aseo y Limpieza de locales comerciales", "100", "73", "23", "50"),
    ("Puntarenas 2", "Buenas Prácticas de Manufactura BPM | Auxiliar de Bodega | Atención y Servicio al Cliente para Salonero | Pistero de Gasolinera | Aseo y Limpieza en Hotelería", "100", "100", "25", "75"),
    ("Limon 2", "Servicio al cliente con énfasis en ferretería | Saloneros | Auxiliar de Bodega", "100", "78", "26", "52"),
    ("Alajuela", "Buenas Prácticas de Manufactura en Industria Alimentaria | Servicio y Atención en Hotelería y Centros de Alojamiento", "100", "87", "45", "42"),
    ("Upala", "Operario Agrícola | Servicio y Atención en Hotelería y Centros de Alojamiento", "100", "89", "31", "58"),
    ("Oreamuno", "Buenas Prácticas de Manufactura con énfasis en industria alimentaria", "30", "31", "6", "25"),
    ("Pococi 2", "Servicio al cliente con énfasis en Cajas | Auxiliar de bodega | Auxiliar de cocina | Aseo y Limpieza de locales comerciales", "100", "100", "19", "81"),
    ("Turrialba 3", "Buenas Prácticas de Manufactura en Industria Alimentaria", "50", "50", "0", "0"),
    ("Mora", "Salonero - Bartender | Cuidadoras de niños | Auxiliar de Bodega", "40", "40", "7", "33"),
    ("Goicoechea", "Buenas Prácticas de Manufactura en Industria Alimentaria | Servicio y Atención en Hotelería y Centros de Alojamiento", "58", "0", "10", "48"),
    ("Santa Cruz", "Servicios de Hotelería y Centros de Alojamiento", "50", "29", "0", "0"),
    ("La Cruz", "Peón de finca | Atención en Hotelería y Centros de Alojamiento", "50", "0", "0", "0"),
    ("Bagaces", "Servicios de Hotelería y Centros de Alojamiento", "50", "47", "0", "0"),
]

def clean_emp_canton(x: str) -> str:
    x = clean_txt(x).replace("La Unión", "La Union").replace("Limón", "Limon")
    # casos "Cartago 1/2", "Puntarenas 1/2", "Limon 1/2", "Pococi 1/2", "Turrialba 1/2/3"
    base = re.sub(r"\s+\d+$", "", x).strip()
    return base

def build_emp_df() -> pd.DataFrame:
    rows = []
    for canton_raw, cursos, mat, egr, h, m in EMP_ROWS:
        canton_base = clean_emp_canton(canton_raw)
        prov = CANTON_TO_PROV.get(canton_base, "San Jose")
        rows.append({
            "provincia": prov,
            "canton": canton_base,
            "sede": clean_txt(canton_raw),
            "cursos": clean_txt(cursos),
            "matriculadas": safe_int(mat),
            "egresadas": safe_int(egr),
            "hombres": safe_int(h),
            "mujeres": safe_int(m),
        })
    df = pd.DataFrame(rows)
    df["lat"] = df["canton"].map(lambda x: CANTON_COORDS.get(x, (None, None))[0])
    df["lon"] = df["canton"].map(lambda x: CANTON_COORDS.get(x, (None, None))[1])
    return df

df_emp = build_emp_df()

# =========================
# HELPERS DE ORDEN Y TABLAS
# =========================
def sort_by_prov_order(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["__prov_order__"] = df["provincia"].apply(lambda x: PROV_ORDER.index(x) if x in PROV_ORDER else 999)
    df = df.sort_values(["__prov_order__", "canton"]).drop(columns=["__prov_order__"])
    return df

def make_filter_box(tabkey: str, provincias, cantones, nombres, label_nombre: str):
    st.markdown("<div class='filterbox'>", unsafe_allow_html=True)
    st.markdown(f"<div class='filtertitle'>Filtros — {tabkey}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        prov_sel = st.multiselect("Provincia", provincias, default=[], key=f"{tabkey}_prov")
    with c2:
        cant_sel = st.multiselect("Cantón", cantones, default=[], key=f"{tabkey}_cant")

    name_sel = st.multiselect(label_nombre, nombres, default=[], key=f"{tabkey}_name")

    st.markdown("<div class='smallhint'>Los filtros son independientes por pestaña.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    return prov_sel, cant_sel, name_sel

# =========================
# RENDER TAB — ESTRUCTURAS
# =========================
def render_tab_estructuras():
    st.markdown("<div class='title'>EstrukturAs criminales</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI, puntos por cantón y detalle de estructuras por ubicación.</div>", unsafe_allow_html=True)

    data = long_struct.copy()
    data["provincia"] = data["provincia"].apply(clean_txt)
    data["canton"] = data["canton"].apply(clean_txt)
    data["estructura"] = data["estructura"].apply(clean_txt)

    provincias = PROV_ORDER[:]  # orden fijo
    cantones = sorted(data["canton"].unique().tolist())
    estructuras = sorted(data["estructura"].unique().tolist())

    prov_sel, cant_sel, estr_sel = make_filter_box("Estructuras", provincias, cantones, estructuras, "Estructura")

    f = data.copy()
    if prov_sel:
        f = f[f["provincia"].isin(prov_sel)]
    if cant_sel:
        f = f[f["canton"].isin(cant_sel)]
    if estr_sel:
        f = f[f["estructura"].isin(estr_sel)]

    cantones_unicos = f["canton"].nunique()
    estructuras_unicas = f["estructura"].nunique()

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-a">
            <div class="kpi-label">Cantones</div>
            <div class="kpi-value">{cantones_unicos:,}</div>
            <div class="kpi-sub">Total según filtros</div>
          </div>
          <div class="kpi kpi-b">
            <div class="kpi-label">Estructuras</div>
            <div class="kpi-value">{estructuras_unicas:,}</div>
            <div class="kpi-sub">Únicas según filtros</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Top 10 estructuras (conteos)")

        top_struct = (
            f.groupby("estructura")
            .size()
            .reset_index(name="conteo")
            .sort_values("conteo", ascending=False)
            .head(10)
        )
        fig_bar = px.bar(top_struct, x="conteo", y="estructura", orientation="h")
        fig_bar.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Tabla normalizada")

        tabla_unificada = (
            f.groupby(["provincia", "canton"])["estructura"]
            .apply(lambda s: ", ".join(sorted(set(s))))
            .reset_index()
            .rename(columns={"estructura": "Estructuras"})
        )
        tabla_unificada = sort_by_prov_order(tabla_unificada)

        st.dataframe(
            tabla_unificada[["provincia", "canton", "Estructuras"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )

        excel_bytes = df_to_pretty_excel_bytes(
            tabla_unificada.rename(columns={"provincia": "Provincia", "canton": "Canton"}),
            sheet_name="Estructuras"
        )
        st.download_button(
            "⬇️ Descargar Excel (Estructuras)",
            data=excel_bytes,
            file_name="estructuras_normalizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — puntos por cantón")

        def popup_builder_struct(row):
            # agrupar para popup completo por cantón (lista de estructuras)
            canton = row["canton"]
            provincia = row["provincia"]
            sub = f[(f["provincia"] == provincia) & (f["canton"] == canton)]
            estructuras_list = sorted(set(sub["estructura"].tolist()))
            registros = int(len(sub))

            html = f"""
            <div style="font-family: Arial; font-size: 13px; line-height: 1.25;">
              <div style="font-size: 14px;"><b>{canton}</b></div>
              <div><b>Provincia:</b> {provincia}</div>
              <div><b>Estructuras:</b> {len(estructuras_list)}</div>
              <div style="margin-top:6px;"><b>Listado:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{e}</li>' for e in estructuras_list])}
              </ul>
            </div>
            """
            radius = 6 + min(16, registros * 1.2)
            return html, radius

        grp = (
            f.dropna(subset=["lat", "lon"])
            .groupby(["provincia", "canton", "lat", "lon"])
            .size()
            .reset_index(name="n")
        )

        render_map_points(grp, height_px=820, popup_builder=popup_builder_struct)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RENDER TAB — BANDAS MUSICALES
# =========================
def render_tab_bandas():
    st.markdown("<div class='title'>Bandas Musicales</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI con beneficiarios por cantón y resumen por provincia.</div>", unsafe_allow_html=True)

    data = df_bandas.copy()
    data["provincia"] = data["provincia"].apply(normalize_prov_name)
    data["canton"] = data["canton"].apply(lambda x: clean_txt(x).replace("San José", "San Jose").replace("Limón", "Limon"))
    data["nombre"] = data["nombre"].apply(clean_txt)
    data["beneficiarios"] = data["beneficiarios"].apply(safe_int)

    provincias = PROV_ORDER[:]
    cantones = sorted(data["canton"].unique().tolist())
    nombres = sorted(data["nombre"].unique().tolist())

    prov_sel, cant_sel, name_sel = make_filter_box("Bandas", provincias, cantones, nombres, "Nombre de club o banda")

    f = data.copy()
    if prov_sel:
        f = f[f["provincia"].isin(prov_sel)]
    if cant_sel:
        f = f[f["canton"].isin(cant_sel)]
    if name_sel:
        f = f[f["nombre"].isin(name_sel)]

    total_benef = int(f["beneficiarios"].sum())
    cantones_unicos = f["canton"].nunique()
    programas = len(f)

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-a">
            <div class="kpi-label">Cantones</div>
            <div class="kpi-value">{cantones_unicos:,}</div>
            <div class="kpi-sub">Total según filtros</div>
          </div>
          <div class="kpi kpi-b">
            <div class="kpi-label">Registros</div>
            <div class="kpi-value">{programas:,}</div>
            <div class="kpi-sub">Bandas/clubes según filtros</div>
          </div>
          <div class="kpi kpi-c">
            <div class="kpi-label">Beneficiarios</div>
            <div class="kpi-value">{total_benef:,}</div>
            <div class="kpi-sub">Suma total según filtros</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Beneficiarios por provincia")

        prov_sum = (
            f.groupby("provincia")["beneficiarios"].sum()
            .reindex(PROV_ORDER)
            .fillna(0)
            .reset_index()
        )
        fig = px.bar(prov_sum, x="provincia", y="beneficiarios")
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabla normalizada")

        tabla = (
            f.groupby(["provincia", "canton"])
            .agg(
                Beneficiarios=("beneficiarios", "sum"),
                Bandas=("nombre", lambda s: ", ".join(sorted(set(s))))
            )
            .reset_index()
        )
        tabla = sort_by_prov_order(tabla)

        st.dataframe(
            tabla[["provincia", "canton", "Beneficiarios", "Bandas"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )

        excel_bytes = df_to_pretty_excel_bytes(
            tabla.rename(columns={"provincia": "Provincia", "canton": "Canton"}),
            sheet_name="Bandas"
        )
        st.download_button(
            "⬇️ Descargar Excel (Bandas)",
            data=excel_bytes,
            file_name="bandas_musicales.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — beneficiarios por cantón")

        grp = (
            f.dropna(subset=["lat", "lon"])
            .groupby(["provincia", "canton", "lat", "lon"])
            .agg(
                beneficiarios=("beneficiarios", "sum"),
                nombres=("nombre", lambda s: sorted(set(s)))
            )
            .reset_index()
        )

        def popup_builder_bandas(row):
            canton = row["canton"]
            provincia = row["provincia"]
            benef = int(row["beneficiarios"])
            nombres = row["nombres"]

            html = f"""
            <div style="font-family: Arial; font-size: 13px; line-height: 1.25;">
              <div style="font-size: 14px;"><b>{canton}</b></div>
              <div><b>Provincia:</b> {provincia}</div>
              <div><b>Beneficiarios:</b> {benef:,}</div>
              <div style="margin-top:6px;"><b>Bandas:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{n}</li>' for n in nombres])}
              </ul>
            </div>
            """
            radius = 6 + min(20, max(1, benef) / 20)
            return html, radius

        render_map_points(grp, height_px=820, popup_builder=popup_builder_bandas)
        st.markdown("</div>", unsafe_allow_html=True)
# ============================== PARTE 4/4 ==============================
# =========================
# RENDER TAB — CENTROS PREVENTIVOS COMUNITARIOS
# =========================
def render_tab_cpc():
    st.markdown("<div class='title'>Centros Preventivos Comunitarios</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI con beneficiarios por cantón, colores por provincia y filtros independientes.</div>", unsafe_allow_html=True)

    data = df_cpc.copy()
    data["provincia"] = data["provincia"].apply(clean_txt)
    data["canton"] = data["canton"].apply(clean_txt)
    data["centro"] = data["centro"].apply(clean_txt)
    data["beneficiarios"] = data["beneficiarios"].apply(safe_int)

    provincias = PROV_ORDER[:]
    cantones = sorted(data["canton"].unique().tolist())
    centros = sorted(data["centro"].unique().tolist())

    prov_sel, cant_sel, name_sel = make_filter_box("CPC", provincias, cantones, centros, "Nombre del centro")

    f = data.copy()
    if prov_sel:
        f = f[f["provincia"].isin(prov_sel)]
    if cant_sel:
        f = f[f["canton"].isin(cant_sel)]
    if name_sel:
        f = f[f["centro"].isin(name_sel)]

    total_benef = int(f["beneficiarios"].sum())
    cantones_unicos = f["canton"].nunique()
    registros = len(f)

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-a">
            <div class="kpi-label">Cantones</div>
            <div class="kpi-value">{cantones_unicos:,}</div>
            <div class="kpi-sub">Total según filtros</div>
          </div>
          <div class="kpi kpi-b">
            <div class="kpi-label">Registros</div>
            <div class="kpi-value">{registros:,}</div>
            <div class="kpi-sub">Centros según filtros</div>
          </div>
          <div class="kpi kpi-c">
            <div class="kpi-label">Beneficiarios</div>
            <div class="kpi-value">{total_benef:,}</div>
            <div class="kpi-sub">Suma total según filtros</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Beneficiarios por provincia")

        prov_sum = (
            f.groupby("provincia")["beneficiarios"].sum()
            .reindex(PROV_ORDER)
            .fillna(0)
            .reset_index()
        )
        fig = px.bar(prov_sum, x="provincia", y="beneficiarios")
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabla normalizada")

        tabla = (
            f.groupby(["provincia", "canton"])
            .agg(
                Beneficiarios=("beneficiarios", "sum"),
                Centros=("centro", lambda s: ", ".join(sorted(set(s))))
            )
            .reset_index()
        )
        tabla = sort_by_prov_order(tabla)

        st.dataframe(
            tabla[["provincia", "canton", "Beneficiarios", "Centros"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )

        excel_bytes = df_to_pretty_excel_bytes(
            tabla.rename(columns={"provincia": "Provincia", "canton": "Canton"}),
            sheet_name="CPC"
        )
        st.download_button(
            "⬇️ Descargar Excel (CPC)",
            data=excel_bytes,
            file_name="centros_preventivos_comunitarios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — beneficiarios por cantón")

        grp = (
            f.dropna(subset=["lat", "lon"])
            .groupby(["provincia", "canton", "lat", "lon"])
            .agg(
                beneficiarios=("beneficiarios", "sum"),
                centros=("centro", lambda s: sorted(set(s)))
            )
            .reset_index()
        )

        def popup_builder_cpc(row):
            canton = row["canton"]
            provincia = row["provincia"]
            benef = int(row["beneficiarios"])
            centros = row["centros"]

            html = f"""
            <div style="font-family: Arial; font-size: 13px; line-height: 1.25;">
              <div style="font-size: 14px;"><b>{canton}</b></div>
              <div><b>Provincia:</b> {provincia}</div>
              <div><b>Beneficiarios:</b> {benef:,}</div>
              <div style="margin-top:6px;"><b>Centros:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{c}</li>' for c in centros])}
              </ul>
            </div>
            """
            radius = 6 + min(20, max(1, benef) / 25)
            return html, radius

        render_map_points(grp, height_px=820, popup_builder=popup_builder_cpc)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RENDER TAB — PROGRAMAS DE EMPLEABILIDAD (NUEVO)
# =========================
def render_tab_empleabilidad():
    st.markdown("<div class='title'>Programas de empleabilidad</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI con detalle por sede/cantón y dos gráficas por provincia.</div>", unsafe_allow_html=True)

    data = df_emp.copy()
    data["provincia"] = data["provincia"].apply(clean_txt)
    data["canton"] = data["canton"].apply(clean_txt)
    data["sede"] = data["sede"].apply(clean_txt)
    data["cursos"] = data["cursos"].apply(clean_txt)

    provincias = PROV_ORDER[:]
    cantones = sorted(data["canton"].unique().tolist())
    sedes = sorted(data["sede"].unique().tolist())

    prov_sel, cant_sel, sede_sel = make_filter_box("Empleabilidad", provincias, cantones, sedes, "Sede (nombre)")

    f = data.copy()
    if prov_sel:
        f = f[f["provincia"].isin(prov_sel)]
    if cant_sel:
        f = f[f["canton"].isin(cant_sel)]
    if sede_sel:
        f = f[f["sede"].isin(sede_sel)]

    total_mat = int(f["matriculadas"].sum())
    total_egr = int(f["egresadas"].sum())
    total_h = int(f["hombres"].sum())
    total_m = int(f["mujeres"].sum())

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-a">
            <div class="kpi-label">Matriculadas</div>
            <div class="kpi-value">{total_mat:,}</div>
            <div class="kpi-sub">Suma según filtros</div>
          </div>
          <div class="kpi kpi-b">
            <div class="kpi-label">Egresadas</div>
            <div class="kpi-value">{total_egr:,}</div>
            <div class="kpi-sub">Suma según filtros</div>
          </div>
          <div class="kpi kpi-c">
            <div class="kpi-label">Hombres / Mujeres</div>
            <div class="kpi-value">{total_h:,} / {total_m:,}</div>
            <div class="kpi-sub">Suma según filtros</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)

        st.subheader("Matriculadas vs Egresadas (por provincia)")
        prov_me = (
            f.groupby("provincia")[["matriculadas", "egresadas"]].sum()
            .reindex(PROV_ORDER)
            .fillna(0)
            .reset_index()
        )
        prov_me_long = prov_me.melt(id_vars=["provincia"], value_vars=["matriculadas", "egresadas"],
                                   var_name="tipo", value_name="cantidad")
        fig1 = px.bar(prov_me_long, x="provincia", y="cantidad", color="tipo", barmode="group")
        fig1.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("Hombres vs Mujeres (por provincia)")
        prov_hm = (
            f.groupby("provincia")[["hombres", "mujeres"]].sum()
            .reindex(PROV_ORDER)
            .fillna(0)
            .reset_index()
        )
        prov_hm_long = prov_hm.melt(id_vars=["provincia"], value_vars=["hombres", "mujeres"],
                                    var_name="sexo", value_name="cantidad")
        fig2 = px.bar(prov_hm_long, x="provincia", y="cantidad", color="sexo", barmode="group")
        fig2.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Tabla normalizada")

        tabla = (
            f.groupby(["provincia", "canton"])
            .agg(
                Matriculadas=("matriculadas", "sum"),
                Egresadas=("egresadas", "sum"),
                Hombres=("hombres", "sum"),
                Mujeres=("mujeres", "sum"),
                Cursos=("cursos", lambda s: " | ".join(sorted(set([x for x in s if x]))))
            )
            .reset_index()
        )
        tabla = sort_by_prov_order(tabla)

        st.dataframe(
            tabla[["provincia", "canton", "Matriculadas", "Egresadas", "Hombres", "Mujeres", "Cursos"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )

        excel_bytes = df_to_pretty_excel_bytes(
            tabla.rename(columns={"provincia": "Provincia", "canton": "Canton"}),
            sheet_name="Empleabilidad"
        )
        st.download_button(
            "⬇️ Descargar Excel (Empleabilidad)",
            data=excel_bytes,
            file_name="programas_empleabilidad.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — detalle por sede/cantón")

        grp = (
            f.dropna(subset=["lat", "lon"])
            .groupby(["provincia", "canton", "lat", "lon"])
            .agg(
                matriculadas=("matriculadas", "sum"),
                egresadas=("egresadas", "sum"),
                hombres=("hombres", "sum"),
                mujeres=("mujeres", "sum"),
                cursos=("cursos", lambda s: sorted(set([x for x in s if x]))),
                sedes=("sede", lambda s: sorted(set([x for x in s if x]))),
            )
            .reset_index()
        )

        def popup_builder_emp(row):
            canton = row["canton"]
            provincia = row["provincia"]
            mat = int(row["matriculadas"])
            egr = int(row["egresadas"])
            h = int(row["hombres"])
            m = int(row["mujeres"])
            cursos = row["cursos"]
            sedes = row["sedes"]

            html = f"""
            <div style="font-family: Arial; font-size: 13px; line-height: 1.25;">
              <div style="font-size: 14px;"><b>{canton}</b></div>
              <div><b>Provincia:</b> {provincia}</div>
              <div><b>Matriculadas:</b> {mat:,}</div>
              <div><b>Egresadas:</b> {egr:,}</div>
              <div><b>Hombres:</b> {h:,} &nbsp;&nbsp; <b>Mujeres:</b> {m:,}</div>
              <div style="margin-top:6px;"><b>Sedes:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{s}</li>' for s in sedes])}
              </ul>
              <div style="margin-top:6px;"><b>Cursos brindados:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{c}</li>' for c in cursos])}
              </ul>
            </div>
            """
            radius = 7 + min(20, max(1, mat) / 25)
            return html, radius

        render_map_points(grp, height_px=820, popup_builder=popup_builder_emp)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# APP PRINCIPAL — PESTAÑAS ARRIBA
# =========================
tabs = st.tabs(["EstrukturAs criminales", "Bandas Musicales", "Centros Preventivos Comunitarios", "Programas de empleabilidad"])

with tabs[0]:
    render_tab_estructuras()

with tabs[1]:
    render_tab_bandas()

with tabs[2]:
    render_tab_cpc()

with tabs[3]:
    render_tab_empleabilidad()

