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
