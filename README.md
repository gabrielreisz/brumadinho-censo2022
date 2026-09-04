# Brumadinho — indicadores por distrito

Pipeline de dados que recorta indicadores públicos para dois distritos de Brumadinho-MG
— **São José do Paraopeba** e **Conceição de Itaguá** — que não aparecem isolados em
nenhum painel oficial (SIDRA e IBGE Cidades param no nível de município).

**Painel interativo:** https://gabrielreisz.github.io/brumadinho-censo2022/

O painel tem uma aba por distrito, com os gráficos daquele distrito sozinho, mais uma
aba de comparação e uma de contexto municipal. A barra de filtros no topo liga e desliga
temas (demografia, educação, saúde, saneamento, renda, série histórica...) — tudo aparece
por padrão, e a escolha fica salva no navegador.

## O que os dados mostram

- **São José do Paraopeba não tem nenhum estabelecimento de saúde dentro dos seus
  limites**, para 1.388 moradores — mas tem uma equipe de atenção primária com o
  distrito como área de referência, sediada na unidade de Marinhos, em outro distrito, e
  marcada no CNES como equipe que assiste população quilombola. Conceição de Itaguá tem
  5 estabelecimentos, 6 equipes e 57 profissionais.
- **526 moradores de São José do Paraopeba se declararam quilombolas** — 37,9% do
  distrito. Em Conceição de Itaguá, nenhum.
- O saneamento separa os dois distritos com folga: **0,6% dos domicílios de São José do
  Paraopeba têm esgoto em rede geral, contra 74,0% em Conceição de Itaguá**. Lixo
  coletado por serviço de limpeza: 51,6% contra 95,6%. Água da rede geral: 60,6% contra
  90,6%.
- Em Conceição de Itaguá, os óbitos declarados se concentram em dois semestres: o
  **1º de 2019 (34 de 115 com semestre informado)** e o **1º de 2021 (28)**. O
  rompimento da barragem da Mina Córrego do Feijão foi em 25/01/2019 e a segunda onda
  da covid-19 no Brasil em 2021 — mas o Censo registra o semestre do falecimento, não a
  causa, então o dado não atribui as mortes a nenhum dos dois eventos.
- **As duas escolas de São José do Paraopeba são as únicas do município em área
  remanescente de quilombo** — e o distrito não oferece anos finais do fundamental nem
  ensino médio: as 113 matrículas param no 5º ano.
- Em 2010 — dado de renda mais recente que existe por distrito — **41,5% dos domicílios
  de São José do Paraopeba viviam com até 1/2 salário mínimo per capita**, contra 20,5%
  em Conceição de Itaguá.
- No município, **22,6% dos empregos formais estão na indústria extrativa**, e o salário
  médio de um homem branco ou amarelo (R$ 5.036) é 63% maior que o de uma mulher preta,
  parda ou indígena (R$ 3.084).

## Fontes e como cada uma foi tratada

### Censo 2022 — IBGE (nível distrito)

O Censo tem um produto separado, "Agregados por Distrito", que já vem pré-agregado
nesse nível. São 13 arquivos, um por tema, cobrindo todos os distritos do Brasil, mais
um dicionário em Excel que traduz cada código de coluna (`V01009`) para o significado.

1. **Filtragem** — cada CSV bruto tem uma linha por distrito do país. O
   `01_processar_censo.py` filtra por `CD_DIST` e reduz cada arquivo a 2 linhas.
2. **Dicionário** — o `02_gerar_dicionario.py` consolida as abas do Excel num CSV único,
   normalizando o código da variável: o IBGE usa `V0001` (4 dígitos) no tema Básico e
   `V00001`/`V01006` (5 dígitos) nos demais.
3. **Ajustes do formato do IBGE** — decimais gravados com vírgula (`"118,8365656"`, que
   o pandas lê como texto) e diferenças residuais de poucas unidades nas somas por sexo,
   que vêm da proteção de confidencialidade em áreas pequenas.
4. **Formato longo** — o `03_piramide_etaria.py` converte a demografia de "uma coluna por
   combinação sexo/faixa" para "uma linha por distrito/sexo/faixa", que é o formato que
   a pirâmide etária e o Power BI usam bem.

### Malha territorial — IBGE (nível distrito)

Shapefile de todos os distritos de MG. O `05_malha_distritos.py` recorta os 5 distritos
de Brumadinho e grava um GeoJSON leve para o mapa do site.

### CNES — Ministério da Saúde (nível distrito, por cruzamento)

A API de dados abertos do CNES devolve os 143 estabelecimentos de Brumadinho com
coordenadas, mas informa só município e bairro. O `06_cnes_saude.py` testa cada
coordenada contra os polígonos da malha do IBGE (ray casting, sem geopandas) e é isso
que transforma um dado municipal em dado distrital.

Contar prédios diz pouco — uma sala de vacina e um centro de saúde contam igual. O
`12_cnes_equipes.py` vai à base completa do CNES (700 MB, lida em streaming) e traz
equipes e profissionais. Uma equipe conta para o distrito se está sediada nele **ou** se
a área de referência cadastrada tem o nome dele: é assim que aparece a equipe com
referência "SÃO JOSE", sediada na unidade de Marinhos. O arquivo com nome e CPF dos
profissionais não é aberto; a contagem usa o identificador anonimizado do vínculo.

Parte das coordenadas do CNES é aproximada: 14 estabelecimentos compartilham coordenada
com outro, 3 têm precisão de ~100 m e 2 caem fora do polígono do município. Esses casos
ficam de fora das contagens por distrito e são listados na aba municipal.

### Censo Escolar — INEP (nível distrito, direto)

Os microdados do Censo Escolar já trazem `CO_DISTRITO`, então aqui não houve cruzamento
geográfico. O `09_censo_escolar.py` lê as tabelas de escolas e de matrículas de dentro
do ZIP de 530 MB, sem descompactar em disco, e guarda só as 32 escolas de Brumadinho.

### Setores censitários — IBGE (nível abaixo do distrito)

O distrito é o menor nível pré-agregado, mas o setor censitário é mais fino. O código do
setor começa com o código do distrito, o que dispensa cruzamento geográfico. O
`10_setores_censitarios.py` junta a malha de setores de MG com os agregados por setor e
gera o GeoJSON do mapa de calor: 26 setores nos dois distritos.

### Censo 2010 — IBGE (série histórica e renda)

O `11_censo2010_serie.py` recorta os agregados por setor censitário de 2010 pelos mesmos
distritos. Serve para duas coisas que não existem de outro jeito: comparar saneamento
entre os dois censos e ter **renda por distrito** — em 2010 o rendimento estava no
questionário do universo e era publicado por setor; em 2022 foi para a amostra, que só
sai até município.

As categorias mudaram entre os censos: só água da rede geral, esgoto em rede geral e
lixo coletado têm definição equivalente, e é só isso que o painel compara.

### DataViva / Cedeplar-UFMG — RAIS (nível município)

Emprego por setor, salário por escolaridade e salário por sexo e cor/raça. Os arquivos
do DataViva cobrem o Brasil inteiro e chegam a 2 GB, então o `07_dataviva_brumadinho.py`
lê em streaming, filtra linha a linha e para assim que passa do código de Brumadinho —
de ~310 MB lidos sobram 1.170 linhas. **RAIS não desce abaixo de município**, então
esses números aparecem numa aba separada no site, como contexto.

## Estrutura do repositório

```
site/                            painel interativo em D3.js (publicado no GitHub Pages)
  index.html, estilo.css, app.js
  dados/                         JSON e GeoJSON gerados pelo pipeline
src/config.py                    caminhos e códigos dos distritos
src/01_processar_censo.py        filtra os ZIPs do Censo para os 2 distritos
src/02_gerar_dicionario.py       consolida o dicionário de variáveis do IBGE
src/03_piramide_etaria.py        converte a demografia para formato longo
src/04_graficos_analise.py       gráficos estáticos em PNG (matplotlib)
src/05_malha_distritos.py        shapefile do IBGE -> GeoJSON dos distritos
src/06_cnes_saude.py             CNES + geometria -> estabelecimentos por distrito
src/07_dataviva_brumadinho.py    RAIS/DataViva -> recorte de Brumadinho
src/08_dados_site.py             consolida tudo no JSON que o site lê
src/09_censo_escolar.py          Censo Escolar do INEP -> escolas por distrito
src/10_setores_censitarios.py    malha + agregados por setor -> GeoJSON do mapa de calor
src/11_censo2010_serie.py        Censo 2010 -> série histórica e renda por distrito
src/12_cnes_equipes.py           base completa do CNES -> equipes e profissionais
src/13_graficos_por_distrito.py  PNGs de um distrito por vez
src/estilo_graficos.py           paleta e layout compartilhados pelos gráficos
docs/01_mapeamento_extracao.md   o que existe e o que não existe por distrito (1ª rodada)
docs/02_novas_fontes.md          SUS, DataViva, malha: o que entrou e por quê
download_censo2022.sh            baixa os arquivos brutos do IBGE
data/raw/                        dados brutos (fora do git, redownload pelo script)
data/processed/                  CSVs filtrados e tratados, um por tema
reports/figuras/                 gráficos comparando os dois distritos (PNG)
reports/figuras/<distrito>/      os mesmos temas com um distrito de cada vez
powerbi/                         arquivos do dashboard
```

## Como rodar

```bash
pip install -r requirements.txt

bash download_censo2022.sh              # dados brutos do IBGE
python src/01_processar_censo.py        # filtra para os 2 distritos
python src/02_gerar_dicionario.py       # dicionário de variáveis
python src/03_piramide_etaria.py        # formato longo da pirâmide
python src/04_graficos_analise.py       # PNGs em reports/figuras/
python src/05_malha_distritos.py        # GeoJSON dos distritos
python src/06_cnes_saude.py             # estabelecimentos de saúde por distrito
python src/07_dataviva_brumadinho.py    # RAIS/DataViva (baixa ~310 MB em streaming)
python src/09_censo_escolar.py          # escolas por distrito (baixa ~530 MB)
python src/10_setores_censitarios.py    # setores censitários
python src/11_censo2010_serie.py        # série histórica e renda de 2010
python src/12_cnes_equipes.py           # equipes e profissionais de saúde
python src/08_dados_site.py             # JSON do site
python src/13_graficos_por_distrito.py  # PNGs de cada distrito
```

O `12_cnes_equipes.py` precisa da base completa do CNES, que não tem link estável:

```bash
curl -L -o data/raw/cnes/BASE_DE_DADOS_CNES_202607.ZIP \
  "https://cnes.datasus.gov.br/EstatisticasServlet?path=BASE_DE_DADOS_CNES_202607.ZIP"
```

Para ver o site localmente:

```bash
python -m http.server 8000 --directory site
```

O site é estático e sem build: HTML, CSS e um arquivo de JavaScript que carrega o D3 por
CDN. Um push em `site/` republica pelo workflow em `.github/workflows/pages.yml`.

## Limitações conhecidas

- **Renda atual por distrito não existe.** Em 2022 virou dado da amostra, publicado só
  até município. O painel mostra a renda de 2010 por distrito (que existe) e a renda e o
  salário atuais numa aba municipal separada.
- **Mortalidade por causa não existe por distrito.** O SIM/DATASUS registra município de
  residência. A única mortalidade distrital é a contagem do Censo (jan/2019–jul/2022),
  sem causa.
- **Números pequenos.** São José do Paraopeba tem 1.388 moradores; em várias aberturas as
  células ficam com poucas unidades e o IBGE aplica proteção de confidencialidade.
  Percentuais sobre bases pequenas oscilam muito — leia as contagens absolutas junto.
- **Comparar 2010 com 2022 exige cuidado.** As categorias de saneamento mudaram entre os
  censos e o número de domicílios cresceu nos dois distritos: um percentual que cai pode
  significar rede que não acompanhou o crescimento, não rede desfeita.
- **CadÚnico/IVCAD** continua sem recorte por distrito no painel público.
