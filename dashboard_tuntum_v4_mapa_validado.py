import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import numpy as np

st.set_page_config(page_title="Dashboard Tuntum V4 - Mapa Validado", layout="wide")

# =========================
# FUNÇÕES
# =========================
def norm_text(s):
    s = str(s).strip().upper()
    s = " ".join(s.split())
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    return s

def sec_key(s):
    s = str(s).upper().replace("SEÇÃO", "").replace("SECAO", "").strip()
    return s

def score_norm(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)

# =========================
# CARREGAMENTO
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
df["bairro_norm"] = df["BAIRRO"].map(norm_text)

# =========================
# AGREGAÇÃO TERRITORIAL
# =========================
territ = (
    df.groupby("bairro_norm")
      .agg(
          bairro=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
          local_principal=("LOCAL DE VOTAÇÃO", lambda x: sorted(set(map(str, x)))[0]),
          secoes=("SEÇÃO", "count"),
          eleitores=("Eleitores aptos", "sum"),
          comparecimento=("Comparecimento", "sum"),
          abstencao=("abstencao", "sum"),
          fernando=("FERNANDO", "sum"),
          tema=("TEMA", "sum")
      )
      .reset_index()
)

territ["validos"] = territ["fernando"] + territ["tema"]
territ["margem_abs"] = (territ["fernando"] - territ["tema"]).abs()
territ["competitividade"] = np.where(
    territ["validos"] > 0,
    1 - (territ["margem_abs"] / territ["validos"]),
    0
)
territ["turnout"] = np.where(
    territ["eleitores"] > 0,
    territ["comparecimento"] / territ["eleitores"],
    0
)
territ["indice_oportunidade"] = (
    0.45 * score_norm(territ["abstencao"]) +
    0.35 * score_norm(territ["eleitores"]) +
    0.20 * score_norm(territ["competitividade"])
)

territ["zona_prioridade"] = np.select(
    [
        territ["indice_oportunidade"] >= 0.70,
        territ["indice_oportunidade"] >= 0.45
    ],
    [
        "Alta prioridade",
        "Média prioridade"
    ],
    default="Monitoramento"
)

# =========================
# COORDENADAS VALIDADAS
# =========================
# Este arquivo deve ser preenchido apenas com localidades confirmadas.
coords_path = base / "localidades_tuntum_validacao_template.csv"
coords = pd.read_csv(coords_path)

coords.columns = [c.strip() for c in coords.columns]
coords["bairro_norm"] = coords["localidade"].map(norm_text)

base_mapa = territ.merge(
    coords[["bairro_norm", "lat", "lon", "status_validacao"]],
    on="bairro_norm",
    how="left"
)

# =========================
# GEO
# =========================
if geo.crs is not None and str(geo.crs) != "EPSG:4326":
    geo = geo.to_crs(epsg=4326)

centroide = geo.geometry.union_all().centroid
center_lat = centroide.y
center_lon = centroide.x

# =========================
# APP
# =========================
st.title("Dashboard Eleitoral Tuntum - V4")
st.caption("Mapa real do município com localidades validadas e prioridade estratégica")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Territórios", int(len(territ)))
c2.metric("Eleitores aptos", f"{int(territ['eleitores'].sum()):,}".replace(",", "."))
c3.metric("Localidades mapeadas", int(base_mapa['lat'].notna().sum()))
c4.metric("Maior prioridade", territ.sort_values("indice_oportunidade", ascending=False)["bairro"].iloc[0])

st.divider()

# =========================
# MAPA
# =========================
fig = go.Figure()

fig.add_trace(
    go.Choroplethmapbox(
        geojson=geo.__geo_interface__,
        locations=geo.index.astype(str),
        z=[1] * len(geo),
        featureidkey="id",
        colorscale=[[0, "rgba(90,160,210,0.18)"], [1, "rgba(90,160,210,0.18)"]],
        marker_line_color="rgb(30,90,160)",
        marker_line_width=2,
        showscale=False,
        hovertext=geo["NM_MUN"] if "NM_MUN" in geo.columns else ["Tuntum"] * len(geo),
        hoverinfo="text"
    )
)

plot_pts = base_mapa.dropna(subset=["lat", "lon"]).copy()

if len(plot_pts) > 0:
    fig.add_trace(
        go.Scattermapbox(
            lat=plot_pts["lat"],
            lon=plot_pts["lon"],
            mode="markers",
            text=plot_pts["bairro"],
            customdata=plot_pts[[
                "local_principal", "eleitores", "abstencao",
                "competitividade", "indice_oportunidade",
                "zona_prioridade", "status_validacao"
            ]].values,
            marker=dict(
                size=(10 + plot_pts["indice_oportunidade"] * 25).round(1),
                color=plot_pts["indice_oportunidade"],
                colorscale="RdYlGn_r",
                cmin=0,
                cmax=1,
                showscale=True,
                colorbar=dict(title="Oportunidade")
            ),
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Local principal: %{customdata[0]}<br>" +
                "Eleitores: %{customdata[1]:,.0f}<br>" +
                "Abstenção: %{customdata[2]:,.0f}<br>" +
                "Competitividade: %{customdata[3]:.1%}<br>" +
                "Índice oportunidade: %{customdata[4]:.3f}<br>" +
                "Faixa: %{customdata[5]}<br>" +
                "Validação: %{customdata[6]}<extra></extra>"
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
    title="Tuntum - malha municipal + localidades confirmadas"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Tabela estratégica")
st.dataframe(
    base_mapa[[
        "bairro", "local_principal", "secoes", "eleitores", "comparecimento",
        "abstencao", "competitividade", "indice_oportunidade",
        "zona_prioridade", "status_validacao", "lat", "lon"
    ]].sort_values("indice_oportunidade", ascending=False)
    .style.format({
        "competitividade": "{:.1%}",
        "indice_oportunidade": "{:.3f}",
        "lat": "{:.6f}",
        "lon": "{:.6f}",
    }),
    use_container_width=True
)

st.info(
    "Use apenas localidades com coordenadas realmente confirmadas. "
    "As demais podem ficar como pendentes até validação."
)