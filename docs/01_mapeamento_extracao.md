# Etapa 1 — Mapeamento e Extração de Dados

Projeto: indicadores do Censo 2022 (IBGE) e do IVCAD/CadÚnico recortados para dois
distritos de Brumadinho-MG.

## 1. Distritos-alvo (códigos oficiais confirmados)

Consultei a API de localidades do IBGE para confirmar os códigos geográficos oficiais
(evita erro de digitação e permite montar URLs de consulta corretamente).

| Distrito (grafia oficial IBGE) | Código do distrito (7 dígitos) | Observação |
|---|---|---|
| **São José do Paraopeba** | `3109006` + `25` → **`310900625`** | O usuário escreveu "São José **de** Paraopeba" — a grafia oficial do IBGE é "São José **do** Paraopeba". Use a grafia oficial nas buscas para não perder resultados. |
| **Conceição de Itaguá** | `3109006` + `15` → **`310900615`** | Grafia confere com o IBGE. |

Município: Brumadinho-MG, código `3109006`. Os 5 distritos do município são: Brumadinho
(sede, `310900605`), Aranha (`310900610`), Conceição de Itaguá (`310900615`), Piedade do
Paraopeba (`310900620`) e São José do Paraopeba (`310900625`).

Fonte: `https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3109006/distritos`
(API pública de localidades do IBGE).

## 2. Censo 2022 — o que existe, e o que **não** existe, no nível de distrito

Investiguei diretamente os metadados das tabelas do SIDRA antes de recomendar qualquer
caminho, porque nem toda tabela do Censo 2022 desce até o nível de distrito.

**Descoberta importante:** as tabelas "clássicas" do SIDRA (as que você navega em
`sidra.ibge.gov.br/tabela/xxxx`) — população por idade/sexo (tabela 9514), população e
área (tabela 4714), características de domicílios, trabalho e rendimento — **só estão
disponíveis até o nível de Município** (BR, Região, UF, Região Intermediária/Imediata,
Concentração Urbana, Município). Não existe seletor de "Distrito" nessas tabelas para o
Censo 2022. Confirmei isso consultando a API de metadados do SIDRA
(`servicodados.ibge.gov.br/api/v3/agregados/{id}/metadados`, campo `nivelTerritorial`)
para várias tabelas.

**O caminho certo — Agregados por Distrito (produto separado, sem login):** desde a
atualização de 20/05/2026, o IBGE publica um produto dedicado, **pré-agregado no nível
de distrito**, dentro de "Agregados por Setores Censitários". Isso poupa você de ter que
agregar setor censitário → distrito manualmente. Diretório oficial:

```
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Distrito_csv/
```

Arquivos disponíveis nessa pasta (nível Brasil inteiro — filtramos Brumadinho/MG depois
em Python, não precisa procurar arquivo por UF):

| Arquivo | Conteúdo |
|---|---|
| `Agregados_por_distritos_basico_BR_20260520.zip` | População total, domicílios — visão geral |
| `Agregados_por_distritos_demografia_BR.zip` | População por sexo e grupos de idade (**pirâmide etária**) |
| `Agregados_por_distritos_cor_ou_raca_BR.zip` | População por cor ou raça |
| `Agregados_por_distritos_alfabetizacao_BR.zip` | Alfabetização |
| `Agregados_por_distritos_caracteristicas_domicilio1_BR.zip` | Abastecimento de água, esgoto |
| `Agregados_por_distritos_caracteristicas_domicilio2_BR_20250417.zip` | Banheiro, lixo |
| `Agregados_por_distritos_caracteristicas_domicilio3_BR_20250417.zip` | Tipo de domicílio |
| `Agregados_por_distritos_parentesco_BR.zip` | Composição familiar/parentesco |
| `Agregados_por_distritos_obitos_BR.zip` | Óbitos informados |
| `Agregados_por_distritos_pessoas_indigenas_BR.zip` / `_quilombolas_BR.zip` | Recortes específicos |

Dicionário de dados (nomes de coluna, códigos de categoria):
```
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx
```

Cada CSV traz colunas de identificação geográfica (`CD_DIST`, `NM_DIST`, `CD_MUN`,
`NM_MUN`, `CD_UF`, `NM_UF` — confirme os nomes exatos no dicionário ao abrir, pois podem
variar levemente por tema) — filtramos por `CD_DIST` igual a `310900615` /
`310900625` (ou por `NM_MUN == "Brumadinho"` e depois pelo nome do distrito).

**⚠️ Limitação real, não contorne isso sem saber:** **renda (faixas de rendimento) não
está nesse pacote.** Rendimento no Censo 2022 é um dado da **amostra** (questionário
longo), e por enquanto (checei a divulgação "Trabalho e Rendimento — Resultados
preliminares da amostra" no SIDRA) os dados de rendimento só são publicados até o nível
de **Município** — não há tabela de renda em nível de distrito ou setor censitário para
2022 disponível publicamente hoje. Isso é diferente do Censo 2010, que tinha renda até
o setor censitário.

Consequência prática para o seu projetos: a métrica "faixa de renda" no Power BI vai
precisar de uma destas soluções (trato isso com mais detalhe na Etapa 3):
1. Mostrar renda apenas no nível municipal (Brumadinho) como contexto, deixando claro
   que não existe abertura oficial por distrito;
2. Usar a **renda familiar do CadÚnico** (que é naturalmente georreferenciada por
   endereço) como proxy de renda no nível distrital — ver seção 3.

**Malha territorial (para mapas no Power BI, se quiser):**
```
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/
```
Contém os polígonos dos setores censitários (shapefile/geopackage) já com atributos de
distrito — útil se você quiser um mapa coroplético dos dois distritos no Power BI.

## 3. CadÚnico / IVCAD — o que dá pra acessar de fato

Aqui a situação é mais restritiva do que os outros passos, e é importante alinhar
expectativa antes de você gastar tempo tentando.

### 3.1 Observatório do Cadastro Único (público, sem login)
```
https://paineis.mds.gov.br/public/extensions/observatorio-do-cadastro-unico/index.html
```
- Mostra o **IVCAD** (6 dimensões / ~40 indicadores) e outros painéis (benefícios,
  população em situação de rua, deficiência, educação, trabalho).
- Filtro territorial: **somente por município** (usando o código IBGE do município).
  Não há filtro por CRAS, bairro ou CEP nessa ferramenta pública — ou seja, ela não
  isola São José do Paraopeba nem Conceição de Itaguá dentro de Brumadinho.
- Tem botões "Exportar" nos gráficos (exporta a série que está na tela, não microdados).
- Por LGPD, quando um grupo tem menos de 100 famílias ou 200 pessoas, o valor aparece
  como "-" — isso é relevante porque os dois distritos-alvo são pequenos e rurais, e
  qualquer extração futura (mesmo autorizada) pode esbarrar nessa supressão para
  indicadores mais granulares.

### 3.2 CECAD 2.0 — onde estão os microdados/família com filtro geográfico fino
```
https://cecad.cidadania.gov.br/
```
- Sem login: dá pra navegar indicadores agregados (nível município), similar ao
  Observatório.
- **Com login (o que você precisa para filtrar por CRAS/bairro/CEP e baixar
  extrações):** exige login gov.br com **selo de confiabilidade prata**, e o sistema
  então confere seu perfil nas bases **SIGPBF/CADSUAS**. Na prática, isso significa que
  só é liberado para:
  - Equipe técnica/gestora do Cadastro Único do próprio município (cadastrada no
    SIGPBF), tipicamente lotada na Secretaria de Assistência Social;
  - Vigilância socioassistencial autorizada pela Resolução SUAS nº 9/2012;
  - Técnicos do Ministério (MDS/SAGICAD) ou gestores de programas federais, mediante
    ofício.
  - **Um cidadão comum ou analista externo, sem vínculo institucional, não consegue
    login liberado no CECAD para extração de dados.**

**Caveat de granularidade, mesmo com acesso:** levantei os CRAS conhecidos de
Brumadinho e encontrei referências a "CRAS Centro" e "CRAS Cohab" — ambos aparentemente
na sede urbana. Isso sugere que **filtrar por CRAS de referência provavelmente não
isola bem os distritos rurais** (as famílias de São José do Paraopeba e Conceição de
Itaguá provavelmente são atendidas por um desses CRAS da sede, junto com outras áreas).
**Filtrar por CEP/bairro/logradouro dentro do módulo de extração do CECAD tende a ser
mais preciso** para isolar os dois distritos — mas confirme isso com quem for rodar a
extração, e valha-se de um levantamento prévio dos CEPs que cobrem cada distrito (o
próprio módulo de extração do CECAD, para usuários autorizados, tem filtro por
"Bairro"/"CEP"/"Logradouro" na busca de famílias).

**Caminhos recomendados, em ordem de praticidade:**
1. **Se você (ou alguém em Brumadinho) tem acesso institucional:** peça para um
   técnico da Secretaria de Assistência Social / CRAS de Brumadinho rodar a extração no
   CECAD filtrando por CEP/bairro dos dois distritos, e te passar o CSV. Eu ajudo a
   redigir exatamente quais campos pedir (renda familiar, composição familiar, IVCAD por
   família) para já vir no formato certo para o pandas.
2. **Solicitação formal (SolicitaCad):** existe um serviço formal para pedir cessão de
   dados identificados do Cadastro Único —
   `https://www.gov.br/pt-br/servicos/solicitar-cessao-de-dados-identificados-do-cadastro-unico`
   — mas costuma ser voltado a órgãos públicos/pesquisa institucional, com prazo mais
   longo. Vale como plano B se o caminho 1 não for viável.
3. **Sem nenhum dos dois:** o projeto fica limitado ao IVCAD/CadÚnico **no nível de
   Brumadinho como um todo** (via Observatório), sem conseguir abrir por distrito — e o
   Censo 2022 (seção 2) passa a ser sua única fonte granular real para os dois
   distritos.

**Decisão registrada (04/09/2026):** você confirmou que não tem acesso institucional
nem vínculo de pesquisa que permita CECAD com filtro por CRAS/CEP. Portanto o projeto
segue pelo cenário 3: o **IVCAD/CadÚnico entra apenas no nível de Brumadinho como um
todo** (via Observatório do Cadastro Único, sem abertura por distrito), e o **Censo
2022 (seção 2, Agregados por Distrito) é a fonte principal e mais confiável para o
recorte de São José do Paraopeba e Conceição de Itaguá**. Isso será refletido na
modelagem da Etapa 3: o IVCAD aparece no dashboard como referência municipal
(contextualizando os dois distritos dentro do todo), não como métrica calculada por
distrito. Se no futuro você conseguir um contato na Secretaria de Assistência
Social/CRAS de Brumadinho, dá pra revisitar isso e enriquecer o modelo com dado
distrital de renda familiar/vulnerabilidade.

## 4. Estrutura de pastas do projeto (já criada na sua pasta local)

```
Brumadinho/
├── data/
│   ├── raw/
│   │   ├── censo2022/     <- ZIPs baixados do IBGE (seção 2) ficam aqui, sem descompactar
│   │   └── cadunico/      <- extração do CECAD (ou export do Observatório), se/quando conseguir
│   └── processed/         <- saída dos scripts Python (Etapa 2): CSV/Parquet prontos para o Power BI
├── docs/
│   └── 01_mapeamento_extracao.md   <- este arquivo
├── src/                    <- scripts Python (Etapa 2)
└── powerbi/                <- arquivo .pbix (Etapa 3)
```

## 5. Checklist do que baixar agora

- [ ] `Agregados_por_distritos_basico_BR_20260520.zip`
- [ ] `Agregados_por_distritos_demografia_BR.zip` (pirâmide etária)
- [ ] `Agregados_por_distritos_cor_ou_raca_BR.zip`
- [ ] `Agregados_por_distritos_alfabetizacao_BR.zip`
- [ ] `Agregados_por_distritos_caracteristicas_domicilio1_BR.zip`
- [ ] `Agregados_por_distritos_caracteristicas_domicilio2_BR_20250417.zip`
- [ ] `Agregados_por_distritos_caracteristicas_domicilio3_BR_20250417.zip`
- [ ] `dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx`
- [ ] (opcional, para mapa) pasta `malha_com_atributos/`
- [ ] Print/export do Observatório do Cadastro Único para Brumadinho (nível município) —
      guarda como contexto, mesmo não sendo distrital
- [ ] Definir com o usuário qual dos 3 cenários da seção 3.2 se aplica, antes da Etapa 2
      tratar CadÚnico

Salve os ZIPs em `data/raw/censo2022/` sem descompactar — o script Python da Etapa 2 lê
direto do ZIP com `pandas.read_csv` (evita descompactar arquivos nacionais grandes
desnecessariamente).

## 6. Fontes consultadas

- [Downloads | Panorama do Censo Demográfico 2022](https://censo2022.ibge.gov.br/panorama/downloads.html)
- [Índice — Agregados por Distrito (CSV)](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Distrito_csv/)
- [SIDRA — Censo Demográfico 2022](https://sidra.ibge.gov.br/pesquisa/censo-demografico/demografico-2022/inicial)
- [API de metadados do SIDRA (agregados)](https://servicodados.ibge.gov.br/api/v3/agregados/9514/metadados)
- [API de localidades do IBGE (distritos de Brumadinho)](https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3109006/distritos)
- [Observatório do Cadastro Único](https://paineis.mds.gov.br/public/extensions/observatorio-do-cadastro-unico/index.html)
- [IVCAD — MDS](https://www.gov.br/mds/pt-br/noticias-e-conteudos/dados-e-ferramentas-informacionais/ivcad)
- [CECAD 2.0 — Como acessar](https://manual-cecad-20.readthedocs.io/como_acessar.html)
- [CECAD 2.0 — Quem pode ter acesso](https://manual-cecad-20.readthedocs.io/quem_pode_ter_acesso.html)
- [Solicitar cessão de dados identificados do Cadastro Único (SolicitaCad)](https://www.gov.br/pt-br/servicos/solicitar-cessao-de-dados-identificados-do-cadastro-unico)
