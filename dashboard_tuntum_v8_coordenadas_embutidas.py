import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import numpy as np
import re

st.set_page_config(page_title="Tuntum - Mapa com Coordenadas Embutidas", layout="wide")

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

def score_norm(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)

# =========================
# COORDENADAS EMBUTIDAS
# =========================
coords = pd.DataFrame([
    ("CENTRO", -5.255784527155879, -44.65021946235093),
    ("MIL REIS", -5.2559198752907115, -44.641672690884654),
    ("VILA LUIZAO", -5.266581547978559, -44.64397428334195),
    ("ASTOLFO SEABRA", -5.273594307933202, -44.64101763053091),
    ("CAMPO VELHO", -5.254167532681394, -44.64570416910529),
    ("VILA BENTO", -5.283613321525536, -44.64185507502784),
    ("TUNTUM DE CIMA", -5.273745522846826, -44.63296501110159),
    ("NOVO MARAJA", -5.522638222192139, -44.85271922811691),
    ("BELEM", -5.758291958744166, -44.6181357973509),
    ("IPU IRU", -5.505905486189621, -44.86646062174089),
    ("SAO LOURENCO", -5.784898314502129, -44.82136028125027),
    ("SAO BENTO", -5.786759446845751, -44.71396464807228),
    ("SANTA ROSA", -5.991448681240779, -44.795677360152),
    ("SERRA GRANDE", -5.258806885478064, -44.783383973294484),
    ("CIGANA", -5.380241037390525, -44.78254052192323),
    ("ARROZ", -5.202527647851387, -44.62631296094674),
    ("ARARA", -5.321341136586182, -44.60145229926725),
    ("MATO VERDE", -5.598402217466002, -44.58942520209541),
    ("BREJO DO JOAO", -5.828978349908755, -44.72723197760513),
    ("JENIPAPO DOS GOMES", -5.6243421285678625, -44.91376255190616),
    ("SAO JOAQUIM DOS MELOS", -5.898484042898876, -44.818655905090054),
    ("CREOLI DO BINA", -5.359662278623261, -44.58848110291113),
    ("CANTO GRANDE", -5.955566044171886, -44.70478986716041),
    ("ALDEIA", -5.168862346832071, -44.75980841936062),
], columns=["localidade", "lat", "lon"])

coords["territ_key"] = coords["localidade"].map(canon_text)
coords["status_validacao"] = "confirmada_usuario"

# =========================
# LEITURA DOS ARQUIVOS
# =========================
base = Path(__file__).resolve().parent

secoes = pd.read_csv(base / "SEÇÕES.csv", encoding="latin1", sep=";")
prefeito = pd.read_csv(base / "VOTACAO_PREFEITO.csv", encoding="latin1", sep=";")
geo = gpd.read_file(base / "tuntum_malha.geojson")

secoes.columns = [c.strip() for c in secoes.columns]
prefeito.columns = [c.strip() for c in prefeito.columns]

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
          fernando=("FERNANDO", "sum"),
          tema=("TEMA", "sum"),
      ).reset_index()
)

territ["validos"] = territ["fernando"] + territ["tema"]
territ["margem_abs"] = (territ["fernando"] - territ["tema"]).abs()
territ["competitividade"] = np.where(
    territ["validos"] > 0,
    1 - (territ["margem_abs"] / territ["validos"]),
    0
)
territ["indice_oportunidade"] = (
    0.45 * score_norm(territ["abstencao"]) +
    0.35 * score_norm(territ["eleitores"]) +
    0.20 * score_norm(territ["competitividade"])
)

base_mapa = coords.merge(territ, on="territ_key", how="left")

if geo.crs is not None and str(geo.crs) != "EPSG:4326":
    geo = geo.to_crs(epsg=4326)

centroide = geo.geometry.union_all().centroid
center_lat = centroide.y
center_lon = centroide.x

st.title("Tuntum - Mapa com Coordenadas Embutidas")
st.caption("Versão sem dependência de CSV de coordenadas")

a, b, c, d = st.columns(4)
a.metric("Coordenadas embutidas", len(coords))
b.metric("Coordenadas válidas", int(base_mapa["lat"].notna().sum()))
c.metric("Casadas com base eleitoral", int(base_mapa["territorio"].notna().sum()))
d.metric("Prontas para mapa", int(base_mapa.dropna(subset=["lat", "lon"]).shape[0]))

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

fig.add_trace(
    go.Scattermapbox(
        lat=pts["lat"],
        lon=pts["lon"],
        mode="markers+text",
        text=pts["localidade"],
        textposition="top right",
        marker=dict(
            size=12,
            color=pts["indice_oportunidade"].fillna(0),
            colorscale="RdYlGn_r",
            showscale=True,
            colorbar=dict(title="Oportunidade")
        ),
        customdata=pts[["territorio", "local_principal", "eleitores", "abstencao"]].fillna("").values,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Base eleitoral: %{customdata[0]}<br>"
            "Local principal: %{customdata[1]}<br>"
            "Eleitores: %{customdata[2]}<br>"
            "Abstenção: %{customdata[3]}<extra></extra>"
        )
    )
)

fig.update_layout(
    mapbox=dict(
        style="carto-positron",
        center=dict(lat=center_lat, lon=center_lon),
        zoom=9.6
    ),
    margin=dict(l=0, r=0, t=40, b=0),
    title="Mapa de Tuntum com pontos carregados no código"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Pontos carregados")
st.dataframe(
    pts[["localidade", "lat", "lon", "territorio", "local_principal"]],
    use_container_width=True
)