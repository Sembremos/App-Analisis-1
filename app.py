# app.py
# streamlit run app.py

import re
import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="Costa Rica | Cantones y Estructuras",
    page_icon="🛰️",
    layout="wide"
)

# ======================================================
# ESTILOS (PROFESIONAL / LIMPIO)
# ======================================================
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.title {font-size:28px;font-weight:900;letter-spacing:-0.02em;}
.subtitle {color:#6b7280;margin-bottom:16px;}
.kpi-grid{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px;}
.kpi{
  background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;
  padding:16px 18px;box-shadow:0 10px 25px rgba(0,0,0,0.06);
  min-width:240px;flex:1;
}
.kpi-label{font-weight:800;font-size:14px;color:#111827;}
.kpi-value{font-size:44px;font-weight:900;color:#111827;line-height:1;}
.kpi-sub{font-size:12px;color:#6b7280;}
.panel{
  background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;
  padding:14px 16px;box-shadow:0 10px 25px rgba(0,0,0,0.05);
}
hr{border:none;border-top:1px solid #e5e7eb;margin:16px 0;}
.caption{font-size:12px;color:#6b7280;}
.mapwrap{border-radius:18px;overflow:hidden;}
.btnrow{display:flex;gap:10px;align-items:center;margin:6px 0;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# SESSION STATE
# ======================================================
if "map_fullscreen" not in st.session_state:
    st.session_state.map_fullscreen = False

# ======================================================
# DATOS (PANTALLAZO – SAN JOSÉ)
# ======================================================
RAW_WIDE = [
    ("San Jose", ["Los Lara (San Sebastia)", "Los coqueros (Pavas)", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "Los Picudos (Carpio)", "Los Diablos (Pavas)", "Los Polacos (Pavas)"]),
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
]

CANTON_COORDS = {
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
}

# ======================================================
# NORMALIZACIÓN
# ======================================================
rows = []
for canton, structs in RAW_WIDE:
    for e in structs:
        if e:
            rows.append({
                "canton": canton,
                "estructura": e,
                "lat": CANTON_COORDS[canton][0],
                "lon": CANTON_COORDS[canton][1]
            })

df = pd.DataFrame(rows)

# ======================================================
# FILTROS
# ======================================================
with st.sidebar:
    st.header("Filtros")
    cant_sel = st.multiselect("Cantón", sorted(df.canton.unique()))
    estr_sel = st.multiselect("Estructura", sorted(df.estructura.unique()))

f = df.copy()
if cant_sel:
    f = f[f.canton.isin(cant_sel)]
if estr_sel:
    f = f[f.estructura.isin(estr_sel)]

# ======================================================
# KPIs (A PRUEBA DE ERRORES)
# ======================================================
cantones_unicos = f.canton.nunique()
estructuras_unicas = f.estructura.nunique()
estructuras_unicos = estructuras_unicas  # alias defensivo

st.markdown("""
<div class="title">Cantones y estructuras</div>
<div class="subtitle">Mapa satelital ESRI con detalle por cantón</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">Cantones</div>
    <div class="kpi-value">{cantones_unicos}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Estructuras</div>
    <div class="kpi-value">{estructuras_unicas}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ======================================================
# MAPA
# ======================================================
def render_map(data, height):
    grp = data.groupby(["canton", "lat", "lon"]).agg(
        estructuras=("estructura", lambda x: sorted(set(x)))
    ).reset_index()

    m = folium.Map(
        location=[grp.lat.mean(), grp.lon.mean()],
        zoom_start=8,
        tiles=None
    )

    folium.TileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="ESRI",
        name="Satélite"
    ).add_to(m)

    folium.TileLayer(
        "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="ESRI",
        overlay=True
    ).add_to(m)

    for _, r in grp.iterrows():
        html = f"<b>{r.canton}</b><ul>" + "".join([f"<li>{e}</li>" for e in r.estructuras]) + "</ul>"
        folium.CircleMarker(
            [r.lat, r.lon],
            radius=10,
            color="#6d28d9",
            fill=True,
            fill_opacity=0.6,
            popup=html
        ).add_to(m)

    st_folium(m, use_container_width=True, height=height)

# ======================================================
# FULLSCREEN
# ======================================================
if st.session_state.map_fullscreen:
    if st.button("⬅️ Salir de pantalla completa"):
        st.session_state.map_fullscreen = False
        st.rerun()
    render_map(f, 920)
    st.stop()

# ======================================================
# LAYOUT NORMAL
# ======================================================
col1, col2 = st.columns([1, 1.2])

with col1:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Tabla")
    st.dataframe(f[["canton", "estructura"]], use_container_width=True, height=380)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    if st.button("⛶ Ver mapa en pantalla completa"):
        st.session_state.map_fullscreen = True
        st.rerun()
    render_map(f, 720)
    st.markdown("</div>", unsafe_allow_html=True)
