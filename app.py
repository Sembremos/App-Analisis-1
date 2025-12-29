# app.py
# Ejecuta: streamlit run app.py

import re
import pandas as pd
import streamlit as st
import plotly.express as px
import pydeck as pdk

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="CR | Estructuras por cantón", page_icon="🗺️", layout="wide")

# =========================
# ESTILO (look limpio tipo infografía)
# =========================
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
      .title{font-size: 28px; font-weight: 900; letter-spacing: -0.02em;}
      .subtitle{color:#6b7280; margin-top:-6px;}
      .kpi-card{
        background:#fff; border:1px solid #eee; border-radius:18px;
        padding:14px 16px; box-shadow:0 6px 18px rgba(0,0,0,0.04);
      }
      .muted{color:#6b7280; font-size:12px;}
      .pill{
        display:inline-block; padding:4px 10px; border-radius:999px;
        background:rgba(139,92,246,0.12); color:#6d28d9; font-weight:800; font-size:12px;
        margin-left:8px;
      }
      hr {border:none; border-top:1px solid #eee; margin: 16px 0;}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# DATOS (CARGADOS DEL PANTALLAZO)
# Provincia: SAN JOSE
# Fuente: La Extra
# =========================
RAW_WIDE = [
    # canton, col1..col10 (estructuras)
    ("San Jose", [
        "Los Lara (San Sebastia)", "Los coqueros (Pavas)", "Los Moreco", "Turesky", "Pollo",
        "Indio", "Ojos Bellos", "Los Picudos (Carpio)", "Los Diablos (Pavas)", "Los Polacos (Pavas)"
    ]),
    ("Escazu", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Desamparados", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Puriscal", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Tarrazu", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Aserri", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Mora", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Goicoechea", [
        "Los Lara", "Mongo", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Santa Ana", [
        "Los Lara", "La H", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Alajuelita", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Vasquez de Coronado", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Acosta", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Tibas", [
        "Los Lara", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Moravia", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Montes de Oca", [
        "Los Lara", "Cartel de Sinaloa", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Turrubares", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Dota", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Curridabat", [
        "GaryGery", "Churro y Tauro", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Perez Zeledon", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
    ("Leon Cortes", [
        "", "", "Los Moreco", "Turesky", "Pollo", "Indio", "Ojos Bellos", "", "", ""
    ]),
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

def build_wide_df():
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
# UI HEADER
# =========================
st.markdown(f'<div class="title">Panel CR — Estructuras por cantón <span class="pill">Prueba 1</span></div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Datos cargados desde el pantallazo (Provincia SAN JOSÉ) + mapa + gráficas.</div>', unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

# =========================
# FILTERS
# =========================
with st.sidebar:
    st.header("Filtros")
    provs = sorted(long["provincia"].unique().tolist())
    cants = sorted(long["canton"].unique().tolist())
    estrs = sorted(long["estructura"].unique().tolist())

    prov_sel = st.multiselect("Provincia", provs, default=provs)
    cant_sel = st.multiselect("Cantón", cants, default=[])
    estr_sel = st.multiselect("Estructura", estrs, default=[])

f = long.copy()
if prov_sel:
    f = f[f["provincia"].isin(prov_sel)]
if cant_sel:
    f = f[f["canton"].isin(cant_sel)]
if estr_sel:
    f = f[f["estructura"].isin(estr_sel)]

# =========================
# KPIs
# =========================
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Registros (cantón-estructura)", f"{len(f):,}")
    st.markdown('<div class="muted">Filas normalizadas</div></div>', unsafe_allow_html=True)

with k2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Cantones únicos", f"{f['canton'].nunique():,}")
    st.markdown('<div class="muted">Según filtros</div></div>', unsafe_allow_html=True)

with k3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Estructuras únicas", f"{f['estructura'].nunique():,}")
    st.markdown('<div class="muted">Sin deduplicación semántica</div></div>', unsafe_allow_html=True)

with k4:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    with_coords = f["lat"].notna().sum()
    st.metric("Georreferenciados", f"{with_coords:,}")
    st.markdown('<div class="muted">Con centroides cantonales</div></div>', unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# =========================
# CHARTS + MAP + TABLE
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

    st.subheader("Tabla normalizada (lo que usa la app)")
    st.dataframe(
        f[["provincia", "canton", "estructura", "fuente", "lat", "lon"]].sort_values(["canton", "estructura"]),
        use_container_width=True,
        height=360
    )

with right:
    st.subheader("Proporción por cantón (Top)")
    top_cant = (
        f.groupby("canton")
        .size()
        .reset_index(name="conteo")
        .sort_values("conteo", ascending=False)
        .head(12)
    )
    fig_donut = px.pie(top_cant, values="conteo", names="canton", hole=0.62)
    fig_donut.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_donut, use_container_width=True)

    st.subheader("Mapa (Costa Rica) — puntos por cantón")
    fm = f.dropna(subset=["lat", "lon"]).copy()

    # un punto por cantón con conteo
    fm_one = (
        fm.groupby(["canton", "lat", "lon"], as_index=False)
        .agg(conteo=("estructura", "count"))
        .sort_values("conteo", ascending=False)
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=fm_one,
        get_position=["lon", "lat"],
        get_radius="conteo * 160",
        pickable=True,
        auto_highlight=True,
    )

    view = pdk.ViewState(latitude=9.85, longitude=-84.10, zoom=8.2, pitch=0)
    tooltip = {"text": "Cantón: {canton}\nRegistros: {conteo}"}

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip), use_container_width=True)

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

st.caption("Prueba 1 lista: datos del pantallazo cargados en el código + normalización + gráficos + mapa.")








