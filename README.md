## Contexto do problema

A alfabetização na idade certa é um dos indicadores mais importantes
do desenvolvimento educacional e social do Brasil, mas conhecer a
taxa atual não é suficiente para orientar políticas públicas efetivas.
Gestores educacionais precisam antecipar riscos, identificar regiões
mais vulneráveis e entender quais fatores realmente pesam sobre o
desempenho dos alunos, sem essa camada de análise decisões de
investimento e intervenção continuam sendo tomadas de forma reativa,
depois que o resultado já aconteceu.

Este projeto parte dos microdados do Indicador Criança Alfabetizada
(2023-2024) e busca entender em que medida fatores territoriais e
socioeconômicos informação já disponível publicamente antes mesmo
do resultado da avaliação conseguem explicar e antecipar a
alfabetização de um aluno.

## Objetivo analítico

Desenvolver um modelo de classificação supervisionada capaz de prever
se um aluno será considerado alfabetizado, utilizando variáveis
educacionais, territoriais e socioeconômicas e a partir desse
modelo, responder perguntas de política pública.

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

## Insights encontrados

**Vulnerabilidade socioeconômica municipal é o fator mais consistente
em toda a análise.** Aparece como a variável mais importante no
modelo (SHAP e Feature Importance), como o critério mais claro de
diferenciação nos clusters, e como um padrão coerente com o que a
análise exploratória já indicava: municípios no quartil mais pobre têm
taxa de alfabetização ~10,6 pontos percentuais menor que os do quartil
menos pobre. 

<img width="720" height="480" alt="image" src="https://github.com/user-attachments/assets/24c20e2e-4b98-4e72-91e1-593ae46fbb49" />


**Efeitos regionais específicos superam o efeito genérico de UF.** O
modelo aprendeu um efeito isolado e forte para Ceará (positivo) e
Bahia (negativo) não é um padrão uniforme, é concentrado em poucos estados com desvio expressivo em relação à
média nacional (Ceará: 85% de alfabetização; Sergipe: 34,85%). O clustering reforça essa nuance: o Ceará aparece distribuído nos três
perfis municipais identificados, sugerindo um efeito estadual que
beneficia municípios de perfis socioeconômicos distintos igualmente.

<img width="1200" height="720" alt="image" src="https://github.com/user-attachments/assets/e2058bd6-e1d4-4106-b495-1d5c3a7d9278" />

**Pobreza explica desempenho, mas não é o único fator e às vezes
nem o principal.** O cluster de melhor desempenho (71,5% de
alfabetização) tem pobreza intermediária, maior que a do cluster de
desempenho médio (66,7%, com a menor pobreza dos três grupos). O
diferencial parece estar mais ligado ao porte do município (o cluster
de melhor desempenho tem a menor população média) do que à
vulnerabilidade econômica isoladamente.

| Cluster | Taxa de alfabetização | % Pessoas pobres | % Pessoas baixa renda | % Pessoas acima de ½ SM | Log população | Qtd. municípios |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.468 | 0.516 | 0.127 | 0.129 | 9.660 | 1723 |
| 1 | 0.667 | 0.153 | 0.092 | 0.115 | 10.106 | 1730 |
| 2 | 0.715 | 0.269 | 0.156 | 0.204 | 8.759 | 2094 |

<img width="1200" height="960" alt="image" src="https://github.com/user-attachments/assets/5a811b7a-2071-40cd-9b7b-297c56c17a65" />

**A estabilidade nacional esconde volatilidade municipal real.** A
taxa de alfabetização nacional variou pouco entre 2023 e 2024 (58,4%
para 59,8%), mas isso mascara mudanças bem mais expressivas no nível
municipal. Entre municípios com pelo menos 100 alunos avaliados nos
dois anos, 36,3% tiveram queda real na taxa observada (incluindo
municípios de porte considerável, como um caso de queda de 31 pontos
percentuais em um município de mais de 700 alunos avaliados). Isso
reforça que uma leitura apenas nacional do indicador esconderia
justamente os municípios que mais precisam de atenção.

| Índice | Classificação de risco | Qtd. municípios | % |
|---:|---|---:|---:|
| 0 | Já superou a meta | 978 | 40.3 |
| 1 | Risco alto (estagnado ou piorando) | 880 | 36.3 |
| 2 | No ritmo (deve atingir a meta) | 267 | 11.0 |
| 3 | Risco alto (ritmo muito lento) | 193 | 8.0 |
| 4 | Risco moderado (ritmo insuficiente) | 108 | 4.5 |

| Índice | ID município | Município | UF | Alunos 2023 | Alunos 2024 | Taxa 2023 | Taxa 2024 | Variação anual | Meta 2025 | Diferença para meta | Classificação |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 2509057 | Marcação | Paraíba | 123 | 129 | 62.60 | 21.71 | -40.90 | 72.42 | -50.71 | Risco alto (estagnado ou piorando) |
| 1 | 2100808 | Anapurus | Maranhão | 179 | 109 | 91.06 | 33.94 | -57.12 | 80.00 | -46.06 | Risco alto (estagnado ou piorando) |
| 2 | 4313953 | Pantano Grande | Rio Grande do Sul | 103 | 103 | 77.67 | 31.07 | -46.60 | 74.82 | -43.75 | Risco alto (estagnado ou piorando) |
| 19 | 4303905 | Campo Bom | Rio Grande do Sul | 716 | 607 | 77.37 | 46.46 | -30.92 | 78.12 | -31.66 | Risco alto (estagnado ou piorando) |

**O risco previsto é, na prática, majoritariamente municipal não
individual.** Ao agregar o risco previsto pelo modelo por município,
93,9% dos municípios têm uma previsão homogênea entre todos os seus
alunos (ou 100% classificados como risco, ou 0%). Apenas 6,1% dos
municípios (178) têm uma mistura real, onde a rede de ensino
(municipal vs. estadual) muda a classificação de parte dos alunos esses são os casos onde a escolha de rede parece ter relevância
prática direta.

**40,3% dos municípios já superam a própria meta de 2025**, mas
36,3% estão estagnados ou piorando, sem qualquer sinal de que vão se
aproximar da meta se o ritmo atual se mantiver.

## Limitações do projeto

- **Cobertura territorial incompleta em 2023**: Acre, Distrito Federal
e São Paulo não têm nenhum registro nos microdados originais desse
ano (confirmado por consulta direta à fonte primária, antes de
qualquer processamento). Para Acre e DF, isso é consistente com
reportagens indicando que os dois estados não participaram do ciclo
de avaliação de 2023 [FONTE](https://jeduca.org.br/noticia/entenda-como-funciona-o-indicador-crianca-alfabetizada-lancado-pelo-mec). Para São Paulo, fontes oficiais indicam
participação e indicador calculado nesse ano no nível agregado, porém não estava presente nos micro dados disponibilizados. O modelo nunca viu esses três estados no treino,
tratando-os como categoria desconhecida no teste, o impacto medido
foi pequeno queda de 0,017 no ROC-AUC ao incluir esses
casos na avaliação.

- **Granularidade municipal, não individual, para o contexto
socioeconômico**: por proteção de privacidade, o identificador de
escola nos microdados de alunos é mascarado/fictício, impedindo
qualquer cruzamento em nível de escola. Todo o enriquecimento
externo (CadÚnico, população) ficou no nível de município como
consequência, a maior parte da variação de risco previsto pelo
modelo ocorre entre municípios, não entre alunos do mesmo município.

- **CadÚnico como fotografia, não série contínua**: os indicadores
socioeconômicos usam apenas o snapshot de dezembro de cada ano, não
a série mensal completa.

- **Cobertura restrita a um único ano-série** (2ª série do ensino
fundamental): os resultados não devem ser generalizados para outras
etapas escolares.

- **Metas oficiais de alfabetização foram excluídas do modelo por
decisão, não por limitação técnica**: têm poder preditivo real
(custo de remoção: entre 0,012 e 0,015 de ROC-AUC), mas foram
descartadas por serem, muito provavelmente, calculadas a partir do
próprio histórico do município pouco acionáveis para orientar
decisões novas de política pública.

- **Desempenho preditivo moderado** (ROC-AUC de 0,637): fatores
territoriais e socioeconômicos têm relação estatisticamente
significativa com a alfabetização, mas explicam apenas uma fração
da variância individual do resultado o restante depende de fatores
não capturados por dados públicos agregados (qualidade do professor,
contexto familiar, engajamento individual).

## Aplicação prática para políticas públicas

O conjunto de análises deste projeto sugere uma abordagem de
priorização em camadas para investimento público em alfabetização:

**Priorização territorial imediata**: municípios como os identificados
na análise de risco (concentrados em Sergipe, Bahia e Rio Grande do
Norte) apresentam risco previsto alto e homogêneo entre todos os
alunos, sinal de que o problema é estrutural ao município, não pontual
a uma escola ou rede específica. Nesses casos, a intervenção mais
eficaz tende a ser de política municipal ampla (renda, infraestrutura,
formação de professores em rede), não seletiva por rede de ensino.

**Priorização por rede nos municípios de risco misto**: nos 178
municípios onde a rede de ensino muda a classificação de risco dos
alunos, há uma oportunidade concreta e mais barata de intervenção,
investigar o que a rede com melhor desempenho local está fazendo
diferente e replicar na outra.

**Monitoramento municipal contínuo, não apenas nacional**: como a
estabilidade da taxa nacional esconde volatilidade municipal real, um
painel de acompanhamento no nível de município (não só do indicador
agregado) permitiria identificar quedas reais a tempo de agir, em vez
de só confirmá-las manualmente depois.

**Uso do modelo como sistema de alerta prévio**: como o modelo usa
apenas variáveis territoriais e socioeconômicas disponíveis
publicamente (sem depender do resultado da própria avaliação), ele
pode, em princípio, ser aplicado a qualquer momento do ciclo escolar, antes mesmo da aplicação da prova para direcionar reforço
pedagógico a municípios/redes de maior risco previsto.

## Possíveis evoluções futuras

- Investigar a causa da ausência de São Paulo nos microdados de 2023,
  o que poderia viabilizar reincluir o estado no treino e reduzir o
  impacto de "categoria desconhecida" observado no teste.
- Buscar uma fonte de dado socioeconômico ou educacional em nível de
  escola que não dependa do identificador mascarado, para reduzir a
  atual concentração de sinal no nível municipal.
- Testar features de interação (ex: rede × vulnerabilidade
  socioeconômica), para verificar se o efeito da rede de ensino muda
  conforme o contexto do município.
- Investigar a causa da queda real de taxa de alfabetização em
  municípios de porte considerável entre 2023 e 2024, não foi
  possível, com os dados disponíveis, distinguir mudança estrutural
  de variação pontual de uma safra específica de alunos.
- Incorporar mais anos de dado, à medida que novos ciclos do
  Indicador Criança Alfabetizada forem publicados, para permitir
  análises de tendência mais robustas do que a reta de dois pontos
  usada neste projeto.
