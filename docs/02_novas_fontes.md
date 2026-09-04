# Etapa 2 — Novas fontes de dados

Continuação de [01_mapeamento_extracao.md](01_mapeamento_extracao.md). Aqui está o que
foi investigado depois da primeira rodada, o que deu certo e o que não existe no nível
de distrito.

## O que entrou

### 1. Censo 2022 — temas que faltavam no "Agregados por Distrito"

A primeira rodada usou 8 dos arquivos do produto. Faltavam quatro que são relevantes:

| Arquivo | O que traz | Achado |
|---|---|---|
| `..._obitos_BR.zip` | Se alguém que morava no domicílio faleceu entre jan/2019 e jul/2022, por sexo, idade ao falecer, semestre e cor/raça de quem responde pelo domicílio | **É a única mortalidade publicada por distrito.** 162 domicílios com óbito em Conceição de Itaguá, 41 em São José do Paraopeba |
| `..._pessoas_quilombolas_BR.zip` | População quilombola por sexo e idade | **526 pessoas quilombolas em São José do Paraopeba (37,9% do distrito); zero em Conceição de Itaguá** |
| `..._pessoas_indigenas_BR.zip` | População indígena | 3 pessoas em Conceição de Itaguá; nada em São José |
| `..._domicilios_quilombolas_BR.zip` / `..._domicilios_indigenas_BR.zip` | Domicílios desses grupos | complementares aos acima |

Do arquivo de óbitos saiu ainda um indicador que não é sobre morte: somando
`V01254`–`V01263` (existe / não existe pessoa falecida, por cor ou raça de quem responde
pelo domicílio) obtém-se o **total de domicílios por cor/raça da pessoa responsável** —
uma abertura de desigualdade por distrito que não aparece isolada em nenhum outro
arquivo do pacote.

Também passaram a ser usadas variáveis que já estavam baixadas mas não iam para gráfico
nenhum: espécie do domicílio (`V00047`–`V00052`) e número de moradores por domicílio
(`V00017`–`V00026`), ambas de `caracteristicas_domicilio1`.

### 2. Malha territorial dos distritos (IBGE)

```
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/distritos/shp/UF/MG/MG_distritos_CD2022.zip
```

Shapefile com todos os 1.817 distritos de Minas Gerais e atributos do Censo. O
`05_malha_distritos.py` recorta os 5 distritos de Brumadinho e grava um GeoJSON de
~240 KB, usado no mapa do site. A projeção do arquivo é SIRGAS 2000, que para desenho
equivale a WGS84 — não há reprojeção.

A API de malhas do IBGE (`servicodados.ibge.gov.br/api/v3/malhas`) **não** desce até
distrito; ela recusa o parâmetro `intrarregiao` para município. Por isso o shapefile.

### 3. CNES / Ministério da Saúde — estabelecimentos de saúde

```
https://apidadosabertos.saude.gov.br/cnes/estabelecimentos?codigo_municipio=310900
```

API pública, sem chave, paginada de 20 em 20. Retorna 143 estabelecimentos em
Brumadinho com **latitude e longitude**. O CNES informa município e bairro, mas não
distrito — e nome de bairro não identifica distrito de forma confiável. O
`06_cnes_saude.py` resolve isso por geometria: testa cada coordenada contra os polígonos
da malha do IBGE (ray casting em Python puro, sem depender de geopandas).

Resultado:

| Distrito | Estabelecimentos |
|---|---|
| Brumadinho (sede) | 126 |
| Conceição de Itaguá | 5 |
| Piedade do Paraopeba | 5 |
| Aranha | 2 |
| **São José do Paraopeba** | **0** |
| sem coordenada no cadastro | 3 |
| coordenada fora dos limites do município | 2 |

Os 5 últimos são falhas de cadastro do próprio CNES (inclusive a USF Marinhos, cuja
coordenada cai fora do polígono municipal) e ficam de fora das contagens por distrito.

### 4. DataViva / Cedeplar-UFMG — emprego e salário (nível município)

O site do DataViva foi reescrito e a API antiga (`api.dataviva.info/rais/...`) não
existe mais. A rota atual são CSVs abertos em S3, montados a partir da RAIS:

```
https://dvp-stg-site.s3.us-east-2.amazonaws.com/downloads/<Base>/<abertura>/<arquivo>.csv
```

Os arquivos cobrem o Brasil inteiro e vão de 11 MB a 2 GB. O `07_dataviva_brumadinho.py`
não baixa nada em disco: lê em streaming, testa linha a linha e, como os arquivos vêm
ordenados por código de município, **para a leitura assim que passa de Brumadinho**.
Dos ~310 MB lidos sobram 1.170 linhas.

**Limitação de nível:** RAIS é declaração de empregador, agregada por município. Não
existe abertura por distrito. Esses números são contexto municipal e no site aparecem
numa aba separada, justamente para não serem lidos como retrato dos distritos.

## O que continua não existindo por distrito

- **Renda domiciliar.** Continua valendo o que está na Etapa 1: é dado da amostra do
  Censo e só é publicado até município.
- **Mortalidade por causa (SIM/DATASUS).** O SIM traz `CODMUNRES` (município de
  residência), não distrito. Óbitos por distrito só pelo Censo, e só como contagem.
- **Morbidade, internações (SIH), cobertura de atenção básica.** Todos por município.
- **CadÚnico / IVCAD.** Sem mudança em relação à Etapa 1: o painel público filtra por
  município, e o recorte fino exige CECAD 2.0 com acesso institucional.
- **Censo Escolar / INEP.** Os microdados trazem endereço da escola e permitiriam o
  mesmo cruzamento geográfico feito com o CNES. Não foi feito aqui — fica como próximo
  passo, é o mesmo padrão do `06_cnes_saude.py`.

---

# Etapa 3 — Segunda rodada de fontes

## 5. Censo Escolar / INEP (nível distrito, sem cruzamento)

```
https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2025_.zip
```

Surpresa boa: **os microdados do INEP já trazem `CO_DISTRITO` com o código do IBGE**.
Não foi preciso o cruzamento geográfico que o CNES exigiu. O ZIP tem 530 MB; o
`09_censo_escolar.py` lê duas tabelas de dentro dele sem descompactar em disco:

| Tabela | O que traz |
|---|---|
| `Tabela_Escola_*.csv` | uma linha por escola: rede, localização, área diferenciada, infraestrutura (`IN_*`), equipe (`QT_PROF_*`) |
| `Tabela_Matricula_*.csv` | uma linha por escola com matrículas por etapa (`QT_MAT_*`) |

Achados:

- As **duas escolas de São José do Paraopeba são as únicas do município** classificadas
  em **área remanescente de quilombo** (`TP_LOCALIZACAO_DIFERENCIADA`), o que bate com
  os 526 quilombolas do Censo.
- O distrito **não oferece anos finais do fundamental nem ensino médio**: as 113
  matrículas terminam no 5º ano. Ensino médio só existe na sede (1.205 matrículas).
- Uma das duas escolas não tem esgoto em rede pública, biblioteca nem quadra.

## 6. Setores censitários (nível abaixo do distrito)

O código do setor censitário (15 dígitos) começa com os 9 do distrito, então o recorte é
por prefixo — de novo sem cruzamento geográfico. O `10_setores_censitarios.py` junta:

```
.../Agregados_por_Setores_Censitarios/malha_com_atributos/setores/shp/UF/MG/MG_setores_CD2022.zip
.../Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/Agregados_por_setores_*.zip
```

São **26 setores** nos dois distritos. A soma da população dos setores bate exatamente
com o total do distrito (7.104 e 1.388), o que serve de conferência do recorte. O
GeoJSON resultante alimenta o mapa de calor do site, com três indicadores selecionáveis.

## 7. Equipes e profissionais do CNES

A API de dados abertos **não** tem endpoint de equipes nem de profissionais (testado:
`/cnes/equipes`, `/cnes/profissionais` e variações retornam 404). O caminho é a base
completa, que não tem link estável no portal:

```
https://cnes.datasus.gov.br/EstatisticasServlet?path=BASE_DE_DADOS_CNES_202607.ZIP
```

São 700 MB, servidos com `Transfer-Encoding: chunked` — sem `Content-Length` e sem
suporte a range, então não dá para ler só um pedaço. O `12_cnes_equipes.py` lê os
arquivos que interessa de dentro do ZIP em streaming:

| Arquivo | Uso |
|---|---|
| `tbEquipe` | equipes ativas, tipo, área de referência e populações assistidas |
| `rlEstabEquipeProf` | vínculos de profissionais, com CBO |
| `tbTipoEquipe`, `tbAtividadeProfissional` | rótulos |

`tbDadosProfissionalSus` (962 MB, com nome e CPF) **não é aberto**: a contagem usa o
identificador anonimizado do vínculo.

**O achado que corrige a leitura anterior:** contar prédios dizia que São José do
Paraopeba tinha "zero saúde". A base de equipes mostra uma **EAP — Equipe de Atenção
Primária com área de referência "SAO JOSE"**, sediada na USF Marinhos (outro distrito) e
marcada como equipe que assiste **população quilombola**. Por isso o script classifica
uma equipe como atendendo o distrito se está sediada nele *ou* se a referência tem o
nome dele.

Profissionais por mil habitantes, por distrito da sede: Piedade do Paraopeba 13,4;
Aranha 11,9; Brumadinho 8,0; Conceição de Itaguá 8,0; São José do Paraopeba 0.

## 8. Censo 2010 — série histórica e a renda que falta

```
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/Resultados_do_Universo/Agregados_por_Setores_Censitarios/MG_20260615.zip
```

O arquivo `Basico_MG.csv` tem `Cod_distrito`, então o recorte é direto. Duas coisas só
existem aqui:

**Renda por distrito.** Em 2010 o rendimento estava no questionário do universo e era
publicado por setor censitário (`DomicilioRenda`, V005–V014, faixas de salário mínimo
per capita). Em 2022 foi para a amostra, publicada até município. É o dado de renda mais
recente que existe nesse nível — e mostra 41,5% dos domicílios de São José do Paraopeba
com até 1/2 SM per capita, contra 20,5% em Conceição de Itaguá.

**Comparação 2010 x 2022.** As categorias mudaram bastante: em 2010 o abastecimento de
água tinha 4 categorias, em 2022 tem 8. Só três indicadores têm definição equivalente e
são os únicos comparados:

| | Conceição de Itaguá | São José do Paraopeba |
|---|---|---|
| Água da rede geral | 80,5% → 90,6% | 66,2% → 60,6% |
| Esgoto em rede geral/pluvial | 81,6% → 74,0% | 2,9% → 0,6% |
| Lixo coletado | 98,1% → 99,7% | 85,8% → 93,2% |

Um erro que quase entrou aqui: na primeira tentativa o lixo aparecia caindo de 85,8%
para 51,6% em São José. Era comparação errada — a variável de 2010 (`V035`, lixo
coletado) inclui caçamba de serviço, e do lado de 2022 estava só o serviço de limpeza.
Com o denominador certo o indicador sobe. **Vale conferir cada par de variáveis antes de
concluir qualquer coisa sobre a série.**

A base de domicílios cresceu nos dois distritos (1.938 → 2.392 e 408 → 486), então
percentual que cai não quer dizer rede desfeita: pode ser rede que não acompanhou o
crescimento.

## O que continua sem existir

Sem mudança em relação à Etapa 2: mortalidade por causa (SIM registra município de
residência), internações, cobertura de atenção básica oficial e CadÚnico/IVCAD continuam
sem abertura por distrito.

---

# Etapa 4 — A relação com o rompimento da barragem

Em 25 de janeiro de 2019 a barragem B1 da Mina Córrego do Feijão, da Vale, rompeu em
Brumadinho. Esta etapa reúne o que as fontes do projeto conseguem dizer sobre a relação
entre esse evento e os dois distritos — e delimita o que elas não dizem.

## O que estes dados não permitem afirmar

Nenhuma fonte usada aqui traz **causa de morte**, **lista de vítimas por distrito** ou a
**mancha de rejeito**. O Censo pergunta se alguém que morava no domicílio faleceu e em
que semestre, não por quê. O cadastro da ANM descreve as barragens hoje, não o que houve
em 2019. A RAIS registra vínculos formais, não o motivo de existirem ou terminarem.

Correlação de datas não é prova de causa, e a aba do site abre com esse aviso.

## 9. ANM — Cadastro Nacional de Barragens de Mineração

```
https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv
```

O servidor recusa requisição sem `User-Agent` de navegador (403). O cadastro dá
município, não distrito, então vale o mesmo cruzamento geográfico do CNES — com o passo
extra de converter as coordenadas de grau-minuto-segundo para decimal.

São **19 barragens em Brumadinho**. A B1 que rompeu não está no cadastro; da mesma mina
restam quatro estruturas (Menezes I, Menezes II, VI e VII), todas em descaracterização,
no distrito-sede.

**O achado:** as **quatro barragens hoje sob declaração de emergência estão todas em
Conceição de Itaguá** — três em nível 1 e uma em nível 2, todas da Mina do Queias
(EMICON), todas com categoria de risco e dano potencial altos e todas com o campo de
população a jusante marcado como "existem pessoas ocupando permanentemente a área
afetada". Há ainda, no mesmo distrito, uma barragem de 55 m com **alteamento a montante**
— o método da B1 — em descaracterização.

## O que dá para medir

| Medida | Resultado | Fonte |
|---|---|---|
| Distância da mina à borda do distrito | sede 1,7 km · Piedade 4,7 · Aranha 6,2 · **Conceição de Itaguá 8,0** · **São José do Paraopeba 11,4** | coordenadas ANM + malha IBGE |
| Domicílios que tiram água de rio, córrego ou lago | **zero** nos dois distritos | Censo 2022, V00117 |
| Domicílios fora da rede geral | Conceição 9,4% · São José **39,4%** (quase todo poço profundo) | Censo 2022, V00111–V00118 |
| Óbitos declarados no 1º semestre de 2019 | Conceição 34 (maior semestre da série) · São José 0 | Censo 2022, V01264 |
| Equipes de saúde mental ativas | **3, todas cadastradas em 2019** | CNES, `DT_ATIVACAO` |
| Emprego formal do município | 9.444 (2018) → 10.721 (2019) → 9.933 (2020) → 14.070 (2022) → 12.390 (2024) | RAIS via DataViva |

A distância é geométrica: não representa o caminho do rejeito, que desceu o córrego do
Ferro-Carvão até o rio Paraopeba. Não há, nas fontes deste projeto, uma camada de
hidrografia que permita dizer que trechos de rio cruzam cada distrito.

O dado de água limita a exposição a água **de superfície**, não a subterrânea: o Censo
não diz se os poços de São José do Paraopeba foram testados.

A série de equipes conta só as que estão ativas hoje — equipes desativadas desde 2019 não
aparecem, então ela mostra o que restou, não tudo o que foi criado.

## Um erro que estava publicado

Ao montar a série de emprego apareceu um problema no arquivo do DataViva que já tinha
contaminado a aba municipal: as categorias de `Sexo e Raça/Cor` **se sobrepõem**.
`BrAm - Total` e `PPI - Total` cortam o universo por cor/raça; `Homem - Total` e
`Mulher - Total` cortam por sexo. Somar as duas famílias conta cada vínculo duas vezes —
era o que o `08_dados_site.py` fazia, e o site publicou "16.757 vínculos formais" quando
o número correto é **12.390**.

O total agora usa o corte por sexo, que é o único que cobre também os vínculos sem
cor/raça declarada (as duas famílias não fecham no mesmo número: 12.390 contra 11.901).

A correção também inverteu uma leitura: com os números errados o emprego parecia
despencar depois de 2019. Com os certos, **ele sobe** — 9.444 em 2018 para 10.721 em
2019, com pico de 14.070 em 2022. A RAIS não diz o porquê, e obra de reparação,
mineração em outras minas e o resto da economia não são separáveis nesse arquivo.
