const CORES = {
  azul: "#2a78d6", laranja: "#eb6834", verde: "#1baf7a", amarelo: "#eda100",
  roxo: "#4a3aa7", vermelho: "#e34948", rosa: "#e87ba4", neutro: "#c6c5ba",
  texto: "#14140f", texto2: "#55544e", texto3: "#8b8981", grade: "#e4e3dc",
};

// Cor fixa por distrito: a identidade nao muda entre graficos
const CORDIST = { "São José do Paraopeba": CORES.laranja, "Conceição de Itaguá": CORES.azul };
const PALETA = [CORES.azul, CORES.verde, CORES.amarelo, CORES.laranja, CORES.vermelho, CORES.roxo, CORES.rosa, CORES.neutro];

const num = (v, casas = 0) => v == null || Number.isNaN(v) ? "—" :
  v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const pct = (v, casas = 1) => num(v, casas) + "%";
const reais = v => "R$ " + num(v, 0);

const L = 700; // largura de referencia do viewBox; o CSS estica pra caber

let DADOS, GEO, ABA;
const dica = d3.select("body").append("div").attr("class", "dica");

function mostrarDica(evento, html) {
  dica.html(html).style("opacity", 1)
    .style("left", (evento.pageX + 14) + "px")
    .style("top", (evento.pageY - 12) + "px");
}
const esconderDica = () => dica.style("opacity", 0);

function bloco(pai, titulo, sub, fonte) {
  const div = pai.append("div").attr("class", "bloco");
  div.append("h3").text(titulo);
  if (sub) div.append("p").attr("class", "sub").text(sub);
  const corpo = div.append("div");
  if (fonte) div.append("p").attr("class", "fonte").text(fonte);
  return corpo;
}

function svg(pai, altura) {
  return pai.append("svg").attr("viewBox", `0 0 ${L} ${altura}`).attr("preserveAspectRatio", "xMidYMid meet");
}

function legenda(pai, itens) {
  const div = pai.append("div").attr("class", "legenda");
  itens.forEach(([rotulo, cor]) => {
    const item = div.append("span");
    item.append("i").style("background", cor);
    item.append("span").text(rotulo);
  });
}

// ---------------------------------------------------------------- graficos

function barrasHorizontais(pai, dados, opcoes = {}) {
  const { cor = CORES.azul, formato = d => pct(d.pct), campo = "pct", rotuloEixo = "" } = opcoes;
  const textoDica = opcoes.dica ?? (d => `<b>${d.rotulo}</b><br>${num(d.valor)} (${pct(d.pct)})`);
  const alturaBarra = 26, topo = 6, base = rotuloEixo ? 30 : 10;
  const altura = topo + dados.length * alturaBarra + base;
  const margemEsq = opcoes.margemEsq ?? 190;
  const s = svg(pai, altura);

  const x = d3.scaleLinear().domain([0, d3.max(dados, d => d[campo]) || 1]).range([margemEsq, L - 60]);
  const y = d3.scaleBand().domain(dados.map(d => d.rotulo)).range([topo, topo + dados.length * alturaBarra]).padding(0.28);

  s.selectAll("rect").data(dados).join("rect")
    .attr("x", margemEsq).attr("y", d => y(d.rotulo))
    .attr("width", d => Math.max(0, x(d[campo]) - margemEsq)).attr("height", y.bandwidth())
    .attr("rx", 3)
    .attr("fill", (d, i) => typeof cor === "function" ? cor(d, i) : cor)
    .on("mousemove", (e, d) => mostrarDica(e, textoDica(d)))
    .on("mouseleave", esconderDica);

  s.selectAll("text.rot").data(dados).join("text").attr("class", "rot")
    .attr("x", margemEsq - 10).attr("y", d => y(d.rotulo) + y.bandwidth() / 2)
    .attr("text-anchor", "end").attr("dominant-baseline", "central")
    .attr("font-size", 12.5).attr("fill", CORES.texto2).text(d => d.rotulo);

  s.selectAll("text.val").data(dados).join("text").attr("class", "val")
    .attr("x", d => x(d[campo]) + 8).attr("y", d => y(d.rotulo) + y.bandwidth() / 2)
    .attr("dominant-baseline", "central").attr("font-size", 12.5)
    .attr("font-weight", 600).attr("fill", CORES.texto).text(formato);

  if (rotuloEixo) {
    s.append("text").attr("x", margemEsq).attr("y", altura - 6)
      .attr("font-size", 11.5).attr("fill", CORES.texto3).text(rotuloEixo);
  }
  return s;
}

function barrasAgrupadas(pai, categorias, series, opcoes = {}) {
  const { formato = v => num(v), rotuloEixo = "" } = opcoes;
  const altura = 300, margem = { topo: 10, dir: 10, base: 62, esq: 52 };
  const s = svg(pai, altura);

  const x0 = d3.scaleBand().domain(categorias).range([margem.esq, L - margem.dir]).padding(0.22);
  const x1 = d3.scaleBand().domain(series.map(s => s.nome)).range([0, x0.bandwidth()]).padding(0.12);
  const maxv = d3.max(series, s => d3.max(s.valores)) || 1;
  const y = d3.scaleLinear().domain([0, maxv * 1.12]).range([altura - margem.base, margem.topo]);

  s.append("g").attr("transform", `translate(0,${altura - margem.base})`)
    .call(d3.axisBottom(x0).tickSize(0)).call(g => g.select(".domain").attr("stroke", CORES.grade))
    .selectAll("text").attr("font-size", 11.5).attr("fill", CORES.texto2)
    .attr("transform", "rotate(-22)").attr("text-anchor", "end").attr("dx", -4).attr("dy", 8);

  s.append("g").attr("transform", `translate(${margem.esq},0)`)
    .call(d3.axisLeft(y).ticks(5).tickFormat(v => num(v)))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("x2", L - margem.dir - margem.esq).attr("stroke", CORES.grade))
    .selectAll("text").attr("font-size", 11).attr("fill", CORES.texto3);

  series.forEach(serie => {
    s.append("g").selectAll("rect").data(categorias.map((c, i) => ({ c, v: serie.valores[i] })))
      .join("rect")
      .attr("x", d => x0(d.c) + x1(serie.nome)).attr("y", d => y(d.v))
      .attr("width", x1.bandwidth()).attr("height", d => Math.max(0, y(0) - y(d.v)))
      .attr("rx", 2).attr("fill", serie.cor)
      .on("mousemove", (e, d) => mostrarDica(e, `<b>${serie.nome}</b><br>${d.c}: ${formato(d.v)}`))
      .on("mouseleave", esconderDica);
  });

  if (rotuloEixo) s.append("text").attr("x", margem.esq).attr("y", altura - 4)
    .attr("font-size", 11.5).attr("fill", CORES.texto3).text(rotuloEixo);
  legenda(pai, series.map(s => [s.nome, s.cor]));
  return s;
}

function piramide(pai, dados, cor) {
  const alturaFaixa = 24, altura = dados.length * alturaFaixa + 34;
  const s = svg(pai, altura);
  const total = d3.sum(dados, d => d.homens + d.mulheres) || 1;
  const dadosPct = dados.map(d => ({ ...d, ph: 100 * d.homens / total, pm: 100 * d.mulheres / total }));
  const maxv = d3.max(dadosPct, d => Math.max(d.ph, d.pm)) * 1.35;

  const meio = L / 2, faixaRotulo = 74;
  const xe = d3.scaleLinear().domain([0, maxv]).range([meio - faixaRotulo / 2, 46]);
  const xd = d3.scaleLinear().domain([0, maxv]).range([meio + faixaRotulo / 2, L - 46]);
  const y = d3.scaleBand().domain(dadosPct.map(d => d.faixa)).range([altura - 24, 4]).padding(0.24);

  const desenhar = (lado, escala, campoPct, campoAbs, corBarra, ancora) => {
    s.selectAll(`rect.${lado}`).data(dadosPct).join("rect").attr("class", lado)
      .attr("x", d => lado === "e" ? escala(d[campoPct]) : escala(0))
      .attr("y", d => y(d.faixa)).attr("height", y.bandwidth())
      .attr("width", d => Math.abs(escala(d[campoPct]) - escala(0)))
      .attr("fill", corBarra).attr("rx", 2)
      .on("mousemove", (e, d) => mostrarDica(e, `<b>${d.faixa}</b><br>${lado === "e" ? "Homens" : "Mulheres"}: ${num(d[campoAbs])} (${pct(d[campoPct])})`))
      .on("mouseleave", esconderDica);
    s.selectAll(`text.v${lado}`).data(dadosPct).join("text").attr("class", `v${lado}`)
      .attr("x", d => escala(d[campoPct]) + (lado === "e" ? -6 : 6))
      .attr("y", d => y(d.faixa) + y.bandwidth() / 2)
      .attr("text-anchor", ancora).attr("dominant-baseline", "central")
      .attr("font-size", 10.5).attr("fill", CORES.texto3).text(d => pct(d[campoPct]));
  };
  desenhar("e", xe, "ph", "homens", cor.homens, "end");
  desenhar("d", xd, "pm", "mulheres", cor.mulheres, "start");

  s.selectAll("text.faixa").data(dadosPct).join("text").attr("class", "faixa")
    .attr("x", meio).attr("y", d => y(d.faixa) + y.bandwidth() / 2)
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .attr("font-size", 11).attr("fill", CORES.texto2).text(d => d.faixa.replace(" anos", "").replace(" ou mais", "+"));

  s.append("text").attr("x", 46).attr("y", altura - 6).attr("font-size", 12)
    .attr("font-weight", 600).attr("fill", cor.homens).text("Homens");
  s.append("text").attr("x", L - 46).attr("y", altura - 6).attr("text-anchor", "end")
    .attr("font-size", 12).attr("font-weight", 600).attr("fill", cor.mulheres).text("Mulheres");
  return s;
}

function empilhada100(pai, series, opcoes = {}) {
  // series: [{nome, partes:[{rotulo, pct, valor}]}]
  const alturaLinha = 44, altura = series.length * alturaLinha + 18;
  const s = svg(pai, altura);
  const margemEsq = opcoes.margemEsq ?? 158;
  const x = d3.scaleLinear().domain([0, 100]).range([margemEsq, L - 12]);
  const y = d3.scaleBand().domain(series.map(d => d.nome)).range([4, 4 + series.length * alturaLinha]).padding(0.42);
  const rotulos = series[0].partes.map(p => p.rotulo);
  const cor = d3.scaleOrdinal().domain(rotulos).range(PALETA);

  series.forEach(serie => {
    let acumulado = 0;
    const segmentos = serie.partes.map(p => { const s0 = acumulado; acumulado += p.pct; return { ...p, s0 }; });
    const g = s.append("g");
    g.selectAll("rect").data(segmentos).join("rect")
      .attr("x", d => x(d.s0)).attr("y", y(serie.nome))
      .attr("width", d => Math.max(0, x(d.s0 + d.pct) - x(d.s0))).attr("height", y.bandwidth())
      .attr("fill", d => cor(d.rotulo))
      .on("mousemove", (e, d) => mostrarDica(e, `<b>${serie.nome}</b><br>${d.rotulo}: ${num(d.valor)} (${pct(d.pct)})`))
      .on("mouseleave", esconderDica);
    g.selectAll("text").data(segmentos.filter(d => d.pct >= 7)).join("text")
      .attr("x", d => x(d.s0 + d.pct / 2)).attr("y", y(serie.nome) + y.bandwidth() / 2)
      .attr("text-anchor", "middle").attr("dominant-baseline", "central")
      .attr("font-size", 11).attr("font-weight", 700).attr("fill", "#fff")
      .text(d => Math.round(d.pct) + "%");
    s.append("text").attr("x", margemEsq - 10).attr("y", y(serie.nome) + y.bandwidth() / 2)
      .attr("text-anchor", "end").attr("dominant-baseline", "central")
      .attr("font-size", 12.5).attr("fill", CORES.texto2).text(serie.nome);
  });

  legenda(pai, rotulos.map(r => [r, cor(r)]));
  return s;
}

function donut(pai, partes, corPrincipal) {
  const altura = 210, raio = 78, cx = L / 2, cy = altura / 2;
  const s = svg(pai, altura);
  const total = d3.sum(partes, d => d.valor) || 1;
  const arcos = d3.pie().sort(null).value(d => d.valor)(partes);
  const arco = d3.arc().innerRadius(raio * 0.62).outerRadius(raio);
  const cores = [corPrincipal, CORES.neutro];

  const g = s.append("g").attr("transform", `translate(${cx},${cy})`);
  g.selectAll("path").data(arcos).join("path").attr("d", arco)
    .attr("fill", (d, i) => cores[i % cores.length]).attr("stroke", "#fff").attr("stroke-width", 2)
    .on("mousemove", (e, d) => mostrarDica(e, `<b>${d.data.rotulo}</b><br>${num(d.data.valor)} (${pct(100 * d.data.valor / total)})`))
    .on("mouseleave", esconderDica);

  g.append("text").attr("text-anchor", "middle").attr("y", -4)
    .attr("font-size", 23).attr("font-weight", 700).attr("fill", CORES.texto)
    .text(pct(100 * partes[0].valor / total));
  g.append("text").attr("text-anchor", "middle").attr("y", 16)
    .attr("font-size", 11.5).attr("fill", CORES.texto3).text(partes[0].rotulo);

  legenda(pai, partes.map((p, i) => [`${p.rotulo} — ${num(p.valor)}`, cores[i % cores.length]]));
  return s;
}

function colunas(pai, dados, cor, opcoes = {}) {
  const altura = 250, margem = { topo: 14, dir: 12, base: 56, esq: 44 };
  const s = svg(pai, altura);
  const x = d3.scaleBand().domain(dados.map(d => d.rotulo)).range([margem.esq, L - margem.dir]).padding(0.3);
  const y = d3.scaleLinear().domain([0, (d3.max(dados, d => d.valor) || 1) * 1.18]).range([altura - margem.base, margem.topo]);

  s.append("g").attr("transform", `translate(${margem.esq},0)`)
    .call(d3.axisLeft(y).ticks(4).tickFormat(v => num(v)))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("x2", L - margem.dir - margem.esq).attr("stroke", CORES.grade))
    .selectAll("text").attr("font-size", 11).attr("fill", CORES.texto3);

  s.selectAll("rect").data(dados).join("rect")
    .attr("x", d => x(d.rotulo)).attr("y", d => y(d.valor))
    .attr("width", x.bandwidth()).attr("height", d => Math.max(0, y(0) - y(d.valor)))
    .attr("rx", 3).attr("fill", d => opcoes.corPorItem ? opcoes.corPorItem(d) : cor)
    .on("mousemove", (e, d) => mostrarDica(e, `<b>${d.rotulo}</b><br>${num(d.valor)}${d.nota ? "<br>" + d.nota : ""}`))
    .on("mouseleave", esconderDica);

  s.selectAll("text.v").data(dados).join("text").attr("class", "v")
    .attr("x", d => x(d.rotulo) + x.bandwidth() / 2).attr("y", d => y(d.valor) - 7)
    .attr("text-anchor", "middle").attr("font-size", 11.5).attr("font-weight", 600)
    .attr("fill", CORES.texto).text(d => num(d.valor) + (opcoes.sufixo || ""));

  s.append("g").attr("transform", `translate(0,${altura - margem.base})`)
    .call(d3.axisBottom(x).tickSize(0)).call(g => g.select(".domain").attr("stroke", CORES.grade))
    .selectAll("text").attr("font-size", 11).attr("fill", CORES.texto2)
    .attr("transform", "rotate(-20)").attr("text-anchor", "end").attr("dx", -4).attr("dy", 8);
  return s;
}

function mapa(pai, destaque) {
  const altura = 330;
  const s = svg(pai, altura);
  const projecao = d3.geoMercator().fitExtent([[14, 14], [L - 14, altura - 14]], GEO);
  const caminho = d3.geoPath(projecao);

  s.selectAll("path").data(GEO.features).join("path")
    .attr("d", caminho)
    .attr("fill", d => {
      const nome = d.properties.nm_dist;
      if (nome === destaque) return CORDIST[nome] || CORES.azul;
      return d.properties.alvo ? (CORDIST[nome] || CORES.azul) : "#e2e0d6";
    })
    // sem destaque, os dois distritos analisados aparecem na cor deles esmaecida;
    // os outros ficam cinza, so como referencia geografica
    .attr("fill-opacity", d => {
      if (d.properties.nm_dist === destaque) return 1;
      return d.properties.alvo ? 0.3 : 1;
    })
    .attr("stroke", "#fff").attr("stroke-width", 1.6)
    .on("mousemove", (e, d) => mostrarDica(e,
      `<b>${d.properties.nm_dist}</b><br>${num(d.properties.populacao)} pessoas<br>${num(d.properties.area_km2, 1)} km²`))
    .on("mouseleave", esconderDica);

  s.selectAll("text").data(GEO.features).join("text")
    .attr("x", d => caminho.centroid(d)[0]).attr("y", d => caminho.centroid(d)[1])
    .attr("text-anchor", "middle").attr("font-size", 11)
    .attr("font-weight", d => d.properties.nm_dist === destaque ? 700 : 400)
    .attr("fill", d => d.properties.nm_dist === destaque ? "#fff" : CORES.texto)
    .attr("pointer-events", "none")
    .text(d => d.properties.nm_dist);

  const pontos = DADOS.saude_pontos.filter(p => p.lat && p.lon);
  s.append("g").selectAll("circle").data(pontos).join("circle")
    .attr("cx", d => projecao([d.lon, d.lat])[0]).attr("cy", d => projecao([d.lon, d.lat])[1])
    .attr("r", 3).attr("fill", d => d.sus ? CORES.verde : CORES.texto3)
    .attr("fill-opacity", 0.85).attr("stroke", "#fff").attr("stroke-width", 0.6)
    .on("mousemove", (e, d) => mostrarDica(e, `<b>${d.nome}</b><br>${d.tipo}<br>${d.distrito}${d.sus ? "<br>Atende pelo SUS" : ""}`))
    .on("mouseleave", esconderDica);

  legenda(pai, [["Estabelecimento de saúde que atende pelo SUS", CORES.verde],
                ["Estabelecimento que não atende pelo SUS", CORES.texto3]]);
  return s;
}

// ---------------------------------------------------------------- paineis

function cartoes(pai, itens) {
  const div = pai.append("div").attr("class", "cartoes");
  itens.forEach(i => {
    const c = div.append("div").attr("class", "cartao");
    c.append("div").attr("class", "valor").text(i.valor);
    c.append("div").attr("class", "rotulo").text(i.rotulo);
    if (i.nota) c.append("div").attr("class", "nota").text(i.nota);
  });
}

function painelDistrito(pai, nome) {
  const d = DADOS.por_distrito[nome];
  const cor = CORDIST[nome];
  const r = d.resumo;

  pai.append("h2").attr("class", "secao").text(nome);
  pai.append("p").attr("class", "secao-sub")
    .text("Distrito de Brumadinho-MG. Todos os números desta aba são só deste distrito.");

  cartoes(pai, [
    { valor: num(r.populacao), rotulo: "Pessoas residentes" },
    { valor: num(r.domicilios_ocupados), rotulo: "Domicílios ocupados" },
    { valor: num(r.area_km2, 1), rotulo: "Área (km²)" },
    { valor: num(r.densidade, 1), rotulo: "Habitantes por km²" },
    { valor: num(r.media_moradores, 1), rotulo: "Moradores por domicílio" },
    { valor: num(d.saude.total), rotulo: "Estabelecimentos de saúde", nota: `${num(d.saude.sus)} atendem pelo SUS` },
  ]);

  if (d.quilombolas.total > 0) {
    pai.append("div").attr("class", "destaque").append("p").html(
      `<strong>${num(d.quilombolas.total)} moradores se declararam quilombolas</strong> — ` +
      `${pct(100 * d.quilombolas.total / r.populacao)} da população do distrito.`);
  }
  if (d.saude.total === 0) {
    pai.append("div").attr("class", "destaque").append("p").html(
      "<strong>Nenhum estabelecimento de saúde cadastrado no CNES dentro dos limites do distrito.</strong> " +
      "O atendimento depende de unidades em outros distritos de Brumadinho.");
  }

  mapa(bloco(pai, "Onde fica o distrito", "Os cinco distritos de Brumadinho; os pontos são estabelecimentos de saúde do CNES.",
    "Malha territorial do Censo 2022 (IBGE) e CNES / Ministério da Saúde, consultado em 2026."), nome);

  const grade1 = pai.append("div").attr("class", "grade");

  piramide(bloco(grade1, "Pirâmide etária", "% da população residente por sexo e faixa de idade",
    "Variáveis V01009–V01030, arquivo 'demografia'. Diferenças de poucas unidades entre a soma por sexo e o total vêm da proteção de confidencialidade do IBGE em áreas pequenas."),
    d.piramide, { homens: CORES.azul, mulheres: CORES.laranja });

  barrasHorizontais(bloco(grade1, "População por cor ou raça", "% da população residente",
    "Variáveis V01317–V01321, arquivo 'cor_ou_raca'."),
    d.cor_raca, { cor: (x, i) => PALETA[i % PALETA.length] });

  barrasHorizontais(bloco(grade1, "Cor ou raça de quem responde pelo domicílio", "% dos domicílios particulares permanentes ocupados",
    "Soma das variáveis V01254–V01263 (com e sem óbito no domicílio), arquivo 'obitos'."),
    d.cor_raca_responsavel, { cor: (x, i) => PALETA[i % PALETA.length] });

  const alfab = d.alfabetizacao;
  donut(bloco(grade1, "Alfabetização — 15 anos ou mais", null,
    "Variáveis V00900 e V00901, arquivo 'alfabetizacao'."),
    [{ rotulo: "Alfabetizados", valor: alfab.alfabetizados }, { rotulo: "Não alfabetizados", valor: alfab.nao_alfabetizados }], cor);

  colunas(bloco(pai, "Taxa de alfabetização por faixa etária",
    "Mostra em quais gerações a iliteracia está concentrada",
    "Alfabetizados (V00748–V00760) sobre o total (V00644–V00656) de cada faixa, arquivo 'alfabetizacao'."),
    alfab.por_idade.map(f => ({ rotulo: f.faixa, valor: f.taxa == null ? 0 : +f.taxa.toFixed(1), nota: `${num(f.alfabetizados)} de ${num(f.total)} pessoas` })), cor, { sufixo: "%" });

  const san = d.saneamento;
  empilhada100(bloco(pai, "Abastecimento de água",
    "% dos domicílios particulares permanentes ocupados — proxy de condições sanitárias, não indicador de saúde",
    "Variáveis V00111–V00118, arquivo 'caracteristicas_domicilio2'."),
    [{ nome: "Abastecimento de água", partes: san.agua }], { margemEsq: 168 });
  empilhada100(bloco(pai, "Esgotamento sanitário", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00309–V00316, arquivo 'caracteristicas_domicilio2'."),
    [{ nome: "Esgotamento sanitário", partes: san.esgoto }], { margemEsq: 168 });
  empilhada100(bloco(pai, "Destino do lixo", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00397–V00402, arquivo 'caracteristicas_domicilio2'."),
    [{ nome: "Destino do lixo", partes: san.lixo }], { margemEsq: 168 });

  const grade2 = pai.append("div").attr("class", "grade");

  barrasHorizontais(bloco(grade2, "Moradores por domicílio", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00017–V00026, arquivo 'caracteristicas_domicilio1'."),
    d.domicilios.moradores, { cor, margemEsq: 60 });

  barrasHorizontais(bloco(grade2, "Composição das unidades domésticas", "% dos domicílios, por tipo de arranjo familiar",
    "Variáveis V01209–V01212, arquivo 'parentesco'."),
    d.domicilios.composicao, { cor });

  barrasHorizontais(bloco(grade2, "Espécie do domicílio", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00047–V00052, arquivo 'caracteristicas_domicilio1'."),
    d.domicilios.especie.filter(x => x.valor > 0), { cor });

  donut(bloco(grade2, "Banheiro de uso exclusivo", "Com chuveiro e vaso sanitário",
    "Variáveis V00494 e V00495, arquivo 'caracteristicas_domicilio2'."),
    [{ rotulo: "Com banheiro exclusivo", valor: san.banheiro.com }, { rotulo: "Sem banheiro exclusivo", valor: san.banheiro.sem }], cor);

  // Obitos
  const ob = d.obitos;
  pai.append("h2").attr("class", "secao").text("Mortalidade declarada no Censo");
  pai.append("p").attr("class", "secao-sub").text(
    "O Censo 2022 perguntou se alguém que morava no domicílio faleceu entre janeiro de 2019 e julho de 2022. " +
    "É a única abertura de mortalidade publicada pelo IBGE no nível de distrito.");

  cartoes(pai, [
    { valor: num(ob.domicilios_com_obito), rotulo: "Domicílios com óbito no período" },
    { valor: pct(100 * ob.domicilios_com_obito / (ob.domicilios_com_obito + ob.domicilios_sem_obito)), rotulo: "% dos domicílios" },
    { valor: num(ob.homens), rotulo: "Falecidos homens" },
    { valor: num(ob.mulheres), rotulo: "Falecidas mulheres" },
  ]);

  const grade3 = pai.append("div").attr("class", "grade");
  barrasAgrupadas(bloco(grade3, "Óbitos por sexo e idade ao falecer", "Pessoas falecidas entre jan/2019 e jul/2022",
    "Variáveis V01228–V01249, arquivo 'obitos'."),
    ob.por_idade.map(f => f.faixa),
    [{ nome: "Homens", cor: CORES.azul, valores: ob.por_idade.map(f => f.homens) },
     { nome: "Mulheres", cor: CORES.laranja, valores: ob.por_idade.map(f => f.mulheres) }]);

  colunas(bloco(grade3, "Óbitos por semestre",
    "Dois eventos caem dentro da série: o rompimento da barragem da Mina Córrego do Feijão (25/01/2019) e a segunda onda da covid-19 (1º semestre de 2021)",
    "Variáveis V01264–V01270, arquivo 'obitos'. O Censo registra o semestre do falecimento, não a causa: a série não permite atribuir mortes a nenhum dos dois eventos. A soma dos semestres é menor que o total de falecidos porque nem todo registro traz a data."),
    ob.por_periodo.map(p => ({ rotulo: p.periodo, valor: p.valor })), cor,
    { corPorItem: p => ["1º sem. 2019", "1º sem. 2021"].includes(p.rotulo) ? CORES.vermelho : cor });

  // Quilombolas
  if (d.quilombolas.total > 0) {
    const q = d.quilombolas;
    pai.append("h2").attr("class", "secao").text("População quilombola");
    const grade4 = pai.append("div").attr("class", "grade");
    barrasHorizontais(bloco(grade4, "Pessoas quilombolas por faixa etária", `${num(q.total)} pessoas no distrito`,
      "Variáveis V03199–V03203, arquivo 'pessoas_quilombolas'."),
      q.por_idade.map(f => ({ rotulo: f.faixa, valor: f.valor, pct: 100 * f.valor / q.total })), { cor: CORES.roxo });
    donut(bloco(grade4, "Quilombolas por sexo", null, "Variáveis V03197 e V03198, arquivo 'pessoas_quilombolas'."),
      [{ rotulo: "Homens", valor: q.homens }, { rotulo: "Mulheres", valor: q.mulheres }], CORES.roxo);
  }

  // Saude
  pai.append("h2").attr("class", "secao").text("Estabelecimentos de saúde no distrito");
  const blocoSaude = bloco(pai, "Unidades cadastradas no CNES dentro dos limites do distrito",
    "Cada estabelecimento foi atribuído a um distrito cruzando suas coordenadas com a malha territorial do IBGE.",
    "CNES / Ministério da Saúde (API de dados abertos) e malha do Censo 2022 (IBGE).");
  const tipos = Object.entries(d.saude.por_tipo || {});
  if (!tipos.length) {
    blocoSaude.append("p").attr("class", "vazio")
      .text("Nenhum estabelecimento cadastrado dentro dos limites deste distrito.");
  } else {
    const t = blocoSaude.append("table").attr("class", "tabela");
    t.append("thead").append("tr").selectAll("th").data(["Tipo de estabelecimento", "Quantidade"]).join("th")
      .attr("class", (x, i) => i ? "num" : null).text(x => x);
    const linhas = t.append("tbody").selectAll("tr").data(tipos.sort((a, b) => b[1] - a[1])).join("tr");
    linhas.append("td").text(x => x[0]);
    linhas.append("td").attr("class", "num").text(x => num(x[1]));
  }
}

function painelComparacao(pai) {
  const nomes = DADOS.distritos;
  pai.append("h2").attr("class", "secao").text("Os dois distritos lado a lado");
  pai.append("p").attr("class", "secao-sub").text(
    "Comparação direta. Nas abas de cada distrito, os mesmos indicadores aparecem sozinhos, sem o outro distrito no gráfico.");

  const t = pai.append("div").attr("class", "bloco").append("table").attr("class", "tabela");
  const linhasTabela = [
    ["População residente", d => num(d.resumo.populacao)],
    ["Domicílios ocupados", d => num(d.resumo.domicilios_ocupados)],
    ["Área (km²)", d => num(d.resumo.area_km2, 1)],
    ["Habitantes por km²", d => num(d.resumo.densidade, 1)],
    ["Moradores por domicílio", d => num(d.resumo.media_moradores, 1)],
    ["Alfabetização (15+)", d => pct(100 * d.alfabetizacao.alfabetizados / (d.alfabetizacao.alfabetizados + d.alfabetizacao.nao_alfabetizados))],
    ["Domicílios com água da rede geral", d => pct(d.saneamento.agua.find(a => a.rotulo === "Rede geral").pct)],
    ["Domicílios com esgoto em rede geral", d => pct(d.saneamento.esgoto.find(a => a.rotulo === "Rede geral/pluvial").pct)],
    ["Lixo coletado por serviço de limpeza", d => pct(d.saneamento.lixo.find(a => a.rotulo === "Coletado por serviço de limpeza").pct)],
    ["Domicílios com banheiro exclusivo", d => pct(d.saneamento.banheiro.pct_com)],
    ["Responsável pelo domicílio preta ou parda", d => pct(d.cor_raca_responsavel.filter(c => c.rotulo === "Preta" || c.rotulo === "Parda").reduce((s, c) => s + c.pct, 0))],
    ["Pessoas quilombolas", d => num(d.quilombolas.total)],
    ["Domicílios com óbito (2019–2022)", d => num(d.obitos.domicilios_com_obito)],
    ["Estabelecimentos de saúde no distrito", d => num(d.saude.total)],
  ];
  t.append("thead").append("tr").selectAll("th").data(["Indicador", ...nomes]).join("th")
    .attr("class", (x, i) => i ? "num" : null).text(x => x);
  const tr = t.append("tbody").selectAll("tr").data(linhasTabela).join("tr");
  tr.append("td").text(l => l[0]);
  nomes.forEach(n => tr.append("td").attr("class", "num").text(l => l[1](DADOS.por_distrito[n])));

  mapa(bloco(pai, "Os cinco distritos de Brumadinho",
    "Em cinza-claro, os dois distritos analisados; os pontos são estabelecimentos de saúde do CNES.",
    "Malha territorial do Censo 2022 (IBGE) e CNES / Ministério da Saúde."), null);

  const grade = pai.append("div").attr("class", "grade");
  nomes.forEach(nome => {
    const d = DADOS.por_distrito[nome];
    piramide(bloco(grade, `Pirâmide etária — ${nome}`, "% da população residente",
      "Variáveis V01009–V01030, arquivo 'demografia'."),
      d.piramide, { homens: CORES.azul, mulheres: CORES.laranja });
  });

  empilhada100(bloco(pai, "Abastecimento de água", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00111–V00118, arquivo 'caracteristicas_domicilio2'."),
    nomes.map(n => ({ nome: n, partes: DADOS.por_distrito[n].saneamento.agua })));

  empilhada100(bloco(pai, "Esgotamento sanitário", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00309–V00316, arquivo 'caracteristicas_domicilio2'."),
    nomes.map(n => ({ nome: n, partes: DADOS.por_distrito[n].saneamento.esgoto })));

  empilhada100(bloco(pai, "Destino do lixo", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00397–V00402, arquivo 'caracteristicas_domicilio2'."),
    nomes.map(n => ({ nome: n, partes: DADOS.por_distrito[n].saneamento.lixo })));

  const faixas = DADOS.por_distrito[nomes[0]].alfabetizacao.por_idade.map(f => f.faixa);
  barrasAgrupadas(bloco(pai, "Taxa de alfabetização por faixa etária", "% de pessoas alfabetizadas em cada faixa",
    "Alfabetizados (V00748–V00760) sobre o total (V00644–V00656) de cada faixa, arquivo 'alfabetizacao'."),
    faixas,
    nomes.map(n => ({
      nome: n, cor: CORDIST[n],
      valores: DADOS.por_distrito[n].alfabetizacao.por_idade.map(f => f.taxa == null ? 0 : +f.taxa.toFixed(1)),
    })), { formato: v => pct(v) });
}

function painelMunicipio(pai) {
  const m = DADOS.municipio;
  pai.append("h2").attr("class", "secao").text("Contexto municipal — Brumadinho");
  pai.append("p").attr("class", "secao-sub").text(
    "Renda, emprego e salário não têm abertura oficial por distrito: a RAIS e o Censo só publicam esses temas " +
    "no nível de município. Os números abaixo são de Brumadinho inteiro e servem de pano de fundo, não de retrato dos distritos.");

  cartoes(pai, m.indicadores_ibge.map(i => ({ valor: i.valor, rotulo: i.rotulo, nota: i.fonte })));

  barrasHorizontais(bloco(pai, "Empregos formais por setor de atividade",
    `${num(m.total_empregos)} vínculos formais em Brumadinho, 2024`,
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024 — seções da CNAE 2.0."),
    m.emprego_por_secao.filter(s => s.pct >= 0.5).map(s => ({ rotulo: s.nome, valor: s.valor, pct: s.pct })),
    { cor: (d, i) => i === 0 ? CORES.vermelho : CORES.azul, margemEsq: 230 });

  const grade = pai.append("div").attr("class", "grade");

  barrasHorizontais(bloco(grade, "Salário médio real por escolaridade", "Média mensal dos vínculos formais, 2024",
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024."),
    m.salario_por_escolaridade.map(s => ({ rotulo: s.escolaridade, valor: s.valor, pct: s.valor })),
    { cor: CORES.verde, formato: d => reais(d.valor), campo: "valor", margemEsq: 170,
      dica: d => `<b>${d.rotulo}</b><br>${reais(d.valor)} por mês` });

  barrasHorizontais(bloco(grade, "Salário médio real por sexo e cor/raça", "Média mensal dos vínculos formais, 2024",
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024. BrAm = brancos e amarelos; PPI = pretos, pardos e indígenas."),
    m.salario_por_sexo_raca.map(s => ({ rotulo: s.grupo.replace(" - ", " · "), valor: s.valor, pct: s.valor })),
    { cor: d => d.rotulo.startsWith("Homem") ? CORES.azul : CORES.laranja, formato: d => reais(d.valor), campo: "valor", margemEsq: 150,
      dica: d => `<b>${d.rotulo}</b><br>${reais(d.valor)} por mês` });

  const totalVinculos = d3.sum(m.vinculos_por_escolaridade, v => v.valor) || 1;
  barrasHorizontais(bloco(grade, "Vínculos formais por escolaridade", "% dos vínculos formais, 2024",
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024."),
    m.vinculos_por_escolaridade.map(v => ({ rotulo: v.escolaridade, valor: v.valor, pct: 100 * v.valor / totalVinculos })),
    { cor: CORES.roxo, margemEsq: 170 });

  const porDistrito = Object.entries(DADOS.saude_municipio)
    .map(([nome, v]) => ({ rotulo: nome, valor: v.total, pct: v.total }))
    .sort((a, b) => b.valor - a.valor);
  barrasHorizontais(bloco(grade, "Estabelecimentos de saúde por distrito", "Todos os distritos de Brumadinho, CNES",
    "CNES / Ministério da Saúde cruzado com a malha do Censo 2022. 'Sem coordenada' e 'fora dos limites' são falhas de cadastro no CNES."),
    porDistrito, { cor: d => CORDIST[d.rotulo] || CORES.neutro, formato: d => num(d.valor), campo: "valor", margemEsq: 210,
      dica: d => `<b>${d.rotulo}</b><br>${num(d.valor)} estabelecimentos` });
}

// ---------------------------------------------------------------- app

function render() {
  const painel = d3.select("#painel").html("");
  if (ABA === "Comparação") painelComparacao(painel);
  else if (ABA === "Contexto municipal") painelMunicipio(painel);
  else painelDistrito(painel, ABA);
  d3.selectAll("#abas button").attr("aria-current", function () { return this.textContent === ABA ? "true" : null; });
  window.scrollTo({ top: 0, behavior: "instant" });
}

Promise.all([d3.json("dados/indicadores.json"), d3.json("dados/distritos.geojson")]).then(([dados, geo]) => {
  DADOS = dados;
  GEO = geo;
  const abas = ["Comparação", ...dados.distritos, "Contexto municipal"];
  ABA = abas[0];
  d3.select("#abas").selectAll("button").data(abas).join("button")
    .text(x => x).on("click", (e, x) => { ABA = x; render(); });
  render();
});
