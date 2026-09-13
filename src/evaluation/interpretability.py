"""
Interpretabilidade dos modelos treinados: Feature Importance nativa
(para modelos baseados em árvore) e SHAP (para qualquer modelo,
mostrando direção e magnitude do efeito de cada feature).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def obter_nomes_features(pipeline) -> list:
    """
    Recupera os nomes finais das colunas após o pré-processamento.
    """
    return pipeline.named_steps["preprocessador"].get_feature_names_out()


def importancia_arvore(pipeline, nome: str) -> pd.DataFrame:
    """
    Extrai a Feature Importance nativa de um modelo baseado em árvore
    (Random Forest, Gradient Boosting).
    """
    modelo = pipeline.named_steps["modelo"]

    if not hasattr(modelo, "feature_importances_"):
        raise AttributeError(
            f"{nome} não possui feature_importances_. "
        )

    nomes = obter_nomes_features(pipeline)
    importancias = modelo.feature_importances_

    tabela = pd.DataFrame({
        "feature": nomes,
        "importancia": importancias,
    }).sort_values("importancia", ascending=False).reset_index(drop=True)

    return tabela


def plotar_importancia(tabela_importancia: pd.DataFrame, nome: str, top_n: int = 15, caminho_saida: str = None):
    """
    Plota as top_n features mais importantes, do maior para o menor.
    """
    top = tabela_importancia.head(top_n).sort_values("importancia")

    plt.figure(figsize=(8, 6))
    plt.barh(top["feature"], top["importancia"], color="#4C72B0")
    plt.xlabel("Importância")
    plt.title(f"Top {top_n} features mais importantes -- {nome}")
    plt.tight_layout()

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120)

    plt.show()


def calcular_shap(pipeline, X: pd.DataFrame, tamanho_amostra: int = 500, random_state: int = 42):
    """
    Calcula os valores SHAP para uma amostra de X.
    """
    import shap

    amostra = X.sample(n=min(tamanho_amostra, len(X)), random_state=random_state)

    preprocessador = pipeline.named_steps["preprocessador"]
    modelo = pipeline.named_steps["modelo"]

    X_transformado = preprocessador.transform(amostra)
    nomes_features = obter_nomes_features(pipeline)
    X_transformado_df = pd.DataFrame(X_transformado, columns=nomes_features, index=amostra.index)

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_transformado_df)

    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        shap_values = shap_values[:, :, 1]

    return shap_values, X_transformado_df


def plotar_shap_summary(shap_values, X_transformado_df: pd.DataFrame, caminho_saida: str = None):
    """
    Plota o gráfico resumo do SHAP.
    """
    import shap

    plt.figure()
    shap.summary_plot(shap_values, X_transformado_df, show=False)

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120, bbox_inches="tight")

    plt.show()


def plotar_shap_importancia_media(shap_values, X_transformado_df: pd.DataFrame, caminho_saida: str = None):
    """
    Plota a importância média absoluta de cada feature segundo o
    SHAP.
    """
    import shap

    plt.figure()
    shap.summary_plot(shap_values, X_transformado_df, plot_type="bar", show=False)

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120, bbox_inches="tight")

    plt.show()