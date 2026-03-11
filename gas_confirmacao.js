// GAS - SisGOPA Confirmação de Missão v2
// Suporte a múltiplas OMs por controlão
// Ações: set_conf_all, get_conf_all, conf_ciente, set_conf (compat)

var SS_ID = '15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA';
var BOT_TOKEN = '8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU';

function doGet(e) {
  return _dispatch(e && e.parameter ? e.parameter : {});
}

function doPost(e) {
  var p = {};
  try { p = JSON.parse(e.postData.contents); } catch(err) {}
  return _dispatch(p);
}

function _dispatch(p) {
  var action = p.action || 'get_conf_all';
  var ss = SpreadsheetApp.openById(SS_ID);

  // ── set_conf_all ─────────────────────────────────────────────────────────
  // Recebe: { action, oms: [ {om, anv, fab, pernas:[str], tripulantes:[{posto,nome,chat_id}]} ] }
  if (action === 'set_conf_all') {
    var oms = p.oms;
    if (typeof oms === 'string') oms = JSON.parse(oms);
    if (!Array.isArray(oms) || oms.length === 0) return _json({ ok: false, error: 'Nenhuma OM fornecida' });

    // Salva todas OMs como JSON na aba "OMs"
    var shOMs = _getOrCreate(ss, 'OMs');
    shOMs.clearContents();
    shOMs.getRange(1,1).setValue(JSON.stringify(oms));

    // Salva sobreaviso na aba "Sobreavisos"
    var sbs = p.sobreavisos;
    if (typeof sbs === 'string') sbs = JSON.parse(sbs);
    if (Array.isArray(sbs) && sbs.length > 0) {
      var shSb = _getOrCreate(ss, 'Sobreavisos');
      shSb.clearContents();
      shSb.getRange(1,1).setValue(JSON.stringify(sbs));
    }

    // Aba Confirmação — todos tripulantes de todas OMs
    var sh2 = _getOrCreate(ss, 'Confirmação');
    sh2.clearContents();
    sh2.getRange(1,1,1,7).setValues([['posto','nome','chat_id','om','anv','ciente','timestamp']]);
    var rows2 = [];
    oms.forEach(function(om) {
      var trip = om.tripulantes || [];
      var anv_str = (om.anv || '') + (om.fab ? ' / FAB ' + om.fab : '');
      trip.forEach(function(t) {
        rows2.push([t.posto||'', t.nome||'', String(t.chat_id||''), om.om||'', anv_str, false, '']);
      });
    });
    if (rows2.length > 0) sh2.getRange(2,1,rows2.length,7).setValues(rows2);

    return _json({ ok: true, oms: oms.length, tripulantes: rows2.length });
  }

  // ── get_conf_all ─────────────────────────────────────────────────────────
  if (action === 'get_conf_all' || action === 'get_conf') {
    // Lê todas as OMs
    var shOMs2 = ss.getSheetByName('OMs');
    var oms2 = [];
    if (shOMs2 && shOMs2.getLastRow() > 0) {
      try { oms2 = JSON.parse(shOMs2.getRange(1,1).getValue() || '[]'); } catch(e2) { oms2 = []; }
    }

    // Lê status de ciência de cada tripulante
    var sh3 = ss.getSheetByName('Confirmação');
    var cienMap = {}; // chat_id+om → {ciente, timestamp}
    if (sh3 && sh3.getLastRow() > 1) {
      var vals3 = sh3.getDataRange().getValues();
      for (var i = 1; i < vals3.length; i++) {
        var r = vals3[i];
        var key = String(r[2]) + '|' + String(r[3]);
        cienMap[key] = { ciente: r[5] === true || String(r[5]).toLowerCase() === 'true', timestamp: String(r[6]||'') };
      }
    }

    // Enriquece OMs com status de ciência
    oms2.forEach(function(om) {
      var anv_str = (om.anv || '') + (om.fab ? ' / FAB ' + om.fab : '');
      om.anv_str = anv_str;
      (om.tripulantes || []).forEach(function(t) {
        var key = String(t.chat_id||'') + '|' + (om.om||'');
        var st = cienMap[key] || {};
        t.ciente = st.ciente || false;
        t.timestamp = st.timestamp || '';
      });
    });

    // Lê sobreaviso
    var shSb2 = ss.getSheetByName('Sobreavisos');
    var sbs2 = [];
    if (shSb2 && shSb2.getLastRow() > 0) {
      try { sbs2 = JSON.parse(shSb2.getRange(1,1).getValue() || '[]'); } catch(e3) { sbs2 = []; }
    }

    return _json({ ok: true, oms: oms2, sobreavisos: sbs2 });
  }

  // ── conf_ciente ───────────────────────────────────────────────────────────
  if (action === 'conf_ciente') {
    var sh4 = ss.getSheetByName('Confirmação');
    if (!sh4) return _json({ ok: false, error: 'Aba Confirmação não encontrada' });
    var vals4 = sh4.getDataRange().getValues();
    var cid = String(p.chat_id || '').trim();
    var om_id = String(p.om || '').trim();
    var ts = p.timestamp || new Date().toISOString();
    for (var j = 1; j < vals4.length; j++) {
      var match_cid = String(vals4[j][2]).trim() === cid;
      var match_om = !om_id || String(vals4[j][3]).trim() === om_id;
      if (match_cid && match_om) {
        sh4.getRange(j+1, 6, 1, 2).setValues([[true, ts]]);
        return _json({ ok: true });
      }
    }
    return _json({ ok: false, error: 'Oficial não encontrado: ' + cid + ' / ' + om_id });
  }

  // ── set_conf (compat — manda OM única, converte pra set_conf_all) ─────────
  if (action === 'set_conf') {
    var oficiais_c = p.oficiais;
    if (typeof oficiais_c === 'string') oficiais_c = JSON.parse(oficiais_c);
    var pernas_c = p.pernas;
    if (typeof pernas_c === 'string') pernas_c = JSON.parse(pernas_c);
    var trip_c = (oficiais_c || []).map(function(o) {
      return { posto: o.posto||'', nome: o.nome||'', chat_id: String(o.chat_id||'') };
    });
    var parts_anv = String(p.anv||'').split('/');
    var anv_c = parts_anv[0].trim().replace('VC-','');
    anv_c = parts_anv[0].trim();
    var fab_c = parts_anv.length > 1 ? parts_anv[1].replace('FAB','').trim() : '';
    p.oms = [{ om: p.missao||'', anv: anv_c, fab: fab_c, pernas: Array.isArray(pernas_c)?pernas_c:[], tripulantes: trip_c }];
    p.action = 'set_conf_all';
    return _dispatch(p);
  }

  // ── send_conf ─────────────────────────────────────────────────────────────
  if (action === 'send_conf') {
    var msgs = p.messages;
    if (typeof msgs === 'string') msgs = JSON.parse(msgs);
    if (!Array.isArray(msgs) || msgs.length === 0) return _json({ ok: false, error: 'Nenhuma mensagem fornecida' });
    var enviados = 0, erros = 0;
    msgs.forEach(function(m) {
      if (!m.chat_id || !m.texto) { erros++; return; }
      var payload = {
        chat_id: String(m.chat_id),
        text: m.texto,
        reply_markup: JSON.stringify({
          inline_keyboard: [[{ text: '✅ CIENTE', callback_data: 'conf_ciente|' + (m.om || m.letra || '') }]]
        })
      };
      var opts = { method: 'post', contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true };
      try {
        var resp = UrlFetchApp.fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage', opts);
        var result = JSON.parse(resp.getContentText());
        if (result.ok) enviados++;
        else { Logger.log('TG error ' + m.chat_id + ': ' + resp.getContentText()); erros++; }
      } catch(e_tg) { Logger.log('Fetch error: ' + e_tg); erros++; }
    });
    return _json({ ok: true, enviados: enviados, erros: erros });
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
