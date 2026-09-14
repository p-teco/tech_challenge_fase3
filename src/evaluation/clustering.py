"""
Clustering municipal para responder à pergunta de negócio "quais
regiões possuem padrões semelhantes?".

Diferente do modelo supervisionado, aqui o objetivo não é prever
alfabetizado a nível de aluno, é agrupar municípios com perfil
parecido (taxa de alfabetização observada + contexto socioeconômico e
territorial). 
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


COLUNAS_PERFIL = [
    "taxa_alfabetizacao",
    "pct_pes_pob",
    "pct_pes_baixa_renda",
    "pct_pes_acima_meio_sm",
    "log_populacao",
]


def construir_perfil_municipal(df_preparado: pd.DataFrame) -> pd.DataFrame:
    """
    Constrói um perfil resumido por município, combinando os dois anos
    disponíveis (2023 e 2024) em uma média.
    """
    perfil = df_preparado.groupby("id_municipio").agg(
        taxa_alfabetizacao=("alfabetizado", "mean"),
        pct_pes_pob=("pct_pes_pob", "mean"),
        pct_pes_baixa_renda=("pct_pes_baixa_renda", "mean"),
        pct_pes_acima_meio_sm=("pct_pes_acima_meio_sm", "mean"),
        log_populacao=("log_populacao", "mean"),
        nome_municipio=("nome_municipio", "first"),
        uf=("uf", "first"),
        qtd_alunos=("alfabetizado", "size"),
    ).reset_index()

    return perfil


def testar_quantidade_clusters(perfil: pd.DataFrame, k_min: int = 2, k_max: int = 10, random_state: int = 42) -> pd.DataFrame:
    """
    Testa diferentes valores de k.
    """
    X = perfil[COLUNAS_PERFIL].copy()
    X_padronizado = StandardScaler().fit_transform(X)

    resultados = []
    for k in range(k_min, k_max + 1):
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(X_padronizado)

        resultados.append({
            "k": k,
            "inercia": kmeans.inertia_,
            "silhouette": silhouette_score(X_padronizado, labels),
        })

    return pd.DataFrame(resultados)


def plotar_escolha_k(tabela_k: pd.DataFrame, caminho_saida: str = None):
    """
    Plota inércia (método do cotovelo) e silhouette score lado a lado,
    para apoiar visualmente a escolha do número de clusters.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(tabela_k["k"], tabela_k["inercia"], marker="o")
    axes[0].set_xlabel("Número de clusters (k)")
    axes[0].set_ylabel("Inércia")
    axes[0].set_title("Método do cotovelo")

    axes[1].plot(tabela_k["k"], tabela_k["silhouette"], marker="o", color="orange")
    axes[1].set_xlabel("Número de clusters (k)")
    axes[1].set_ylabel("Silhouette score")
    axes[1].set_title("Silhouette score por k")

    plt.tight_layout()

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120)

    plt.show()


def aplicar_clustering(perfil: pd.DataFrame, k: int, random_state: int = 42) -> pd.DataFrame:
    """
    Aplica o KMeans com o k escolhido e retorna o perfil municipal com
    a coluna 'cluster' adicionada.
    """
    perfil = perfil.copy()

    X = perfil[COLUNAS_PERFIL]
    X_padronizado = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    perfil["cluster"] = kmeans.fit_predict(X_padronizado)

    return perfil


def descrever_clusters(perfil_com_cluster: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna a média de cada variável do perfil por cluster, e a
    contagem de municípios em cada um.
    """
    resumo = perfil_com_cluster.groupby("cluster")[COLUNAS_PERFIL].mean().round(3)
    resumo["qtd_municipios"] = perfil_com_cluster.groupby("cluster").size()
    return resumo.sort_values("taxa_alfabetizacao")


def plotar_distribuicao_geografica_clusters(perfil_com_cluster: pd.DataFrame, caminho_saida: str = None):
    """
    Plota a quantidade de municípios de cada cluster, separado por UF.
    """
    tabela_cruzada = pd.crosstab(perfil_com_cluster["uf"], perfil_com_cluster["cluster"])

    plt.figure(figsize=(10, 8))
    sns.heatmap(tabela_cruzada, annot=True, fmt="d", cmap="Blues")
    plt.title("Distribuição de municípios por cluster e UF")
    plt.xlabel("Cluster")
    plt.ylabel("UF")
    plt.tight_layout()

    if caminho_saida:
        plt.savefig(caminho_saida, dpi=120)

    plt.show()