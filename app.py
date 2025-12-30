# app.py
# streamlit run app.py

import re
import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="CR | Cantones y estructuras", page_icon="🛰️", layout="wide")

# =========================
# ESTILO (IGUAL + SOLO COLOR KPIs)
# =========================
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.0rem; padding-bottom: 2rem;}
      .title{font-size: 28px; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 2px;}
      .subtitle{color:#6b7280; margin-top:0px; margin-bottom: 14px;}
      .kpi-grid{display:flex; gap:14px; flex-wrap:wrap; margin-bottom: 10px;}

      /* === KPI con color (nuevo) === */
      .kpi{
        border-radius:18px;
        padding:16px 18px;
        box-shadow:0 10px 25px rgba(0,0,0,0.08);
        min-width: 240px; flex:1;
        border:1px solid rgba(255,255,255,0.14);
        color:#0b1220;
      }
      .kpi.kpi-cantones{
        background: linear-gradient(135deg, rgba(99,102,241,0.22), rgba(59,130,246,0.10));
        border:1px solid rgba(99,102,241,0.35);
      }
      .kpi.kpi-estructuras{
        background: linear-gradient(135deg, rgba(16,185,129,0.22), rgba(34,197,94,0.10));
        border:1px solid rgba(16,185,129,0.35);
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
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# FIX VISIBILIDAD DE TABS (NUEVO)
# =========================
st.markdown(
    """
    <style>
      div[data-baseweb="tab-list"]{
        position: relative !important;
        z-index: 99999 !important;
        margin-top: 6px !important;
        margin-bottom: 14px !important;
      }
      button[data-baseweb="tab"]{
        font-weight: 800 !important;
        font-size: 14px !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# SESSION STATE (IGUAL + 3 fullscreen)
# =========================
if "map_fullscreen" not in st.session_state:
    st.session_state["map_fullscreen"] = False
if "map_fullscreen_bandas" not in st.session_state:
    st.session_state["map_fullscreen_bandas"] = False
if "map_fullscreen_cpc" not in st.session_state:
    st.session_state["map_fullscreen_cpc"] = False

# =========================
# ORDEN FIJO DE PROVINCIAS (NUEVO SOLO PARA TABLAS)
# =========================
PROV_ORDER = ["San Jose", "Alajuela", "Cartago", "Heredia", "Guanacaste", "Puntarenas", "Limon"]
PROV_RANK = {p: i for i, p in enumerate(PROV_ORDER)}

def sort_by_prov_order(df: pd.DataFrame, prov_col: str = "provincia") -> pd.DataFrame:
    df = df.copy()
    df["_prov_rank"] = df[prov_col].map(lambda x: PROV_RANK.get(x, 999))
    return df.sort_values(["_prov_rank", prov_col], ascending=[True, True]).drop(columns=["_prov_rank"])

# =========================
# COLORES POR PROVINCIA (IGUAL)
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

# =========================
# NORMALIZACIÓN (IGUAL)
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

# =========================
# NORMALIZACIÓN EXTRA (Bandas + CPC) (NUEVO, NO ROMPE)
# =========================
def _strip_accents(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    repl = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("ñ", "n"), ("Ñ", "N")
    )
    for a, b in repl:
        s = s.replace(a, b)
    return s

def normalize_prov_generic(p: str) -> str:
    p = clean_txt(p)
    p = _strip_accents(p)
    p = p.replace(".", "")
    p = p.replace("  ", " ")
    p_low = p.lower()

    if p_low in ["san jose", "san josé"]:
        return "San Jose"
    if p_low in ["limon", "limón"]:
        return "Limon"
    if p_low == "puntarenas":
        return "Puntarenas"
    if p_low == "guanacaste":
        return "Guanacaste"
    if p_low == "heredia":
        return "Heredia"
    if p_low == "cartago":
        return "Cartago"
    if p_low == "alajuela":
        return "Alajuela"
    return p

def normalize_canton_generic(c: str) -> str:
    c = clean_txt(c)
    c = _strip_accents(c)
    c = c.replace("  ", " ")

    # ajustes comunes
    if c.lower() == "peñas blancas":
        return "Penas Blancas"
    if c.lower() == "cóbano":
        return "Cobano"
    if c.lower() == "río cuarto":
        return "Rio Cuarto"
    if c.lower() == "san josé":
        return "San Jose"
    if c.lower() == "turrialba":
        return "Turrialba"
    if c.lower() == "tucurrique":
        return "Tucurrique"
    if c.lower() == "tarrazú":
        return "Tarrazu"
    if c.lower() == "aserrí":
        return "Aserri"
    if c.lower() == "sarapiquí":
        return "Sarapiqui"
    if c.lower() == "santa bárbara":
        return "Santa Barbara"
    return c

def split_canton_base(x: str) -> str:
    """
    Ej: 'San José/ Pavas' => 'San José'
        'Alajuela / Los Cocos' => 'Alajuela'
        'La Cruz Santa Cecilia' => 'La Cruz' (heurística)
    """
    x = clean_txt(x)
    if not x:
        return ""
    # si viene con /, el cantón base suele estar antes del primer /
    if "/" in x:
        base = x.split("/")[0].strip()
        return base
    # si viene con " / " (ya cubierto por /)
    # si viene "La Cruz Santa Cecilia", asumimos cantón "La Cruz"
    low = _strip_accents(x).lower()
    if low.startswith("la cruz"):
        return "La Cruz"
    return x

# =========================
# DATOS (MATRIZ ANCHA) — IGUAL
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
# =========================
# COORDENADAS (centroides cantonales aprox. para mapear ya)
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

    # extra
    "Penas Blancas": (10.9780, -84.7370),
    "Cobano": (9.6840, -85.0960),
    "Quepos": (9.4310, -84.1620),
    "Colorado": (10.6000, -85.2000),
    "Cervantes": (9.8940, -83.8050),
    "Tucurrique": (9.8600, -83.7220),
}

# =========================
# MAPA DE CANTON -> PROVINCIA (NUEVO, SOLO PARA ASIGNAR PROVINCIA EN CPC)
# =========================
CANTON_TO_PROV = {}
for _p, _items in RAW_BY_PROV.items():
    for _c, _ in _items:
        CANTON_TO_PROV[normalize_canton_generic(_c)] = _p

# =========================
# HELPERS (IGUAL)
# =========================
def build_wide_df() -> pd.DataFrame:
    rows = []
    for prov, items in RAW_BY_PROV.items():
        for canton, structs in items:
            r = {"provincia": prov, "canton": canton}
            for i in range(10):
                r[f"e{i+1}"] = structs[i] if i < len(structs) else ""
            rows.append(r)
    return pd.DataFrame(rows)

def normalize_long(df_wide: pd.DataFrame) -> pd.DataFrame:
    struct_cols = [c for c in df_wide.columns if c.startswith("e")]
    long = df_wide.melt(
        id_vars=["provincia", "canton"],
        value_vars=struct_cols,
        var_name="col",
        value_name="estructura"
    )
    long["estructura"] = long["estructura"].apply(clean_txt)
    long["estructura"] = long["estructura"].apply(normalize_estructura)
    long = long[long["estructura"].str.len() > 0].copy()
    long.drop(columns=["col"], inplace=True)
    return long.reset_index(drop=True)

def add_coords(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["lat"] = df["canton"].map(lambda c: CANTON_COORDS.get(c, (None, None))[0])
    df["lon"] = df["canton"].map(lambda c: CANTON_COORDS.get(c, (None, None))[1])
    return df

# =========================
# BUILD DATA (IGUAL)
# =========================
wide = build_wide_df()
long = add_coords(normalize_long(wide))

# =========================
# ✅ TABS (3 PESTAÑAS)
# =========================
tab_estructuras, tab_bandas, tab_cpc = st.tabs(
    ["🛰️ Cantones y estructuras", "🎶 Bandas / Beneficiarios", "🏘️ Centros Preventivos Comunitarios"]
)

# =============================================================================
# ============================== TAB 1 (TU APP) =================================
# =============================================================================
with tab_estructuras:

    st.markdown("<div class='title'>Cantones y estructuras (Prueba 1)</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI, puntos por cantón y detalle de estructuras por ubicación.</div>", unsafe_allow_html=True)

    # =========================
    # FILTROS (TAB 1) — SEPARADOS
    # =========================
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Filtros (Estructuras)")

    fcol1, fcol2, fcol3 = st.columns([1, 1, 1], gap="medium")

    provincias = sorted(long["provincia"].unique().tolist(), key=lambda x: PROV_RANK.get(x, 999))
    cantones = sorted(long["canton"].unique().tolist())
    estructuras = sorted(long["estructura"].unique().tolist())

    with fcol1:
        prov_sel = st.multiselect("Provincia", provincias, default=[], key="tab1_prov")
    with fcol2:
        cant_sel = st.multiselect("Cantón", cantones, default=[], key="tab1_cant")
    with fcol3:
        estr_sel = st.multiselect("Estructura", estructuras, default=[], key="tab1_estr")

    st.markdown("</div>", unsafe_allow_html=True)

    f = long.copy()
    if prov_sel:
        f = f[f["provincia"].isin(prov_sel)]
    if cant_sel:
        f = f[f["canton"].isin(cant_sel)]
    if estr_sel:
        f = f[f["estructura"].isin(estr_sel)]

    cantones_unicos = f["canton"].nunique()
    estructuras_unicas = f["estructura"].nunique()

    # =========================
    # KPI (IGUAL)
    # =========================
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-cantones">
            <div class="kpi-label">Cantones</div>
            <div class="kpi-value">{cantones_unicos:,}</div>
            <div class="kpi-sub">Total según filtros</div>
          </div>
          <div class="kpi kpi-estructuras">
            <div class="kpi-label">Estructuras</div>
            <div class="kpi-value">{estructuras_unicas:,}</div>
            <div class="kpi-sub">Únicas según filtros</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    # =========================
    # MAP BUILDER (IGUAL)
    # =========================
    def render_map(df_filtered: pd.DataFrame, height_px: int):
        fm = df_filtered.dropna(subset=["lat", "lon"]).copy()
        if fm.empty:
            st.warning("No hay puntos con coordenadas para mostrar.")
            return

        grp = (
            fm.groupby(["provincia", "canton", "lat", "lon"])
            .agg(
                registros=("estructura", "count"),
                estructuras=("estructura", lambda s: sorted(set(s)))
            )
            .reset_index()
        )

        center_lat = float(grp["lat"].mean())
        center_lon = float(grp["lon"].mean())

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

        for _, r in grp.iterrows():
            provincia = r["provincia"]
            canton = r["canton"]
            estructuras_list = r["estructuras"]
            registros = int(r["registros"])

            colors = PROV_COLORS.get(provincia, {"stroke": "#111827", "fill": "#9ca3af"})

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
            popup = folium.Popup(html, max_width=420)
            tooltip = f"{canton} ({provincia}) | {len(estructuras_list)} estructuras"

            radius = 6 + min(16, registros * 1.2)

            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=radius,
                weight=2,
                color=colors["stroke"],
                fill=True,
                fill_color=colors["fill"],
                fill_opacity=0.55,
                tooltip=tooltip,
                popup=popup
            ).add_to(m)

        st.markdown("<div class='mapwrap'>", unsafe_allow_html=True)
        st_folium(m, use_container_width=True, height=height_px)
        st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # FULLSCREEN MODE (IGUAL)
    # =========================
    if st.session_state["map_fullscreen"]:
        st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
        if st.button("⬅️ Salir de pantalla completa", key="tab1_exit_full"):
            st.session_state["map_fullscreen"] = False
            st.rerun()
        st.markdown("<span class='caption'>Modo pantalla completa: el mapa ocupa casi toda la pantalla.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_map(f, height_px=920)
        st.stop()

    # =========================
    # VISTA NORMAL (IGUAL)
    # =========================
    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Top estructuras (conteos)")

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
            .rename(columns={"estructura": "estructuras"})
        )

        # ✅ ORDEN DE PROVINCIAS (NUEVO)
        tabla_unificada = sort_by_prov_order(tabla_unificada, "provincia").sort_values(
            ["provincia", "canton"], key=lambda col: col if col.name != "provincia" else col.map(lambda x: PROV_RANK.get(x, 999))
        )

        st.dataframe(
            tabla_unificada[["provincia", "canton", "estructuras"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — puntos por cantón")

        st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
        if st.button("⛶ Ver mapa en pantalla completa", key="tab1_full_btn"):
            st.session_state["map_fullscreen"] = True
            st.rerun()
        st.markdown("<span class='caption'>Abre el mapa ocupando casi toda la pantalla.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_map(f, height_px=820)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    csv_bytes = f.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar datos filtrados (CSV)",
        data=csv_bytes,
        file_name="cantones_estructuras_normalizado.csv",
        mime="text/csv",
        key="tab1_csv"
    )

    st.markdown(
        f"<div class='caption'>Resumen: <b>{estructuras_unicas}</b> estructuras únicas en <b>{cantones_unicos}</b> cantones (según filtros).</div>",
        unsafe_allow_html=True
    )
# =============================================================================
# ============================== TAB 2 (BANDAS) =================================
# =============================================================================
with tab_bandas:

    # =========================
    # DATOS DE BANDAS (EN CÓDIGO)
    # =========================
    BANDAS_RAW = [
        # Alajuela
        ("Alajuela", "Alajuela", "Banda Municipal de Alajuela", 82),
        ("Alajuela", "Atenas", "Banda Escuela Municipal de Atenas", 50),
        ("Alajuela", "Grecia", "Centro de la Cultura (Academia Edol)", 10),
        ("Alajuela", "Guatuso", "Centro preventivo", 25),
        ("Alajuela", "Guatuso", "Banda Escuela Municipal de Guatuso", 25),
        ("Alajuela", "Los Chiles", "Banda Municipal de Los Chiles", 40),
        ("Alajuela", "Naranjo", "Banda Escuela de Concepción, Colegio La Candelaria, Banda Municipal", 155),
        ("Alajuela", "Orotina", "Banda Comunal de Orotina", 250),
        ("Alajuela", "Palmares", "Banda Escuela Municipal de Palmares", 178),
        ("Alajuela", "Peñas Blancas", "Banda Municipal de Peñas Blancas", 40),
        ("Alajuela", "Rio Cuarto", "Banda Comunal de Rio Cuarto", 50),
        ("Alajuela", "San Carlos", "Banda Municipal de San Carlos", 150),
        ("Alajuela", "San Mateo", "Banda Municipal de San Mateo", 100),
        ("Alajuela", "Upala", "Escuela Música Municipal de Upala", 100),
        ("Alajuela", "Zarcero", "Banda de marcha de Zarcero", 300),

        # Cartago
        ("Cartago", "Cartago", "Banda Escuela de Cartago", None),
        ("Cartago", "Cervantes", "Banda Escuela for Cerva de Cervantes", None),
        ("Cartago", "Jiménez", "Escuela Municipal de Música de Jiménez", 79),
        ("Cartago", "La Unión", "Escuela de la Música de La Unión", 20),
        ("Cartago", "La Unión", "Banda Municipal de Marca de la Unión", 30),
        ("Cartago", "Tucurrique", "Banda Escuela de Tucurrique", None),
        ("Cartago", "Turrialba", "Banda Municipal de Turrialba", 42),

        # Guanacaste
        ("Guanacaste", "Abangares", "Banda Melorítmica Lourdes y Pozo Azul (LP)", 32),
        ("Guanacaste", "Bagaces", "Banda Comunitaria", 27),
        ("Guanacaste", "Colorado", "Banda Municipal de Marcha de Colorado", 149),
        ("Guanacaste", "La Cruz", "Escuela de Musica La Cruz", 350),
        ("Guanacaste", "Nicoya", "Banda de marcha municipal", 180),
        ("Guanacaste", "Santa Cruz", "Centro Civico por la Paz Santa Cruz/Proy Policiamiento Comunitario", None),
        ("Guanacaste", "Tilarán", "Banda Escuela Municipal de Tilaran", 150),

        # Heredia
        ("Heredia", "Barva", "Casa de la música de Barva", 50),
        ("Heredia", "Flores", "Banda Escuela Municipal de Flores", 50),
        ("Heredia", "Heredia", "Banda Escuela for Heredia de Heredia", 100),
        ("Heredia", "San Pablo", "Escuela de Musica", 100),
        ("Heredia", "San Pablo", "Banda estudiantil MAVISA", 150),
        ("Heredia", "Santa Bárbara", "Banda Municipal de Santa Bárbara", 50),
        ("Heredia", "Sarapiquí", "Banda Escuela Piano de Sarapiqui", 25),
        ("Heredia", "Sarapiquí", "Banda Escuela de Sarapiqui", 100),

        # Institución (sin coords)
        ("Institucion", "Vice Paz", "Centro Civico por la Paz", 25),

        # Limón
        ("Limón", "Limón", "Kawe Calipso Youth", 30),
        ("Limón", "Matina", "Banda Municipal d Matina", 45),
        ("Limón", "Pococi", "Banda Escuela Municipal de Pococi", 100),
        ("Limón", "Pococi", "Banda Cospnli de for NPA Pococi", 100),
        ("Limón", "Siquirres", "Banda Escuela for Siqui de Siquirres", 50),

        # Puntarenas
        ("Puntarenas", "Cóbano", "Banda Escuela for CMD C de Cóbano", 75),
        ("Puntarenas", "Coto Brus", "Banda Municipal de Coto Brus", 75),
        ("Puntarenas", "Coto Brus", "Colideportivo de Brus", 50),
        ("Puntarenas", "Puntarenas", "Banda de Puntarenas Barranca", 150),
        ("Puntarenas", "Quepos", "Banda Escuela for Munic de Quepos", 120),

        # San José
        ("San José", "Acosta", "Banda Escuela Instrumen de Acosta", 50),
        ("San José", "Aserrí", "Banda Escuela for Aserr de Aserri", 50),
        ("San José", "Desamparados", "Banda Municipal de Desamparados", 195),
        ("San José", "Desamparados", "Banda Municipal de Desamparados", 0),
        ("San José", "Desamparados", "Banda Escuela de Desamparados", 75),
        ("San José", "Dota", "Banda Escuela for Dota", 100),
        ("San José", "Montes de Oca", "Banda Estudiantil Liceo Anastasio Alfaro", 100),
        ("San José", "Montes de Oca", "Banda Estudiantil Liceo Anastasio Alfaro", 0),
        ("San José", "Puriscal", "Banda Municipal de Puriscal", 130),
        ("San José", "San José", "Banda Municipal de San José", 200),
        ("San José", "Goicoechea", "Banda de Marcha de Heredia", 50),
        ("San José", "Santa Ana", "Banda Cantonal Municipal de Santa Ana", 115),
        ("San José", "Santa Ana", "EMAI", 100),
        ("San José", "Tarrazú", "Banda Escuela Municipal de Tarrazu", 30),
        ("San José", "Turrubares", "Banda Escuela Municipal de Turrubares", 25),
    ]

    def build_bandas_df() -> pd.DataFrame:
        rows = []
        for prov, canton, banda, ben in BANDAS_RAW:
            prov_n = normalize_prov_generic(prov)
            canton_n = normalize_canton_generic(canton)

            lat = CANTON_COORDS.get(canton_n, (None, None))[0]
            lon = CANTON_COORDS.get(canton_n, (None, None))[1]

            rows.append({
                "provincia": prov_n,
                "canton": canton_n,
                "banda": clean_txt(banda),
                "beneficiarios": ben,
                "lat": lat,
                "lon": lon
            })
        df = pd.DataFrame(rows)
        df["beneficiarios_num"] = pd.to_numeric(df["beneficiarios"], errors="coerce")
        return df

    bandas = build_bandas_df()

    st.markdown("<div class='title'>Bandas / Beneficiarios</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI, puntos por cantón y total de beneficiarios por provincia.</div>", unsafe_allow_html=True)

    # =========================
    # FILTROS (TAB 2) — SEPARADOS
    # =========================
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Filtros (Bandas)")

    bcol1, bcol2, bcol3 = st.columns([1, 1, 1], gap="medium")

    prov_b = sorted(bandas["provincia"].dropna().unique().tolist(), key=lambda x: PROV_RANK.get(x, 999))
    cant_b = sorted(bandas["canton"].dropna().unique().tolist())
    banda_b = sorted(bandas["banda"].dropna().unique().tolist())

    with bcol1:
        prov_sel_b = st.multiselect("Provincia (Bandas)", prov_b, default=[], key="tab2_prov")
    with bcol2:
        cant_sel_b = st.multiselect("Cantón (Bandas)", cant_b, default=[], key="tab2_cant")
    with bcol3:
        banda_sel_b = st.multiselect("Banda/Club", banda_b, default=[], key="tab2_banda")

    st.markdown("</div>", unsafe_allow_html=True)

    fb = bandas.copy()
    if prov_sel_b:
        fb = fb[fb["provincia"].isin(prov_sel_b)]
    if cant_sel_b:
        fb = fb[fb["canton"].isin(cant_sel_b)]
    if banda_sel_b:
        fb = fb[fb["banda"].isin(banda_sel_b)]

    cantones_b = fb["canton"].nunique()
    bandas_unicas_b = fb["banda"].nunique()
    total_benef = float(fb["beneficiarios_num"].sum(skipna=True))

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-cantones">
            <div class="kpi-label">Cantones (Bandas)</div>
            <div class="kpi-value">{cantones_b:,}</div>
            <div class="kpi-sub">Total según filtros</div>
          </div>
          <div class="kpi kpi-estructuras">
            <div class="kpi-label">Beneficiarios</div>
            <div class="kpi-value">{int(total_benef):,}</div>
            <div class="kpi-sub">Suma (solo valores con número)</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    def render_map_bandas(df_filtered: pd.DataFrame, height_px: int):
        fm = df_filtered.dropna(subset=["lat", "lon"]).copy()
        if fm.empty:
            st.warning("No hay puntos con coordenadas para mostrar.")
            return

        grp = (
            fm.groupby(["provincia", "canton", "lat", "lon"])
            .agg(
                beneficiarios=("beneficiarios_num", lambda s: float(pd.to_numeric(s, errors="coerce").sum(skipna=True))),
                bandas=("banda", lambda s: sorted(set([clean_txt(x) for x in s if clean_txt(x)])))
            )
            .reset_index()
        )

        center_lat = float(grp["lat"].mean())
        center_lon = float(grp["lon"].mean())

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

        for _, r in grp.iterrows():
            provincia = r["provincia"]
            canton = r["canton"]
            beneficiarios = int(r["beneficiarios"]) if pd.notna(r["beneficiarios"]) else 0
            bandas_list = r["bandas"]

            colors = PROV_COLORS.get(provincia, {"stroke": "#111827", "fill": "#9ca3af"})

            html = f"""
            <div style="font-family: Arial; font-size: 13px; line-height: 1.25;">
              <div style="font-size: 14px;"><b>{canton}</b></div>
              <div><b>Provincia:</b> {provincia}</div>
              <div><b>Beneficiarios:</b> {beneficiarios:,}</div>
              <div><b>Bandas/Clubes:</b> {len(bandas_list)}</div>
              <div style="margin-top:6px;"><b>Listado:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{b}</li>' for b in bandas_list])}
              </ul>
            </div>
            """
            popup = folium.Popup(html, max_width=440)
            tooltip = f"{canton} ({provincia}) | {beneficiarios:,} beneficiarios"

            radius = 7 + min(18, (beneficiarios / 25) if beneficiarios else 6)

            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=radius,
                weight=2,
                color=colors["stroke"],
                fill=True,
                fill_color=colors["fill"],
                fill_opacity=0.60,
                tooltip=tooltip,
                popup=popup
            ).add_to(m)

        st.markdown("<div class='mapwrap'>", unsafe_allow_html=True)
        st_folium(m, use_container_width=True, height=height_px)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state["map_fullscreen_bandas"]:
        st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
        if st.button("⬅️ Salir de pantalla completa (Bandas)", key="tab2_exit_full"):
            st.session_state["map_fullscreen_bandas"] = False
            st.rerun()
        st.markdown("<span class='caption'>Modo pantalla completa: el mapa ocupa casi toda la pantalla.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_map_bandas(fb, height_px=920)
        st.stop()

    left2, right2 = st.columns([1.05, 0.95], gap="large")

    with left2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Beneficiarios por provincia")

        prov_sum = (
            fb.groupby("provincia")["beneficiarios_num"]
            .sum(min_count=1)
            .reset_index(name="beneficiarios")
        )
        prov_sum["beneficiarios"] = prov_sum["beneficiarios"].fillna(0)
        prov_sum["_rank"] = prov_sum["provincia"].map(lambda x: PROV_RANK.get(x, 999))
        prov_sum = prov_sum.sort_values(["_rank", "provincia"]).drop(columns=["_rank"])

        fig_prov = px.bar(prov_sum, x="provincia", y="beneficiarios")
        fig_prov.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_prov, use_container_width=True)

        st.subheader("Tabla unificada (provincia, cantón, beneficiarios)")

        tabla_bandas = (
            fb.groupby(["provincia", "canton"])
            .agg(
                beneficiarios=("beneficiarios_num", lambda s: float(pd.to_numeric(s, errors="coerce").sum(skipna=True))),
                bandas=("banda", lambda s: ", ".join(sorted(set([clean_txt(x) for x in s if clean_txt(x)]))))
            )
            .reset_index()
        )
        tabla_bandas["beneficiarios"] = tabla_bandas["beneficiarios"].fillna(0).astype(int)

        # ✅ ORDEN DE PROVINCIAS (NUEVO)
        tabla_bandas["_rank"] = tabla_bandas["provincia"].map(lambda x: PROV_RANK.get(x, 999))
        tabla_bandas = tabla_bandas.sort_values(["_rank", "provincia", "canton"]).drop(columns=["_rank"])

        st.dataframe(
            tabla_bandas[["provincia", "canton", "beneficiarios", "bandas"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — Bandas por cantón")

        st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
        if st.button("⛶ Ver mapa en pantalla completa (Bandas)", key="tab2_full_btn"):
            st.session_state["map_fullscreen_bandas"] = True
            st.rerun()
        st.markdown("<span class='caption'>Al tocar un punto: cantón + beneficiarios + listado de bandas.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_map_bandas(fb, height_px=820)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    csv_bandas = fb.copy()
    csv_bandas.drop(columns=["beneficiarios_num"], inplace=True, errors="ignore")
    csv_bytes_b = csv_bandas.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Descargar datos filtrados (Bandas) (CSV)",
        data=csv_bytes_b,
        file_name="bandas_beneficiarios_filtrado.csv",
        mime="text/csv",
        key="tab2_csv"
    )

    st.markdown(
        f"<div class='caption'>Resumen: <b>{bandas_unicas_b}</b> bandas/clubes en <b>{cantones_b}</b> cantones. Beneficiarios (sumados): <b>{int(total_benef):,}</b>.</div>",
        unsafe_allow_html=True
    )

# =============================================================================
# ============================== TAB 3 (CPC) ===================================
# =============================================================================
with tab_cpc:

    # =========================
    # DATOS CPC (EN CÓDIGO) — SIN PROVINCIA (SE ASIGNA)
    # =========================
    CPC_RAW = [
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
        (75, "Montes de Oca", "Community Prevention Center /Circo Social de Sinaí"),
        (60, "Mora", "Casa de la Juventud/Club House"),
        (45, "Osa/ Bahia Ballena", "Centro Preventivo Comunitario"),
        (20, "Pococi/ la Sole", "ADI Sole, DINADECO, UNICEF, PANI, INL"),
        (100, "Puntarenas/ Barranca", "Centro Preventivo Comunitario ONG Barranca Sport Club"),
        (15, "Puntarenas/ Chacarita", "Safe Space"),
        (50, "Puntarenas/ Fray Casiano", "Safe Space"),
        (20, "Quepos /Pies Mojados", "Safe Space"),
        (70, "San Carlos", "Civic Center of Peace"),
        (40, "San José/ Pavas", "Safe Space"),
        (30, "San José / Hatillo", "Safe Space"),
        (150, "San José / Carpio", "Safe Space"),

        (25, "San Ramón", "Safe Space"),
        (100, "Santa Ana", "Casita de Escucha Corazón de Jesús"),
        (100, "Santa Ana", "Casita de Escucha El Triunfo"),
        (40, "Sarapiquí / llanuras de Gaspal", "Safe Space"),
        (40, "Sarapiquí / puerto Viejo", "Safe Space"),
        (15, "Siquirres/ 3 Cercas", "Safe Space"),
        (25, "Turrialba", "Community Prevention Center"),
        (52, "Turrubares", "Safe Space"),
        (20, "Upala/ Mexico", "Safe Space"),
        (30, "Upala/ La Real", "Safe Space"),
    ]

    def build_cpc_df() -> pd.DataFrame:
        rows = []
        for ben, canton_raw, centro in CPC_RAW:
            base = split_canton_base(canton_raw)
            canton_base = normalize_canton_generic(base)

            prov = CANTON_TO_PROV.get(canton_base, "")
            prov = normalize_prov_generic(prov) if prov else ""

            # si no se pudo inferir, lo dejamos en blanco (pero casi todos están en el mapeo)
            if not prov:
                prov = "Sin provincia"

            lat = CANTON_COORDS.get(canton_base, (None, None))[0]
            lon = CANTON_COORDS.get(canton_base, (None, None))[1]

            rows.append({
                "provincia": prov,
                "canton": canton_base,
                "canton_detalle": clean_txt(canton_raw),
                "centro": clean_txt(centro),
                "beneficiarios": ben,
                "lat": lat,
                "lon": lon
            })

        df = pd.DataFrame(rows)
        df["beneficiarios_num"] = pd.to_numeric(df["beneficiarios"], errors="coerce")
        return df

    cpc = build_cpc_df()

    st.markdown("<div class='title'>Centros Preventivos Comunitarios</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mapa satelital ESRI, puntos por cantón y total de beneficiarios por provincia.</div>", unsafe_allow_html=True)

    # =========================
    # FILTROS (TAB 3) — SEPARADOS (provincia, canton, centro)
    # =========================
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Filtros (CPC)")

    ccol1, ccol2, ccol3 = st.columns([1, 1, 1], gap="medium")

    prov_c = sorted(cpc["provincia"].dropna().unique().tolist(), key=lambda x: PROV_RANK.get(x, 999) if x in PROV_RANK else 999)
    cant_c = sorted(cpc["canton"].dropna().unique().tolist())
    centro_c = sorted(cpc["centro"].dropna().unique().tolist())

    with ccol1:
        prov_sel_c = st.multiselect("Provincia (CPC)", prov_c, default=[], key="tab3_prov")
    with ccol2:
        cant_sel_c = st.multiselect("Cantón (CPC)", cant_c, default=[], key="tab3_cant")
    with ccol3:
        centro_sel_c = st.multiselect("Centro (CPC)", centro_c, default=[], key="tab3_centro")

    st.markdown("</div>", unsafe_allow_html=True)

    fc = cpc.copy()
    if prov_sel_c:
        fc = fc[fc["provincia"].isin(prov_sel_c)]
    if cant_sel_c:
        fc = fc[fc["canton"].isin(cant_sel_c)]
    if centro_sel_c:
        fc = fc[fc["centro"].isin(centro_sel_c)]

    cantones_c = fc["canton"].nunique()
    centros_unicos_c = fc["centro"].nunique()
    total_benef_c = float(fc["beneficiarios_num"].sum(skipna=True))

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi kpi-cantones">
            <div class="kpi-label">Cantones (CPC)</div>
            <div class="kpi-value">{cantones_c:,}</div>
            <div class="kpi-sub">Total según filtros</div>
          </div>
          <div class="kpi kpi-estructuras">
            <div class="kpi-label">Beneficiarios</div>
            <div class="kpi-value">{int(total_benef_c):,}</div>
            <div class="kpi-sub">Suma total</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    def render_map_cpc(df_filtered: pd.DataFrame, height_px: int):
        fm = df_filtered.dropna(subset=["lat", "lon"]).copy()
        if fm.empty:
            st.warning("No hay puntos con coordenadas para mostrar.")
            return

        grp = (
            fm.groupby(["provincia", "canton", "lat", "lon"])
            .agg(
                beneficiarios=("beneficiarios_num", lambda s: float(pd.to_numeric(s, errors="coerce").sum(skipna=True))),
                centros=("centro", lambda s: sorted(set([clean_txt(x) for x in s if clean_txt(x)])))
            )
            .reset_index()
        )

        center_lat = float(grp["lat"].mean())
        center_lon = float(grp["lon"].mean())

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

        for _, r in grp.iterrows():
            provincia = r["provincia"]
            canton = r["canton"]
            beneficiarios = int(r["beneficiarios"]) if pd.notna(r["beneficiarios"]) else 0
            centros_list = r["centros"]

            colors = PROV_COLORS.get(provincia, {"stroke": "#111827", "fill": "#9ca3af"})

            html = f"""
            <div style="font-family: Arial; font-size: 13px; line-height: 1.25;">
              <div style="font-size: 14px;"><b>{canton}</b></div>
              <div><b>Provincia:</b> {provincia}</div>
              <div><b>Beneficiarios:</b> {beneficiarios:,}</div>
              <div><b>Centros:</b> {len(centros_list)}</div>
              <div style="margin-top:6px;"><b>Listado:</b></div>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{c}</li>' for c in centros_list])}
              </ul>
            </div>
            """
            popup = folium.Popup(html, max_width=460)
            tooltip = f"{canton} ({provincia}) | {beneficiarios:,} beneficiarios"

            radius = 7 + min(18, (beneficiarios / 25) if beneficiarios else 6)

            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=radius,
                weight=2,
                color=colors["stroke"],
                fill=True,
                fill_color=colors["fill"],
                fill_opacity=0.60,
                tooltip=tooltip,
                popup=popup
            ).add_to(m)

        st.markdown("<div class='mapwrap'>", unsafe_allow_html=True)
        st_folium(m, use_container_width=True, height=height_px)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state["map_fullscreen_cpc"]:
        st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
        if st.button("⬅️ Salir de pantalla completa (CPC)", key="tab3_exit_full"):
            st.session_state["map_fullscreen_cpc"] = False
            st.rerun()
        st.markdown("<span class='caption'>Modo pantalla completa: el mapa ocupa casi toda la pantalla.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_map_cpc(fc, height_px=920)
        st.stop()

    left3, right3 = st.columns([1.05, 0.95], gap="large")

    with left3:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Beneficiarios por provincia")

        prov_sum_c = (
            fc.groupby("provincia")["beneficiarios_num"]
            .sum(min_count=1)
            .reset_index(name="beneficiarios")
        )
        prov_sum_c["beneficiarios"] = prov_sum_c["beneficiarios"].fillna(0)
        prov_sum_c["_rank"] = prov_sum_c["provincia"].map(lambda x: PROV_RANK.get(x, 999))
        prov_sum_c = prov_sum_c.sort_values(["_rank", "provincia"]).drop(columns=["_rank"])

        fig_c = px.bar(prov_sum_c, x="provincia", y="beneficiarios")
        fig_c.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_c, use_container_width=True)

        st.subheader("Tabla unificada (provincia, cantón, beneficiarios, centros)")

        tabla_cpc = (
            fc.groupby(["provincia", "canton"])
            .agg(
                beneficiarios=("beneficiarios_num", lambda s: float(pd.to_numeric(s, errors="coerce").sum(skipna=True))),
                centros=("centro", lambda s: ", ".join(sorted(set([clean_txt(x) for x in s if clean_txt(x)]))))
            )
            .reset_index()
        )
        tabla_cpc["beneficiarios"] = tabla_cpc["beneficiarios"].fillna(0).astype(int)

        # ✅ ORDEN DE PROVINCIAS (NUEVO)
        tabla_cpc["_rank"] = tabla_cpc["provincia"].map(lambda x: PROV_RANK.get(x, 999))
        tabla_cpc = tabla_cpc.sort_values(["_rank", "provincia", "canton"]).drop(columns=["_rank"])

        st.dataframe(
            tabla_cpc[["provincia", "canton", "beneficiarios", "centros"]],
            use_container_width=True,
            height=360,
            hide_index=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right3:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Mapa satelital (ESRI) — CPC por cantón")

        st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
        if st.button("⛶ Ver mapa en pantalla completa (CPC)", key="tab3_full_btn"):
            st.session_state["map_fullscreen_cpc"] = True
            st.rerun()
        st.markdown("<span class='caption'>Al tocar un punto: cantón + beneficiarios + listado de centros.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_map_cpc(fc, height_px=820)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    csv_cpc = fc.copy()
    csv_cpc.drop(columns=["beneficiarios_num"], inplace=True, errors="ignore")
    csv_bytes_c = csv_cpc.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Descargar datos filtrados (CPC) (CSV)",
        data=csv_bytes_c,
        file_name="cpc_beneficiarios_filtrado.csv",
        mime="text/csv",
        key="tab3_csv"
    )

    st.markdown(
        f"<div class='caption'>Resumen: <b>{centros_unicos_c}</b> centros en <b>{cantones_c}</b> cantones. Beneficiarios (sumados): <b>{int(total_benef_c):,}</b>.</div>",
        unsafe_allow_html=True
    )

