
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import unicodedata
from pathlib import Path
import re

st.set_page_config(
    page_title="Dashboard Eleitoral Tuntum 2024",
    layout="wide"
)

# =========================
# FUNÇÕES AUXILIARES
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
    s = str(s).upper().replace("  ", " ").strip()
    s = s.replace("SEÇÃO", "").replace("SECAO", "").strip()
    return s

def score_norm(series):
    series = pd.to_numeric(series, errors="coerce")
    mn, mx = series.min(), series.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)

def carregar_dados():
    base = Path(__file__).resolve().parent

    secoes = pd.read_csv(base / "SEÇÕES.csv", encoding="latin1", sep=";")
    prefeito = pd.read_csv(base / "VOTACAO_PREFEITO.csv", encoding="latin1", sep=";")
    vereador = pd.read_csv(base / "VOTAÇÃO_VEREADOR.csv", encoding="latin1", sep=";")

    secoes.columns = [c.strip() for c in secoes.columns]
    prefeito.columns = [c.strip() for c in prefeito.columns]
    vereador.columns = [c.strip() for c in vereador.columns]

    secoes = secoes.loc[:, ~secoes.columns.str.contains(r"^Unnamed", na=False)]
    vereador = vereador.loc[:, ~vereador.columns.str.contains(r"^Unnamed", na=False)]

    secoes["sec_key"] = secoes["SEÇÃO"].map(sec_key)
    prefeito["sec_key"] = prefeito["SEÇÃO"].map(sec_key)

    base_sec = secoes.merge(
        prefeito[["sec_key", "FERNANDO", "TEMA"]],
        on="sec_key",
        how="left"
    )

    base_sec["bairro_norm"] = base_sec["BAIRRO"].map(norm_text)
    base_sec["eleitores_aptos"] = pd.to_numeric(base_sec["Eleitores aptos"], errors="coerce").fillna(0)
    base_sec["comparecimento"] = pd.to_numeric(base_sec["Comparecimento"], errors="coerce").fillna(0)
    base_sec["abstencao"] = base_sec["eleitores_aptos"] - base_sec["comparecimento"]
    base_sec["FERNANDO"] = pd.to_numeric(base_sec["FERNANDO"], errors="coerce").fillna(0)
    base_sec["TEMA"] = pd.to_numeric(base_sec["TEMA"], errors="coerce").fillna(0)
    base_sec["validos_prefeito"] = base_sec["FERNANDO"] + base_sec["TEMA"]
    base_sec["turnout"] = np.where(
        base_sec["eleitores_aptos"] > 0,
        base_sec["comparecimento"] / base_sec["eleitores_aptos"],
        0
    )

    ver_long = vereador.melt(
        id_vars="CANDIDATO",
        var_name="SEÇÃO",
        value_name="votos"
    ).dropna(subset=["votos"])

    ver_long["SEÇÃO"] = ver_long["SEÇÃO"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    ver_long["sec_key"] = ver_long["SEÇÃO"].map(sec_key)
    ver_long["CANDIDATO"] = ver_long["CANDIDATO"].astype(str).str.strip()
    ver_long["votos"] = pd.to_numeric(ver_long["votos"], errors="coerce").fillna(0)

    ver_long = ver_long.merge(
        base_sec[["sec_key", "bairro_norm", "BAIRRO", "LOCAL DE VOTAÇÃO"]],
        on="sec_key",
        how="left"
    )

    return base_sec, ver_long

def agregar_bairros(base_sec):
    bairros = (
        base_sec.groupby("bairro_norm")
        .agg(
            bairro=("BAIRRO", lambda x: sorted(set(map(str, x)))[0]),
            secoes=("sec_key", "count"),
            eleitores=("eleitores_aptos", "sum"),
            comparecimento=("comparecimento", "sum"),
            abstencao=("abstencao", "sum"),
            fernando=("FERNANDO", "sum"),
            tema=("TEMA", "sum"),
        )
        .reset_index()
    )

    bairros["validos"] = bairros["fernando"] + bairros["tema"]
    bairros["margem_abs"] = (bairros["fernando"] - bairros["tema"]).abs()
    bairros["competitividade"] = np.where(
        bairros["validos"] > 0,
        1 - (bairros["margem_abs"] / bairros["validos"]),
        0
    )
    bairros["turnout"] = np.where(
        bairros["eleitores"] > 0,
        bairros["comparecimento"] / bairros["eleitores"],
        0
    )
    bairros["peso_eleitoral"] = bairros["eleitores"] / bairros["eleitores"].sum()

    bairros["indice_oportunidade"] = (
        0.45 * score_norm(bairros["abstencao"]) +
        0.35 * score_norm(bairros["eleitores"]) +
        0.20 * score_norm(bairros["competitividade"])
    )

    bairros["lider_prefeito"] = np.where(
        bairros["fernando"] >= bairros["tema"], "FERNANDO", "TEMA"
    )
    bairros["vantagem_lider"] = np.where(
        bairros["validos"] > 0,
        (bairhos_max(bairros[["fernando", "tema"]]) - bairros_min(bairros[["fernando", "tema"]])) / bairros["validos"],
        0
    )

    return bairros.sort_values("indice_oportunidade", ascending=False)

def bairros_max(df2):
    return df2.max(axis=1)

def bairros_min(df2):
    return df2.min(axis=1)

def ranking_vereador(ver_long):
    cand_total = (
        ver_long.groupby("CANDIDATO", as_index=False)["votos"]
        .sum()
        .sort_values("votos", ascending=False)
    )
    cand_total["participacao"] = cand_total["votos"] / cand_total["votos"].sum()
    return cand_total

def desempenho_candidato_bairro(ver_long, candidato):
    base = ver_long.copy()
    total_bairro = (
        base.groupby("bairro_norm", as_index=False)["votos"]
        .sum()
        .rename(columns={"votos": "votos_totais_bairro_vereador"})
    )

    cand = (
        base[base["CANDIDATO"] == candidato]
        .groupby("bairro_norm", as_index=False)["votos"]
        .sum()
        .rename(columns={"votos": "votos_candidato"})
    )

    out = total_bairro.merge(cand, on="bairro_norm", how="left")
    out["votos_candidato"] = out["votos_candidato"].fillna(0)
    out["share_bairro"] = np.where(
        out["votos_totais_bairro_vereador"] > 0,
        out["votos_candidato"] / out["votos_totais_bairro_vereador"],
        0
    )
    return out

# =========================
# APP
# =========================
st.title("Dashboard Inteligente — Votação 2024 em Tuntum")
st.caption(
    "Painel exploratório para identificar força eleitoral, competitividade por bairro, "
    "abstenção e regiões com maior potencial para as próximas eleições."
)

base_sec, ver_long = carregar_dados()
bairros = agregar_bairros(base_sec)
cand_total = ranking_vereador(ver_long)

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Filtros estratégicos")
visao = st.sidebar.radio(
    "Escolha a visão do painel:",
    ["Prefeito 2024", "Vereadores 2024", "Exploração Territorial"]
)

bairro_escolhido = st.sidebar.selectbox(
    "Filtrar bairro",
    ["Todos"] + sorted(bairros["bairro"].dropna().unique().tolist())
)

if bairro_escolhido != "Todos":
    bairro_norm_escolhido = norm_text(bairro_escolhido)
    base_sec_f = base_sec[base_sec["bairro_norm"] == bairro_norm_escolhido].copy()
    ver_long_f = ver_long[ver_long["bairro_norm"] == bairro_norm_escolhido].copy()
    bairros_f = bairros[bairros["bairro_norm"] == bairro_norm_escolhido].copy()
else:
    base_sec_f = base_sec.copy()
    ver_long_f = ver_long.copy()
    bairros_f = bairros.copy()

# =========================
# KPIs
# =========================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Seções analisadas", int(base_sec_f["sec_key"].nunique()))
col2.metric("Eleitores aptos", f"{int(base_sec_f['eleitores_aptos'].sum()):,}".replace(",", "."))
col3.metric("Comparecimento", f"{int(base_sec_f['comparecimento'].sum()):,}".replace(",", "."))
col4.metric("Abstenções", f"{int(base_sec_f['abstencao'].sum()):,}".replace(",", "."))

st.divider()

# =========================
# VISÃO PREFEITO
# =========================
if visao == "Prefeito 2024":
    pref_bairro = (
        base_sec_f.groupby(["bairro_norm", "BAIRRO"], as_index=False)
        .agg(
            FERNANDO=("FERNANDO", "sum"),
            TEMA=("TEMA", "sum"),
            eleitores=("eleitores_aptos", "sum"),
            comparecimento=("comparecimento", "sum"),
            abstencao=("abstencao", "sum"),
        )
    )
    pref_bairro["validos"] = pref_bairro["FERNANDO"] + pref_bairro["TEMA"]
    pref_bairro["share_fernando"] = np.where(pref_bairro["validos"] > 0, pref_bairro["FERNANDO"] / pref_bairro["validos"], 0)
    pref_bairro["share_tema"] = np.where(pref_bairro["validos"] > 0, pref_bairro["TEMA"] / pref_bairro["validos"], 0)
    pref_bairro["margem_abs"] = (pref_bairro["FERNANDO"] - pref_bairro["TEMA"]).abs()
    pref_bairro["competitividade"] = np.where(pref_bairro["validos"] > 0, 1 - (pref_bairro["margem_abs"] / pref_bairro["validos"]), 0)

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            pref_bairro.sort_values("validos", ascending=False),
            x="BAIRRO",
            y=["FERNANDO", "TEMA"],
            barmode="group",
            title="Comparação por bairro — prefeito"
        )
        fig.update_layout(xaxis_title="Bairro", yaxis_title="Votos")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.scatter(
            pref_bairro,
            x="abstencao",
            y="competitividade",
            size="eleitores",
            hover_name="BAIRRO",
            title="Bairros mais estratégicos: abstenção x competitividade"
        )
        fig.update_layout(
            xaxis_title="Abstenções",
            yaxis_title="Competitividade (quanto maior, mais disputado)"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tabela estratégica por bairro")
    mostrar = pref_bairro.copy()
    mostrar["taxa_comparecimento"] = np.where(
        mostrar["eleitores"] > 0,
        mostrar["comparecimento"] / mostrar["eleitores"],
        0
    )
    mostrar = mostrar[[
        "BAIRRO", "FERNANDO", "TEMA", "eleitores", "comparecimento",
        "abstencao", "taxa_comparecimento", "competitividade"
    ]].sort_values(["competitividade", "abstencao"], ascending=[False, False])

    st.dataframe(
        mostrar.style.format({
            "taxa_comparecimento": "{:.1%}",
            "competitividade": "{:.1%}",
        }),
        use_container_width=True
    )

# =========================
# VISÃO VEREADORES
# =========================
elif visao == "Vereadores 2024":
    candidato_escolhido = st.sidebar.selectbox(
        "Escolha um candidato a vereador",
        cand_total["CANDIDATO"].tolist()
    )

    cand_bairro = desempenho_candidato_bairro(ver_long_f, candidato_escolhido)
    mapa_bairro = (
        base_sec_f.groupby(["bairro_norm", "BAIRRO"], as_index=False)
        .agg(
            eleitores=("eleitores_aptos", "sum"),
            comparecimento=("comparecimento", "sum"),
            abstencao=("abstencao", "sum")
        )
    )

    cand_bairro = cand_bairro.merge(
        mapa_bairro,
        on="bairro_norm",
        how="left"
    )
    cand_bairro["BAIRRO"] = cand_bairro["BAIRRO"].fillna(cand_bairro["bairro_norm"])

    cand_bairro["indice_expansao"] = (
        0.40 * score_norm(cand_bairro["abstencao"]) +
        0.35 * score_norm(cand_bairro["eleitores"]) +
        0.25 * (1 - score_norm(cand_bairro["share_bairro"]))
    )

    total_candidato = int(cand_total.loc[cand_total["CANDIDATO"] == candidato_escolhido, "votos"].iloc[0])

    a1, a2, a3 = st.columns(3)
    a1.metric("Votos totais do candidato", f"{total_candidato:,}".replace(",", "."))
    a2.metric(
        "Melhor share em bairro",
        f"{cand_bairro['share_bairro'].max():.1%}"
    )
    a3.metric(
        "Maior oportunidade de expansão",
        cand_bairro.sort_values("indice_expansao", ascending=False)["BAIRRO"].iloc[0]
    )

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            cand_bairro.sort_values("votos_candidato", ascending=False),
            x="BAIRRO",
            y="votos_candidato",
            title=f"Votos de {candidato_escolhido} por bairro"
        )
        fig.update_layout(xaxis_title="Bairro", yaxis_title="Votos")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.scatter(
            cand_bairro,
            x="share_bairro",
            y="indice_expansao",
            size="eleitores",
            hover_name="BAIRRO",
            title="Força atual x potencial de crescimento"
        )
        fig.update_layout(
            xaxis_title="Participação do candidato no bairro",
            yaxis_title="Índice de expansão"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Leitura estratégica")
    top_forca = cand_bairro.sort_values("share_bairro", ascending=False).head(5)
    top_exp = cand_bairro.sort_values("indice_expansao", ascending=False).head(5)

    e1, e2 = st.columns(2)
    with e1:
        st.markdown("**Bairros onde o candidato já é forte**")
        st.dataframe(
            top_forca[["BAIRRO", "votos_candidato", "share_bairro", "eleitores", "abstencao"]]
            .style.format({"share_bairro": "{:.1%}"}),
            use_container_width=True
        )

    with e2:
        st.markdown("**Bairros onde vale investir expansão**")
        st.dataframe(
            top_exp[["BAIRRO", "votos_candidato", "share_bairro", "eleitores", "abstencao", "indice_expansao"]]
            .style.format({"share_bairro": "{:.1%}", "indice_expansao": "{:.3f}"}),
            use_container_width=True
        )

# =========================
# VISÃO TERRITORIAL
# =========================
else:
    topo = bairros_f.sort_values("indice_oportunidade", ascending=False)

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            topo.head(15).sort_values("indice_oportunidade", ascending=True),
            x="indice_oportunidade",
            y="bairro",
            orientation="h",
            title="Top 15 bairros com maior oportunidade eleitoral"
        )
        fig.update_layout(xaxis_title="Índice de oportunidade", yaxis_title="Bairro")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.scatter(
            topo,
            x="eleitores",
            y="abstencao",
            size="competitividade",
            hover_name="bairro",
            title="Peso eleitoral x abstenção"
        )
        fig.update_layout(
            xaxis_title="Eleitores aptos",
            yaxis_title="Abstenções"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Bairros prioritários para próxima eleição")
    st.dataframe(
        topo[[
            "bairro", "secoes", "eleitores", "comparecimento", "abstencao",
            "turnout", "competitividade", "indice_oportunidade",
            "lider_prefeito"
        ]]
        .sort_values("indice_oportunidade", ascending=False)
        .style.format({
            "turnout": "{:.1%}",
            "competitividade": "{:.1%}",
            "indice_oportunidade": "{:.3f}",
        }),
        use_container_width=True
    )

    st.info(
        "Leitura do índice de oportunidade: bairros com muitos eleitores, "
        "abstenção relevante e disputa apertada tendem a ser mais estratégicos "
        "para ações de campo, comunicação segmentada e mobilização."
    )

st.divider()
st.markdown(
    """
**Próximo nível recomendado**
- adicionar resultado por zona/localidade rural x urbana;
- incluir histórico 2020/2022/2024 para tendência;
- geocodificar corretamente os locais de votação para mapa real;
- inserir pesquisa qualitativa e perfil social por região para prever expansão.
"""
)
