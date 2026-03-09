function doGet(e) {
  try {
    var p = e.parameter;
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var action = p.action || 'get';

    if (action === 'save') {
      var vc = p.vc || 'VC-1';
      var nome = p.nome || '';
      var respostas = p.respostas || '';
      var confirmado = p.confirmado || 'false';
      var timestamp = new Date().toISOString();
      var sh = ss.getSheetByName(vc);
      if (!sh) {
        sh = ss.insertSheet(vc);
        sh.getRange(1,1,1,6).setValues([['Timestamp','Nome','Respostas','Confirmado','VC','Atualizado']]);
      }
      var data = sh.getDataRange().getValues();
      var found = false;
      for (var i = 1; i < data.length; i++) {
        if (data[i][1] === nome) {
          sh.getRange(i+1,1,1,6).setValues([[timestamp,nome,respostas,confirmado,vc,timestamp]]);
          found = true; break;
        }
      }
      if (!found) sh.appendRow([timestamp,nome,respostas,confirmado,vc,timestamp]);
      return _json({ok:true});
    }

    if (action === 'clear') {
      var vc2 = p.vc || 'VC-1';
      var sh2 = ss.getSheetByName(vc2);
      if (sh2 && sh2.getLastRow() > 1)
        sh2.getRange(2,1,sh2.getLastRow()-1,sh2.getLastColumn()).clear();
      return _json({ok:true});
    }

    if (action === 'register') {
      var chatId = p.chat_id || '';
      var tgName = p.tg_name || '';
      var posto  = (p.posto || '').toUpperCase().trim();
      var nomeGuerra = (p.nome_guerra || '').toUpperCase().trim();
      var vcR = p.vc || '';
      var timestamp2 = new Date().toISOString();
      if (!vcR) vcR = _lookupVCfromMP(nomeGuerra);
      var shT = ss.getSheetByName('Tripulantes');
      if (!shT) {
        shT = ss.insertSheet('Tripulantes');
        shT.getRange(1,1,1,7).setValues([['chat_id','tg_name','posto','nome_guerra','vc','ativo','cadastrado_em']]);
      }
      var rowsT = shT.getDataRange().getValues();
      var found2 = false;
      for (var j = 1; j < rowsT.length; j++) {
        if (String(rowsT[j][0]) === String(chatId)) {
          shT.getRange(j+1,1,1,7).setValues([[chatId,tgName,posto,nomeGuerra,vcR,'SIM',timestamp2]]);
          found2 = true; break;
        }
      }
      if (!found2) shT.appendRow([chatId,tgName,posto,nomeGuerra,vcR,'SIM',timestamp2]);
      return _json({ok:true, vc: vcR});
    }

    if (action === 'get_tripulantes') {
      var shT2 = ss.getSheetByName('Tripulantes');
      if (!shT2) return _json({ok:true, tripulantes:[]});
      var rows2 = shT2.getDataRange().getValues();
      var list = [];
      for (var k = 1; k < rows2.length; k++) {
        var r = rows2[k];
        if (r[5] && String(r[5]).toUpperCase() !== 'NÃO' && String(r[5]).toUpperCase() !== 'NAO' && String(r[5]).toUpperCase() !== 'FALSE') {
          list.push({chat_id:String(r[0]),tg_name:r[1],posto:r[2],nome_guerra:r[3],vc:r[4]});
        }
      }
      return _json({ok:true, tripulantes:list});
    }

    // action === 'get' — retorna VC-1 e VC-2 juntos
    var result = {ok:true, vc1:[], vc2:[]};
    var sh1 = ss.getSheetByName('VC-1');
    var sh2b = ss.getSheetByName('VC-2');
    if (sh1) result.vc1 = sh1.getDataRange().getValues();
    if (sh2b) result.vc2 = sh2b.getDataRange().getValues();
    return _json(result);

  } catch(err) {
    return _json({ok:false, error:err.message});
  }
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function _lookupVCfromMP(nomeGuerra) {
  try {
    // Planilha principal (SHEET) — aba "Dados"
    // Estrutura: col5=QT (VC1/VC2), col6=TRIGRAMA, col7=nome completo
    var MP_ID = '1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao';
    var mp = SpreadsheetApp.openById(MP_ID);
    var sh = mp.getSheetByName('Dados');
    if (!sh) return '';
    var vals = sh.getDataRange().getValues();
    var ng = nomeGuerra.toUpperCase().trim();
    for (var i = 0; i < vals.length; i++) {
      var qt  = String(vals[i][5]||'').toUpperCase().trim(); // VC1 ou VC2
      var tri = String(vals[i][6]||'').toUpperCase().trim(); // trigrama ex: MAC
      var nom = String(vals[i][7]||'').toUpperCase().trim(); // ex: MJ MACHADO
      if (!qt) continue;
      // Compara trigrama ou parte do nome
      if (tri === ng || nom.includes(ng) || ng.includes(tri)) {
        // Normaliza para VC-1 / VC-2
        return qt.replace('VC1','VC-1').replace('VC2','VC-2');
      }
    }
  } catch(e) { Logger.log('_lookupVCfromMP err: '+e.message); }
  return '';
}

function doPost(e) {
  try {
    var p = JSON.parse(e.postData.contents);
    return doGet({ parameter: p });
  } catch(err) {
    return _json({ok:false, error:err.message});
  }
}
