"""
Compara a tendência observada de alfabetização municipal (2023 -> 2024)
contra a meta oficial de 2025, respondendo à pergunta de negócio "como
identificar municípios que podem não atingir metas futuras?".

"""

import pandas as pd


def calcular_taxa_por_municipio_ano(df: pd.DataFrame, coluna_elegibilidade: str = "elegivel_modelagem") -> pd.DataFrame:
    """
    Calcula a taxa de alfabetização observada por município e ano.
    """
    df_elegivel = df[df[coluna_elegibilidade] == 1]

    taxa = df_elegivel.groupby(["id_municipio", "ano"]).agg(
        taxa_alfabetizacao=("alfabetizado", "mean"),
        qtd_alunos=("alfabetizado", "size"),
    ).reset_index()


    taxa["taxa_alfabetizacao"] = taxa["taxa_alfabetizacao"] * 100

    return taxa


def construir_tabela_tendencia_meta(
    df: pd.DataFrame,
    coluna_elegibilidade: str = "elegivel_modelagem",
    minimo_alunos_por_ano: int = 30,
) -> pd.DataFrame:
    """
    Monta a tabela completa: taxa de 2023, taxa de 2024, variação
    observada, meta de 2025, diferença até a meta e uma classificação
    de risco baseada no ritmo observado.

    """
    taxa = calcular_taxa_por_municipio_ano(df, coluna_elegibilidade)

    pivot_taxa = taxa.pivot(index="id_municipio", columns="ano", values="taxa_alfabetizacao")
    pivot_taxa.columns = [f"taxa_{int(c)}" for c in pivot_taxa.columns]

    pivot_qtd = taxa.pivot(index="id_municipio", columns="ano", values="qtd_alunos")
    pivot_qtd.columns = [f"qtd_alunos_{int(c)}" for c in pivot_qtd.columns]

    pivot = pivot_taxa.join(pivot_qtd).reset_index()

    # Precisa ter os dois anos para calcular tendência
    pivot = pivot.dropna(subset=["taxa_2023", "taxa_2024"])

    # Filtro de amostra mínima em AMBOS os anos
    pivot = pivot[
        (pivot["qtd_alunos_2023"] >= minimo_alunos_por_ano)
        & (pivot["qtd_alunos_2024"] >= minimo_alunos_por_ano)
    ]

    pivot["variacao_anual"] = pivot["taxa_2024"] - pivot["taxa_2023"]

    # Meta e referência geográfica: valores fixos por município, então
    # 'first' pega qualquer linha sem risco de inconsistência.
    referencia = df.groupby("id_municipio").agg(
        nome_municipio=("nome_municipio", "first"),
        uf=("uf", "first"),
        meta_municipio_2025=("meta_municipio_2025", "first"),
    ).reset_index()

    tabela = pivot.merge(referencia, on="id_municipio", how="left")

    tabela = tabela.dropna(subset=["meta_municipio_2025"])

    tabela["diferenca_para_meta"] = tabela["taxa_2024"] - tabela["meta_municipio_2025"]

    def _classificar_risco(linha):
        if linha["diferenca_para_meta"] >= 0:
            return "Já superou a meta"
        if linha["variacao_anual"] <= 0:
            return "Risco alto (estagnado ou piorando)"
        # Quanto do caminho até a meta seria coberto em 1 ano no ritmo atual
        cobertura_no_ritmo_atual = linha["variacao_anual"] / abs(linha["diferenca_para_meta"])
        if cobertura_no_ritmo_atual >= 1:
            return "No ritmo (deve atingir a meta)"
        elif cobertura_no_ritmo_atual >= 0.5:
            return "Risco moderado (ritmo insuficiente)"
        else:
            return "Risco alto (ritmo muito lento)"

    tabela["classificacao_risco"] = tabela.apply(_classificar_risco, axis=1)

    tabela = tabela.sort_values("diferenca_para_meta")

    colunas_ordem = [
        "id_municipio", "nome_municipio", "uf",
        "qtd_alunos_2023", "qtd_alunos_2024",
        "taxa_2023", "taxa_2024", "variacao_anual",
        "meta_municipio_2025", "diferenca_para_meta", "classificacao_risco",
    ]
    return tabela[colunas_ordem].reset_index(drop=True)


def resumo_classificacao_risco(tabela_tendencia: pd.DataFrame) -> pd.DataFrame:
    """
    Conta quantos municípios caem em cada categoria de risco.
    """
    contagem = tabela_tendencia["classificacao_risco"].value_counts().reset_index()
    contagem.columns = ["classificacao_risco", "qtd_municipios"]
    contagem["pct"] = (contagem["qtd_municipios"] / contagem["qtd_municipios"].sum() * 100).round(1)
    return contagem