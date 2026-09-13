## Descrição das bases utilizadas
 
O projeto usa como fonte central o **Indicador Criança Alfabetizada**,
com os microdados de alunos avaliados em 2023 e 2024 (~3,9 milhões de
registros). Cada linha representa um aluno avaliado em um determinado
ano, com informações de rede de ensino, presença na prova, proficiência
e o resultado final de alfabetização.
 
Como o indicador sozinho não diz muito sobre o *contexto* do aluno,
cruzei essa base com outras três fontes, todas no nível de município:
 
- **População:** (IBGE) Tamanho do município em cada ano.
- **Cadastro Único (CadÚnico):** Indicadores de vulnerabilidade social
  por município, usando a foto de dezembro de cada ano (2023 e 2024).
- **Metas de alfabetização:** Metas oficiais de taxa de alfabetização
  definidas até 2030, em três níveis: nacional, estadual e municipal.
- **RELATORIO_DTB:** Também foi usado a base de referência de municípios do IBGE (RELATORIO_DTB)
para trazer nome do município, UF e região, útil pra qualquer análise
geográfica.
 
**Fontes:**
 
| Base | Fonte |
|---|---|
| Indicador Criança Alfabetizada | [basedosdados.org](https://basedosdados.org/dataset/073a39d4-89cf-4068-b1e8-34ed0d9c0b72?table=e1de7a6a-5038-4e81-89f0-a15f2cc12c9b)|
| População municipal | [basedosdados.org](https://basedosdados.org/dataset/d30222ad-7a5c-4778-a1ec-f0785371d1ca?table=0c279444-165b-41da-92cd-50fd7e66baa1) |
| Malha de municípios (DTB 2024) | [ibge.gov.br](https://www.ibge.gov.br/explica/codigos-dos-municipios.php) |
| Cadastro Único — cadastros e renda per capita | [dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/pessoas-inscritas-no-cadastro-unico-por-faixa-de-renda-per-capita) |

## Como a Gold foi montada

A tabela final (`gold_alfabetizacao.csv`) tem uma linha por aluno por
ano (3.867.999 linhas, 44 colunas), juntando o indicador de
alfabetização com o contexto municipal (população, CadÚnico, metas) por
`id_municipio` e `ano`.
 
#### Decisões que foram tomadas:
 
- **`id_escola` é um código anonimizado** nos microdados de alunos
  não corresponde ao código real de escola usado em outras bases
  públicas (isso é proposital, para proteger a identidade dos alunos).
  Por isso, não foi possível cruzar informação por escola; todo o
  enriquecimento externo ficou no nível de município.
- **`proficiencia` define `alfabetizado` por um corte fixo (743
  pontos)** na escala do Saeb ou seja, é a mesma informação, só que
  em outra forma. Por isso essa coluna existe na base só para conferência,
  e não deve ser usada como variável de entrada do modelo.
- Cerca de 13% dos registros correspondem a alunos que não responderam
  à prova (ausentes ou presentes sem preencher o caderno) esses não
  têm proficiência aferida e não representam um resultado pedagógico
  real. Eles ficam marcados na coluna `elegivel_modelagem`.


  ## Etapas de modelagem

**Filtros aplicados antes da modelagem:**
- Mantidos apenas alunos com `elegivel_modelagem = 1` ou seja, que
  de fato responderam ao caderno e têm proficiência aferida (os
  demais são ausência ou não resposta, uma questão administrativa
  distinta do resultado pedagógico).
- Removidos os 24 registros de `rede = 4` (Privada) e os 12 registros
  de `caderno = 43`, ambos volumes residuais demais para gerar
  qualquer inferência confiável.

**Split treino/teste:** split por
ano **treino em 2023, teste em 2024**. Essa escolha simula a
situação real de uso do modelo de aprender com o passado, validar contra
um período nunca visto e é sustentada pela EDA: a taxa de
alfabetização observada é estável entre os dois anos (58,39% para
59,78%), então não há indício de mudança de metodologia que
invalidasse essa comparação.

**Features utilizadas no modelo final:**
- `log_populacao` log da população municipal, para reduzir a
  assimetria extrema da distribuição (municípios variam de 854 a quase
  12 milhões de habitantes).
- `pct_pes_pob`, `pct_pes_baixa_renda`, `pct_pes_acima_meio_sm` 
  indicadores do CadÚnico normalizados pela população municipal.
- `rede` e `uf` categóricas, com one-hot encoding.

**Features avaliadas e descartadas:**
- `serie` e `caderno` não têm variância útil: `serie` é constante
  (só existe 2ª série na base) e a taxa de alfabetização é praticamente
  idêntica entre as 21 versões válidas de caderno (58,4% : 59,9%),
  indicando que são apenas versões equivalentes da prova.
- `presenca` e `preenchimento_caderno`, dentro do subconjunto elegível
  para modelagem, são constantes (sempre 1) não carregam informação
  útil nesse recorte.
- `proficiencia` define `alfabetizado` por um corte fixo, então seu
  uso como feature seria repetir a própria resposta.
- `peso_aluno` é um peso de ponderação amostral, não uma característica do aluno.
- As metas de alfabetização (`meta_municipio_2025`, `meta_uf_2025`)
  chegaram a ser testadas, mas optei por não usá-las no modelo final. A meta
  provavelmente foi definida pelo MEC a partir do desempenho histórico
  do próprio município, tornando-a um proxy indireto do problema que
  buscamos entender.

O pré-processamento (imputação, padronização, encoding) foi
implementado como um `ColumnTransformer` do Scikit-learn, integrado ao
mesmo `Pipeline` do modelo. Ele é treinado apenas com os dados
de 2023.

## Escolha do algoritmo

Testei quatro algoritmos sob exatamente o mesmo pré-processamento e
os mesmos dados de treino: um baseline ingênuo (`DummyClassifier`),
Regressão Logística, Random Forest e Gradient Boosting.

A comparação usou **ROC-AUC**, não acurácia ou F1 diretos com o
alvo levemente desbalanceado (~59% alfabetizado / 41% não), um
classificador que sempre prevê a classe majoritária já atinge F1 alto
sem ter aprendido nada real. Isso ficou evidente no próprio teste: o
baseline teve ROC-AUC de exatos **0,50** (equivalente a chute
aleatório), enquanto os três modelos reais ficaram entre 0,632 e 0,639.

| Modelo | ROC-AUC |
|---|---:|
| Gradient Boosting | 0,639 |
| Random Forest | 0,637 |
| Regressão Logística | 0,632 |
| Baseline | 0,500 |

Random Forest e Gradient Boosting ficaram estatisticamente empatados.
Escolhemos **Random Forest** como modelo final: desempenho equivalente,
com a vantagem de ser mais simples de explicar em contexto de política
pública e de fornecer Feature Importance nativa.

Também testei `class_weight="balanced"` e limitar a profundidade das
árvores `max_depth=15` ambos os ajustes pioraram o resultado. O modelo final manteve a configuração mais
simples: `RandomForestClassifier(n_estimators=200, random_state=42)`,
sem restrições adicionais.

## Métricas de avaliação

Além do ROC-AUC (usado para comparar algoritmos), foi avaliado o modelo
final também por precisão, recall e F1 macro com atenção especial ao
recall da classe **"não alfabetizado"**, já que essa é a classe que
importa para identificar risco educacional. Com o threshold padrão
(0,5), o modelo identificava corretamente menos de 40% dos alunos
realmente não-alfabetizados.

Testei diferentes pontos de corte (threshold) sobre a probabilidade
prevista, em vez de usar o padrão de 0,5 do Scikit-learn, buscando o
ponto de maior F1. O ponto
ótimo encontrado foi **threshold = 0,60**:

| | precisão | recall | f1-score |
|---|---:|---:|---:|
| Não alfabetizado | 0,48 | 0,59 | 0,53 |
| Alfabetizado | 0,68 | 0,57 | 0,62 |
| **acurácia geral** | | | **0,58** |

Optei por esse ponto de equilíbrio em vez de maximizar acurácia
geral: para uma aplicação de identificação de risco educacional, o
custo de não identificar um aluno que precisa de apoio é maior que o
custo de um falso alarme.

## Interpretação dos resultados

Usei Feature Importance nativa do Random Forest e SHAP para
entender quais variáveis mais influenciam a previsão, e em que
direção.

**Vulnerabilidade socioeconômica municipal é o fator dominante**: os
três indicadores do CadÚnico juntos respondem por ~40% da importância
total do modelo, liderados por `pct_pes_pob` (proporção de pessoas em
situação de pobreza). O SHAP confirma a direção esperada: municípios
mais pobres empurram a previsão para "não alfabetizado".

**Efeitos regionais específicos e extremos**: o modelo aprendeu um
efeito isolado muito forte para **Ceará** (positivo) e **Bahia**
(negativo) coerente com o que a EDA já mostrava (85% de alfabetização
no Ceará contra 36,7% na Bahia). A maioria das demais 24 UFs tem
impacto individual pequeno; não é um efeito genérico de "UF importa",
é específico a alguns estados.

**População municipal tem uma relação inversa discreta**: municípios
menores tendem a levar uma vantagem pequena sobre municípios maiores,
contrário à intuição de que cidades grandes teriam mais recursos
educacionais.

**Rede de ensino tem efeito menor do que o esperado** (`rede_3`,
municipal, aparece entre as últimas posições de importância) o
contexto socioeconômico municipal pesa mais do que a rede em si.