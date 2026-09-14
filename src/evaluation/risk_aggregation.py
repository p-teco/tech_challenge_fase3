"""
Agregação do risco previsto pelo modelo por município -- responde a
pergunta de negócio "quais municípios apresentam maior risco
educacional?".

"""

import pandas as pd

from src.evaluation.metrics import THRESHOLD_DECISAO


def agregar_risco_por_municipio(
    pipeline,
    X_test: pd.DataFrame,
    chaves_teste: pd.DataFrame,
    df_referencia: pd.DataFrame,
    threshold: float = THRESHOLD_DECISAO,
) -> pd.DataFrame:
    """
    Calcula, para cada município presente no conjunto de teste:
    - probabilidade média prevista de NÃO alfabetização (risco médio);
    - percentual de alunos classificados como risco, usando o
      threshold do projeto;
    - quantidade de alunos avaliados naquele município no teste.

    """
    proba_alfabetizado = pipeline.predict_proba(X_test)[:, 1]
    proba_risco = 1 - proba_alfabetizado
    classificado_risco = (proba_alfabetizado < threshold).astype(int)

    base_risco = chaves_teste.copy()
    base_risco["proba_risco"] = proba_risco
    base_risco["classificado_risco"] = classificado_risco

    agregado = base_risco.groupby("id_municipio").agg(
        risco_medio_previsto=("proba_risco", "mean"),
        pct_alunos_classificados_risco=("classificado_risco", "mean"),
        qtd_alunos_avaliados=("proba_risco", "size"),
    ).reset_index()

    agregado["pct_alunos_classificados_risco"] = (agregado["pct_alunos_classificados_risco"] * 100).round(2)
    agregado["risco_medio_previsto"] = (agregado["risco_medio_previsto"] * 100).round(2)

    # Traz nome do município e UF para leitura, sem duplicar linhas
    referencia_municipios = df_referencia[["id_municipio", "nome_municipio", "uf"]].drop_duplicates("id_municipio")
    agregado = agregado.merge(referencia_municipios, on="id_municipio", how="left")

    agregado = agregado.sort_values("risco_medio_previsto", ascending=False).reset_index(drop=True)

    def _classificar_homogeneidade(pct):
        if pct == 0:
            return "Sem risco (nenhum aluno)"
        elif pct == 100:
            return "Risco generalizado (todos os alunos)"
        else:
            return "Risco misto (depende da rede)"

    agregado["categoria_risco"] = agregado["pct_alunos_classificados_risco"].apply(_classificar_homogeneidade)

    colunas_ordem = [
        "id_municipio", "nome_municipio", "uf",
        "risco_medio_previsto", "pct_alunos_classificados_risco", "categoria_risco",
        "qtd_alunos_avaliados",
    ]
    return agregado[colunas_ordem]


def filtrar_municipios_relevantes(tabela_risco: pd.DataFrame, minimo_alunos: int = 30) -> pd.DataFrame:
    """
    Filtra municípios com poucos alunos avaliados no teste, cujo risco
    médio é estatisticamente pouco confiável.
    """
    return tabela_risco[tabela_risco["qtd_alunos_avaliados"] >= minimo_alunos].reset_index(drop=True)