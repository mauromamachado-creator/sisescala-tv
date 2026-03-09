// ═══════════════════════════════════════════════════════════════
// GAS — RESPOSTA CONSULTA  (v3 — raio estruturado)
// Estrutura VC-1 / VC-2:
//   [ordem, posto, nome_guerra, respostas, confirmado, atualizado]
// ═══════════════════════════════════════════════════════════════

function doGet(e) {
  try {
    var p = e.parameter || {};
    return _dispatch(p);
  } catch(err) {
    return _json({ok:false, error:err.message});
  }
}

function doPost(e) {
  try {
    var p = JSON.parse(e.postData.contents);
    return _dispatch(p);
  } catch(err) {
    return _json({ok:false, error:err.message});
  }
}

function _dispatch(p) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var action = p.action || 'get';

  // ── set_raio ────────────────────────────────────────────────────
  if (action === 'set_raio') {
    var vcSheet = p.vc || 'VC-1';
    var pilotos = p.pilotos; // [{posto, nome_guerra}, ...]
    if (typeof pilotos === 'string') pilotos = JSON.parse(pilotos);
    var sh = _getOrCreateSheet(ss, vcSheet);
    sh.clearContents();
    sh.getRange(1,1,1,6).setValues([['ordem','posto','nome_guerra','respostas','confirmado','atualizado']]);
    if (Array.isArray(pilotos) && pilotos.length > 0) {
      var rows = pilotos.map(function(p2, i) {
        return [i+1, p2.posto||'', (p2.nome_guerra||'').toUpperCase(), '', false, ''];
      });
      sh.getRange(2,1,rows.length,6).setValues(rows);
    }
    return _json({ok:true, count: Array.isArray(pilotos)?pilotos.length:0});
  }

  // ── save_response ───────────────────────────────────────────────
  if (action === 'save_response') {
    var vcSheet2 = p.vc || 'VC-1';
    var ng = (p.nome_guerra||'').toUpperCase().trim();
    var respostas = p.respostas || '';
    var confirmado = p.confirmado === true || p.confirmado === 'true' || p.confirmado === '1';
    var ts = new Date().toISOString();
    var sh2 = ss.getSheetByName(vcSheet2);
    if (!sh2) return _json({ok:false, error:'Sheet not found: '+vcSheet2});
    var vals = sh2.getDataRange().getValues();
    for (var i = 1; i < vals.length; i++) {
      var rowNg = String(vals[i][2]||'').toUpperCase().trim();
      if (rowNg === ng || rowNg.includes(ng) || ng.includes(rowNg)) {
        sh2.getRange(i+1, 4, 1, 3).setValues([[respostas, confirmado, ts]]);
        return _json({ok:true});
      }
    }
    return _json({ok:false, error:'Piloto não encontrado: '+ng});
  }

  // ── archive_vc (limpa respostas, mantém nomes) ──────────────────
  if (action === 'archive_vc') {
    var vcSheet3 = p.vc || 'VC-1';
    var sh3 = ss.getSheetByName(vcSheet3);
    if (sh3 && sh3.getLastRow() > 1) {
      var nRows = sh3.getLastRow() - 1;
      // Zera cols 4-6 (respostas, confirmado, atualizado) — mantém ordem/posto/nome
      var blank = [];
      for (var r = 0; r < nRows; r++) blank.push(['', false, '']);
      sh3.getRange(2, 4, nRows, 3).setValues(blank);
    }
    return _json({ok:true});
  }

  // ── register ────────────────────────────────────────────────────
  if (action === 'register') {
    var chatId = p.chat_id || '';
    var tgName = p.tg_name || '';
    var posto  = (p.posto || '').toUpperCase().trim();
    var nomeGuerra = (p.nome_guerra || '').toUpperCase().trim();
    var vcR = p.vc || '';
    var ts2 = new Date().toISOString();
    var shT = _getOrCreateSheet(ss, 'Tripulantes');
    if (shT.getLastRow() < 1 || shT.getRange(1,1).getValue() !== 'chat_id') {
      shT.clearContents();
      shT.getRange(1,1,1,7).setValues([['chat_id','tg_name','posto','nome_guerra','vc','ativo','cadastrado_em']]);
    }
    var rowsT = shT.getDataRange().getValues();
    var found2 = false;
    for (var j = 1; j < rowsT.length; j++) {
      if (String(rowsT[j][0]) === String(chatId)) {
        shT.getRange(j+1,1,1,7).setValues([[chatId,tgName,posto,nomeGuerra,vcR,true,ts2]]);
        found2 = true; break;
      }
    }
    if (!found2) shT.appendRow([chatId,tgName,posto,nomeGuerra,vcR,true,ts2]);
    return _json({ok:true, vc: vcR});
  }

  // ── get_tripulantes ─────────────────────────────────────────────
  if (action === 'get_tripulantes') {
    var shT2 = ss.getSheetByName('Tripulantes');
    if (!shT2) return _json({ok:true, tripulantes:[]});
    var rows2 = shT2.getDataRange().getValues();
    var list = [];
    for (var k = 1; k < rows2.length; k++) {
      var r = rows2[k];
      var ativo = r[5];
      if (ativo === true || String(ativo).toUpperCase() === 'SIM' || String(ativo).toUpperCase() === 'TRUE') {
        list.push({chat_id:String(r[0]),tg_name:r[1],posto:r[2],nome_guerra:r[3],vc:r[4]});
      }
    }
    return _json({ok:true, tripulantes:list});
  }

  // ── get (padrão) — retorna raio + respostas de VC-1 e VC-2 ─────
  var result = {ok:true, vc1:[], vc2:[]};
  var sh1 = ss.getSheetByName('VC-1');
  var sh2b = ss.getSheetByName('VC-2');
  if (sh1 && sh1.getLastRow() > 0) result.vc1 = sh1.getDataRange().getValues();
  if (sh2b && sh2b.getLastRow() > 0) result.vc2 = sh2b.getDataRange().getValues();
  return _json(result);
}

function _getOrCreateSheet(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
