import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import numpy as np
import re

st.set_page_config(page_title="Dashboard Tuntum V5 - Diagnóstico de Mapa", layout="wide")

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
        "MIL REIS": "MIL REIS",
        "VILA LUIZAO": "VILA LUIZAO",
        "NOVO MARAJA": "NOVO MARAJA",
        "BREJO DO JOAO": "BREJO DO JOAO",
        "SAO LOURENCO": "SAO LOURENCO",
        "SAO BENTO": "SAO BENTO",
        "SAO JOAQUIM DOS MELOS": "SAO JOAQUIM DOS MELOS",
    }
    return aliases.get(s, s)

base = Path(__file__).resolve().parent

# Arquivos necessários
req = ["SEÇÕES.csv", "VOTACAO_PREFEITO.csv", "tuntum_malha.geojson", "localidades_tuntum_validacao_template.csv"]
faltando = [f for f in req if not (base / f).exists()]
if faltando:
    st.error("Arquivos faltando na pasta: " + ", ".join(faltando))
    st.stop()

secoes = pd.read_csv(base / "SEÇÕES.csv", encoding="latin1", sep=";")
prefeito = pd.read_csv(base / "VOTACAO_PREFEITO.csv", encoding="latin1", sep=";")
geo = gpd.read_file(base / "tuntum_malha.geojson")
coords = pd.read_csv(base / "localidades_tuntum_validacao_template.csv")

secoes.columns = [c.strip() for c in secoes.columns]
prefeito.columns = [c.strip() for c in prefeito.columns]
coords.columns = [c.strip() for c in coords.columns]

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
df["bairro_base"] = df["BAIRRO"].astype(str)
df["bairro_key"] = df["bairro_base"].map(canon_text).map(apply_aliases)

territ = (
    df.groupby("bairro_key", dropna=False)
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
territ["indice_oportunidade"] = (
    0.45 * score_norm(territ["abstencao"]) +
    0.35 * score_norm(territ["eleitores"]) +
    0.20 * score_norm(territ["competitividade"])
)

territ["zona_prioridade"] = np.select(
    [territ["indice_oportunidade"] >= 0.70, territ["indice_oportunidade"] >= 0.45],
    ["Alta prioridade", "Média prioridade"],
    default="Monitoramento"
)

coords["localidade_original"] = coords["localidade"].astype(str)
coords["bairro_key"] = coords["localidade_original"].map(canon_text).map(apply_aliases)

# deduplicar coords por chave, mantendo a primeira linha preenchida
coords = coords.sort_values(
    by=["lat", "lon"],
    ascending=[False, False],
    na_position="last"
).drop_duplicates(subset=["bairro_key"], keep="first")

base_mapa = territ.merge(
    coords[["bairro_key", "localidade_original", "lat", "lon", "status_validacao"]],
    on="bairro_key",
    how="left"
)

if geo.crs is not None and str(geo.crs) != "EPSG:4326":
    geo = geo.to_crs(epsg=4326)

centroide = geo.geometry.union_all().centroid
center_lat = centroide.y
center_lon = centroide.x

st.title("Dashboard Tuntum - Mapa com Diagnóstico")
st.caption("Associação robusta entre localidades da base eleitoral e coordenadas validadas")

a, b, c, d = st.columns(4)
a.metric("Territórios na base", len(territ))
b.metric("Com chave casada", int(base_mapa["status_validacao"].notna().sum()))
c.metric("Com coordenadas", int(base_mapa["lat"].notna().sum()))
d.metric("Sem coordenadas", int(base_mapa["lat"].isna().sum()))

fig = go.Figure()

fig.add_trace(
    go.Choroplethmapbox(
        geojson=geo.__geo_interface__,
        locations=geo.index.astype(str),
        z=[1] * len(geo),
        featureidkey="id",
        colorscale=[[0, "rgba(90,160,210,0.15)"], [1, "rgba(90,160,210,0.15)"]],
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
            mode="markers+text",
            text=plot_pts["bairro"],
            textposition="top right",
            customdata=plot_pts[[
                "local_principal", "eleitores", "abstencao", "competitividade",
                "indice_oportunidade", "zona_prioridade", "status_validacao",
                "bairro_key"
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
                "Chave: %{customdata[7]}<br>" +
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
    mapbox=dict(style="carto-positron", center=dict(lat=center_lat, lon=center_lon), zoom=9.6),
    margin=dict(l=0, r=0, t=40, b=0),
    title="Tuntum - malha municipal + localidades associadas"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Diagnóstico de associação")
diag = base_mapa[[
    "bairro", "bairro_key", "localidade_original", "status_validacao", "lat", "lon"
]].copy()
diag["associado"] = np.where(diag["localidade_original"].notna(), "SIM", "NÃO")
st.dataframe(diag.sort_values(["associado", "bairro"], ascending=[True, True]), use_container_width=True)

st.subheader("Territórios sem coordenadas")
sem = base_mapa[base_mapa["lat"].isna()][[
    "bairro", "bairro_key", "local_principal", "eleitores", "abstencao", "indice_oportunidade"
]].sort_values("indice_oportunidade", ascending=False)
st.dataframe(
    sem.style.format({"indice_oportunidade": "{:.3f}"}),
    use_container_width=True
)

st.subheader("Exemplo de preenchimento do CSV")
st.code(
"""localidade,lat,lon,status_validacao
CENTRO,-5.257800,-44.648500,confirmada_publicamente
BELEM,-5.238900,-44.633500,confirmada_publicamente
IPU IRU,-5.244800,-44.639700,confirmada_publicamente""",
language="csv"
)

st.info("Se o mapa aparecer sem pontos, confira se o CSV de localidades tem lat/lon preenchidos. Se aparecerem poucos pontos, veja a tabela de diagnóstico para identificar nomes que não casaram.")