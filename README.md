## Descrição das bases utilizadas
 
O projeto usa como fonte central o **Indicador Criança Alfabetizada**,
com os microdados de alunos avaliados em 2023 e 2024 (~3,9 milhões de
registros). Cada linha representa um aluno avaliado em um determinado
ano, com informações de rede de ensino, presença na prova, proficiência
e o resultado final de alfabetização.
 
Como o indicador sozinho não diz muito sobre o *contexto* do aluno,
cruzamos essa base com outras três fontes, todas no nível de município:
 
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
  real. Eles ficam marcados na coluna `elegivel_modelagem`, e a
  modelagem usa apenas quem tem valor 1 ali (~3,35 milhões de alunos).