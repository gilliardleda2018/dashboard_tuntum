import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import numpy as np
import re

st.set_page_config(page_title="Dashboard Tuntum V6 - Atlas Territorial", layout="wide")

def canon_text(s):
    s = "" if pd.isna(s) else str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("-", " ")
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

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

def apply_aliases(s):
    aliases = {
        "IPU IRU": "IPU IRU",
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
        "MARAJA": "MARAJA",
    }
    return aliases.get(s, s)

base = Path(__file__).resolve().parent
req = ["SEÇÕES.csv", "VOTACAO_PREFEITO.csv", "tuntum_malha.geojson", "atlas_territorial_tuntum_base.csv"]
faltando = [f for f in req if not (base / f).exists()]
if faltando:
    st.error("Arquivos faltando: " + ", ".join(faltando))
    st.stop()

secoes = pd.read_csv(base / "SEÇÕES.csv", encoding="latin1", sep=";")
prefeito = pd.read_csv(base / "VOTACAO_PREFEITO.csv", encoding="latin1", sep=";")
geo = gpd.read_file(base / "tuntum_malha.geojson")
atlas = pd.read_csv(base / "atlas_territorial_tuntum_base.csv")

secoes.columns = [c.strip() for c in secoes.columns]
prefeito.columns = [c.strip() for c in prefeito.columns]
atlas.columns = [c.strip() for c in atlas.columns]

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
df["territ_key"] = df["BAIRRO"].map(canon_text).map(apply_aliases)

territ = (
    df.groupby("territ_key", dropna=False)
      .agg(
          territorio=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
          local_principal=("LOCAL DE VOTAÇÃO", lambda x: sorted(set(map(str, x)))[0]),
          secoes=("SEÇÃO", "count"),
          eleitores=("Eleitores aptos", "sum"),
          comparecimento=("Comparecimento", "sum"),
          abstencao=("abstencao", "sum"),
          fernando=("FERNANDO", "sum"),
          tema=("TEMA", "sum")
      ).reset_index()
)

territ["validos"] = territ["fernando"] + territ["tema"]
territ["margem_abs"] = (territ["fernando"] - territ["tema"]).abs()
territ["competitividade"] = np.where(
    territ["validos"] > 0, 1 - (territ["margem_abs"] / territ["validos"]), 0
)
territ["indice_oportunidade"] = (
    0.45 * score_norm(territ["abstencao"]) +
    0.35 * score_norm(territ["eleitores"]) +
    0.20 * score_norm(territ["competitividade"])
)
territ["faixa"] = np.select(
    [territ["indice_oportunidade"] >= 0.70, territ["indice_oportunidade"] >= 0.45],
    ["Alta prioridade", "Média prioridade"],
    default="Monitoramento"
)

atlas["territ_key"] = atlas["localidade"].map(canon_text).map(apply_aliases)
atlas["lat"] = pd.to_numeric(atlas["lat"], errors="coerce")
atlas["lon"] = pd.to_numeric(atlas["lon"], errors="coerce")

base_mapa = territ.merge(
    atlas[["territ_key", "localidade", "origem", "lat", "lon", "status_validacao", "observacao"]],
    on="territ_key",
    how="outer"
)

base_mapa["nome_exibicao"] = base_mapa["territorio"].fillna(base_mapa["localidade"])
base_mapa["eleitores"] = base_mapa["eleitores"].fillna(0)
base_mapa["comparecimento"] = base_mapa["comparecimento"].fillna(0)
base_mapa["abstencao"] = base_mapa["abstencao"].fillna(0)
base_mapa["competitividade"] = base_mapa["competitividade"].fillna(0)
base_mapa["indice_oportunidade"] = base_mapa["indice_oportunidade"].fillna(0)
base_mapa["faixa"] = base_mapa["faixa"].fillna("Sem base eleitoral")
base_mapa["origem"] = base_mapa["origem"].fillna("base_eleitoral_sem_atlas")
base_mapa["status_validacao"] = base_mapa["status_validacao"].fillna("sem_cadastro_atlas")

if geo.crs is not None and str(geo.crs) != "EPSG:4326":
    geo = geo.to_crs(epsg=4326)

centroide = geo.geometry.union_all().centroid
center_lat = centroide.y
center_lon = centroide.x

st.title("Dashboard Tuntum V6 - Atlas Territorial")
st.caption("Malha municipal + atlas de localidades/povoados + inteligência eleitoral")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Territórios eleitorais", int(territ["territ_key"].nunique()))
k2.metric("Localidades no atlas", int(atlas["territ_key"].nunique()))
k3.metric("Com coordenadas", int(base_mapa["lat"].notna().sum()))
k4.metric("Sem coordenadas", int(base_mapa["lat"].isna().sum()))

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
            text=pts["nome_exibicao"],
            textposition="top right",
            customdata=pts[[
                "local_principal", "eleitores", "abstencao", "competitividade",
                "indice_oportunidade", "faixa", "status_validacao", "origem"
            ]].fillna("").values,
            marker=dict(
                size=(9 + pts["indice_oportunidade"] * 24).round(1),
                color=pts["indice_oportunidade"],
                colorscale="RdYlGn_r",
                cmin=0,
                cmax=max(1.0, float(pts["indice_oportunidade"].max())),
                showscale=True,
                colorbar=dict(title="Oportunidade")
            ),
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Local principal: %{customdata[0]}<br>" +
                "Eleitores: %{customdata[1]:,.0f}<br>" +
                "Abstenção: %{customdata[2]:,.0f}<br>" +
                "Competitividade: %{customdata[3]:.1%}<br>" +
                "Índice: %{customdata[4]:.3f}<br>" +
                "Faixa: %{customdata[5]}<br>" +
                "Validação: %{customdata[6]}<br>" +
                "Origem: %{customdata[7]}<extra></extra>"
            )
        )
    )

fig.update_layout(
    mapbox=dict(style="carto-positron", center=dict(lat=center_lat, lon=center_lon), zoom=9.6),
    margin=dict(l=0, r=0, t=40, b=0),
    title="Tuntum - Atlas territorial e territórios eleitorais"
)
st.plotly_chart(fig, use_container_width=True)

aba1, aba2, aba3 = st.tabs(["Diagnóstico", "Territórios prioritários", "Atlas completo"])

with aba1:
    sem = base_mapa[base_mapa["lat"].isna()][[
        "nome_exibicao", "territ_key", "origem", "status_validacao", "indice_oportunidade"
    ]].sort_values("indice_oportunidade", ascending=False)
    st.dataframe(sem.style.format({"indice_oportunidade": "{:.3f}"}), use_container_width=True)

with aba2:
    prior = base_mapa[base_mapa["eleitores"] > 0][[
        "nome_exibicao", "local_principal", "eleitores", "abstencao",
        "competitividade", "indice_oportunidade", "faixa", "lat", "lon"
    ]].sort_values("indice_oportunidade", ascending=False)
    st.dataframe(
        prior.style.format({
            "competitividade": "{:.1%}",
            "indice_oportunidade": "{:.3f}",
            "lat": "{:.6f}",
            "lon": "{:.6f}",
        }),
        use_container_width=True
    )

with aba3:
    st.dataframe(base_mapa, use_container_width=True)

st.info("Preencha o CSV do atlas com coordenadas confirmadas do seu mapa base. O painel plota automaticamente o que tiver lat/lon válidos.")