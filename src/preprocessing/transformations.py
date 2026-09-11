"""
Pré-processamento da camada Gold para a modelagem supervisionada de
`alfabetizado`.

Este módulo contém apenas transformações.

As decisões encapsuladas aqui foram justificadas na análise
exploratória (notebooks/EDA.ipynb).
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# Features finais do modelo.

FEATURES_NUMERICAS = [
    "log_populacao",
    "pct_pes_pob",
    "pct_pes_baixa_renda",
    "pct_pes_acima_meio_sm",
    "meta_municipio_2025",
    "meta_uf_2025",
]

FEATURES_CATEGORICAS = [
    "rede",
    "uf",
]

COLUNA_ALVO = "alfabetizado"

# Mantidas para chaves de agregação e auditoria, nunca como feature.
COLUNAS_CHAVE = ["id_aluno", "id_municipio", "ano"]


def filtrar_registros_invalidos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove os registros residuais identificados na EDA:
    - rede == 4 (Privada): 24 registros, volume insuficiente.
    - caderno == 43: 12 registros, versão residual da prova.
    Mantém apenas elegivel_modelagem == 1 (aluno respondeu ao caderno
    e tem proficiência aferida).
    """
    antes = len(df)

    df_filtrado = df[
        (df["elegivel_modelagem"] == 1)
        & (df["rede"] != 4)
        & (df["caderno"] != 43)
    ].copy()

    depois = len(df_filtrado)
    print(f"Registros antes do filtro: {antes:,}")
    print(f"Registros depois do filtro: {depois:,}")
    print(f"Registros removidos: {antes - depois:,}")

    return df_filtrado


def calcular_features_derivadas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula as features derivadas definidas na EDA:
    - log_populacao: log(1 + populacao), para reduzir a assimetria
      extrema da distribuição de população.
    - Indicadores do CadÚnico normalizados por população, com clip em
      1.0 (afeta 2 municípios onde a contagem administrativa do
      CadÚnico supera levemente a estimativa populacional do IBGE).
    """
    df = df.copy()

    df["log_populacao"] = np.log1p(df["populacao"])

    mapa_normalizacao = {
        "qtd_pes_pob": "pct_pes_pob",
        "qtd_pes_baixa_renda": "pct_pes_baixa_renda",
        "qtd_pes_acima_meio_sm": "pct_pes_acima_meio_sm",
    }

    for coluna_absoluta, coluna_pct in mapa_normalizacao.items():
        df[coluna_pct] = (df[coluna_absoluta] / df["populacao"]).clip(upper=1.0)

    return df


def selecionar_colunas_modelagem(df: pd.DataFrame) -> pd.DataFrame:
    """
    Seleciona apenas chaves, features e alvo.
    """
    colunas = COLUNAS_CHAVE + FEATURES_NUMERICAS + FEATURES_CATEGORICAS + [COLUNA_ALVO]
    return df[colunas].copy()


def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executa, em ordem, as três etapas de preparação: filtro de
    registros inválidos, cálculo de features derivadas e seleção
    final de colunas.
    """
    df = filtrar_registros_invalidos(df)
    df = calcular_features_derivadas(df)
    df = selecionar_colunas_modelagem(df)
    return df


def construir_preprocessador() -> ColumnTransformer:
    """
    Monta o ColumnTransformer a ser integrado ao pipeline do modelo.

    Numéricas: imputação pela mediana (necessária para
    meta_municipio_2025 e meta_uf_2025, que têm nulos para municípios
    sem meta definida) + padronização.

    Categóricas: one-hot encoding com drop='first', para evitar a
    armadilha da variável dummy em `rede` e reduzir dimensionalidade
    em `uf`.
    """
    transformador_numerico = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    transformador_categorico = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(drop="first", handle_unknown="ignore")),
    ])

    preprocessador = ColumnTransformer(transformers=[
        ("num", transformador_numerico, FEATURES_NUMERICAS),
        ("cat", transformador_categorico, FEATURES_CATEGORICAS),
    ])

    return preprocessador