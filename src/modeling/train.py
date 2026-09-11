"""
Split temporal, construção de pipeline e treino, para a modelagem supervisionada de
`alfabetizado`.

As transformações de pré-processamento (src/preprocessing/transformations.py)
são incorporadas ao Pipeline junto com o algoritmo. O treino acontece sempre e
somente sobre os dados de 2023, nunca sobre 2024 que será usado para teste, para não vazar informações.
"""

import pandas as pd
from sklearn.pipeline import Pipeline

from src.preprocessing.transformations import (
    construir_preprocessador,
    FEATURES_NUMERICAS,
    FEATURES_CATEGORICAS,
    COLUNA_ALVO,
    COLUNAS_CHAVE,
)


def split_temporal(df: pd.DataFrame, ano_treino: int = 2023, ano_teste: int = 2024):
    """
    Separa treino e teste por ano, em vez de split aleatório.

    Justificativa (ver EDA.ipynb): a taxa de alfabetização observada é
    estável entre 2023 e 2024 (58,39% -> 59,78%), o que sustenta essa
    escolha. Um split temporal simula a situação real de uso do
    modelo.

    Retorna X_train, X_test, y_train, y_test e também as colunas-chave
    do conjunto de teste (chaves_teste), preservadas separadamente
    para permitir agregações posteriores por município sem que essas
    colunas sejam usadas como feature.
    """
    features = FEATURES_NUMERICAS + FEATURES_CATEGORICAS

    df_treino = df[df["ano"] == ano_treino]
    df_teste = df[df["ano"] == ano_teste]

    X_train = df_treino[features].copy()
    y_train = df_treino[COLUNA_ALVO].copy()

    X_test = df_teste[features].copy()
    y_test = df_teste[COLUNA_ALVO].copy()

    chaves_teste = df_teste[COLUNAS_CHAVE].copy()

    print(f"Treino ({ano_treino}): {len(X_train):,} registros")
    print(f"Teste  ({ano_teste}): {len(X_test):,} registros")

    return X_train, X_test, y_train, y_test, chaves_teste


def construir_pipeline(modelo) -> Pipeline:
    """
    Monta o pipeline completo: pré-processamento + algoritmo.

    Recebe o algoritmo do Scikit-learn e retorna um Pipeline pronto para treino.
    """
    preprocessador = construir_preprocessador()

    pipeline = Pipeline(steps=[
        ("preprocessador", preprocessador),
        ("modelo", modelo),
    ])

    return pipeline


def treinar_modelos(modelos: dict, X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    """
    Treina um Pipeline (pré-processamento + algoritmo) para cada
    modelo em `modelos`, permitindo comparar algoritmos diferentes sob
    exatamente o mesmo pré-processamento e os mesmos dados de treino.

    `modelos` deve ser um dicionário neste formato:
        {"Regressão Logística": LogisticRegression(...),
         "Random Forest": RandomForestClassifier(...)}

    Retorna um dicionário {nome: pipeline_treinado}.
    """
    pipelines_treinados = {}

    for nome, modelo in modelos.items():
        print(f"Treinando: {nome}...")
        pipeline = construir_pipeline(modelo)
        pipeline.fit(X_train, y_train)
        pipelines_treinados[nome] = pipeline
        print(f"  Concluído.")

    return pipelines_treinados