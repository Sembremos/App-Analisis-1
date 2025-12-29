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
# ESTILO (IGUAL)
# =========================
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.0rem; padding-bottom: 2rem;}
      .title{font-size: 28px; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 2px;}
      .subtitle{color:#6b7280; margin-top:0px; margin-bottom: 14px;}
      .kpi-grid{display:flex; gap:14px; flex-wrap:wrap; margin-bottom: 10px;}
      .kpi{
        background:#ffffff; border:1px solid #e5e7eb; border-radius:18px;
        padding:16px 18px; box-shadow:0 10px 25px rgba(0,0,0,0.06);
        min-width: 240px; flex:1;
      }
      .kpi-label{color:#111827; font-weight:800; font-size:14px; letter-spacing:0.01em;}
      .kpi-value{color:#111827; font-weight:900; font-size:44px; margin-top:6px; line-height:1;}
      .kpi-sub{color:#6b7280; font-size:12px; margin-top:6px;}
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
# SESSION STATE (IGUAL)
# =========================
if "map_fullscreen" not in st.session_state:
    st.session_state["map_fullscreen"] = False

# =========================
# COLORES POR PROVINCIA (NUEVO, SOLO PARA MARCAS)
# =========================
PROV_COLORS = {
    "San Jose": {"stroke": "#6d28d9", "fill": "#8b5cf6"},   # morado
    "Alajuela": {"stroke": "#0f766e", "fill": "#14b8a6"},   # teal
    "Cartago":  {"stroke": "#b45309", "fill": "#f59e0b"},   # naranja
    "Heredia":  {"stroke": "#1d4ed8", "fill": "#60a5fa"},   # azul
}

# =========================
# DATOS (MATRIZ ANCHA) — NO RESUMIDO
# =========================
# NOTA: Cada fila trae 10 "celdas" de estructuras (e1..e10) como tu Excel.
RAW_BY_PROV = {
    # -----------------------
    # SAN JOSE (tu prueba 1)
    # -----------------------
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

    # -----------------------
    # ALAJUELA (según pantallazo visible)
    # -----------------------
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

    # -----------------------
    # CARTAGO (según pantallazo visible)
    # -----------------------
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

    # -----------------------
    # HEREDIA (según pantallazo visible)
    # -----------------------
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
}

# =========================
# HELPERS (IGUAL)
# =========================
def clean_txt(x: str) -> str:
    if pd.isna(x):
        return ""
    x = str(x).strip()
    x = re.sub(r"\s+", " ", x)
    return x

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
# HEADER (IGUAL)
# =========================
st.markdown("<div class='title'>Cantones y estructuras (Prueba 1)</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Mapa satelital ESRI, puntos por cantón y detalle de estructuras por ubicación.</div>", unsafe_allow_html=True)

# =========================
# FILTROS (NUEVO provincia + los mismos)
# =========================
with st.sidebar:
    st.header("Filtros")

    provincias = sorted(long["provincia"].unique().tolist())
    prov_sel = st.multiselect("Provincia", provincias, default=[])

    cantones = sorted(long["canton"].unique().tolist())
    estructuras = sorted(long["estructura"].unique().tolist())

    cant_sel = st.multiselect("Cantón", cantones, default=[])
    estr_sel = st.multiselect("Estructura", estructuras, default=[])

f = long.copy()
if prov_sel:
    f = f[f["provincia"].isin(prov_sel)]
if cant_sel:
    f = f[f["canton"].isin(cant_sel)]
if estr_sel:
    f = f[f["estructura"].isin(estr_sel)]

cantones_unicos = f["canton"].nunique()
estructuras_unicas = f["estructura"].nunique()
estructuras_unicos = estructuras_unicas  # alias defensivo

# =========================
# KPI (IGUAL)
# =========================
st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi">
        <div class="kpi-label">Cantones</div>
        <div class="kpi-value">{cantones_unicos:,}</div>
        <div class="kpi-sub">Total según filtros</div>
      </div>
      <div class="kpi">
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
# MAP BUILDER (IGUAL + color por provincia)
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
    if st.button("⬅️ Salir de pantalla completa"):
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
        .head(15)
    )
    fig_bar = px.bar(top_struct, x="conteo", y="estructura", orientation="h")
    fig_bar.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Tabla normalizada")
    # ✅ solo canton + estructura (como pediste)
    st.dataframe(
        f[["canton", "estructura"]].sort_values(["canton", "estructura"]),
        use_container_width=True,
        height=360
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Mapa satelital (ESRI) — puntos por cantón")

    st.markdown("<div class='btnrow'>", unsafe_allow_html=True)
    if st.button("⛶ Ver mapa en pantalla completa"):
        st.session_state["map_fullscreen"] = True
        st.rerun()
    st.markdown("<span class='caption'>Abre el mapa ocupando casi toda la pantalla.</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    render_map(f, height_px=820)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# =========================
# DESCARGA + RESUMEN (SIN INDENTACIÓN RARA)
# =========================
csv_bytes = f.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar datos filtrados (CSV)",
    data=csv_bytes,
    file_name="cantones_estructuras_normalizado.csv",
    mime="text/csv"
)

st.markdown(
    f"<div class='caption'>Resumen: <b>{estructuras_unicas}</b> estructuras únicas en <b>{cantones_unicos}</b> cantones (según filtros).</div>",
    unsafe_allow_html=True
)

