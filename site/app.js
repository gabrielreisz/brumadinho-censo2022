const CORES = {
  azul: "#2a78d6", laranja: "#eb6834", verde: "#1baf7a", amarelo: "#eda100",
  roxo: "#4a3aa7", vermelho: "#e34948", rosa: "#e87ba4", neutro: "#c6c5ba",
  texto: "#14140f", texto2: "#55544e", texto3: "#8b8981", grade: "#e4e3dc",
};

// Cor fixa por distrito: a identidade nao muda entre graficos
const CORDIST = { "São José do Paraopeba": CORES.laranja, "Conceição de Itaguá": CORES.azul };
const PALETA = [CORES.azul, CORES.verde, CORES.amarelo, CORES.laranja, CORES.vermelho, CORES.roxo, CORES.rosa, CORES.neutro];

const TEMAS = [
  ["demografia", "Demografia"],
  ["cor_raca", "Cor e raça"],
  ["educacao", "Educação"],
  ["saude", "Saúde"],
  ["saneamento", "Saneamento"],
  ["domicilios", "Domicílios"],
  ["mortalidade", "Mortalidade"],
  ["quilombolas", "Quilombolas"],
  ["renda", "Renda e trabalho"],
  ["historico", "Série histórica"],
  ["territorio", "Território"],
  ["barragens", "Barragens e rompimento"],
];

const num = (v, casas = 0) => v == null || Number.isNaN(v) ? "—" :
  v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const pct = (v, casas = 1) => num(v, casas) + "%";
const reais = v => "R$ " + num(v, 0);

const L = 700; // largura de referencia do viewBox; o CSS estica pra caber

let DADOS, GEO, SETORES, ABA;
let ativos = new Set(TEMAS.map(t => t[0]));
const dica = d3.select("body").append("div").attr("class", "dica");

function mostrarDica(evento, html) {
  dica.html(html).style("opacity", 1)
    .style("left", (evento.pageX + 14) + "px")
    .style("top", (evento.pageY - 12) + "px");
}
const esconderDica = () => dica.style("opacity", 0);

function bloco(pai, tema, titulo, sub, fonte) {
  const div = pai.append("div").attr("class", "bloco").attr("data-tema", tema);
  div.append("h3").text(titulo);
  if (sub) div.append("p").attr("class", "sub").text(sub);
  const corpo = div.append("div");
  if (fonte) div.append("p").attr("class", "fonte").text(fonte);
  return corpo;
}

function secao(pai, tema, titulo, sub) {
  const div = pai.append("div").attr("data-tema", tema);
  div.append("h2").attr("class", "secao").text(titulo);
  if (sub) div.append("p").attr("class", "secao-sub").text(sub);
  return div;
}

function grade(pai, tema) {
  return pai.append("div").attr("class", "grade").attr("data-grade", tema || "");
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

function tabela(pai, colunas, linhas) {
  const t = pai.append("table").attr("class", "tabela");
  t.append("thead").append("tr").selectAll("th").data(colunas).join("th")
    .attr("class", (c, i) => i && c.num !== false ? "num" : null)
    .text(c => c.rotulo ?? c);
  const tr = t.append("tbody").selectAll("tr").data(linhas).join("tr");
  colunas.forEach((c, i) => {
    tr.append("td").attr("class", i && c.num !== false ? "num" : null).text(l => l[i]);
  });
  return t;
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
  const altura = opcoes.altura ?? 300, margem = { topo: 10, dir: 10, base: 62, esq: 52 };
  const s = svg(pai, altura);

  const x0 = d3.scaleBand().domain(categorias).range([margem.esq, L - margem.dir]).padding(0.22);
  const x1 = d3.scaleBand().domain(series.map(s => s.nome)).range([0, x0.bandwidth()]).padding(0.12);
  const maxv = d3.max(series, s => d3.max(s.valores)) || 1;
  const y = d3.scaleLinear().domain([0, maxv * 1.14]).range([altura - margem.base, margem.topo]);

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
    const g = s.append("g");
    const pontos = categorias.map((c, i) => ({ c, v: serie.valores[i] }));
    g.selectAll("rect").data(pontos).join("rect")
      .attr("x", d => x0(d.c) + x1(serie.nome)).attr("y", d => y(d.v))
      .attr("width", x1.bandwidth()).attr("height", d => Math.max(0, y(0) - y(d.v)))
      .attr("rx", 2).attr("fill", serie.cor)
      .on("mousemove", (e, d) => mostrarDica(e, `<b>${serie.nome}</b><br>${d.c}: ${formato(d.v)}`))
      .on("mouseleave", esconderDica);
    if (opcoes.rotulos) {
      g.selectAll("text").data(pontos).join("text")
        .attr("x", d => x0(d.c) + x1(serie.nome) + x1.bandwidth() / 2).attr("y", d => y(d.v) - 5)
        .attr("text-anchor", "middle").attr("font-size", 10).attr("fill", CORES.texto2)
        .text(d => formato(d.v));
    }
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

  const idRecorte = "recorte-mapa-" + (destaque || "geral").replace(/\W/g, "");
  s.append("clipPath").attr("id", idRecorte).append("rect")
    .attr("x", 0).attr("y", 0).attr("width", L).attr("height", altura);

  s.selectAll("path").data(GEO.features).join("path")
    .attr("d", caminho)
    .attr("fill", d => {
      const nome = d.properties.nm_dist;
      if (nome === destaque) return CORDIST[nome] || CORES.azul;
      return d.properties.alvo ? (CORDIST[nome] || CORES.azul) : "#e2e0d6";
    })
    .attr("fill-opacity", d => d.properties.nm_dist === destaque ? 1 : (d.properties.alvo ? 0.3 : 1))
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

  // Dois estabelecimentos tem coordenada fora do poligono municipal (erro de
  // cadastro do CNES) e ficariam desenhados por cima do resto da pagina.
  const pontos = DADOS.saude_pontos.filter(p => p.lat && p.lon && p.dentro);
  s.append("g").attr("clip-path", `url(#${idRecorte})`)
    .selectAll("circle").data(pontos).join("circle")
    .attr("cx", d => projecao([d.lon, d.lat])[0]).attr("cy", d => projecao([d.lon, d.lat])[1])
    .attr("r", 3).attr("fill", d => d.sus ? CORES.verde : CORES.texto3)
    .attr("fill-opacity", 0.85).attr("stroke", "#fff").attr("stroke-width", 0.6)
    .on("mousemove", (e, d) => mostrarDica(e, `<b>${d.nome}</b><br>${d.tipo}<br>${d.distrito}${d.sus ? "<br>Atende pelo SUS" : ""}`))
    .on("mouseleave", esconderDica);

  legenda(pai, [["Estabelecimento de saúde que atende pelo SUS", CORES.verde],
                ["Estabelecimento que não atende pelo SUS", CORES.texto3]]);
  return s;
}

function mapaBarragens(pai) {
  const r = DADOS.rompimento;
  const altura = 360;
  const s = svg(pai, altura);
  const projecao = d3.geoMercator().fitExtent([[14, 14], [L - 14, altura - 14]], GEO);
  const caminho = d3.geoPath(projecao);

  s.append("clipPath").attr("id", "recorte-barragens").append("rect")
    .attr("x", 0).attr("y", 0).attr("width", L).attr("height", altura);

  s.selectAll("path").data(GEO.features).join("path")
    .attr("d", caminho)
    .attr("fill", d => d.properties.alvo ? (CORDIST[d.properties.nm_dist] || CORES.azul) : "#e2e0d6")
    .attr("fill-opacity", d => d.properties.alvo ? 0.22 : 1)
    .attr("stroke", "#fff").attr("stroke-width", 1.6)
    .on("mousemove", (e, d) => mostrarDica(e, `<b>${d.properties.nm_dist}</b><br>${num(d.properties.populacao)} pessoas`))
    .on("mouseleave", esconderDica);

  s.selectAll("text.dist").data(GEO.features).join("text").attr("class", "dist")
    .attr("x", d => caminho.centroid(d)[0]).attr("y", d => caminho.centroid(d)[1])
    .attr("text-anchor", "middle").attr("font-size", 10.5).attr("fill", CORES.texto2)
    .attr("pointer-events", "none").text(d => d.properties.nm_dist);

  const g = s.append("g").attr("clip-path", "url(#recorte-barragens)");
  const corEmergencia = e => e === "Sem emergência" ? CORES.texto3
    : (e === "Emergência Nivel 1" ? CORES.amarelo : CORES.vermelho);

  // local da mina que rompeu, marcado pelo centroide das estruturas que restaram
  const mina = r.barragens.mina_feijao;
  const pm = projecao([mina.lon, mina.lat]);
  g.append("path").attr("transform", `translate(${pm[0]},${pm[1]})`)
    .attr("d", d3.symbol().type(d3.symbolCross).size(150)())
    .attr("fill", CORES.vermelho).attr("stroke", "#fff").attr("stroke-width", 1)
    .attr("transform", `translate(${pm[0]},${pm[1]}) rotate(45)`)
    .on("mousemove", e => mostrarDica(e, "<b>Mina Córrego do Feijão</b><br>Posição aproximada, pelo centroide das " +
      `${mina.estruturas} estruturas que restam no cadastro da ANM<br>A barragem B1 rompeu em 25/01/2019`))
    .on("mouseleave", esconderDica);

  g.selectAll("circle").data(r.barragens.pontos).join("circle")
    .attr("cx", d => projecao([d.lon, d.lat])[0]).attr("cy", d => projecao([d.lon, d.lat])[1])
    .attr("r", d => d.emergencia === "Sem emergência" ? 3.5 : 5)
    .attr("fill", d => corEmergencia(d.emergencia))
    .attr("fill-opacity", 0.9).attr("stroke", "#fff").attr("stroke-width", 0.8)
    .on("mousemove", (e, d) => mostrarDica(e,
      `<b>${d.nome}</b><br>${d.mina || "sem mina informada"}<br>${d.distrito}<br>${d.emergencia}<br>${d.situacao}`))
    .on("mouseleave", esconderDica);

  legenda(pai, [["Sem emergência", CORES.texto3], ["Emergência nível 1", CORES.amarelo],
                ["Emergência nível 2", CORES.vermelho], ["Mina Córrego do Feijão", CORES.vermelho]]);
  return s;
}

function mapaSetores(pai, distrito) {
  const indicadores = SETORES.indicadores;
  const chaves = Object.keys(indicadores);
  const feicoes = SETORES.features.filter(f => !distrito || f.properties.distrito === distrito);
  if (!feicoes.length) { pai.append("p").attr("class", "vazio").text("Sem setores para este recorte."); return; }

  const controles = pai.append("div").attr("class", "controles");
  controles.append("span").attr("class", "controles-rotulo").text("Indicador:");
  const botoes = controles.selectAll("button").data(chaves).join("button")
    .text(k => indicadores[k]).on("click", (e, k) => desenhar(k));

  const area = pai.append("div");
  const rodape = pai.append("p").attr("class", "fonte");

  function desenhar(chave) {
    botoes.attr("aria-current", k => k === chave ? "true" : null);
    area.html("");
    const altura = 340;
    const s = svg(area, altura);
    const colecao = { type: "FeatureCollection", features: feicoes };
    const projecao = d3.geoMercator().fitExtent([[10, 10], [L - 10, altura - 10]], colecao);
    const caminho = d3.geoPath(projecao);
    const valores = feicoes.map(f => f.properties[chave]).filter(v => v != null);
    const escala = d3.scaleSequential()
      .domain([d3.min(valores) ?? 0, d3.max(valores) ?? 100])
      .interpolator(d3.interpolateRgb("#f4eee6", CORES.azul));

    s.selectAll("path").data(feicoes).join("path")
      .attr("d", caminho)
      .attr("fill", f => f.properties[chave] == null ? "#eceae2" : escala(f.properties[chave]))
      .attr("stroke", "#fff").attr("stroke-width", 0.8)
      .on("mousemove", (e, f) => {
        const p = f.properties;
        mostrarDica(e, `<b>Setor ${p.cd_setor.slice(-6)}</b><br>${p.distrito}<br>` +
          `${indicadores[chave]}: ${p[chave] == null ? "sem dado" : pct(p[chave])}<br>` +
          `${num(p.populacao || 0)} pessoas · ${p.situacao}`);
      })
      .on("mouseleave", esconderDica);

    const larguraEscala = 190, x0 = L - larguraEscala - 12, y0 = altura - 26;
    const grad = s.append("defs").append("linearGradient").attr("id", "grad-" + chave);
    d3.range(0, 1.01, 0.1).forEach(t => grad.append("stop")
      .attr("offset", `${t * 100}%`).attr("stop-color", escala(escala.domain()[0] + t * (escala.domain()[1] - escala.domain()[0]))));
    s.append("rect").attr("x", x0).attr("y", y0).attr("width", larguraEscala).attr("height", 9)
      .attr("rx", 2).attr("fill", `url(#grad-${chave})`).attr("stroke", CORES.grade);
    s.append("text").attr("x", x0).attr("y", y0 - 5).attr("font-size", 10.5).attr("fill", CORES.texto3)
      .text(pct(escala.domain()[0], 0));
    s.append("text").attr("x", x0 + larguraEscala).attr("y", y0 - 5).attr("text-anchor", "end")
      .attr("font-size", 10.5).attr("fill", CORES.texto3).text(pct(escala.domain()[1], 0));

    rodape.text(`${feicoes.length} setores censitários. ${indicadores[chave]}, % dos domicílios do setor. ` +
      "Malha e agregados por setor censitário do Censo 2022 (IBGE).");
  }
  desenhar(chaves[0]);
}

// ---------------------------------------------------------------- paineis

function cartoes(pai, tema, itens) {
  const div = pai.append("div").attr("class", "cartoes").attr("data-tema", tema);
  itens.forEach(i => {
    const c = div.append("div").attr("class", "cartao");
    c.append("div").attr("class", "valor").text(i.valor);
    c.append("div").attr("class", "rotulo").text(i.rotulo);
    if (i.nota) c.append("div").attr("class", "nota").text(i.nota);
  });
}

function destaque(pai, tema, html) {
  pai.append("div").attr("class", "destaque").attr("data-tema", tema).append("p").html(html);
}

function painelDistrito(pai, nome) {
  const d = DADOS.por_distrito[nome];
  const cor = CORDIST[nome];
  const r = d.resumo;
  const eq = d.saude_equipes;

  pai.append("h2").attr("class", "secao").text(nome);
  pai.append("p").attr("class", "secao-sub")
    .text("Distrito de Brumadinho-MG. Todos os números desta aba são só deste distrito.");

  cartoes(pai, "demografia", [
    { valor: num(r.populacao), rotulo: "Pessoas residentes" },
    { valor: num(r.domicilios_ocupados), rotulo: "Domicílios ocupados" },
    { valor: num(r.area_km2, 1), rotulo: "Área (km²)" },
    { valor: num(r.densidade, 1), rotulo: "Habitantes por km²" },
    { valor: num(d.escolas.ativas), rotulo: "Escolas em atividade", nota: `${num(d.escolas.matriculas)} matrículas` },
    { valor: num(eq.equipes_que_atendem), rotulo: "Equipes de saúde que atendem", nota: `${num(eq.equipes_sediadas)} sediadas no distrito` },
  ]);

  if (d.quilombolas.total > 0) {
    destaque(pai, "quilombolas",
      `<strong>${num(d.quilombolas.total)} moradores se declararam quilombolas</strong> — ` +
      `${pct(100 * d.quilombolas.total / r.populacao)} da população do distrito.`);
  }
  if (d.saude.total === 0 && eq.equipes_que_atendem > 0) {
    destaque(pai, "saude",
      "<strong>Nenhum estabelecimento de saúde fica dentro dos limites do distrito</strong>, mas " +
      `${eq.equipes_que_atendem === 1 ? "uma equipe de atenção primária tem" : eq.equipes_que_atendem + " equipes têm"} ` +
      "o distrito como área de referência — sediada em unidade de outro distrito.");
  }

  mapa(bloco(pai, "territorio", "Onde fica o distrito",
    "Os cinco distritos de Brumadinho; os pontos são estabelecimentos de saúde do CNES.",
    "Malha territorial do Censo 2022 (IBGE) e CNES / Ministério da Saúde."), nome);

  mapaSetores(bloco(pai, "territorio", "Desigualdade dentro do distrito",
    "Cada polígono é um setor censitário — o recorte mais fino que o Censo publica."), nome);

  const g1 = grade(pai);
  piramide(bloco(g1, "demografia", "Pirâmide etária", "% da população residente por sexo e faixa de idade",
    "Variáveis V01009–V01030, arquivo 'demografia'. Diferenças de poucas unidades entre a soma por sexo e o total vêm da proteção de confidencialidade do IBGE em áreas pequenas."),
    d.piramide, { homens: CORES.azul, mulheres: CORES.laranja });

  barrasHorizontais(bloco(g1, "cor_raca", "População por cor ou raça", "% da população residente",
    "Variáveis V01317–V01321, arquivo 'cor_ou_raca'."),
    d.cor_raca, { cor: (x, i) => PALETA[i % PALETA.length] });

  barrasHorizontais(bloco(g1, "cor_raca", "Cor ou raça de quem responde pelo domicílio",
    "% dos domicílios particulares permanentes ocupados",
    "Soma das variáveis V01254–V01263 (com e sem óbito no domicílio), arquivo 'obitos'."),
    d.cor_raca_responsavel, { cor: (x, i) => PALETA[i % PALETA.length] });

  const alfab = d.alfabetizacao;
  donut(bloco(g1, "educacao", "Alfabetização — 15 anos ou mais", null,
    "Variáveis V00900 e V00901, arquivo 'alfabetizacao'."),
    [{ rotulo: "Alfabetizados", valor: alfab.alfabetizados }, { rotulo: "Não alfabetizados", valor: alfab.nao_alfabetizados }], cor);

  colunas(bloco(pai, "educacao", "Taxa de alfabetização por faixa etária",
    "Mostra em quais gerações a iliteracia está concentrada",
    "Alfabetizados (V00748–V00760) sobre o total (V00644–V00656) de cada faixa, arquivo 'alfabetizacao'."),
    alfab.por_idade.map(f => ({ rotulo: f.faixa, valor: f.taxa == null ? 0 : +f.taxa.toFixed(1), nota: `${num(f.alfabetizados)} de ${num(f.total)} pessoas` })),
    cor, { sufixo: "%" });

  // Educacao basica (INEP)
  secao(pai, "educacao", "Escolas no distrito",
    "Censo Escolar do INEP. Os microdados já trazem o código do distrito, então aqui não houve cruzamento geográfico.");
  const gEsc = grade(pai);
  const etapas = d.escolas.por_etapa.filter(e => e.valor > 0);
  if (etapas.length) {
    const totalMat = d3.sum(etapas, e => e.valor) || 1;
    barrasHorizontais(bloco(gEsc, "educacao", "Matrículas por etapa de ensino",
      `${num(d.escolas.matriculas)} matrículas na educação básica`,
      "Tabela de matrículas do Censo Escolar 2025 (INEP)."),
      etapas.map(e => ({ rotulo: e.rotulo, valor: e.valor, pct: 100 * e.valor / totalMat })),
      { cor, formato: e => num(e.valor), campo: "valor", margemEsq: 210,
        dica: e => `<b>${e.rotulo}</b><br>${num(e.valor)} matrículas` });
  }
  const curtos = { "Educação infantil": "educação infantil", "Fundamental — anos iniciais": "anos iniciais do fundamental",
                   "Fundamental — anos finais": "anos finais do fundamental", "Ensino médio": "ensino médio" };
  const faltando = d.escolas.por_etapa.filter(e => e.valor === 0).map(e => curtos[e.rotulo] || e.rotulo.toLowerCase());
  if (faltando.length) {
    const lista = faltando.length > 1
      ? faltando.slice(0, -1).join(", ") + " nem " + faltando.at(-1)
      : faltando[0];
    destaque(pai, "educacao",
      `<strong>Nenhuma escola do distrito oferece ${lista}.</strong> ` +
      "Quem estuda nessas etapas precisa se deslocar para outro distrito.");
  }
  barrasHorizontais(bloco(gEsc, "educacao", "Infraestrutura das escolas",
    "% das escolas em atividade no distrito que têm cada item",
    "Campos IN_* da tabela de escolas do Censo Escolar 2025 (INEP)."),
    d.escolas.infraestrutura.map(i => ({ rotulo: i.rotulo, valor: i.escolas, pct: i.pct ?? 0 })),
    { cor: i => i.pct === 100 ? CORES.verde : (i.pct === 0 ? CORES.vermelho : cor), margemEsq: 200,
      dica: i => `<b>${i.rotulo}</b><br>${num(i.valor)} de ${num(d.escolas.ativas)} escolas` });

  tabela(bloco(pai, "educacao", "Lista de escolas", null,
    "Censo Escolar 2025 (INEP)."),
    ["Escola", { rotulo: "Rede", num: false }, { rotulo: "Localização", num: false },
     { rotulo: "Área diferenciada", num: false }, { rotulo: "Situação", num: false }, "Matrículas"],
    d.escolas.lista.map(e => [e.nome, e.dependencia, e.localizacao, e.area_diferenciada, e.situacao,
                              e.matriculas == null ? "—" : num(e.matriculas)]));

  // Saneamento
  secao(pai, "saneamento", "Saneamento", "Proxy de condições sanitárias — não são indicadores de saúde.");
  empilhada100(bloco(pai, "saneamento", "Abastecimento de água", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00111–V00118, arquivo 'caracteristicas_domicilio2'."),
    [{ nome: "Abastecimento de água", partes: d.saneamento.agua }], { margemEsq: 168 });
  empilhada100(bloco(pai, "saneamento", "Esgotamento sanitário", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00309–V00316, arquivo 'caracteristicas_domicilio2'."),
    [{ nome: "Esgotamento sanitário", partes: d.saneamento.esgoto }], { margemEsq: 168 });
  empilhada100(bloco(pai, "saneamento", "Destino do lixo", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00397–V00402, arquivo 'caracteristicas_domicilio2'."),
    [{ nome: "Destino do lixo", partes: d.saneamento.lixo }], { margemEsq: 168 });

  // Serie historica
  secao(pai, "historico", "2010 e 2022 lado a lado",
    "Só estes três indicadores têm definição equivalente nos dois censos — as categorias mudaram no resto.");
  barrasAgrupadas(bloco(pai, "historico", "Saneamento em 2010 e 2022", "% dos domicílios particulares permanentes",
    "Censo 2010 (agregados por setor censitário, variáveis V012, V017 e V035 de Domicilio01) e Censo 2022 (arquivo 'caracteristicas_domicilio2'). O número de domicílios do distrito cresceu entre os dois censos, então a queda de um percentual pode significar rede que não acompanhou o crescimento, e não rede desfeita."),
    d.serie_2010.map(t => t.indicador),
    [{ nome: "2010", cor: CORES.neutro, valores: d.serie_2010.map(t => +t["2010"].toFixed(1)) },
     { nome: "2022", cor, valores: d.serie_2010.map(t => +t["2022"].toFixed(1)) }],
    { formato: v => pct(v), rotulos: true, altura: 280 });

  barrasHorizontais(bloco(pai, "renda", "Renda domiciliar per capita em 2010",
    "% dos domicílios particulares por faixa de rendimento",
    "Censo 2010, arquivo DomicilioRenda por setor censitário. Em 2022 a renda saiu do questionário do universo e foi para a amostra, publicada só até município — por isso este é o dado de renda mais recente que existe por distrito."),
    d.renda_2010, { cor: (x, i) => i < 3 ? CORES.vermelho : (i < 5 ? CORES.amarelo : CORES.verde), margemEsq: 140 });

  // Domicilios
  secao(pai, "domicilios", "Domicílios");
  const g2 = grade(pai);
  barrasHorizontais(bloco(g2, "domicilios", "Moradores por domicílio", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00017–V00026, arquivo 'caracteristicas_domicilio1'."),
    d.domicilios.moradores, { cor, margemEsq: 60 });
  barrasHorizontais(bloco(g2, "domicilios", "Composição das unidades domésticas", "% dos domicílios, por tipo de arranjo familiar",
    "Variáveis V01209–V01212, arquivo 'parentesco'."),
    d.domicilios.composicao, { cor });
  barrasHorizontais(bloco(g2, "domicilios", "Espécie do domicílio", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00047–V00052, arquivo 'caracteristicas_domicilio1'."),
    d.domicilios.especie.filter(x => x.valor > 0), { cor });
  donut(bloco(g2, "domicilios", "Banheiro de uso exclusivo", "Com chuveiro e vaso sanitário",
    "Variáveis V00494 e V00495, arquivo 'caracteristicas_domicilio2'."),
    [{ rotulo: "Com banheiro exclusivo", valor: d.saneamento.banheiro.com },
     { rotulo: "Sem banheiro exclusivo", valor: d.saneamento.banheiro.sem }], cor);

  // Mortalidade
  const ob = d.obitos;
  secao(pai, "mortalidade", "Mortalidade declarada no Censo",
    "O Censo 2022 perguntou se alguém que morava no domicílio faleceu entre janeiro de 2019 e julho de 2022. " +
    "É a única abertura de mortalidade publicada pelo IBGE no nível de distrito.");
  cartoes(pai, "mortalidade", [
    { valor: num(ob.domicilios_com_obito), rotulo: "Domicílios com óbito no período" },
    { valor: pct(100 * ob.domicilios_com_obito / (ob.domicilios_com_obito + ob.domicilios_sem_obito)), rotulo: "% dos domicílios" },
    { valor: num(ob.homens), rotulo: "Falecidos homens" },
    { valor: num(ob.mulheres), rotulo: "Falecidas mulheres" },
  ]);
  const g3 = grade(pai);
  barrasAgrupadas(bloco(g3, "mortalidade", "Óbitos por sexo e idade ao falecer", "Pessoas falecidas entre jan/2019 e jul/2022",
    "Variáveis V01228–V01249, arquivo 'obitos'."),
    ob.por_idade.map(f => f.faixa),
    [{ nome: "Homens", cor: CORES.azul, valores: ob.por_idade.map(f => f.homens) },
     { nome: "Mulheres", cor: CORES.laranja, valores: ob.por_idade.map(f => f.mulheres) }]);
  colunas(bloco(g3, "mortalidade", "Óbitos por semestre",
    "Dois eventos caem dentro da série: o rompimento da barragem da Mina Córrego do Feijão (25/01/2019) e a segunda onda da covid-19 (1º semestre de 2021)",
    "Variáveis V01264–V01270, arquivo 'obitos'. O Censo registra o semestre do falecimento, não a causa: a série não permite atribuir mortes a nenhum dos dois eventos. A soma dos semestres é menor que o total de falecidos porque nem todo registro traz a data."),
    ob.por_periodo.map(p => ({ rotulo: p.periodo, valor: p.valor })), cor,
    { corPorItem: p => ["1º sem. 2019", "1º sem. 2021"].includes(p.rotulo) ? CORES.vermelho : cor });

  // Quilombolas
  if (d.quilombolas.total > 0) {
    const q = d.quilombolas;
    secao(pai, "quilombolas", "População quilombola");
    const g4 = grade(pai);
    barrasHorizontais(bloco(g4, "quilombolas", "Pessoas quilombolas por faixa etária", `${num(q.total)} pessoas no distrito`,
      "Variáveis V03199–V03203, arquivo 'pessoas_quilombolas'."),
      q.por_idade.map(f => ({ rotulo: f.faixa, valor: f.valor, pct: 100 * f.valor / q.total })), { cor: CORES.roxo });
    donut(bloco(g4, "quilombolas", "Quilombolas por sexo", null, "Variáveis V03197 e V03198, arquivo 'pessoas_quilombolas'."),
      [{ rotulo: "Homens", valor: q.homens }, { rotulo: "Mulheres", valor: q.mulheres }], CORES.roxo);
  }

  // Saude
  secao(pai, "saude", "Saúde",
    "Estabelecimentos vêm do CNES cruzado com a malha do IBGE; equipes e profissionais, da base completa do CNES.");
  cartoes(pai, "saude", [
    { valor: num(d.saude.total), rotulo: "Estabelecimentos no distrito", nota: `${num(d.saude.sus)} atendem pelo SUS` },
    { valor: num(eq.equipes_que_atendem), rotulo: "Equipes que atendem o distrito" },
    { valor: num(eq.profissionais), rotulo: "Profissionais em equipes sediadas aqui" },
    { valor: r.populacao ? num(1000 * eq.profissionais / r.populacao, 1) : "—", rotulo: "Profissionais por mil habitantes" },
  ]);

  const blocoEquipes = bloco(pai, "saude", "Equipes que têm o distrito como área de referência",
    "Inclui equipe sediada em unidade de outro distrito cuja área de referência cadastrada é este distrito.",
    "Base de dados do CNES (tbEquipe), competência 07/2026.");
  if (!eq.lista_equipes.length) {
    blocoEquipes.append("p").attr("class", "vazio").text("Nenhuma equipe cadastrada com este distrito como referência.");
  } else {
    tabela(blocoEquipes,
      [{ rotulo: "Tipo de equipe", num: false }, { rotulo: "Área de referência", num: false },
       { rotulo: "Sediada em", num: false }, { rotulo: "Populações assistidas", num: false }],
      eq.lista_equipes.map(x => [x.tipo, x.referencia, `${x.estabelecimento} (${x.sediada_em})`, x.populacoes || "—"]));
  }

  const ocupacoes = Object.entries(eq.por_ocupacao || {});
  if (ocupacoes.length) {
    const totalOc = d3.sum(ocupacoes, o => o[1]);
    barrasHorizontais(bloco(pai, "saude", "Profissionais por ocupação",
      "Vínculos ativos em equipes sediadas no distrito",
      "Base de dados do CNES (rlEstabEquipeProf) cruzada com a tabela de CBO, competência 07/2026. O arquivo com nome e CPF dos profissionais não é usado."),
      ocupacoes.map(([rotulo, valor]) => ({ rotulo, valor, pct: 100 * valor / totalOc })),
      { cor, formato: o => num(o.valor), campo: "valor", margemEsq: 260,
        dica: o => `<b>${o.rotulo}</b><br>${num(o.valor)} vínculos` });
  }

  const blocoEstab = bloco(pai, "saude", "Estabelecimentos dentro dos limites do distrito",
    "Cada estabelecimento foi atribuído a um distrito cruzando suas coordenadas com a malha territorial do IBGE.",
    "CNES / Ministério da Saúde. Parte das coordenadas do CNES é aproximada: 14 estabelecimentos do município compartilham coordenada com outro e 3 têm precisão de ~100 m.");
  const tipos = Object.entries(d.saude.por_tipo || {});
  if (!tipos.length) {
    blocoEstab.append("p").attr("class", "vazio")
      .text("Nenhum estabelecimento cadastrado dentro dos limites deste distrito.");
  } else {
    tabela(blocoEstab, [{ rotulo: "Tipo de estabelecimento", num: false }, "Quantidade"],
      tipos.sort((a, b) => b[1] - a[1]).map(t => [t[0], num(t[1])]));
  }
}

function painelComparacao(pai) {
  const nomes = DADOS.distritos;
  pai.append("h2").attr("class", "secao").text("Os dois distritos lado a lado");
  pai.append("p").attr("class", "secao-sub").text(
    "Comparação direta. Nas abas de cada distrito, os mesmos indicadores aparecem sozinhos, sem o outro distrito no gráfico.");

  const linhas = [
    ["demografia", "População residente", d => num(d.resumo.populacao)],
    ["demografia", "Domicílios ocupados", d => num(d.resumo.domicilios_ocupados)],
    ["demografia", "Área (km²)", d => num(d.resumo.area_km2, 1)],
    ["demografia", "Habitantes por km²", d => num(d.resumo.densidade, 1)],
    ["educacao", "Alfabetização (15+)", d => pct(100 * d.alfabetizacao.alfabetizados / (d.alfabetizacao.alfabetizados + d.alfabetizacao.nao_alfabetizados))],
    ["educacao", "Escolas em atividade", d => num(d.escolas.ativas)],
    ["educacao", "Matrículas na educação básica", d => num(d.escolas.matriculas)],
    ["educacao", "Oferta de anos finais do fundamental", d => d.escolas.por_etapa.find(e => e.rotulo.includes("anos finais")).valor > 0 ? "sim" : "não"],
    ["saneamento", "Domicílios com água da rede geral", d => pct(d.saneamento.agua.find(a => a.rotulo === "Rede geral").pct)],
    ["saneamento", "Domicílios com esgoto em rede geral", d => pct(d.saneamento.esgoto.find(a => a.rotulo === "Rede geral/pluvial").pct)],
    ["saneamento", "Lixo coletado por serviço de limpeza", d => pct(d.saneamento.lixo.find(a => a.rotulo === "Coletado por serviço de limpeza").pct)],
    ["saneamento", "Domicílios com banheiro exclusivo", d => pct(d.saneamento.banheiro.pct_com)],
    ["renda", "Domicílios até 1/2 SM per capita (2010)", d => pct(d3.sum(d.renda_2010.filter(r => ["Até 1/8 SM", "1/8 a 1/4 SM", "1/4 a 1/2 SM"].includes(r.rotulo)), r => r.pct))],
    ["cor_raca", "Responsável pelo domicílio preta ou parda", d => pct(d.cor_raca_responsavel.filter(c => c.rotulo === "Preta" || c.rotulo === "Parda").reduce((s, c) => s + c.pct, 0))],
    ["quilombolas", "Pessoas quilombolas", d => num(d.quilombolas.total)],
    ["mortalidade", "Domicílios com óbito (2019–2022)", d => num(d.obitos.domicilios_com_obito)],
    ["saude", "Estabelecimentos de saúde no distrito", d => num(d.saude.total)],
    ["saude", "Equipes que atendem o distrito", d => num(d.saude_equipes.equipes_que_atendem)],
    ["saude", "Profissionais por mil habitantes", d => num(1000 * d.saude_equipes.profissionais / d.resumo.populacao, 1)],
  ];
  const blocoTabela = pai.append("div").attr("class", "bloco");
  const t = blocoTabela.append("table").attr("class", "tabela");
  t.append("thead").append("tr").selectAll("th").data(["Indicador", ...nomes]).join("th")
    .attr("class", (x, i) => i ? "num" : null).text(x => x);
  const tr = t.append("tbody").selectAll("tr").data(linhas).join("tr").attr("data-tema", l => l[0]);
  tr.append("td").text(l => l[1]);
  nomes.forEach(n => tr.append("td").attr("class", "num").text(l => l[2](DADOS.por_distrito[n])));

  mapa(bloco(pai, "territorio", "Os cinco distritos de Brumadinho",
    "Em cor esmaecida, os dois distritos analisados; os pontos são estabelecimentos de saúde do CNES.",
    "Malha territorial do Censo 2022 (IBGE) e CNES / Ministério da Saúde."), null);

  mapaSetores(bloco(pai, "territorio", "Desigualdade por setor censitário",
    "Cada polígono é um setor censitário dos dois distritos — recorte mais fino que o distrito."), null);

  const g = grade(pai);
  nomes.forEach(nome => {
    piramide(bloco(g, "demografia", `Pirâmide etária — ${nome}`, "% da população residente",
      "Variáveis V01009–V01030, arquivo 'demografia'."),
      DADOS.por_distrito[nome].piramide, { homens: CORES.azul, mulheres: CORES.laranja });
  });

  empilhada100(bloco(pai, "saneamento", "Abastecimento de água", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00111–V00118, arquivo 'caracteristicas_domicilio2'."),
    nomes.map(n => ({ nome: n, partes: DADOS.por_distrito[n].saneamento.agua })));
  empilhada100(bloco(pai, "saneamento", "Esgotamento sanitário", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00309–V00316, arquivo 'caracteristicas_domicilio2'."),
    nomes.map(n => ({ nome: n, partes: DADOS.por_distrito[n].saneamento.esgoto })));
  empilhada100(bloco(pai, "saneamento", "Destino do lixo", "% dos domicílios particulares permanentes ocupados",
    "Variáveis V00397–V00402, arquivo 'caracteristicas_domicilio2'."),
    nomes.map(n => ({ nome: n, partes: DADOS.por_distrito[n].saneamento.lixo })));

  const indicadoresHist = DADOS.por_distrito[nomes[0]].serie_2010.map(t => t.indicador);
  indicadoresHist.forEach(indicador => {
    barrasAgrupadas(bloco(pai, "historico", `${indicador} — 2010 e 2022`, "% dos domicílios particulares permanentes",
      "Censo 2010 (agregados por setor censitário) e Censo 2022 (agregados por distrito), com definições equivalentes."),
      nomes,
      [{ nome: "2010", cor: CORES.neutro, valores: nomes.map(n => +DADOS.por_distrito[n].serie_2010.find(t => t.indicador === indicador)["2010"].toFixed(1)) },
       { nome: "2022", cor: CORES.azul, valores: nomes.map(n => +DADOS.por_distrito[n].serie_2010.find(t => t.indicador === indicador)["2022"].toFixed(1)) }],
      { formato: v => pct(v), rotulos: true, altura: 250 });
  });

  barrasAgrupadas(bloco(pai, "renda", "Renda domiciliar per capita em 2010", "% dos domicílios particulares por faixa",
    "Censo 2010, arquivo DomicilioRenda por setor censitário. Não existe equivalente em 2022 por distrito."),
    DADOS.por_distrito[nomes[0]].renda_2010.map(r => r.rotulo),
    nomes.map(n => ({ nome: n, cor: CORDIST[n], valores: DADOS.por_distrito[n].renda_2010.map(r => +r.pct.toFixed(1)) })),
    { formato: v => pct(v), altura: 300 });

  const faixas = DADOS.por_distrito[nomes[0]].alfabetizacao.por_idade.map(f => f.faixa);
  barrasAgrupadas(bloco(pai, "educacao", "Taxa de alfabetização por faixa etária", "% de pessoas alfabetizadas em cada faixa",
    "Alfabetizados (V00748–V00760) sobre o total (V00644–V00656) de cada faixa, arquivo 'alfabetizacao'."),
    faixas,
    nomes.map(n => ({ nome: n, cor: CORDIST[n],
      valores: DADOS.por_distrito[n].alfabetizacao.por_idade.map(f => f.taxa == null ? 0 : +f.taxa.toFixed(1)) })),
    { formato: v => pct(v) });

  barrasAgrupadas(bloco(pai, "educacao", "Matrículas por etapa de ensino", "Educação básica, 2025",
    "Censo Escolar 2025 (INEP). Ausência de barra significa que nenhuma escola do distrito oferece a etapa."),
    DADOS.por_distrito[nomes[0]].escolas.por_etapa.map(e => e.rotulo),
    nomes.map(n => ({ nome: n, cor: CORDIST[n], valores: DADOS.por_distrito[n].escolas.por_etapa.map(e => e.valor) })),
    { rotulos: true });
}

function painelRompimento(pai) {
  const r = DADOS.rompimento;
  const nomes = DADOS.distritos;

  pai.append("h2").attr("class", "secao").text("O rompimento da barragem e estes distritos");
  pai.append("p").attr("class", "secao-sub").html(
    "Em <strong>25 de janeiro de 2019</strong> a barragem B1 da Mina Córrego do Feijão, da Vale, rompeu em Brumadinho. " +
    "Esta aba reúne o que as fontes deste projeto conseguem dizer sobre a relação entre esse evento e os dois distritos — e, " +
    "com o mesmo cuidado, o que elas não dizem.");

  pai.append("div").attr("class", "aviso").html(
    "<strong>O que estes dados não permitem afirmar.</strong> Nenhuma fonte usada aqui traz causa de morte, " +
    "lista de vítimas por distrito ou a mancha de rejeito. O Censo registra o semestre do falecimento, não a causa; " +
    "o cadastro da ANM traz a situação das barragens hoje, não o que houve em 2019; a RAIS registra vínculos formais, " +
    "não o motivo de sua criação ou fim. Tudo abaixo é <em>contexto mensurável</em>, e cada gráfico diz de onde vem e o que mede. " +
    "Correlação de datas não é prova de causa.");

  // Distancia
  const distancias = r.distancias.map(d => ({ rotulo: d.distrito, valor: d.km, pct: d.km }));
  barrasHorizontais(bloco(pai, "barragens", "Distância da mina até cada distrito",
    "Quilômetros em linha reta da mina até a borda mais próxima de cada distrito",
    "Coordenadas das estruturas remanescentes da Mina Córrego do Feijão no cadastro da ANM e malha do Censo 2022 (IBGE). " +
    "É distância geométrica: não representa o caminho do rejeito, que desceu o córrego do Ferro-Carvão até o rio Paraopeba."),
    distancias,
    { cor: d => nomes.includes(d.rotulo) ? CORDIST[d.rotulo] : CORES.neutro, campo: "valor",
      formato: d => num(d.valor, 1) + " km", margemEsq: 190,
      dica: d => `<b>${d.rotulo}</b><br>${num(d.valor, 1)} km da mina` });

  mapaBarragens(bloco(pai, "barragens", "As barragens de mineração em Brumadinho hoje",
    `${num(r.barragens.total)} estruturas cadastradas, ${num(r.barragens.em_emergencia)} em nível de emergência`,
    "Cadastro Nacional de Barragens de Mineração (ANM), cruzado com a malha do Censo 2022. A B1 que rompeu não está no " +
    "cadastro: o que aparece da mesma mina são as estruturas remanescentes, todas em descaracterização."));

  const emergencia = Object.entries(r.barragens.por_distrito)
    .filter(([, v]) => v.em_emergencia > 0)
    .map(([distrito, v]) => ({ distrito, ...v }));
  if (emergencia.length) {
    destaque(pai, "barragens",
      "<strong>Todas as barragens hoje sob declaração de emergência em Brumadinho estão em " +
      emergencia.map(e => e.distrito).join(" e ") + "</strong> — " +
      emergencia.map(e => `${e.em_emergencia} das ${e.total} cadastradas no distrito`).join(", ") +
      ". Segundo o próprio cadastro, há pessoas ocupando permanentemente a área a jusante delas.");
  }

  nomes.forEach(nome => {
    const b = r.barragens.por_distrito[nome];
    const blocoDistrito = bloco(pai, "barragens", `Barragens em ${nome}`,
      b ? `${num(b.total)} estruturas cadastradas` : null,
      "Cadastro Nacional de Barragens de Mineração (ANM), competência do arquivo aberto mais recente.");
    if (!b || !b.lista.length) {
      blocoDistrito.append("p").attr("class", "vazio").text("Nenhuma barragem de mineração cadastrada neste distrito.");
      return;
    }
    tabela(blocoDistrito,
      [{ rotulo: "Barragem", num: false }, { rotulo: "Empreendedor", num: false },
       { rotulo: "Emergência", num: false }, { rotulo: "Dano potencial", num: false },
       { rotulo: "Método construtivo", num: false }, { rotulo: "População a jusante", num: false }],
      b.lista.map(x => [x.nome, x.empreendedor, x.emergencia, x.dano, x.metodo, x.jusante]));
  });

  // Obitos
  secao(pai, "barragens", "Óbitos declarados no Censo, por semestre",
    "O rompimento foi no 1º semestre de 2019, dentro da janela que o Censo 2022 perguntou (jan/2019 a jul/2022).");
  nomes.forEach(nome => {
    const ob = DADOS.por_distrito[nome].obitos;
    colunas(bloco(pai, "barragens", `Óbitos por semestre — ${nome}`,
      `${num(ob.domicilios_com_obito)} domicílios declararam ao menos um óbito no período`,
      "Variáveis V01264–V01270, arquivo 'obitos' do Censo 2022. O Censo pergunta se alguém que morava no domicílio faleceu " +
      "e em que semestre — não a causa nem o local. A segunda onda da covid-19 também cai nesta série, no 1º semestre de 2021."),
      ob.por_periodo.map(p => ({ rotulo: p.periodo, valor: p.valor })), CORDIST[nome],
      { corPorItem: p => p.rotulo === "1º sem. 2019" ? CORES.vermelho : CORDIST[nome] });
  });

  // Agua
  secao(pai, "barragens", "De onde vem a água dos domicílios",
    "O rejeito atingiu o córrego do Ferro-Carvão e o rio Paraopeba. Quem depende de água superficial fica mais exposto a " +
    "contaminação de curso d'água do que quem está na rede geral.");
  empilhada100(bloco(pai, "barragens", "Fonte de abastecimento de água", "% dos domicílios particulares permanentes ocupados, 2022",
    "Variáveis V00111–V00118, arquivo 'caracteristicas_domicilio2' do Censo 2022."),
    nomes.map(n => ({ nome: n, partes: r.agua[n].partes })));

  const semSuperficial = nomes.filter(n => r.agua[n].superficial_pct === 0);
  if (semSuperficial.length === nomes.length) {
    destaque(pai, "barragens",
      "<strong>Nenhum domicílio dos dois distritos declarou tirar água de rio, açude, córrego ou lago em 2022.</strong> " +
      "Quem está fora da rede geral usa poço ou nascente — em São José do Paraopeba são " +
      `${pct(r.agua["São José do Paraopeba"].fora_da_rede_pct)} dos domicílios, quase todos poço profundo. ` +
      "O Censo não diz se esses poços foram testados, então isto delimita a exposição a água de superfície, não a subterrânea.");
  }

  // Saude
  secao(pai, "barragens", "O que mudou no cadastro de saúde depois de 2019",
    "Datas de ativação das equipes que hoje estão ativas no CNES. Equipes desativadas desde então não aparecem, " +
    "então a série mostra o que restou, não tudo o que foi criado.");
  colunas(bloco(pai, "barragens", "Equipes de saúde ativas hoje, por ano de ativação",
    "Cada barra é o número de equipes hoje ativas que foram cadastradas naquele ano",
    "Campo DT_ATIVACAO da tabela de equipes da base do CNES, competência 07/2026."),
    r.equipes_por_ano.map(e => ({ rotulo: String(e.ano), valor: e.valor })), CORES.azul,
    { corPorItem: e => e.rotulo === "2019" ? CORES.vermelho : CORES.azul });

  if (r.saude_mental.length) {
    const anos = [...new Set(r.saude_mental.map(e => e.ano))].sort();
    destaque(pai, "barragens",
      `<strong>As ${num(r.saude_mental.length)} equipes de saúde mental de Brumadinho foram cadastradas em ${anos.join(" e ")}</strong>` +
      " — o ano do rompimento. São equipes multiprofissionais de atenção especializada em saúde mental, sediadas no ambulatório " +
      "de especialidades, na sede do município. O cadastro registra a data de ativação, não o motivo.");
  }

  // Emprego
  if (r.emprego_extrativa.length) {
    secao(pai, "barragens", "Emprego formal na mineração, antes e depois",
      "Vínculos formais em Brumadinho na seção B da CNAE (indústrias extrativas). É dado municipal: a RAIS não desce a distrito. " +
      "Ao contrário do que se poderia supor, o emprego formal do município cresceu depois de 2019.");
    barrasAgrupadas(bloco(pai, "barragens", "Vínculos formais em Brumadinho",
      "Indústrias extrativas e total do município",
      "DataViva / Cedeplar-UFMG, a partir da RAIS. As categorias de sexo e cor/raça se sobrepõem no arquivo de origem; " +
      "o total usa o corte por sexo, que é o único que cobre todos os vínculos. O emprego formal do município não caiu depois " +
      "do rompimento: subiu em 2019 e chegou ao pico em 2022. A RAIS registra o vínculo, não o motivo de ele existir, então " +
      "não dá para separar aqui o que é obra de reparação, o que é mineração em outras minas e o que é outra coisa."),
      r.emprego_extrativa.map(e => String(e.ano)),
      [{ nome: "Indústrias extrativas", cor: CORES.vermelho, valores: r.emprego_extrativa.map(e => e.extrativa) },
       { nome: "Total do município", cor: CORES.neutro, valores: r.emprego_extrativa.map(e => e.total) }],
      { rotulos: true, altura: 320 });

    colunas(bloco(pai, "barragens", "Peso da mineração no emprego formal",
      "% dos vínculos formais de Brumadinho na seção B da CNAE",
      "DataViva / Cedeplar-UFMG, a partir da RAIS."),
      r.emprego_extrativa.map(e => ({ rotulo: String(e.ano), valor: +e.pct.toFixed(1) })), CORES.vermelho, { sufixo: "%" });
  }
}

function painelMunicipio(pai) {
  const m = DADOS.municipio;
  pai.append("h2").attr("class", "secao").text("Contexto municipal — Brumadinho");
  pai.append("p").attr("class", "secao-sub").text(
    "Renda, emprego e salário atuais não têm abertura oficial por distrito: a RAIS e o Censo 2022 só publicam esses temas " +
    "no nível de município. Os números abaixo são de Brumadinho inteiro e servem de pano de fundo, não de retrato dos distritos.");

  cartoes(pai, "renda", m.indicadores_ibge.map(i => ({ valor: i.valor, rotulo: i.rotulo, nota: i.fonte })));

  barrasHorizontais(bloco(pai, "renda", "Empregos formais por setor de atividade",
    `${num(m.total_empregos)} vínculos formais em Brumadinho, 2024`,
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024 — seções da CNAE 2.0."),
    m.emprego_por_secao.filter(s => s.pct >= 0.5).map(s => ({ rotulo: s.nome, valor: s.valor, pct: s.pct })),
    { cor: (d, i) => i === 0 ? CORES.vermelho : CORES.azul, margemEsq: 230 });

  const g = grade(pai);
  barrasHorizontais(bloco(g, "renda", "Salário médio real por escolaridade", "Média mensal dos vínculos formais, 2024",
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024."),
    m.salario_por_escolaridade.map(s => ({ rotulo: s.escolaridade, valor: s.valor, pct: s.valor })),
    { cor: CORES.verde, formato: d => reais(d.valor), campo: "valor", margemEsq: 170,
      dica: d => `<b>${d.rotulo}</b><br>${reais(d.valor)} por mês` });

  barrasHorizontais(bloco(g, "renda", "Salário médio real por sexo e cor/raça", "Média mensal dos vínculos formais, 2024",
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024. BrAm = brancos e amarelos; PPI = pretos, pardos e indígenas."),
    m.salario_por_sexo_raca.map(s => ({ rotulo: s.grupo.replace(" - ", " · "), valor: s.valor, pct: s.valor })),
    { cor: d => d.rotulo.startsWith("Homem") ? CORES.azul : CORES.laranja, formato: d => reais(d.valor), campo: "valor", margemEsq: 150,
      dica: d => `<b>${d.rotulo}</b><br>${reais(d.valor)} por mês` });

  const totalVinculos = d3.sum(m.vinculos_por_escolaridade, v => v.valor) || 1;
  barrasHorizontais(bloco(g, "renda", "Vínculos formais por escolaridade", "% dos vínculos formais, 2024",
    "DataViva / Cedeplar-UFMG, a partir da RAIS 2024."),
    m.vinculos_por_escolaridade.map(v => ({ rotulo: v.escolaridade, valor: v.valor, pct: 100 * v.valor / totalVinculos })),
    { cor: CORES.roxo, margemEsq: 170 });

  const porDistrito = Object.entries(DADOS.saude_municipio)
    .map(([nome, v]) => ({ rotulo: nome, valor: v.total, pct: v.total }))
    .sort((a, b) => b.valor - a.valor);
  barrasHorizontais(bloco(g, "saude", "Estabelecimentos de saúde por distrito", "Todos os distritos de Brumadinho, CNES",
    "CNES / Ministério da Saúde cruzado com a malha do Censo 2022. 'Sem coordenada' e 'fora dos limites' são falhas de cadastro no CNES."),
    porDistrito, { cor: d => CORDIST[d.rotulo] || CORES.neutro, formato: d => num(d.valor), campo: "valor", margemEsq: 210,
      dica: d => `<b>${d.rotulo}</b><br>${num(d.valor)} estabelecimentos` });
}

// ---------------------------------------------------------------- filtro

function aplicarFiltro() {
  const painel = document.getElementById("painel");
  painel.querySelectorAll("[data-tema]").forEach(el => {
    el.hidden = !ativos.has(el.dataset.tema);
  });
  // Uma grade sem nenhum filho visivel deixaria um vao no layout
  painel.querySelectorAll("[data-grade]").forEach(el => {
    el.hidden = ![...el.children].some(f => !f.hidden);
  });
  const total = painel.querySelectorAll(".bloco").length;
  const visiveis = [...painel.querySelectorAll(".bloco")].filter(b => !b.hidden).length;
  d3.select("#contagem").text(visiveis === total ? `${total} blocos` : `${visiveis} de ${total} blocos`);
  d3.selectAll("#filtros button[data-tema]").attr("aria-pressed", function () {
    return ativos.has(this.dataset.tema) ? "true" : "false";
  });
  // Guarda tambem quais temas existiam quando o usuario escolheu: assim um tema
  // novo entra ligado em vez de aparecer desligado para quem ja visitou o site.
  try {
    localStorage.setItem("temas", JSON.stringify({
      ativos: [...ativos],
      conhecidos: TEMAS.map(t => t[0]),
    }));
  } catch (e) { /* modo privado */ }
}

function montarFiltros() {
  const barra = d3.select("#filtros");
  barra.append("span").attr("class", "filtros-rotulo").text("Mostrar:");
  barra.selectAll("button.tema").data(TEMAS).join("button")
    .attr("class", "tema").attr("data-tema", t => t[0]).text(t => t[1])
    .on("click", (e, t) => {
      if (ativos.has(t[0])) ativos.delete(t[0]); else ativos.add(t[0]);
      aplicarFiltro();
    });
  const acoes = barra.append("span").attr("class", "acoes");
  acoes.append("button").attr("class", "acao").text("Tudo")
    .on("click", () => { ativos = new Set(TEMAS.map(t => t[0])); aplicarFiltro(); });
  acoes.append("button").attr("class", "acao").text("Nada")
    .on("click", () => { ativos = new Set(); aplicarFiltro(); });
  acoes.append("span").attr("id", "contagem").attr("class", "contagem");
}

function render() {
  const painel = d3.select("#painel").html("");
  if (ABA === "Comparação") painelComparacao(painel);
  else if (ABA === "Rompimento da barragem") painelRompimento(painel);
  else if (ABA === "Contexto municipal") painelMunicipio(painel);
  else painelDistrito(painel, ABA);
  d3.selectAll("#abas button").attr("aria-current", function () { return this.textContent === ABA ? "true" : null; });
  aplicarFiltro();
  window.scrollTo({ top: 0, behavior: "instant" });
}

Promise.all([
  d3.json("dados/indicadores.json"),
  d3.json("dados/distritos.geojson"),
  d3.json("dados/setores.geojson"),
]).then(([dados, geo, setores]) => {
  DADOS = dados;
  GEO = geo;
  SETORES = setores;
  try {
    const salvo = JSON.parse(localStorage.getItem("temas") || "null");
    if (Array.isArray(salvo)) {
      // formato antigo: so a lista de ativos, sem registro do que existia
      if (salvo.length) ativos = new Set(salvo);
    } else if (salvo && Array.isArray(salvo.ativos)) {
      const conhecidos = new Set(salvo.conhecidos || []);
      ativos = new Set(salvo.ativos);
      TEMAS.forEach(([chave]) => { if (!conhecidos.has(chave)) ativos.add(chave); });
    }
  } catch (e) { /* modo privado */ }

  const abas = ["Comparação", ...dados.distritos, "Rompimento da barragem", "Contexto municipal"];
  ABA = abas[0];
  d3.select("#abas").selectAll("button").data(abas).join("button")
    .text(x => x).on("click", (e, x) => { ABA = x; render(); });
  montarFiltros();
  render();
});
