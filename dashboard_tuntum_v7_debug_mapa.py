import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import numpy as np
import re

st.set_page_config(page_title="Dashboard Tuntum V7 - Debug do Mapa", layout="wide")

def canon_text(s):
    s = "" if pd.isna(s) else str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("-", " ")
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    aliases = {
        "IPUIRU": "IPU IRU",
        "BELEM": "BELEM",
        "BELÉM": "BELEM",
        "MIL REIS": "MIL REIS",
        "VILA LUIZAO": "VILA LUIZAO",
        "NOVO MARAJA": "NOVO MARAJA",
        "BREJO DO JOAO": "BREJO DO JOAO",
        "SAO LOURENCO": "SAO LOURENCO",
        "SAO BENTO": "SAO BENTO",
        "SAO JOAQUIM DOS MELOS": "SAO JOAQUIM DOS MELOS",
    }
    return aliases.get(s, s)

def sec_key(s):
    s = str(s).upper().replace("SEÇÃO", "").replace("SECAO", "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

base = Path(__file__).resolve().parent

atlas_candidates = [
    "atlas_territorial_tuntum_base_atualizado.csv",
    "atlas_territorial_tuntum_base.csv",
]

atlas_file = None
for f in atlas_candidates:
    if (base / f).exists():
        atlas_file = f
        break

req = ["SEÇÕES.csv", "VOTACAO_PREFEITO.csv", "tuntum_malha.geojson"]
faltando = [f for f in req if not (base / f).exists()]
if faltando:
    st.error("Arquivos faltando: " + ", ".join(faltando))
    st.stop()

if atlas_file is None:
    st.error("Nenhum atlas encontrado. Coloque na pasta um destes arquivos: " + ", ".join(atlas_candidates))
    st.stop()

secoes = pd.read_csv(base / "SEÇÕES.csv", encoding="latin1", sep=";")
prefeito = pd.read_csv(base / "VOTACAO_PREFEITO.csv", encoding="latin1", sep=";")
geo = gpd.read_file(base / "tuntum_malha.geojson")
atlas = pd.read_csv(base / atlas_file)

secoes.columns = [c.strip() for c in secoes.columns]
prefeito.columns = [c.strip() for c in prefeito.columns]
atlas.columns = [c.strip() for c in atlas.columns]

for col in ["lat", "lon"]:
    if col in atlas.columns:
        atlas[col] = (
            atlas[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("--", "-", regex=False)
            .str.strip()
        )
        atlas[col] = pd.to_numeric(atlas[col], errors="coerce")

atlas["territ_key"] = atlas["localidade"].map(canon_text)

secoes["sec_key"] = secoes["SEÇÃO"].map(sec_key)
prefeito["sec_key"] = prefeito["SEÇÃO"].map(sec_key)

df = secoes.merge(
    prefeito[["sec_key", "FERNANDO", "TEMA"]],
    on="sec_key",
    how="left"
)

for c in ["Eleitores aptos", "Comparecimento", "FERNANDO", "TEMA"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["abstencao"] = df["Eleitores aptos"] - df["Comparecimento"]
df["territ_key"] = df["BAIRRO"].map(canon_text)

territ = (
    df.groupby("territ_key", dropna=False)
      .agg(
          territorio=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
          local_principal=("LOCAL DE VOTAÇÃO", lambda x: sorted(set(map(str, x)))[0]),
          eleitores=("Eleitores aptos", "sum"),
          comparecimento=("Comparecimento", "sum"),
          abstencao=("abstencao", "sum"),
      ).reset_index()
)

base_mapa = atlas.merge(territ, on="territ_key", how="left")

if geo.crs is not None and str(geo.crs) != "EPSG:4326":
    geo = geo.to_crs(epsg=4326)

centroide = geo.geometry.union_all().centroid
center_lat = centroide.y
center_lon = centroide.x

st.title("Dashboard Tuntum V7 - Debug do Mapa")
st.caption(f"Atlas em uso: {atlas_file}")

a, b, c, d = st.columns(4)
a.metric("Linhas no atlas", len(atlas))
b.metric("Com lat/lon válidos", int(atlas["lat"].notna().sum()))
c.metric("Atlas casado com base eleitoral", int(base_mapa["territorio"].notna().sum()))
d.metric("Pontos prontos para mapa", int(base_mapa.dropna(subset=["lat", "lon"]).shape[0]))

fig = go.Figure()

fig.add_trace(
    go.Choroplethmapbox(
        geojson=geo.__geo_interface__,
        locations=geo.index.astype(str),
        z=[1] * len(geo),
        featureidkey="id",
        colorscale=[[0, "rgba(90,160,210,0.16)"], [1, "rgba(90,160,210,0.16)"]],
        marker_line_color="rgb(30,90,160)",
        marker_line_width=2,
        showscale=False,
        hovertext=geo["NM_MUN"] if "NM_MUN" in geo.columns else ["Tuntum"] * len(geo),
        hoverinfo="text"
    )
)

pts = base_mapa.dropna(subset=["lat", "lon"]).copy()

if len(pts) > 0:
    fig.add_trace(
        go.Scattermapbox(
            lat=pts["lat"],
            lon=pts["lon"],
            mode="markers+text",
            text=pts["localidade"],
            textposition="top right",
            marker=dict(size=11, color="red"),
            customdata=pts[["territorio", "local_principal", "status_validacao"]].fillna("").values,
            hovertemplate="<b>%{text}</b><br>Base eleitoral: %{customdata[0]}<br>Local principal: %{customdata[1]}<br>Status: %{customdata[2]}<extra></extra>"
        )
    )

fig.update_layout(
    mapbox=dict(style="carto-positron", center=dict(lat=center_lat, lon=center_lon), zoom=9.6),
    margin=dict(l=0, r=0, t=40, b=0),
    title="Mapa de Tuntum com pontos do atlas"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Prévia do atlas carregado")
st.dataframe(atlas[["localidade", "lat", "lon", "status_validacao"]], use_container_width=True)

st.subheader("Pontos que serão plotados")
st.dataframe(pts[["localidade", "lat", "lon", "territorio", "local_principal"]], use_container_width=True)

st.subheader("Localidades do atlas sem coordenadas válidas")
st.dataframe(atlas[atlas["lat"].isna() | atlas["lon"].isna()][["localidade", "lat", "lon", "status_validacao"]], use_container_width=True)