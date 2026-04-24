
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import numpy as np
import re

st.set_page_config(page_title="Dashboard Eleitoral Tuntum 2024", layout="wide")

# =========================================================
# FUNÇÕES
# =========================================================
def canon_text(s):
    s = "" if pd.isna(s) else str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("-", " ")
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    aliases = {
        "IPUIRU": "IPU IRU",
        "IPU IRU": "IPU IRU",
        "BELÉM": "BELEM",
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

# =========================================================
# COORDENADAS INFORMADAS PELO USUÁRIO
# =========================================================
coords = pd.DataFrame([
    ("ARROZ", -5.202527647851387, -44.62631296094674),
    ("IPU IRU", -5.505905486189621, -44.86646062174089),
    ("SAO JOAQUIM DOS MELOS", -5.898484042898876, -44.818655905090054),
    ("CENTRO", -5.255784527155879, -44.65021946235093),
    ("MIL REIS", -5.2559198752907115, -44.641672690884654),
    ("VILA LUIZAO", -5.266581547978559, -44.64397428334195),
    ("ASTOLFO SEABRA", -5.273594307933202, -44.64101763053091),
    ("CAMPO VELHO", -5.254167532681394, -44.64570416910529),
    ("VILA BENTO", -5.283613321525536, -44.64185507502784),
    ("TUNTUM DE CIMA", -5.273745522846826, -44.63296501110159),
    ("NOVO MARAJA", -5.522638222192139, -44.85271922811691),
    ("BELEM", -5.758291958744166, -44.6181357973509),
    ("SAO LOURENCO", -5.784898314502129, -44.82136028125027),
    ("SAO BENTO", -5.786759446845751, -44.71396464807228),
    ("SANTA ROSA", -5.991448681240779, -44.795677360152),
    ("SERRA GRANDE", -5.258806885478064, -44.783383973294484),
    ("CIGANA", -5.380241037390525, -44.78254052192323),
    ("ARARA", -5.321341136586182, -44.60145229926725),
    ("MATO VERDE", -5.598402217466002, -44.58942520209541),
    ("BREJO DO JOAO", -5.828978349908755, -44.72723197760513),
    ("JENIPAPO DOS GOMES", -5.6243421285678625, -44.91376255190616),
    ("CREOLI DO BINA", -5.359662278623261, -44.58848110291113),
    ("CANTO GRANDE", -5.955566044171886, -44.70478986716041),
    ("ALDEIA", -5.168862346832071, -44.75980841936062),
], columns=["localidade_key", "lat", "lon"])

coords["localidade_key"] = coords["localidade_key"].map(canon_text)

# =========================================================
# LEITURA DOS DADOS
# =========================================================
base = Path(__file__).resolve().parent
req = ["SEÇÕES.csv", "VOTACAO_PREFEITO.csv", "tuntum_malha.geojson"]
missing = [f for f in req if not (base / f).exists()]
if missing:
    st.error("Arquivos faltando na pasta: " + ", ".join(missing))
    st.stop()

secoes = pd.read_csv(base / "SEÇÕES.csv", sep=";", encoding="latin1")
pref = pd.read_csv(base / "VOTACAO_PREFEITO.csv", sep=";", encoding="latin1")
geo = gpd.read_file(base / "tuntum_malha.geojson")

secoes.columns = [c.strip() for c in secoes.columns]
pref.columns = [c.strip() for c in pref.columns]

secoes["sec_key"] = secoes["SEÇÃO"].map(sec_key)
pref["sec_key"] = pref["SEÇÃO"].map(sec_key)

df = secoes.merge(pref[["sec_key", "FERNANDO", "TEMA"]], on="sec_key", how="left")

for c in ["Eleitores aptos", "Comparecimento", "FERNANDO", "TEMA"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["bairro_key"] = df["BAIRRO"].map(canon_text)
df["abstencao"] = df["Eleitores aptos"] - df["Comparecimento"]
df["validos_prefeito"] = df["FERNANDO"] + df["TEMA"]
df["turnout"] = np.where(df["Eleitores aptos"] > 0, df["Comparecimento"] / df["Eleitores aptos"], 0)

local = (
    df.groupby("bairro_key", dropna=False)
      .agg(
          localidade=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
          local_principal=("LOCAL DE VOTAÇÃO", lambda x: sorted(set(map(str, x)))[0]),
          secoes=("SEÇÃO", "count"),
          eleitores=("Eleitores aptos", "sum"),
          comparecimento=("Comparecimento", "sum"),
          abstencao=("abstencao", "sum"),
          fernando=("FERNANDO", "sum"),
          tema=("TEMA", "sum"),
      )
      .reset_index()
)

local["validos"] = local["fernando"] + local["tema"]
local["margem_abs"] = (local["fernando"] - local["tema"]).abs()
local["competitividade"] = np.where(local["validos"] > 0, 1 - (local["margem_abs"] / local["validos"]), 0)
local["share_fernando"] = np.where(local["validos"] > 0, local["fernando"] / local["validos"], 0)
local["share_tema"] = np.where(local["validos"] > 0, local["tema"] / local["validos"], 0)
local["turnout"] = np.where(local["eleitores"] > 0, local["comparecimento"] / local["eleitores"], 0)
local["lider"] = np.where(local["fernando"] >= local["tema"], "FERNANDO", "TEMA")
local["indice_oportunidade"] = (
    0.45 * score_norm(local["abstencao"]) +
    0.35 * score_norm(local["eleitores"]) +
    0.20 * score_norm(local["competitividade"])
)
local["faixa"] = np.select(
    [local["indice_oportunidade"] >= 0.70, local["indice_oportunidade"] >= 0.45],
    ["Alta atenção", "Média atenção"],
    default="Monitoramento"
)

base_mapa = local.merge(coords, left_on="bairro_key", right_on="localidade_key", how="left")

if geo.crs is not None and str(geo.crs) != "EPSG:4326":
    geo = geo.to_crs(epsg=4326)

centroide = geo.geometry.union_all().centroid
center_lat = centroide.y
center_lon = centroide.x

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Filtros")
ordem = st.sidebar.selectbox(
    "Ordenar localidades por",
    ["Índice de oportunidade", "Eleitores", "Abstenção", "Fernando", "Tema", "Competitividade"]
)
mostrar_sem_coord = st.sidebar.checkbox("Mostrar tabela de localidades sem coordenadas", value=True)

order_map = {
    "Índice de oportunidade": "indice_oportunidade",
    "Eleitores": "eleitores",
    "Abstenção": "abstencao",
    "Fernando": "fernando",
    "Tema": "tema",
    "Competitividade": "competitividade",
}
sort_col = order_map[ordem]

# =========================================================
# TÍTULO E KPIs
# =========================================================
st.title("Dashboard Eleitoral Tuntum 2024")
st.caption("Comparação territorial entre Fernando e Tema por localidade, usando a sua base de seções, votação e coordenadas.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Localidades", int(local.shape[0]))
k2.metric("Seções", int(df["sec_key"].nunique()))
k3.metric("Votos Fernando", f"{int(local['fernando'].sum()):,}".replace(",", "."))
k4.metric("Votos Tema", f"{int(local['tema'].sum()):,}".replace(",", "."))
k5.metric("Localidades com coordenadas", int(base_mapa["lat"].notna().sum()))

# =========================================================
# MAPA
# =========================================================
fig_map = go.Figure()
fig_map.add_trace(
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
    pts["cor_num"] = np.where(pts["lider"] == "FERNANDO", 1, 0)
    fig_map.add_trace(
        go.Scattermapbox(
            lat=pts["lat"],
            lon=pts["lon"],
            mode="markers+text",
            text=pts["localidade"],
            textposition="top right",
            marker=dict(
                size=(10 + pts["indice_oportunidade"] * 22).round(1),
                color=pts["cor_num"],
                colorscale=[[0, "#d95f5f"], [1, "#4f83ff"]],
                cmin=0,
                cmax=1,
                showscale=False
            ),
            customdata=pts[[
                "local_principal", "fernando", "tema", "eleitores", "abstencao",
                "competitividade", "indice_oportunidade", "lider"
            ]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Local principal: %{customdata[0]}<br>"
                "Fernando: %{customdata[1]:,.0f}<br>"
                "Tema: %{customdata[2]:,.0f}<br>"
                "Eleitores: %{customdata[3]:,.0f}<br>"
                "Abstenção: %{customdata[4]:,.0f}<br>"
                "Competitividade: %{customdata[5]:.1%}<br>"
                "Índice oportunidade: %{customdata[6]:.3f}<br>"
                "Líder local: %{customdata[7]}<extra></extra>"
            )
        )
    )

fig_map.update_layout(
    mapbox=dict(style="carto-positron", center=dict(lat=center_lat, lon=center_lon), zoom=9.6),
    margin=dict(l=0, r=0, t=40, b=0),
    title="Mapa territorial: liderança local e intensidade por oportunidade"
)
st.plotly_chart(fig_map, use_container_width=True)

# =========================================================
# GRÁFICOS
# =========================================================
ordered = local.sort_values(sort_col, ascending=False).copy()

c1, c2 = st.columns(2)

with c1:
    fig_bar = px.bar(
        ordered,
        x="localidade",
        y=["fernando", "tema"],
        barmode="group",
        title="Comparação de votos por localidade: Fernando x Tema"
    )
    fig_bar.update_layout(xaxis_title="Localidade", yaxis_title="Votos")
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    fig_share = px.bar(
        ordered,
        x="localidade",
        y=["share_fernando", "share_tema"],
        barmode="group",
        title="Participação dos votos válidos por localidade"
    )
    fig_share.update_layout(xaxis_title="Localidade", yaxis_title="Participação")
    fig_share.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_share, use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    fig_scatter = px.scatter(
        ordered,
        x="abstencao",
        y="competitividade",
        size="eleitores",
        color="lider",
        hover_name="localidade",
        title="Abstenção x competitividade por localidade"
    )
    fig_scatter.update_layout(xaxis_title="Abstenção", yaxis_title="Competitividade")
    fig_scatter.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_scatter, use_container_width=True)

with c4:
    top_margin = ordered.copy()
    top_margin["vantagem"] = top_margin["fernando"] - top_margin["tema"]
    fig_margin = px.bar(
        top_margin.sort_values("vantagem", ascending=False),
        x="localidade",
        y="vantagem",
        title="Saldo de votos por localidade (Fernando - Tema)"
    )
    fig_margin.update_layout(xaxis_title="Localidade", yaxis_title="Saldo de votos")
    st.plotly_chart(fig_margin, use_container_width=True)

# =========================================================
# CENÁRIOS DESCRITIVOS
# =========================================================
st.subheader("Cenários territoriais")
d1, d2, d3, d4 = st.columns(4)

mais_abst = local.sort_values("abstencao", ascending=False).iloc[0]
mais_comp = local.sort_values("competitividade", ascending=False).iloc[0]
mais_fern = local.sort_values("fernando", ascending=False).iloc[0]
mais_tema = local.sort_values("tema", ascending=False).iloc[0]

d1.metric("Maior abstenção", mais_abst["localidade"], f"{int(mais_abst['abstencao'])} abstenções")
d2.metric("Mais competitiva", mais_comp["localidade"], f"{mais_comp['competitividade']:.1%}")
d3.metric("Maior votação de Fernando", mais_fern["localidade"], f"{int(mais_fern['fernando'])} votos")
d4.metric("Maior votação de Tema", mais_tema["localidade"], f"{int(mais_tema['tema'])} votos")

# =========================================================
# TABELAS
# =========================================================
st.subheader("Tabela estratégica por localidade")
show = ordered[[
    "localidade", "local_principal", "secoes", "eleitores", "comparecimento",
    "abstencao", "fernando", "tema", "share_fernando", "share_tema",
    "competitividade", "indice_oportunidade", "lider", "lat", "lon"
]].copy()

st.dataframe(
    show.style.format({
        "share_fernando": "{:.1%}",
        "share_tema": "{:.1%}",
        "competitividade": "{:.1%}",
        "indice_oportunidade": "{:.3f}",
        "lat": "{:.6f}",
        "lon": "{:.6f}",
    }),
    use_container_width=True
)

if mostrar_sem_coord:
    st.subheader("Localidades sem coordenadas associadas")
    sem = base_mapa[base_mapa["lat"].isna() | base_mapa["lon"].isna()][[
        "localidade", "local_principal", "eleitores", "fernando", "tema", "abstencao"
    ]].copy()
    st.dataframe(sem, use_container_width=True)

st.info(
    "Leitura neutra do painel: ele compara o desempenho territorial dos dois candidatos, "
    "a participação dos votos válidos, a abstenção e a competitividade entre localidades."
)
