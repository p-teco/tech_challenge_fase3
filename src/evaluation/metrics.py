"""
Avaliação e comparação dos modelos treinados, sobre o conjunto de
teste (ano 2024) definido pelo split temporal.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


# Threshold de decisão escolhido a partir do sweep de thresholds
# (ver notebooks/Modelagem.ipynb): ponto onde o F1 macro atinge seu
# pico, equilibrando recall e precisão entre as duas classes. 
THRESHOLD_DECISAO = 0.55


def prever_com_threshold(pipeline, X: pd.DataFrame, threshold: float = THRESHOLD_DECISAO) -> np.ndarray:
    """
    Gera previsões binárias usando o threshold escolhido.
    """
    y_proba = pipeline.predict_proba(X)[:, 1]
    return (y_proba >= threshold).astype(int)


def avaliar_modelo(pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """
    Calcula as métricas de classificação de um pipeline treinado sobre
    o conjunto de teste.
    """
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    metricas = {
        "acuracia": accuracy_score(y_test, y_pred),
        "precisao": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }

    return metricas


def comparar_modelos(pipelines: dict, X_test: pd.DataFrame, y_test: pd.Series) -> pd.DataFrame:
    """
    Avalia todos os pipelines treinados e retorna uma tabela
    comparativa, ordenada pelo ROC-AUC (do melhor para o pior).
    """
    resultados = {}

    for nome, pipeline in pipelines.items():
        resultados[nome] = avaliar_modelo(pipeline, X_test, y_test)

    tabela = pd.DataFrame(resultados).T
    tabela = tabela.sort_values("roc_auc", ascending=False)
    tabela = tabela.round(4)

    return tabela


def plotar_matriz_confusao(pipeline, X_test: pd.DataFrame, y_test: pd.Series, nome: str,
                             threshold: float = THRESHOLD_DECISAO, caminho_saida: str = None):
    """
    Plota a matriz de confusão de um modelo específico, com contagens
    absolutas e percentuais.
    """
    y_pred = prever_com_threshold(pipeline, X_test, threshold)
    matriz = confusion_matrix(y_test, y_pred)
    matriz_pct = matriz / matriz.sum() * 100

    rotulos = [f"{v:,}\n({p:.1f}%)" for v, p in zip(matriz.flatten(), matriz_pct.flatten())]
    rotulos = [rotulos[i:i + 2] for i in range(0, len(rotulos), 2)]

    plt.figure(figsize=(5, 4))
    sns.heatmap(matriz, annot=rotulos, fmt="", cmap="Blues",
                xticklabels=["Não alfabetizado", "Alfabetizado"],
                yticklabels=["Não alfabetizado", "Alfabetizado"])
    plt.title(f"Matriz de confusão -- {nome}")
    plt.xlabel("Previsto")
    plt.ylabel("Real")
    plt.tight_layout()

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120)

    plt.show()


def sweep_thresholds(pipeline, X_test: pd.DataFrame, y_test: pd.Series, thresholds=None) -> pd.DataFrame:
    """
    Testa diferentes pontos de corte (threshold) sobre a probabilidade
    prevista de alfabetizado=1.
    """
    import numpy as np

    if thresholds is None:
        thresholds = np.arange(0.30, 0.71, 0.05)

    y_proba = pipeline.predict_proba(X_test)[:, 1]

    linhas = []
    for limiar in thresholds:
        y_pred = (y_proba >= limiar).astype(int)

        linhas.append({
            "threshold": round(float(limiar), 2),
            "recall_nao_alfabetizado": recall_score(y_test, y_pred, pos_label=0),
            "precisao_nao_alfabetizado": precision_score(y_test, y_pred, pos_label=0, zero_division=0),
            "recall_alfabetizado": recall_score(y_test, y_pred, pos_label=1),
            "precisao_alfabetizado": precision_score(y_test, y_pred, pos_label=1, zero_division=0),
            "acuracia": accuracy_score(y_test, y_pred),
            "f1_macro": f1_score(y_test, y_pred, average="macro"),
        })

    return pd.DataFrame(linhas).round(4)


def plotar_sweep_thresholds(tabela_sweep: pd.DataFrame, nome: str, caminho_saida: str = None):
    """
    Plota recall e precisão da classe "não alfabetizado" em função do
    threshold, para visualizar onde fica o ponto de equilíbrio
    desejado antes de escolher um limiar final.
    """
    plt.figure(figsize=(7, 5))
    plt.plot(tabela_sweep["threshold"], tabela_sweep["recall_nao_alfabetizado"],
              marker="o", label="Recall (não alfabetizado)")
    plt.plot(tabela_sweep["threshold"], tabela_sweep["precisao_nao_alfabetizado"],
              marker="o", label="Precisão (não alfabetizado)")
    plt.axvline(0.5, color="gray", linestyle="--", alpha=0.5, label="Threshold padrão (0.5)")
    plt.xlabel("Threshold (probabilidade mínima para prever 'alfabetizado')")
    plt.ylabel("Score")
    plt.title(f"Trade-off recall/precisão por threshold -- {nome}")
    plt.legend()
    plt.ylim(0, 1)
    plt.tight_layout()

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120)

    plt.show()


def relatorio_completo(pipeline, X_test: pd.DataFrame, y_test: pd.Series, nome: str,
                         threshold: float = THRESHOLD_DECISAO):
    """
    Imprime o classification_report completo do Scikit-learn.
    """
    y_pred = prever_com_threshold(pipeline, X_test, threshold)
    print(f"Relatório de classificação -- {nome} (threshold={threshold})")
    print(classification_report(y_test, y_pred, target_names=["Não alfabetizado", "Alfabetizado"]))