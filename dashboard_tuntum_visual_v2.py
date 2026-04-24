
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from pathlib import Path
import unicodedata

st.set_page_config(page_title="Dashboard Eleitoral Tuntum Visual", layout="wide")

# =========================
# AUXILIARES
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
    series = pd.to_numeric(series, errors="coerce")
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0]*len(series))
    return (series - mn)/(mx-mn)

# =========================
# CARREGAR BASE
# =========================
base = Path(__file__).resolve().parent

secoes = pd.read_csv(base / "SEÇÕES.csv", encoding="latin1", sep=";")
prefeito = pd.read_csv(base / "VOTACAO_PREFEITO.csv", encoding="latin1", sep=";")

secoes.columns = [c.strip() for c in secoes.columns]
prefeito.columns = [c.strip() for c in prefeito.columns]

secoes["sec_key"] = secoes["SEÇÃO"].map(sec_key)
prefeito["sec_key"] = prefeito["SEÇÃO"].map(sec_key)

df = secoes.merge(
    prefeito[["sec_key", "FERNANDO", "TEMA"]],
    on="sec_key",
    how="left"
)

df["bairro_norm"] = df["BAIRRO"].map(norm_text)

for c in ["Eleitores aptos", "Comparecimento", "FERNANDO", "TEMA"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["abstencao"] = df["Eleitores aptos"] - df["Comparecimento"]

# =========================
# AGREGAÇÃO BAIRRO
# =========================
bairro = (
    df.groupby("bairro_norm")
    .agg(
        bairro=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
        eleitores=("Eleitores aptos", "sum"),
        comparecimento=("Comparecimento", "sum"),
        abstencao=("abstencao", "sum"),
        fernando=("FERNANDO", "sum"),
        tema=("TEMA", "sum")
    )
    .reset_index()
)

bairro["validos"] = bairro["fernando"] + bairro["tema"]
bairro["margem"] = (bairro["fernando"] - bairro["tema"]).abs()
bairro["competitividade"] = np.where(
    bairro["validos"] > 0,
    1 - (bairro["margem"]/bairro["validos"]),
    0
)

bairro["indice_oportunidade"] = (
    0.45*score_norm(bairro["abstencao"]) +
    0.35*score_norm(bairro["eleitores"]) +
    0.20*score_norm(bairro["competitividade"])
)

# classificação visual
bairro["zona"] = np.select(
    [
        bairro["indice_oportunidade"] >= 0.70,
        bairro["indice_oportunidade"] >= 0.45
    ],
    [
        "Alta prioridade",
        "Média prioridade"
    ],
    default="Monitoramento"
)

# =========================
# APP
# =========================
st.title("Mapa Estratégico Eleitoral — Tuntum 2024")
st.caption("Visualização territorial inteligente para próximas eleições")

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Bairros analisados", len(bairro))
k2.metric("Eleitores", f"{int(bairro['eleitores'].sum()):,}".replace(",", "."))
k3.metric("Abstenções", f"{int(bairro['abstencao'].sum()):,}".replace(",", "."))
k4.metric("Maior prioridade", bairro.sort_values("indice_oportunidade", ascending=False)["bairro"].iloc[0])

st.divider()

# =========================
# MAPA VISUAL TERRITORIAL
# =========================
fig = px.scatter(
    bairro,
    x="eleitores",
    y="abstencao",
    size="competitividade",
    color="zona",
    hover_name="bairro",
    title="Mapa de calor político territorial"
)

fig.update_layout(
    xaxis_title="Peso eleitoral",
    yaxis_title="Abstenção"
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# RANKING VISUAL
# =========================
fig2 = px.bar(
    bairro.sort_values("indice_oportunidade", ascending=False).head(15),
    x="indice_oportunidade",
    y="bairro",
    color="zona",
    orientation="h",
    title="Top 15 territórios prioritários"
)

fig2.update_layout(
    xaxis_title="Índice de oportunidade",
    yaxis_title="Bairro"
)

st.plotly_chart(fig2, use_container_width=True)

# =========================
# FORÇA PREFEITO
# =========================
fig3 = px.bar(
    bairro.sort_values("validos", ascending=False),
    x="bairro",
    y=["fernando", "tema"],
    barmode="group",
    title="Comparativo prefeito por bairro"
)

st.plotly_chart(fig3, use_container_width=True)

# =========================
# TABELA FINAL
# =========================
st.subheader("Tabela estratégica territorial")

mostrar = bairro[[
    "bairro", "eleitores", "comparecimento", "abstencao",
    "competitividade", "indice_oportunidade", "zona"
]].sort_values("indice_oportunidade", ascending=False)

st.dataframe(
    mostrar.style.format({
        "competitividade": "{:.1%}",
        "indice_oportunidade": "{:.3f}"
    }),
    use_container_width=True
)

st.info(
    "Alta prioridade = territórios com maior eleitorado, maior abstenção e disputa sensível."
)
