# app.py
# Ejecuta: streamlit run app.py

import re
import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="CR | Estructuras por cantón", page_icon="🛰️", layout="wide")

# =========================
# ESTILO (KPI tipo infografía)
# =========================
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.0rem; padding-bottom: 2rem;}
      .title{font-size: 28px; font-weight: 900; letter-spacing: -0.02em;}
      .subtitle{color:#9ca3af; margin-top:-6px;}
      .kpi-row{display:flex; gap:14px; flex-wrap:wrap;}
      .kpi-card{
        background:#0b0f17; border:1px solid rgba(255,255,255,0.06); border-radius:18px;
        padding:14px 16px; box-shadow:0 10px 30px rgba(0,0,0,0.25);
        min-width: 220px; flex:1;
      }
      .kpi-label{color:#e5e7eb; font-weight:700; font-size:14px; opacity:0.95; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
      .kpi-value{color:#ffffff; font-weight:900; font-size:42px; margin-top:6px;}
      .kpi-sub{color:#9ca3af; font-size:12px; margin-top:2px;}
      hr {border:none; border-top:1px solid rgba(255,255,255,0.08); margin: 16px 0;}
      .panel{background:#0b0f17; border:1px solid rgba(255,255,255,0.06); border-radius:18px; padding:14px 16px;}
      .caption{color:#9ca3af; font-size:12px;}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# DATOS (CARGADOS DEL PANTALLAZO)
# Provincia: SAN JOSE | Fuente: La Extra
# =========================
RAW_WIDE = [
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
]

PROVINCIA = "SAN JOSE"
FUENTE = "La Extra"

# =========================
# COORDENADAS (centroides aprox. por cantón)
# =========================
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

# =========================
# HELPERS
# =========================
def clean_txt(x: str) -> str:
    if pd.isna(x):
        return ""
    x = str(x).strip()
    x = re.sub(r"\s+", " ", x)
    return x

def build_wide_df() -> pd.DataFrame:
    rows = []
    for canton, structs in RAW_WIDE:
        r = {"provincia": PROVINCIA, "canton": canton, "fuente": FUENTE}
        for i in range(10):
            r[f"e{i+1}"] = structs[i] if i < len(structs) else ""
        rows.append(r)
    return pd.DataFrame(rows)

def normalize_long(df_wide: pd.DataFrame) -> pd.DataFrame:
    struct_cols = [c for c in df_wide.columns if c.startswith("e")]
    long = df_wide.melt(
        id_vars=["provincia", "canton", "fuente"],
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
# BUILD DATA
# =========================
wide = build_wide_df()
long = add_coords(normalize_long(wide))

# =========================
# HEADER
# =========================
st.markdown(f'<div class="title">Panel CR — Estructuras por cantón <span class="pill">ESRI Satélite</span></div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Datos del pantallazo (Provincia SAN JOSÉ) + mapa satelital + gráficas + lista.</div>', unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

# =========================
# FILTROS
# =========================
with st.sidebar:
    st.header("Filtros")
    cantones = sorted(long["canton"].unique().tolist())
    estructuras = sorted(long["estructura"].unique().tolist())

    cant_sel = st.multiselect("Cantón", cantones, default=[])
    estr_sel = st.multiselect("Estructura", estructuras, default=[])

f = long.copy()
if cant_sel:
    f = f[f["canton"].isin(cant_sel)]
if estr_sel:
    f = f[f["estructura"].isin(estr_sel)]

# =========================
# RESPUESTA A TU PREGUNTA (conteos)
# =========================
cantones_unicos = f["canton"].nunique()
estructuras_unicas = f["estructura"].nunique()

# =========================
# KPIs (como tu captura)
# =========================
st.markdown(
    f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">Registros (cantón-estructura)</div>
        <div class="kpi-value">{len(f):,}</div>
        <div class="kpi-sub">Filas normalizadas</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Cantones únicos</div>
        <div class="kpi-value">{cantones_unicos:,}</div>
        <div class="kpi-sub">Según filtros</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Estructuras únicas</div>
        <div class="kpi-value">{estructuras_unicas:,}</div>
        <div class="kpi-sub">Sin deduplicación semántica</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Georreferenciados</div>
        <div class="kpi-value">{int(f["lat"].notna().sum()):,}</div>
        <div class="kpi-sub">Con centroides cantonales</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<hr/>", unsafe_allow_html=True)

# =========================
# VISUALS
# =========================
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("Top estructuras (conteos)")
    top_struct = (
        f.groupby("estructura")
        .size()
        .reset_index(name="conteo")
        .sort_values("conteo", ascending=False)
        .head(15)
    )
    fig_bar = px.bar(top_struct, x="conteo", y="estructura", orientation="h")
    fig_bar.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Tabla normalizada")
    st.dataframe(
        f[["provincia", "canton", "estructura", "fuente", "lat", "lon"]].sort_values(["canton", "estructura"]),
        use_container_width=True,
        height=360
    )

with right:
    st.subheader("Mapa satelital (ESRI) — marcadores con lista de estructuras")

    fm = f.dropna(subset=["lat", "lon"]).copy()

    if fm.empty:
        st.warning("No hay puntos con coordenadas para mostrar.")
    else:
        # Agrupar: cantón -> lista de estructuras (únicas)
        grp = (
            fm.groupby(["canton", "lat", "lon"])
            .agg(
                registros=("estructura", "count"),
                estructuras=("estructura", lambda s: sorted(set(s)))
            )
            .reset_index()
        )

        # Centro del mapa (promedio)
        center_lat = float(grp["lat"].mean())
        center_lon = float(grp["lon"].mean())

        # Mapa folium con ESRI World Imagery
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8, control_scale=True, tiles=None)

        # ESRI Satélite (World Imagery)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri, Maxar, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community",
            name="Esri World Imagery",
            overlay=False,
            control=True
        ).add_to(m)

        # Opcional: bordes/labels (para leer mejor)
        folium.TileLayer(
            tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="Límites y lugares",
            overlay=True,
            control=True,
            opacity=0.9
        ).add_to(m)

        folium.LayerControl(collapsed=True).add_to(m)

        # Marcadores con "nube" (popup) mostrando cantón + estructuras
        for _, r in grp.iterrows():
            canton = r["canton"]
            registros = int(r["registros"])
            estructuras_list = r["estructuras"]

            # Popup HTML (nube)
            html = f"""
            <div style="font-family: Arial; font-size: 13px;">
              <b>Cantón:</b> {canton}<br/>
              <b>Registros:</b> {registros}<br/>
              <b>Estructuras presentes:</b>
              <ul style="margin: 6px 0 0 18px; padding: 0;">
                {''.join([f'<li>{e}</li>' for e in estructuras_list])}
              </ul>
            </div>
            """

            popup = folium.Popup(html, max_width=360)

            # Tooltip breve (solo cantón)
            tooltip = f"{canton} | Registros: {registros}"

            # Tamaño del marcador según registros
            radius = 6 + min(18, registros * 1.2)

            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=radius,
                weight=2,
                color="#a78bfa",      # borde
                fill=True,
                fill_color="#7c3aed", # relleno
                fill_opacity=0.65,
                tooltip=tooltip,
                popup=popup
            ).add_to(m)

        st_folium(m, use_container_width=True, height=720)

st.markdown("<hr/>", unsafe_allow_html=True)

# =========================
# DESCARGA (opcional)
# =========================
csv_bytes = f.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar datos filtrados (CSV)",
    data=csv_bytes,
    file_name="estructuras_por_canton_normalizado.csv",
    mime="text/csv"
)

st.markdown(
    f"<div class='caption'>Resumen: <b>{estructuras_unicas}</b> estructuras únicas en <b>{cantones_unicos}</b> cantones (según filtros actuales).</div>",
    unsafe_allow_html=True
)








