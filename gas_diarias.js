// GAS — SisGOPA Diárias
// Planilha: 1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE
// Deploy: Web App, executa como Mauro, acesso "Qualquer pessoa"
//
// Ações GET:
//   ?action=get_numero&om_id=XXX  → retorna próximo número sequencial e registra
//   (sem action)                   → retorna pdfs_gerados + diarias_concluidas (comportamento original)
//
// Ações POST (body JSON):
//   {action:"salvar_numero", om_id, numero}  → salva número da OM na aba Numeros
//   {action:"pdf_gerado", om_id}
//   {action:"concluir",   om_id}
//   {action:"desfazer",   om_id}

var SS_ID = '1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE';

function doGet(e) {
  var p = (e && e.parameter) ? e.parameter : {};
  return _dispatch(p);
}

function doPost(e) {
  var p = {};
  try { p = JSON.parse(e.postData.contents); } catch(err) {}
  return _dispatch(p);
}

function _dispatch(p) {
  var ss = SpreadsheetApp.openById(SS_ID);
  var action = p.action || '';

  // ── get_numero ────────────────────────────────────────────────────────────
  // Gera e registra número sequencial para a solicitação de diária
  if (action === 'get_numero') {
    var omId = p.om_id || '';
    var sh = _getOrCreate(ss, 'Numeros');

    // Garante cabeçalho
    if (sh.getLastRow() === 0) {
      sh.getRange(1,1,1,4).setValues([['Numero','OM','Timestamp','Ano']]);
    }

    var ano = new Date().getFullYear();

    // Verifica se já existe número para esta OM no ano corrente
    var lastRow = sh.getLastRow();
    if (lastRow > 1) {
      var dados = sh.getRange(2, 1, lastRow - 1, 4).getValues();
      for (var i = 0; i < dados.length; i++) {
        if (String(dados[i][1]) === String(omId) && Number(dados[i][3]) === ano) {
          // Já tem número — retorna o mesmo
          return _json({ ok: true, numero: Number(dados[i][0]), existente: true });
        }
      }
    }

    // Calcula próximo número (dentro do ano)
    var proximo = 1;
    if (lastRow > 1) {
      var todos = sh.getRange(2, 1, lastRow - 1, 4).getValues();
      var doAno = todos.filter(function(r){ return Number(r[3]) === ano; });
      if (doAno.length > 0) {
        proximo = Math.max.apply(null, doAno.map(function(r){ return Number(r[0]); })) + 1;
      }
    }

    // Registra
    sh.appendRow([proximo, omId, new Date().toISOString(), ano]);

    return _json({ ok: true, numero: proximo, existente: false });
  }

  // ── salvar_numero ──────────────────────────────────────────────────────────
  // Salva número da OM na aba Numeros (usado quando número vem do ID da OM)
  if (action === 'salvar_numero') {
    var omId = p.om_id || '';
    var numero = Number(p.numero) || 0;
    var sh = _getOrCreate(ss, 'Numeros');
    if (sh.getLastRow() === 0) {
      sh.getRange(1,1,1,4).setValues([['Numero','OM','Timestamp','Ano']]);
    }
    var ano = new Date().getFullYear();
    // Verifica se já existe registro para esta OM no ano
    if (sh.getLastRow() > 1) {
      var dados = sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues();
      for (var i = 0; i < dados.length; i++) {
        if (String(dados[i][1]) === String(omId) && Number(dados[i][3]) === ano) {
          return _json({ ok: true, existente: true });
        }
      }
    }
    sh.appendRow([numero, omId, new Date().toISOString(), ano]);
    return _json({ ok: true, existente: false });
  }

  // ── pdf_gerado ────────────────────────────────────────────────────────────
  if (action === 'pdf_gerado') {
    var sh2 = _getOrCreate(ss, 'PDFs');
    if (sh2.getLastRow() === 0) sh2.getRange(1,1,1,2).setValues([['om_id','timestamp']]);
    // Remove duplicata se existir
    _removeRow(sh2, p.om_id);
    sh2.appendRow([p.om_id, new Date().toISOString()]);
    return _json({ ok: true });
  }

  // ── concluir ──────────────────────────────────────────────────────────────
  if (action === 'concluir') {
    var sh3 = _getOrCreate(ss, 'Concluidas');
    if (sh3.getLastRow() === 0) sh3.getRange(1,1,1,2).setValues([['om_id','timestamp']]);
    _removeRow(sh3, p.om_id);
    sh3.appendRow([p.om_id, new Date().toISOString()]);
    return _json({ ok: true });
  }

  // ── desfazer ─────────────────────────────────────────────────────────────
  if (action === 'desfazer') {
    var sh4 = _getOrCreate(ss, 'Concluidas');
    _removeRow(sh4, p.om_id);
    return _json({ ok: true });
  }

  // ── GET padrão — retorna estado atual (pdfs + concluídas) ─────────────────
  // pdfs_gerados: lê aba Numeros (toda OM com número = PDF foi gerado)
  var shN = ss.getSheetByName('Numeros');
  var pdfs = [];
  if (shN && shN.getLastRow() > 1) {
    pdfs = shN.getRange(2, 2, shN.getLastRow()-1, 1).getValues()
              .map(function(r){ return String(r[0]); })
              .filter(function(v){ return v; });
  }

  var shC = ss.getSheetByName('Concluidas');
  var conc = [];
  if (shC && shC.getLastRow() > 1) {
    conc = shC.getRange(2, 1, shC.getLastRow()-1, 1).getValues()
              .map(function(r){ return String(r[0]); })
              .filter(function(v){ return v; });
  }

  return _json({ ok: true, pdfs_gerados: pdfs, concluidas: conc });
}

// ── Helpers ───────────────────────────────────────────────────────────────

function _getOrCreate(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function _removeRow(sh, omId) {
  if (!omId || sh.getLastRow() < 2) return;
  var data = sh.getRange(2, 1, sh.getLastRow()-1, 1).getValues();
  for (var i = data.length - 1; i >= 0; i--) {
    if (String(data[i][0]) === String(omId)) {
      sh.deleteRow(i + 2);
    }
  }
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}
