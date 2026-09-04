# Brumadinho — Censo 2022 por distrito

Pipeline de dados que recorta os indicadores do Censo 2022 (IBGE) para dois
distritos específicos de Brumadinho-MG — **São José do Paraopeba** e
**Conceição de Itaguá** — que não aparecem isolados em nenhum painel oficial
(SIDRA e o IBGE Cidades só abrem até o nível de município). A ideia é ter
dados tratados nesse nível de detalhe para análise e, depois, um dashboard
no Power BI.

## Como os dados foram tratados

1. **Extração**: o Censo 2022 tem um produto específico chamado "Agregados
   por Distrito" (`ftp.ibge.gov.br`), com um CSV por tema (demografia, cor
   ou raça, alfabetização, saneamento, composição domiciliar etc.) cobrindo
   todos os distritos do Brasil, mais um dicionário de variáveis em Excel
   que traduz cada código de coluna (ex.: `V01009`) para o que ele significa.

2. **Filtragem**: cada CSV bruto tem uma linha por distrito do país inteiro.
   `src/01_processar_censo.py` filtra pelo código do distrito (`CD_DIST`)
   para manter só os dois distritos-alvo, reduzindo cada arquivo a 2 linhas.

3. **Tratamento**: os arquivos do IBGE têm algumas particularidades que
   precisam de ajuste manual — decimais gravados com vírgula
   (`"118,8365656"`, que o pandas lê como texto), nomes de variável com
   paddings diferentes entre abas do dicionário (`V0001` vs `V00001`), e
   pequenas diferenças residuais em somas de sexo por causa da proteção de
   confidencialidade do IBGE em setores pequenos.

4. **Estruturação**: a maior parte dos dados fica em formato "largo" (uma
   coluna por variável), que já serve para a maioria dos gráficos. Para a
   pirâmide etária, `src/03_piramide_etaria.py` transforma esses dados em
   formato "longo" (uma linha por distrito/sexo/faixa etária), que é o que
   o Power BI usa bem para esse tipo de gráfico.

5. **Visualização**: `src/04_graficos_analise.py` lê só os CSVs já tratados
   em `data/processed/` e gera os gráficos, sem tocar nos dados brutos.
   Cada gráfico cita a variável e o arquivo de origem no rodapé.

## Estrutura do repositório

```
docs/01_mapeamento_extracao.md   documentação da etapa de mapeamento: onde
                                  cada dado vem, códigos de distrito, o que
                                  não existe no Censo nesse nível (renda,
                                  saúde) e por quê
download_censo2022.sh            baixa os arquivos brutos do IBGE
requirements.txt                 dependências Python (pandas, pyarrow, openpyxl, matplotlib)
src/config.py                    caminhos e constantes compartilhadas
src/01_processar_censo.py        filtra os ZIPs brutos para os 2 distritos
src/02_gerar_dicionario.py       consolida o dicionário de variáveis do IBGE
src/03_piramide_etaria.py        formata os dados de demografia para a pirâmide etária
src/04_graficos_analise.py       gera os gráficos em reports/figuras/
data/raw/                        dados brutos baixados do IBGE (fora do git)
data/processed/                  CSVs já filtrados e tratados, um por tema
reports/figuras/                 gráficos gerados (PNG)
powerbi/                         arquivos do dashboard (próxima etapa)
```

## Como rodar

```bash
pip install -r requirements.txt --break-system-packages

bash download_censo2022.sh                # baixa os dados brutos do IBGE
python src/01_processar_censo.py          # filtra para os 2 distritos
python src/02_gerar_dicionario.py         # consolida o dicionário de variáveis
python src/03_piramide_etaria.py          # formata dados da pirâmide etária
python src/04_graficos_analise.py         # gera os gráficos em reports/figuras/
```

## Limitações conhecidas

- **Renda**: o Censo 2022 não publica renda abaixo do nível municipal.
- **Saúde**: não há indicador de saúde (mortalidade, cobertura de atenção
  básica) no nível distrital nas fontes usadas aqui; os gráficos de
  saneamento (água, esgoto, lixo) servem de proxy indireto.
- **CadÚnico/IVCAD**: o Observatório do Cadastro Único público não permite
  recorte por distrito, e a extração por família exigiria acesso
  institucional ao CECAD 2.0 (fora do escopo deste projeto). O Observatório
  público expõe um filtro por CRAS — Brumadinho tem três (Aranha, Centro,
  Cohab) — que é uma via possível a explorar depois, mas a área de
  cobertura de um CRAS não é exatamente igual à de um distrito.

## Fontes

- Censo Demográfico 2022 / IBGE — Agregados por Distrito (`ftp.ibge.gov.br`)
- IBGE Cidades — painel Brumadinho (contexto municipal, não distrital)
- Observatório do Cadastro Único / MDS (`paineis.mds.gov.br`)
