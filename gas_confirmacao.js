// GAS - SisGOPA Confirmação de Missão
// Planilha separada, independente da consulta/raio
// Ações: set_conf, conf_ciente, get_conf

var SS_ID = '15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA';

function doGet(e) {
  return _dispatch(e && e.parameter ? e.parameter : {});
}

function doPost(e) {
  var p = {};
  try { p = JSON.parse(e.postData.contents); } catch(err) {}
  return _dispatch(p);
}

function _dispatch(p) {
  var action = p.action || 'get_conf';
  var ss = SpreadsheetApp.openById(SS_ID);

  // ── get_conf ─────────────────────────────────────────────────────────────
  if (action === 'get_conf') {
    var sh = ss.getSheetByName('Confirmação');
    if (!sh || sh.getLastRow() < 2) return _json({ ok: true, oficiais: [], missao: '', anv: '', pernas: [], obs: '' });
    var rows = sh.getDataRange().getValues();
    // Linha 1 = header; linha 0 do array
    var meta = rows[1] || []; // Row 2 = meta: missao, anv, obs, pernas (JSON)
    var missao = '';
    var anv = '';
    var obs = '';
    var pernas = [];
    // Meta está na aba "Meta" separada
    var shMeta = ss.getSheetByName('Meta');
    if (shMeta && shMeta.getLastRow() > 0) {
      var metaVals = shMeta.getDataRange().getValues();
      missao = metaVals[0] ? String(metaVals[0][1] || '') : '';
      anv    = metaVals[1] ? String(metaVals[1][1] || '') : '';
      obs    = metaVals[2] ? String(metaVals[2][1] || '') : '';
      try { pernas = JSON.parse(metaVals[3] ? String(metaVals[3][1] || '[]') : '[]'); } catch(e2) { pernas = []; }
    }
    var oficiais = [];
    for (var i = 1; i < rows.length; i++) {
      var r = rows[i];
      if (!r[0]) continue;
      oficiais.push({
        posto:     String(r[0] || ''),
        nome:      String(r[1] || ''),
        chat_id:   String(r[2] || ''),
        missao:    String(r[3] || ''),
        ciente:    r[4] === true || String(r[4]).toLowerCase() === 'true',
        timestamp: String(r[5] || '')
      });
    }
    return _json({ ok: true, oficiais: oficiais, missao: missao, anv: anv, obs: obs, pernas: pernas });
  }

  // ── set_conf ──────────────────────────────────────────────────────────────
  // Recebe: {action, missao, anv, obs, pernas:[str], oficiais:[{posto,nome,chat_id}]}
  if (action === 'set_conf') {
    var oficiais2 = p.oficiais;
    if (typeof oficiais2 === 'string') oficiais2 = JSON.parse(oficiais2);
    var pernas2 = p.pernas;
    if (typeof pernas2 === 'string') pernas2 = JSON.parse(pernas2);

    // Aba Confirmação — limpa e repopula
    var sh2 = _getOrCreate(ss, 'Confirmação');
    sh2.clearContents();
    sh2.getRange(1,1,1,6).setValues([['posto','nome','chat_id','missao','ciente','timestamp']]);
    if (Array.isArray(oficiais2) && oficiais2.length > 0) {
      var rows2 = oficiais2.map(function(o) {
        return [o.posto||'', o.nome||'', String(o.chat_id||''), p.missao||'', false, ''];
      });
      sh2.getRange(2,1,rows2.length,6).setValues(rows2);
    }

    // Aba Meta — salva metadados da missão
    var shM = _getOrCreate(ss, 'Meta');
    shM.clearContents();
    shM.getRange(1,1,4,2).setValues([
      ['missao', p.missao || ''],
      ['anv',    p.anv    || ''],
      ['obs',    p.obs    || ''],
      ['pernas', JSON.stringify(Array.isArray(pernas2) ? pernas2 : [])]
    ]);

    return _json({ ok: true, count: Array.isArray(oficiais2) ? oficiais2.length : 0 });
  }

  // ── conf_ciente ───────────────────────────────────────────────────────────
  // Recebe: {action, chat_id, nome, timestamp}
  if (action === 'conf_ciente') {
    var sh3 = ss.getSheetByName('Confirmação');
    if (!sh3) return _json({ ok: false, error: 'Aba Confirmação não encontrada' });
    var vals3 = sh3.getDataRange().getValues();
    var cid = String(p.chat_id || '').trim();
    var ts  = p.timestamp || new Date().toISOString();
    for (var j = 1; j < vals3.length; j++) {
      if (String(vals3[j][2]).trim() === cid) {
        sh3.getRange(j+1, 5, 1, 2).setValues([[true, ts]]);
        return _json({ ok: true });
      }
    }
    return _json({ ok: false, error: 'Oficial não encontrado: ' + cid });
  }

  return _json({ ok: false, error: 'Ação desconhecida: ' + action });
}

function _getOrCreate(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
