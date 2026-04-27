from pathlib import Path
import textwrap

readme = r"""
# Dashboard Eleitoral Inteligente — Tuntum MA

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![GeoPandas](https://img.shields.io/badge/GeoPandas-Geospatial-green)
![Plotly](https://img.shields.io/badge/Plotly-Visualização-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## Dashboard territorial inteligente para análise da votação municipal de **Tuntum-MA**, integrando dados eleitorais, georreferenciamento, indicadores estratégicos e inteligência artificial híbrida.

---

## Visão geral

## Este projeto foi desenvolvido para transformar dados eleitorais em leitura estratégica territorial.

## O painel permite analisar a votação por:

- localidade;
- ponto de votação;
- seção eleitoral;
- zona urbana;
- zona rural;
- candidato;
- abstenção;
- competitividade;
- índice de oportunidade.

## Além da visualização dos dados, o projeto inclui uma camada de **IA local, online e híbrida**, permitindo perguntas dinâmicas ao painel.

---

## Objetivo

## Ajudar na identificação de territórios com maior potencial de atuação eleitoral, considerando:

- concentração de eleitores;
- volume de abstenção;
- disputa acirrada;
- liderança local;
- pontos de votação estratégicos;
- diferença entre zona urbana e zona rural.

---

## Demonstração visual

> Adicione aqui prints do dashboard.

Sugestões de imagens:


assets/dashboard_home.png
assets/mapa_tuntum.png
assets/zona_rural.png
assets/analise_ia.png


Principais funcionalidades
Visão geral da eleição
KPIs principais;
total de votos por candidato;
percentual geral da votação;
gráfico de barras;
gráfico de pizza.
Mapa territorial
malha geográfica de Tuntum em GeoJSON;
pontos das localidades;
liderança local;
índice de oportunidade;
informações por hover no mapa.
Análise por localidade
comparação Fernando x Tema;
saldo de votos;
participação percentual;
abstenção;
competitividade;
índice de oportunidade;
recomendações práticas.
Análise por ponto de votação
agrupamento por escola/prédio;
seções associadas;
localidades atendidas;
votos por candidato;
pontos mais estratégicos.
Organização territorial

O painel separa as análises em:

Zona Urbana;
Zona Rural.

Cada aba possui:

KPIs próprios;
gráficos comparativos;
tabela de seções;
resumo por ponto de votação.
Inteligência artificial híbrida

O painel possui três modos de IA:

IA Local: gera análise estratégica sem custo de API;
IA Online: usa API da OpenAI;
IA Híbrida: tenta API online e, em caso de erro, usa IA local automaticamente.

A IA responde perguntas como:

Quais localidades são mais promissoras?
Onde há maior risco?
Onde Fernando pode crescer?
Onde Tema pode crescer?
Quais pontos de votação são prioritários?
Qual a diferença entre zona urbana e zona rural?
Índice de oportunidade

O índice de oportunidade é calculado com base em três fatores:

Índice = 0.45 * abstenção normalizada
       + 0.35 * eleitorado normalizado
       + 0.20 * competitividade normalizada
Interpretação

Quanto maior o índice, maior o potencial estratégico da localidade.

Territórios com alto índice tendem a reunir:

muitos eleitores;
abstenção relevante;
disputa competitiva.
Competitividade eleitoral

A competitividade mede o quanto a votação foi equilibrada entre os candidatos.

competitividade = 1 - (diferença absoluta entre os candidatos / votos válidos)

Quanto mais próximo de 1, mais disputada é a localidade.

Tecnologias utilizadas
Python
Streamlit
Pandas
NumPy
Plotly
GeoPandas
OpenAI API
Estrutura do projeto
dashboard-eleitoral-tuntum-ia/
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── data/
│   ├── SEÇÕES.csv
│   ├── SEÇÕES(1).csv
│   ├── VOTACAO_PREFEITO.csv
│   └── tuntum_malha.geojson
├── docs/
├── assets/
├── outputs/
├── notebooks/
└── tests/
Instalação

## Clone o repositório:

git clone https://github.com/gilliardleda2018/dashboard-eleitoral-tuntum-ia.git

## Entre na pasta:

cd dashboard-eleitoral-tuntum-ia

## Crie um ambiente virtual:

python -m venv .venv

Ative o ambiente no Windows:

.\.venv\Scripts\Activate.ps1

## Instale as dependências:

pip install -r requirements.txt
Executar o dashboard
python -m streamlit run app.py

O painel abrirá no navegador, normalmente em:

http://localhost:8501
Configurar IA Online

Para usar a API da OpenAI, configure a variável de ambiente:

setx OPENAI_API_KEY "SUA_CHAVE_AQUI"

Depois feche e abra o PowerShell novamente.

## Caso a API esteja sem crédito, use:

## IA Local

ou:

## IA Híbrida
## Dados necessários

## O projeto espera os seguintes arquivos:

SEÇÕES.csv
SEÇÕES(1).csv
VOTACAO_PREFEITO.csv
tuntum_malha.geojson

## Esses arquivos devem estar na pasta esperada pelo app.py.

Possíveis melhorias futuras
integração com dados históricos de 2020 e 2022;
simulação de transferência de votos;
projeção de comparecimento;
modelo preditivo por seção;
clusterização territorial;
geração automática de relatório PDF;
deploy em Streamlit Community Cloud;
autenticação para uso privado.
Aplicações práticas

## Este projeto pode apoiar:

leitura territorial;
planejamento de campanha;
priorização de visitas;
análise de abstenção;
avaliação de desempenho por região;
construção de narrativa estratégica;
organização de inteligência eleitoral.
Observação ética

## Este painel é uma ferramenta de apoio analítico. A interpretação dos resultados deve considerar contexto local, validação de campo, legislação eleitoral e análise humana.

## Autor

Gilliard Léda
Data Scientist | Ciência de Dados aplicada a campanhas eleitorais, gestão pública e inteligência territorial.

GitHub: gilliardleda2018

Licença

Este projeto está licenciado sob a licença MIT.
"""

out = Path("/mnt/data/README_premium_dashboard_tuntum.md")
out.write_text(textwrap.dedent(readme).strip(), encoding="utf-8")
print(out)
