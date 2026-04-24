
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
# CLASSIFICAÇÃO TERRITORIAL
# =========================================================
URBAN_LOCALIDADES = {
    "CENTRO", "MIL REIS", "VILA LUIZAO", "ASTOLFO SEABRA",
    "CAMPO VELHO", "VILA BENTO", "TUNTUM DE CIMA"
}

def classificar_zona(localidade_key):
    return "Zona Urbana" if localidade_key in URBAN_LOCALIDADES else "Zona Rural"

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
    ("SAO MIGUEL", -5.602168662642484, -44.55582551563351),
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

# Base principal de localidades
secoes = pd.read_csv(base / "SEÇÕES.csv", sep=";", encoding="latin1")

# Base adicional para organização por ponto de votação
arquivo_pontos = "SEÇÕES(1).csv" if (base / "SEÇÕES(1).csv").exists() else "SEÇÕES.csv"
secoes_pontos = pd.read_csv(base / arquivo_pontos, sep=";", encoding="latin1")

pref = pd.read_csv(base / "VOTACAO_PREFEITO.csv", sep=";", encoding="latin1")
geo = gpd.read_file(base / "tuntum_malha.geojson")

secoes.columns = [c.strip() for c in secoes.columns]
secoes_pontos.columns = [c.strip() for c in secoes_pontos.columns]
pref.columns = [c.strip() for c in pref.columns]

secoes["sec_key"] = secoes["SEÇÃO"].map(sec_key)
secoes_pontos["sec_key"] = secoes_pontos["SEÇÃO"].map(sec_key)
pref["sec_key"] = pref["SEÇÃO"].map(sec_key)

# Ignora propositalmente as coordenadas da base SEÇÕES(1).csv e mantém apenas a estrutura de ponto de votação
df = secoes.merge(pref[["sec_key", "FERNANDO", "TEMA"]], on="sec_key", how="left")
df_pontos = secoes_pontos.merge(pref[["sec_key", "FERNANDO", "TEMA"]], on="sec_key", how="left")

for c in ["Eleitores aptos", "Comparecimento", "FERNANDO", "TEMA"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["bairro_key"] = df["BAIRRO"].map(canon_text)
df["zona"] = df["bairro_key"].map(classificar_zona)
df["abstencao"] = df["Eleitores aptos"] - df["Comparecimento"]
df["validos_prefeito"] = df["FERNANDO"] + df["TEMA"]
df["turnout"] = np.where(df["Eleitores aptos"] > 0, df["Comparecimento"] / df["Eleitores aptos"], 0)

for c in ["Eleitores aptos", "Comparecimento", "FERNANDO", "TEMA"]:
    df_pontos[c] = pd.to_numeric(df_pontos[c], errors="coerce").fillna(0)

df_pontos["bairro_key"] = df_pontos["BAIRRO"].map(canon_text)
df_pontos["zona"] = df_pontos["bairro_key"].map(classificar_zona)
df_pontos["abstencao"] = df_pontos["Eleitores aptos"] - df_pontos["Comparecimento"]
df_pontos["validos_prefeito"] = df_pontos["FERNANDO"] + df_pontos["TEMA"]
df_pontos["turnout"] = np.where(df_pontos["Eleitores aptos"] > 0, df_pontos["Comparecimento"] / df_pontos["Eleitores aptos"], 0)
df_pontos["ponto_key"] = df_pontos["LOCAL DE VOTAÇÃO"].map(canon_text)

local = (
    df.groupby("bairro_key", dropna=False)
      .agg(
          localidade=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
          local_principal=("LOCAL DE VOTAÇÃO", lambda x: sorted(set(map(str, x)))[0]),
          zona=("zona", lambda x: sorted(set(map(str, x)))[0]),
          secoes=("SEÇÃO", "count"),
          secoes_lista=("SEÇÃO", lambda x: ", ".join(sorted(set(map(str, x))))),
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

# Organização adicional por ponto de votação (sem substituir a leitura por localidade)
pontos_votacao = (
    df_pontos.groupby("ponto_key", dropna=False)
      .agg(
          ponto_votacao=("LOCAL DE VOTAÇÃO", lambda x: sorted(set(map(str, x)))[0]),
          zona=("zona", lambda x: sorted(set(map(str, x)))[0]),
          localidades_atendidas=("BAIRRO", lambda x: ", ".join(sorted(set(map(str, x))))),
          secoes=("SEÇÃO", "count"),
          secoes_lista=("SEÇÃO", lambda x: ", ".join(sorted(set(map(str, x))))),
          eleitores=("Eleitores aptos", "sum"),
          comparecimento=("Comparecimento", "sum"),
          abstencao=("abstencao", "sum"),
          fernando=("FERNANDO", "sum"),
          tema=("TEMA", "sum"),
      )
      .reset_index()
)

pontos_votacao["validos"] = pontos_votacao["fernando"] + pontos_votacao["tema"]
pontos_votacao["margem_abs"] = (pontos_votacao["fernando"] - pontos_votacao["tema"]).abs()
pontos_votacao["competitividade"] = np.where(
    pontos_votacao["validos"] > 0, 1 - (pontos_votacao["margem_abs"] / pontos_votacao["validos"]), 0
)
pontos_votacao["share_fernando"] = np.where(pontos_votacao["validos"] > 0, pontos_votacao["fernando"] / pontos_votacao["validos"], 0)
pontos_votacao["share_tema"] = np.where(pontos_votacao["validos"] > 0, pontos_votacao["tema"] / pontos_votacao["validos"], 0)
pontos_votacao["turnout"] = np.where(pontos_votacao["eleitores"] > 0, pontos_votacao["comparecimento"] / pontos_votacao["eleitores"], 0)
pontos_votacao["lider"] = np.where(pontos_votacao["fernando"] >= pontos_votacao["tema"], "FERNANDO", "TEMA")
pontos_votacao["indice_oportunidade"] = (
    0.45 * score_norm(pontos_votacao["abstencao"]) +
    0.35 * score_norm(pontos_votacao["eleitores"]) +
    0.20 * score_norm(pontos_votacao["competitividade"])
)
pontos_votacao["faixa"] = np.select(
    [pontos_votacao["indice_oportunidade"] >= 0.70, pontos_votacao["indice_oportunidade"] >= 0.45],
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

lider_filtro = st.sidebar.multiselect(
    "Filtrar líder local",
    options=["FERNANDO", "TEMA"],
    default=["FERNANDO", "TEMA"]
)

faixa_filtro = st.sidebar.multiselect(
    "Filtrar faixa estratégica",
    options=["Alta atenção", "Média atenção", "Monitoramento"],
    default=["Alta atenção", "Média atenção", "Monitoramento"]
)

somente_com_coord = st.sidebar.checkbox("Mostrar apenas localidades com coordenadas", value=False)

top_n = st.sidebar.slider("Top N nos rankings", min_value=5, max_value=30, value=10)

zona_filtro = st.sidebar.multiselect(
    "Filtrar zona territorial",
    options=["Zona Urbana", "Zona Rural"],
    default=["Zona Urbana", "Zona Rural"]
)

base_filtrada = base_mapa.copy()
base_filtrada = base_filtrada[base_filtrada["zona"].isin(zona_filtro)]
base_filtrada = base_filtrada[base_filtrada["lider"].isin(lider_filtro)]
base_filtrada = base_filtrada[base_filtrada["faixa"].isin(faixa_filtro)]
if somente_com_coord:
    base_filtrada = base_filtrada.dropna(subset=["lat", "lon"])

ordered_filtrado = base_filtrada.sort_values(sort_col, ascending=False).copy()

# =========================================================
# TÍTULO E KPIs
# =========================================================
st.title("Dashboard Eleitoral Tuntum 2024 - Painel Executivo")
st.caption("Comparação territorial entre Fernando e Tema por localidade, ponto de votação e seção, com organização por zona urbana e zona rural.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Localidades", int(base_filtrada.shape[0]))
k2.metric("Seções", int(df["sec_key"].nunique()))
k3.metric("Votos Fernando", f"{int(local['fernando'].sum()):,}".replace(",", "."))
k4.metric("Votos Tema", f"{int(local['tema'].sum()):,}".replace(",", "."))
k5.metric("Localidades com coordenadas", int(base_filtrada["lat"].notna().sum()))

# =========================================================
# CARD EXPLICATIVO DO ÍNDICE DE OPORTUNIDADE
# =========================================================
top5_oportunidade = ordered_filtrado.sort_values("indice_oportunidade", ascending=False).head(5).copy()

st.markdown("### Índice de oportunidade")
st.info(
    "O índice de oportunidade combina três sinais territoriais: "
    "**abstenção**, **tamanho do eleitorado** e **competitividade local**. "
    "Na fórmula do painel, a abstenção pesa 45%, o número de eleitores pesa 35% "
    "e a competitividade pesa 20%. Em termos práticos, localidades com muitos eleitores, "
    "muita abstenção e disputa apertada tendem a aparecer como áreas mais promissoras "
    "para ações de mobilização, comunicação segmentada e ganho de voto."
)

st.markdown("#### Avaliação das 5 localidades com maior índice de oportunidade")
for _, row in top5_oportunidade.iterrows():
    st.markdown(
        f"**{row['localidade']}** — seções: **{row['secoes_lista']}** | índice **{row['indice_oportunidade']:.3f}** | "
        f"eleitores: **{int(row['eleitores'])}** | abstenção: **{int(row['abstencao'])}** | "
        f"competitividade: **{row['competitividade']:.1%}** | líder local: **{row['lider']}**. "
        + (
            "Leitura: território muito estratégico, com boa margem para captura ou defesa de voto."
            if row['indice_oportunidade'] >= 0.70 else
            "Leitura: território relevante, com sinais claros de que uma atuação focada pode melhorar o desempenho."
        )
    )

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

pts = base_filtrada.dropna(subset=["lat", "lon"]).copy()
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
                "local_principal", "secoes_lista", "fernando", "tema", "eleitores", "abstencao",
                "competitividade", "indice_oportunidade", "lider"
            ]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Local principal: %{customdata[0]}<br>"
                "Seções: %{customdata[1]}<br>"
                "Fernando: %{customdata[2]:,.0f}<br>"
                "Tema: %{customdata[3]:,.0f}<br>"
                "Eleitores: %{customdata[4]:,.0f}<br>"
                "Abstenção: %{customdata[5]:,.0f}<br>"
                "Competitividade: %{customdata[6]:.1%}<br>"
                "Índice oportunidade: %{customdata[7]:.3f}<br>"
                "Líder local: %{customdata[8]}<extra></extra>"
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
ordered = ordered_filtrado.copy()

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

st.subheader("Rankings automáticos e cenários melhoráveis")

r1, r2 = st.columns(2)

with r1:
    st.markdown("**Top oportunidades territoriais**")
    top_oportunidade = ordered.head(top_n)[[
        "localidade", "secoes_lista", "eleitores", "abstencao", "fernando", "tema",
        "competitividade", "indice_oportunidade", "lider"
    ]].copy()
    st.dataframe(
        top_oportunidade.style.format({
            "competitividade": "{:.1%}",
            "indice_oportunidade": "{:.3f}",
        }),
        use_container_width=True
    )

with r2:
    st.markdown("**Localidades mais disputadas**")
    mais_disputadas = ordered.sort_values(
        ["competitividade", "validos"], ascending=[False, False]
    ).head(top_n)[[
        "localidade", "secoes_lista", "fernando", "tema", "validos",
        "competitividade", "abstencao", "lider"
    ]].copy()
    st.dataframe(
        mais_disputadas.style.format({
            "competitividade": "{:.1%}",
        }),
        use_container_width=True
    )

r3, r4 = st.columns(2)

with r3:
    st.markdown("**Onde Fernando pode crescer**")
    crescimento_fernando = ordered.copy()
    crescimento_fernando["gap_para_virada"] = np.where(
        crescimento_fernando["lider"] == "TEMA",
        (crescimento_fernando["tema"] - crescimento_fernando["fernando"]) + 1,
        0
    )
    crescimento_fernando = crescimento_fernando[
        crescimento_fernando["lider"] == "TEMA"
    ].sort_values(
        ["indice_oportunidade", "gap_para_virada"], ascending=[False, True]
    ).head(top_n)[[
        "localidade", "secoes_lista", "fernando", "tema", "gap_para_virada",
        "abstencao", "indice_oportunidade"
    ]]
    st.dataframe(
        crescimento_fernando.style.format({"indice_oportunidade": "{:.3f}"}),
        use_container_width=True
    )

with r4:
    st.markdown("**Onde Tema pode crescer**")
    crescimento_tema = ordered.copy()
    crescimento_tema["gap_para_virada"] = np.where(
        crescimento_tema["lider"] == "FERNANDO",
        (crescimento_tema["fernando"] - crescimento_tema["tema"]) + 1,
        0
    )
    crescimento_tema = crescimento_tema[
        crescimento_tema["lider"] == "FERNANDO"
    ].sort_values(
        ["indice_oportunidade", "gap_para_virada"], ascending=[False, True]
    ).head(top_n)[[
        "localidade", "secoes_lista", "fernando", "tema", "gap_para_virada",
        "abstencao", "indice_oportunidade"
    ]]
    st.dataframe(
        crescimento_tema.style.format({"indice_oportunidade": "{:.3f}"}),
        use_container_width=True
    )

st.download_button(
    label="Baixar tabela estratégica filtrada em CSV",
    data=ordered.to_csv(index=False).encode("utf-8-sig"),
    file_name="tuntum_tabela_estrategica_filtrada.csv",
    mime="text/csv"
)


st.subheader("Recomendações práticas por localidade")

def recomendacao_territorial(row):
    acoes = []
    if row["abstencao"] >= local["abstencao"].quantile(0.75):
        acoes.append("priorizar mobilização de comparecimento")
    if row["competitividade"] >= local["competitividade"].quantile(0.75):
        acoes.append("reforçar comunicação e presença de campo")
    if row["lider"] == "FERNANDO":
        acoes.append("atuar na defesa e ampliação da vantagem")
    else:
        acoes.append("atuar para reduzir desvantagem e buscar virada")
    if row["eleitores"] >= local["eleitores"].quantile(0.75):
        acoes.append("tratar como território de alto peso eleitoral")
    return "; ".join(acoes)

reco = ordered.head(top_n).copy()
reco["recomendacao"] = reco.apply(recomendacao_territorial, axis=1)
st.dataframe(
    reco[[
        "localidade", "secoes_lista", "local_principal", "eleitores", "abstencao",
        "fernando", "tema", "competitividade", "indice_oportunidade", "lider", "recomendacao"
    ]].style.format({
        "competitividade": "{:.1%}",
        "indice_oportunidade": "{:.3f}",
    }),
    use_container_width=True
)

st.subheader("Análise por ponto de votação")

pv1, pv2 = st.columns(2)

with pv1:
    fig_pv_bar = px.bar(
        pontos_votacao.sort_values("indice_oportunidade", ascending=False).head(top_n),
        x="ponto_votacao",
        y=["fernando", "tema"],
        barmode="group",
        title="Top pontos de votação por oportunidade: Fernando x Tema"
    )
    fig_pv_bar.update_layout(xaxis_title="Ponto de votação", yaxis_title="Votos")
    st.plotly_chart(fig_pv_bar, use_container_width=True)

with pv2:
    fig_pv_turnout = px.scatter(
        pontos_votacao,
        x="abstencao",
        y="competitividade",
        size="eleitores",
        color="lider",
        hover_name="ponto_votacao",
        title="Pontos de votação: abstenção x competitividade"
    )
    fig_pv_turnout.update_layout(xaxis_title="Abstenção", yaxis_title="Competitividade")
    fig_pv_turnout.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_pv_turnout, use_container_width=True)

st.markdown("**Tabela estratégica por ponto de votação**")
st.dataframe(
    pontos_votacao.sort_values(sort_col if sort_col in pontos_votacao.columns else "indice_oportunidade", ascending=False)[[
        "zona", "ponto_votacao", "localidades_atendidas", "secoes", "secoes_lista",
        "eleitores", "comparecimento", "abstencao", "fernando", "tema",
        "share_fernando", "share_tema", "competitividade", "indice_oportunidade", "lider"
    ]].style.format({
        "share_fernando": "{:.1%}",
        "share_tema": "{:.1%}",
        "competitividade": "{:.1%}",
        "indice_oportunidade": "{:.3f}",
    }),
    use_container_width=True
)

st.subheader("Tabela estratégica por localidade")
# Usa a base já enriquecida com coordenadas para evitar erro quando ordered não tiver lat/lon
show = base_filtrada.copy()
show = show.sort_values(sort_col, ascending=False)

# Garante a existência das colunas de coordenadas mesmo quando não houver associação
for col in ["lat", "lon"]:
    if col not in show.columns:
        show[col] = np.nan

show = show[[
    "zona", "localidade", "local_principal", "secoes", "secoes_lista", "eleitores", "comparecimento",
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
    sem = base_filtrada[base_filtrada["lat"].isna() | base_filtrada["lon"].isna()][[
        "zona", "localidade", "local_principal", "secoes_lista", "eleitores", "fernando", "tema", "abstencao"
    ]].copy()
    st.dataframe(sem, use_container_width=True)


st.subheader("Organização territorial por zona")

# Base de seções detalhadas para as abas
secoes_detalhadas = df_pontos[[
    "zona", "SEÇÃO", "LOCAL DE VOTAÇÃO", "BAIRRO", "Eleitores aptos",
    "Comparecimento", "abstencao", "FERNANDO", "TEMA", "turnout"
]].copy()

secoes_detalhadas["competitividade_secao"] = np.where(
    (secoes_detalhadas["FERNANDO"] + secoes_detalhadas["TEMA"]) > 0,
    1 - (abs(secoes_detalhadas["FERNANDO"] - secoes_detalhadas["TEMA"]) / (secoes_detalhadas["FERNANDO"] + secoes_detalhadas["TEMA"])),
    0
)

tab_urbana, tab_rural = st.tabs(["Zona Urbana", "Zona Rural"])

for nome_zona, tab in [("Zona Urbana", tab_urbana), ("Zona Rural", tab_rural)]:
    with tab:
        local_z = local[local["zona"] == nome_zona].sort_values(sort_col, ascending=False).copy()
        pontos_z = pontos_votacao[pontos_votacao["zona"] == nome_zona].sort_values(
            sort_col if sort_col in pontos_votacao.columns else "indice_oportunidade", ascending=False
        ).copy()
        secoes_z = secoes_detalhadas[secoes_detalhadas["zona"] == nome_zona].copy()

        kz1, kz2, kz3, kz4 = st.columns(4)
        kz1.metric("Localidades", int(local_z.shape[0]))
        kz2.metric("Pontos de votação", int(pontos_z.shape[0]))
        kz3.metric("Seções", int(secoes_z["SEÇÃO"].nunique()))
        kz4.metric("Eleitores", f"{int(local_z['eleitores'].sum()):,}".replace(",", "."))

        cz1, cz2 = st.columns(2)

        with cz1:
            fig_z_local = px.bar(
                local_z.head(top_n),
                x="localidade",
                y=["fernando", "tema"],
                barmode="group",
                title=f"{nome_zona}: comparação Fernando x Tema por localidade"
            )
            fig_z_local.update_layout(xaxis_title="Localidade", yaxis_title="Votos")
            st.plotly_chart(fig_z_local, use_container_width=True)

        with cz2:
            fig_z_pontos = px.bar(
                pontos_z.head(top_n),
                x="ponto_votacao",
                y=["fernando", "tema"],
                barmode="group",
                title=f"{nome_zona}: comparação Fernando x Tema por ponto de votação"
            )
            fig_z_pontos.update_layout(xaxis_title="Ponto de votação", yaxis_title="Votos")
            st.plotly_chart(fig_z_pontos, use_container_width=True)

        st.markdown(f"**Seções de {nome_zona}**")
        st.dataframe(
            secoes_z[[
                "SEÇÃO", "LOCAL DE VOTAÇÃO", "BAIRRO", "Eleitores aptos",
                "Comparecimento", "abstencao", "FERNANDO", "TEMA",
                "turnout", "competitividade_secao"
            ]].sort_values(["LOCAL DE VOTAÇÃO", "SEÇÃO"]).style.format({
                "turnout": "{:.1%}",
                "competitividade_secao": "{:.1%}",
            }),
            use_container_width=True
        )

        st.markdown(f"**Resumo por ponto de votação — {nome_zona}**")
        st.dataframe(
            pontos_z[[
                "ponto_votacao", "localidades_atendidas", "secoes_lista", "eleitores",
                "abstencao", "fernando", "tema", "competitividade", "indice_oportunidade", "lider"
            ]].style.format({
                "competitividade": "{:.1%}",
                "indice_oportunidade": "{:.3f}",
            }),
            use_container_width=True
        )
st.info(
    "Leitura neutra do painel: ele compara o desempenho territorial dos dois candidatos, "
    "a participação dos votos válidos, a abstenção e a competitividade entre localidades e também por ponto de votação."
)
