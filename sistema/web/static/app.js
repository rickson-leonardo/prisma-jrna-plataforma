/* PRISMA JRNA — JS vanilla minimo (sem dependencias). */
(function () {
  "use strict";

  /* ---------------------------------------------------------------
     0. Modo Consulta (Somente Leitura) por padrao: destravamento explicito
     --------------------------------------------------------------- */
  var mainEl = document.getElementById("conteudo");
  var btnModoAba = document.getElementById("btn-modo-aba");
  var modoBadge = document.getElementById("modo-badge");
  var modoDesc = document.getElementById("modo-desc");

  function syncModo() {
    if (!mainEl || !mainEl.hasAttribute("data-modo")) return;
    var abaEdicao = mainEl.getAttribute("data-modo") === "edicao";
    if (modoBadge) {
      modoBadge.textContent = abaEdicao ? "Modo Edição ativo (toda a aba)" : "Modo Consulta (Somente leitura)";
      modoBadge.className = "badge " + (abaEdicao ? "b-at" : "b-in");
    }
    if (modoDesc) {
      modoDesc.textContent = abaEdicao
        ? "Todos os formulários desta aba estão liberados para inclusão, alteração e exclusão."
        : "Navegue, expanda registros e consulte os ícones de ajuda sem risco de alteração acidental.";
    }
    if (btnModoAba) {
      btnModoAba.textContent = abaEdicao ? "Voltar ao modo consulta" : "Ativar modo edição na aba";
      btnModoAba.setAttribute("aria-pressed", abaEdicao ? "true" : "false");
    }
    document.querySelectorAll("[data-crud-bloco]").forEach(function (bloco) {
      var ativo = abaEdicao || bloco.getAttribute("data-editando") === "1";
      bloco.querySelectorAll("fieldset.crud-fs").forEach(function (fs) { fs.disabled = !ativo; });
      var est = bloco.querySelector(".crud-estado");
      if (est) {
        est.textContent = ativo ? "Edição habilitada" : "Somente leitura";
        est.className = "badge crud-estado " + (ativo ? "b-at" : "b-neutro");
      }
      var dica = bloco.querySelector(".crud-dica");
      if (dica) {
        dica.textContent = abaEdicao
          ? "Modo edição da aba ativo."
          : (ativo ? "Edição liberada apenas neste bloco." : "Campos protegidos contra cliques acidentais.");
      }
      var optEd = bloco.querySelector(".crud-opt-editar");
      var optBl = bloco.querySelector(".crud-opt-bloquear");
      if (optEd) optEd.hidden = ativo;
      if (optBl) optBl.hidden = abaEdicao || !ativo;
    });
  }

  if (mainEl && mainEl.hasAttribute("data-modo")) {
    syncModo();
    window.addEventListener("pageshow", function () {
      mainEl.setAttribute("data-modo", "consulta");
      document.querySelectorAll("[data-crud-bloco][data-editando]").forEach(function (b) { b.removeAttribute("data-editando"); });
      syncModo();
    });
    if (btnModoAba) {
      btnModoAba.addEventListener("click", function () {
        var indoEdicao = mainEl.getAttribute("data-modo") !== "edicao";
        mainEl.setAttribute("data-modo", indoEdicao ? "edicao" : "consulta");
        if (!indoEdicao) {
          document.querySelectorAll("[data-crud-bloco][data-editando]").forEach(function (b) { b.removeAttribute("data-editando"); });
        }
        syncModo();
      });
    }
    document.addEventListener("click", function (e) {
      var btnEd = e.target.closest && e.target.closest(".js-crud-editar");
      if (btnEd) {
        var b = btnEd.closest("[data-crud-bloco]");
        if (!b) return;
        b.setAttribute("data-editando", "1");
        syncModo();
        var primeiro = b.querySelector("fieldset.crud-fs:not([disabled]) input:not([type=hidden]):not([disabled]), fieldset.crud-fs:not([disabled]) select:not([disabled]), fieldset.crud-fs:not([disabled]) textarea:not([disabled])");
        b.querySelectorAll("textarea.longo").forEach(function (ta) { if (ta._setMdMode) ta._setMdMode("raw"); });
        if (primeiro) primeiro.focus();
        return;
      }
      var btnBl = e.target.closest && e.target.closest(".js-crud-bloquear");
      if (btnBl) {
        var b2 = btnBl.closest("[data-crud-bloco]");
        if (!b2) return;
        b2.removeAttribute("data-editando");
        b2.querySelectorAll("textarea.longo").forEach(function (ta) { if (ta._setMdMode) ta._setMdMode("fmt"); });
        syncModo();
      }
      var btnMk = e.target.closest && e.target.closest(".js-ins-mk");
      if (btnMk) {
        var blocoMk = btnMk.closest("[data-crud-bloco]");
        var ta = blocoMk && blocoMk.querySelector('textarea[name="conteudo_md"]:not([disabled])');
        if (!ta) return;
        if (ta._setMdMode) ta._setMdMode("raw");
        var mk = btnMk.getAttribute("data-mk") || "";
        var pos = ta.selectionStart || 0, fim = ta.selectionEnd || 0;
        ta.value = ta.value.slice(0, pos) + mk + ta.value.slice(fim);
        ta.focus();
        ta.setSelectionRange(pos + mk.length, pos + mk.length);
      }
    });
  }

  /* ---------------------------------------------------------------
     1. Ajuda contextual: hover/foco = dica rapida; clique/Enter = fixa
     --------------------------------------------------------------- */
  var AJUDA = {};
  try { AJUDA = JSON.parse(document.getElementById("ajuda-json").textContent); } catch (e) { AJUDA = {}; }
  var pop = document.createElement("div");
  pop.id = "tip-pop"; pop.setAttribute("role", "tooltip"); pop.hidden = true;
  document.body.appendChild(pop);
  var atual = null, fixo = false;

  function posicionar(alvo) {
    var r = alvo.getBoundingClientRect(), m = 8;
    pop.style.left = "0px"; pop.style.top = "0px";
    var w = pop.offsetWidth, h = pop.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
    var left = Math.min(Math.max(m, r.left + r.width / 2 - w / 2), vw - w - m);
    var top = r.bottom + 6;
    if (top + h > vh - m) top = Math.max(m, r.top - h - 6);
    pop.style.left = left + "px"; pop.style.top = top + "px";
  }
  function abrir(alvo, pin) {
    var txt = AJUDA[alvo.getAttribute("data-k")] || alvo.getAttribute("data-tip") || "Sem descrição cadastrada.";
    if (atual && atual !== alvo) atual.setAttribute("aria-expanded", "false");
    atual = alvo; fixo = !!pin;
    pop.textContent = txt;
    pop.className = fixo ? "fixo" : "";
    if (fixo) {
      var b = document.createElement("button");
      b.type = "button"; b.setAttribute("aria-label", "Fechar ajuda"); b.textContent = "×";
      b.addEventListener("click", fechar); pop.appendChild(b);
    }
    pop.hidden = false;
    if (!alvo.id) alvo.id = "tip-" + Math.random().toString(36).slice(2, 8);
    alvo.setAttribute("aria-describedby", "tip-pop");
    alvo.setAttribute("aria-expanded", fixo ? "true" : "false");
    posicionar(alvo);
  }
  function fechar() {
    pop.hidden = true; fixo = false;
    if (atual) { atual.setAttribute("aria-expanded", "false"); atual.removeAttribute("aria-describedby"); }
    atual = null;
  }
  document.addEventListener("mouseover", function (e) {
    var t = e.target.closest && e.target.closest(".tip");
    if (t && !fixo) abrir(t, false);
  });
  document.addEventListener("mouseout", function (e) {
    var t = e.target.closest && e.target.closest(".tip");
    if (t && !fixo && (!e.relatedTarget || !t.contains(e.relatedTarget))) fechar();
  });
  document.addEventListener("focusin", function (e) {
    if (e.target.classList && e.target.classList.contains("tip") && !fixo) abrir(e.target, false);
  });
  document.addEventListener("focusout", function (e) {
    if (e.target.classList && e.target.classList.contains("tip") && !fixo) fechar();
  });
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest(".tip");
    if (t) {
      e.preventDefault(); e.stopPropagation(); // nao ativa label/summary
      if (fixo && atual === t) fechar(); else abrir(t, true);
      return;
    }
    if (fixo && !pop.contains(e.target)) fechar();
  }, true);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !pop.hidden) { var a = atual; fechar(); if (a) a.focus(); return; }
    var t = e.target;
    if (t.classList && t.classList.contains("tip") && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault(); e.stopPropagation();
      if (fixo && atual === t) fechar(); else abrir(t, true);
    }
  });
  window.addEventListener("scroll", function () { if (atual && !pop.hidden) posicionar(atual); }, true);
  window.addEventListener("resize", function () { if (atual && !pop.hidden) posicionar(atual); });

  /* ---------------------------------------------------------------
     2. Exclusao com dialogo acessivel (nunca em 1 clique)
     --------------------------------------------------------------- */
  var dlg = document.createElement("dialog");
  dlg.className = "confirma"; dlg.setAttribute("aria-labelledby", "dlg-t");
  dlg.innerHTML = '<h3 id="dlg-t">Confirmar exclusão</h3><p id="dlg-m"></p>' +
    '<div class="acoes"><button type="button" class="btn btn-sec" value="nao">Cancelar</button>' +
    '<button type="button" class="btn btn-danger" value="sim">Excluir definitivamente</button></div>';
  document.body.appendChild(dlg);
  var formPendente = null;
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (f.classList.contains("js-confirm") && !f.dataset.confirmado) {
      e.preventDefault(); formPendente = f;
      dlg.querySelector("#dlg-m").textContent = f.getAttribute("data-confirm");
      dlg.showModal(); dlg.querySelector('[value="nao"]').focus();
    }
  });
  dlg.addEventListener("click", function (e) {
    var v = e.target.value;
    if (v === "sim" && formPendente) { formPendente.dataset.confirmado = "1"; dlg.close(); formPendente.submit(); }
    else if (v === "nao" || e.target === dlg) { dlg.close(); formPendente = null; }
  });

  /* ---------------------------------------------------------------
     3. Trava de homologacao: exige justificativa preenchida
     --------------------------------------------------------------- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest('button[name="acao"][value="homologar"]');
    if (!b) return;
    var f = b.form, campo = f && f.elements[b.getAttribute("data-exige")];
    if (campo && !String(campo.value || "").trim()) {
      e.preventDefault();
      campo.classList.add("erro");
      campo.setCustomValidity("Registre a justificativa técnica antes de homologar.");
      campo.reportValidity();
      campo.addEventListener("input", function () { campo.setCustomValidity(""); campo.classList.remove("erro"); }, { once: true });
    }
  });

  /* ---------------------------------------------------------------
     4. Filtros rapidos + busca instantanea
     --------------------------------------------------------------- */
  function norm(s) { return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  document.querySelectorAll("[data-filtra]").forEach(function (box) {
    var lista = document.getElementById(box.getAttribute("data-filtra"));
    if (!lista) return;
    var itens = Array.prototype.slice.call(lista.querySelectorAll("[data-item]"));
    var busca = box.querySelector("[data-busca]"), cont = box.querySelector("[data-contador]"), st = "";
    function aplicar() {
      var q = norm(busca.value).trim(), n = 0;
      itens.forEach(function (it) {
        // busca no resumo e nos valores digitados (nao nos rotulos dos campos, comuns a todos os itens)
        var resumo = it.querySelector("summary");
        var ok = (!st || it.getAttribute("data-status") === st) && (!q || norm(resumo ? resumo.textContent : it.textContent).indexOf(q) >= 0 ||
          Array.prototype.some.call(it.querySelectorAll("input[type=text],textarea"), function (i) { return norm(i.value).indexOf(q) >= 0; }));
        it.hidden = !ok; if (ok) n++;
      });
      if (cont) cont.textContent = n + " de " + itens.length;
    }
    busca.addEventListener("input", aplicar);
    box.querySelectorAll(".chip").forEach(function (c) {
      c.addEventListener("click", function () {
        box.querySelectorAll(".chip").forEach(function (x) { x.classList.remove("on"); });
        c.classList.add("on"); st = c.getAttribute("data-st"); aplicar();
      });
    });
    aplicar();
  });

  /* ---------------------------------------------------------------
     5. Ancora (#clausula-18, #cenario-3): abre e destaca o registro exato
     --------------------------------------------------------------- */
  function irAncora() {
    if (!location.hash) return;
    var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!el) return;
    if (el.tagName === "DETAILS") { el.open = true; el.hidden = false; el.classList.add("alvo"); }
    var d = el.closest("details"); if (d) d.open = true;
    el.scrollIntoView({ block: "start" });
  }
  window.addEventListener("hashchange", irAncora); irAncora();

  /* ---------------------------------------------------------------
     6. Validacao amigavel de numeros brasileiros (R$ 1.500,00 · 20.000 · 15,0%)
     --------------------------------------------------------------- */
  var REGRAS = {
    brl: { re: /^-?(?:R\$\s?)?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?$/, msg: "Use o formato brasileiro de moeda: 1.500,00" },
    pct: { re: /^\d{1,3}(?:,\d{1,4})?\s?%?$/, msg: "Use percentual com vírgula: 15,0 (de 0 a 100)" },
    int: { re: /^(?:\d{1,3}(?:\.\d{3})+|\d+)$/, msg: "Use número inteiro (aceita separador de milhar: 20.000)" }
  };
  function fmtBRL(n) { return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function paraNumero(v) { return Number(v.replace(/R\$\s?/, "").replace(/\./g, "").replace(",", ".").replace("%", "")); }
  document.querySelectorAll("input[data-fmt]").forEach(function (inp) {
    var regra = REGRAS[inp.getAttribute("data-fmt")]; if (!regra) return;
    inp.setAttribute("inputmode", inp.getAttribute("data-fmt") === "int" ? "numeric" : "decimal");
    var msg = document.createElement("span"); msg.className = "msg-erro"; msg.setAttribute("aria-live", "polite");
    inp.insertAdjacentElement("afterend", msg);
    function validar() {
      var v = inp.value.trim(), ok = !v || regra.re.test(v);
      if (ok && inp.getAttribute("data-fmt") === "pct" && v && paraNumero(v) > 100) ok = false;
      inp.setCustomValidity(ok ? "" : regra.msg); inp.classList.toggle("erro", !ok); msg.textContent = ok ? "" : regra.msg;
      return ok;
    }
    inp.addEventListener("input", validar);
    inp.addEventListener("blur", function () {
      var v = inp.value.trim();
      if (!v) return;
      // aceita "1500" ou "1500.5" e normaliza para pt-BR
      if (inp.getAttribute("data-fmt") === "brl" && /^-?\d+(\.\d{1,2})?$/.test(v)) inp.value = fmtBRL(Number(v));
      else if (validar() && inp.getAttribute("data-fmt") === "brl") inp.value = fmtBRL(paraNumero(v));
      validar();
    });
  });
  /* ---------------------------------------------------------------
     7. Visualizacao Markdown (Ver formatado x Ver texto puro)
     --------------------------------------------------------------- */
  function escHtml(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function mdInline(s) {
    var out = escHtml(s);
    out = out.replace(/\{\{([A-Z0-9_]+)\}\}/g, '<span class="mk-tag">{{$1}}</span>');
    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return out;
  }
  function mdParaHtml(src) {
    var lines = (src || "").replace(/\r\n/g, "\n").split("\n"), html = [], i = 0;
    function splitRow(l) { return l.trim().replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); }); }
    while (i < lines.length) {
      var l = lines[i], tr = l.trim();
      if (!tr) { i++; continue; }
      if (/^#{1,4}\s+/.test(tr)) {
        var m = tr.match(/^(#{1,4})\s+(.*)$/);
        html.push("<h" + m[1].length + ">" + mdInline(m[2]) + "</h" + m[1].length + ">");
        i++; continue;
      }
      if (tr.indexOf("|") >= 0 && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        var hdr = splitRow(l); i += 2;
        html.push("<table><thead><tr>" + hdr.map(function (c) { return "<th>" + mdInline(c) + "</th>"; }).join("") + "</tr></thead><tbody>");
        while (i < lines.length && lines[i].trim().indexOf("|") >= 0) {
          var row = splitRow(lines[i]);
          html.push("<tr>" + row.map(function (c) { return "<td>" + mdInline(c) + "</td>"; }).join("") + "</tr>");
          i++;
        }
        html.push("</tbody></table>"); continue;
      }
      if (/^[-*]\s+/.test(tr)) {
        html.push("<ul>");
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
          html.push("<li>" + mdInline(lines[i].replace(/^\s*[-*]\s+/, "")) + "</li>"); i++;
        }
        html.push("</ul>"); continue;
      }
      if (/^\d+\.\s+/.test(tr)) {
        html.push("<ol>");
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
          html.push("<li>" + mdInline(lines[i].replace(/^\s*\d+\.\s+/, "")) + "</li>"); i++;
        }
        html.push("</ol>"); continue;
      }
      if (/^>\s*/.test(tr)) {
        var bq = [];
        while (i < lines.length && /^\s*>\s*/.test(lines[i])) { bq.push(mdInline(lines[i].replace(/^\s*>\s*/, ""))); i++; }
        html.push("<blockquote><p>" + bq.join("<br>") + "</p></blockquote>"); continue;
      }
      var p = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s+|[-*]\s+|\d+\.\s+|>\s*)/.test(lines[i].trim()) &&
             !(lines[i].trim().indexOf("|") >= 0 && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1]))) {
        p.push(mdInline(lines[i].trim())); i++;
      }
      html.push("<p>" + p.join(" ") + "</p>");
    }
    return html.join("") || '<span class="meta-tec">Sem conteúdo preenchido.</span>';
  }
  document.querySelectorAll("textarea.longo").forEach(function (ta) {
    var bar = document.createElement("span");
    bar.className = "md-bar";
    var btnFmt = document.createElement("span");
    btnFmt.className = "chip on js-md-fmt"; btnFmt.setAttribute("role", "button"); btnFmt.setAttribute("tabindex", "0"); btnFmt.textContent = "Ver formatado";
    var btnRaw = document.createElement("span");
    btnRaw.className = "chip js-md-raw"; btnRaw.setAttribute("role", "button"); btnRaw.setAttribute("tabindex", "0"); btnRaw.textContent = "Ver texto puro";
    bar.appendChild(btnFmt); bar.appendChild(btnRaw);
    var view = document.createElement("div");
    view.className = "md-view texto-md";
    ta.parentNode.insertBefore(bar, ta);
    ta.parentNode.insertBefore(view, ta.nextSibling);
    function setMode(m) {
      var fmt = m === "fmt";
      if (fmt) view.innerHTML = mdParaHtml(ta.value);
      view.hidden = !fmt;
      ta.hidden = fmt;
      btnFmt.classList.toggle("on", fmt);
      btnRaw.classList.toggle("on", !fmt);
    }
    ta._setMdMode = setMode;
    function bind(el, m) {
      el.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); setMode(m); });
      el.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); setMode(m); } });
    }
    bind(btnFmt, "fmt"); bind(btnRaw, "raw");
    setMode((ta.value || "").trim() ? "fmt" : "raw");
  });
})();
