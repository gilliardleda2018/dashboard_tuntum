# Dashboard Eleitoral Inteligente — Tuntum MA

Sistema de análise territorial da votação municipal de Tuntum-MA com visualização geográfica, indicadores estratégicos e análise híbrida com inteligência artificial.

## Visão geral

Este projeto foi desenvolvido para apoiar leitura estratégica de dados eleitorais por localidade, ponto de votação e zona territorial, integrando análise quantitativa, georreferenciamento e inteligência artificial aplicada.

## Tecnologias utilizadas

* Python
* Streamlit
* Pandas
* NumPy
* Plotly
* GeoPandas
* OpenAI API

## Principais funcionalidades

* análise por localidade
* análise por ponto de votação
* separação zona urbana / zona rural
* índice de oportunidade eleitoral
* competitividade territorial
* mapa geográfico interativo
* recomendações automáticas
* IA local
* IA online
* IA híbrida
* perguntas dinâmicas ao painel

## Estrutura do projeto

```text id="g2f8cn"
dashboard-eleitoral-tuntum-ia/
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── data/
├── docs/
├── assets/
├── outputs/
├── notebooks/
└── tests/
```

## Executar localmente

```bash id="l5w7pr"
pip install -r requirements.txt
python -m streamlit run app.py
```

## Configurar API OpenAI

```powershell id="n4m1tb"
setx OPENAI_API_KEY "SUA_CHAVE_AQUI"
```

## Modos de IA disponíveis

* IA local
* IA online
* IA híbrida

## Aplicações práticas

* leitura estratégica de território
* apoio à decisão política
* priorização de agenda
* mobilização territorial
* análise de competitividade

## Autor

Gilliard Léda
MIT License

Copyright (c) 2026 Gilliard Léda

Permission is hereby granted, free of charge, to any person obtaining a copy...
