/**
 * Google Apps Script — Proxy de Escrita para Consultas de Escala
 * Deploy como Web App (executar como: eu, acesso: qualquer pessoa)
 * 
 * Planilha: Dados Bot GTE-1 Escala (1MxhMnlzZNdXUkFRs_XmBI8SI3xhL1TDLEiCZ7aJKE-g)
 * 
 * INSTRUÇÕES DE DEPLOY:
 * 1. Abra a planilha "Dados Bot GTE-1 Escala"
 * 2. Vá em Extensões → Apps Script
 * 3. Cole este código
 * 4. Deploy → New deployment → Web app
 *    - Executar como: Eu
 *    - Quem tem acesso: Qualquer pessoa
 * 5. Copie a URL e coloque no bot (APPS_SCRIPT_URL)
 * 
 * AÇÕES SUPORTADAS:
 * 
 * 1. action=create_consulta
 *    - Grava o texto da consulta na aba "Consulta VC-1" ou "Consulta VC-2"
 *    - Params: vc (1|2), text (texto da consulta)
 * 
 * 2. action=save_response
 *    - Grava resposta de um tripulante na aba "Raio Final VC-1" ou "Raio Final VC-2"
 *    - Params: vc (1|2), name (nome do tripulante), responses (JSON: {"A": true, "B": false}), motivo (opcional)
 * 
 * 3. action=lock_consulta
 *    - Marca consulta como encerrada (grava timestamp na aba)
 *    - Params: vc (1|2)
 * 
 * 4. action=get_responses
 *    - Retorna todas as respostas da aba Raio Final
 *    - Params: vc (1|2)
 */

var SHEET_ID = '1MxhMnlzZNdXUkFRs_XmBI8SI3xhL1TDLEiCZ7aJKE-g';

function doPost(e) {
  try {
    var params = JSON.parse(e.postData.contents);
    return handleRequest(params);
  } catch (err) {
    return jsonResponse({ok: false, error: err.message});
  }
}

function doGet(e) {
  try {
    var params = e.parameter;
    return handleRequest(params);
  } catch (err) {
    return jsonResponse({ok: false, error: err.message});
  }
}

function handleRequest(params) {
  var action = params.action;
  var vc = params.vc || '1';
  var ss = SpreadsheetApp.openById(SHEET_ID);
  
  if (action === 'create_consulta') {
    return createConsulta(ss, vc, params.text || '');
  }
  if (action === 'save_response') {
    return saveResponse(ss, vc, params.name, params.responses, params.motivo || '');
  }
  if (action === 'lock_consulta') {
    return lockConsulta(ss, vc);
  }
  if (action === 'get_responses') {
    return getResponses(ss, vc);
  }
  if (action === 'clear_consulta') {
    return clearConsulta(ss, vc);
  }
  
  return jsonResponse({ok: false, error: 'Ação desconhecida: ' + action});
}

// ─── Criar consulta ──────────────────────────────────────────────────────────
function createConsulta(ss, vc, text) {
  var sheetName = 'Consulta VC-' + vc;
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return jsonResponse({ok: false, error: 'Aba não encontrada: ' + sheetName});
  
  // Limpa a aba e grava o texto da consulta
  sheet.clear();
  sheet.getRange('A1').setValue(text);
  sheet.getRange('A2').setValue('Criada em: ' + new Date().toLocaleString('pt-BR'));
  sheet.getRange('A3').setValue('Status: ATIVA');
  
  return jsonResponse({ok: true, sheet: sheetName});
}

// ─── Gravar resposta ─────────────────────────────────────────────────────────
function saveResponse(ss, vc, name, responsesRaw, motivo) {
  var sheetName = 'Raio Final VC-' + vc;
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return jsonResponse({ok: false, error: 'Aba não encontrada: ' + sheetName});
  
  var responses = typeof responsesRaw === 'string' ? JSON.parse(responsesRaw) : responsesRaw;
  
  // Procurar tripulante na coluna D (nome)
  var dataRange = sheet.getDataRange();
  var values = dataRange.getValues();
  var headerRow = values[0]; // Primeira linha = cabeçalho com letras das missões
  
  // Mapear letras das missões para colunas (A partir da col G = index 6)
  var missionCols = {};
  for (var c = 6; c < headerRow.length; c++) {
    var letter = String(headerRow[c]).trim().toUpperCase();
    if (letter.match(/^[A-Z]$/)) {
      missionCols[letter] = c;
    }
  }
  
  // Buscar tripulante pelo nome (coluna D = index 3)
  var found = false;
  for (var r = 1; r < values.length; r++) {
    var cellName = String(values[r][3]).trim().toUpperCase();
    if (cellName && name.toUpperCase().indexOf(cellName.split('(')[0].trim()) >= 0) {
      // Encontrou — gravar respostas
      for (var letra in responses) {
        if (missionCols.hasOwnProperty(letra)) {
          var col = missionCols[letra];
          var value = responses[letra] ? '1' : '-';
          sheet.getRange(r + 1, col + 1).setValue(value);
        }
      }
      // Motivo na última coluna usada + 1, ou col Q (17)
      if (motivo) {
        sheet.getRange(r + 1, 17).setValue(motivo);
      }
      // Timestamp
      sheet.getRange(r + 1, 2).setValue(new Date().toLocaleString('pt-BR'));
      found = true;
      break;
    }
  }
  
  if (!found) {
    // Tripulante não existe — adicionar nova linha
    var newRow = values.length + 1;
    sheet.getRange(newRow, 4).setValue(name); // Col D = nome
    for (var letra2 in responses) {
      if (missionCols.hasOwnProperty(letra2)) {
        sheet.getRange(newRow, missionCols[letra2] + 1).setValue(responses[letra2] ? '1' : '-');
      }
    }
    if (motivo) sheet.getRange(newRow, 17).setValue(motivo);
    sheet.getRange(newRow, 2).setValue(new Date().toLocaleString('pt-BR'));
  }
  
  return jsonResponse({ok: true, found: found, name: name});
}

// ─── Encerrar consulta ──────────────────────────────────────────────────────
function lockConsulta(ss, vc) {
  var sheetName = 'Consulta VC-' + vc;
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return jsonResponse({ok: false, error: 'Aba não encontrada'});
  
  sheet.getRange('A3').setValue('Status: ENCERRADA em ' + new Date().toLocaleString('pt-BR'));
  return jsonResponse({ok: true});
}

// ─── Buscar respostas ────────────────────────────────────────────────────────
function getResponses(ss, vc) {
  var sheetName = 'Raio Final VC-' + vc;
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return jsonResponse({ok: false, error: 'Aba não encontrada'});
  
  var data = sheet.getDataRange().getValues();
  return jsonResponse({ok: true, data: data});
}

// ─── Limpar consulta (arquivar) ─────────────────────────────────────────────
function clearConsulta(ss, vc) {
  var consultaSheet = ss.getSheetByName('Consulta VC-' + vc);
  var raioSheet = ss.getSheetByName('Raio Final VC-' + vc);
  
  if (consultaSheet) consultaSheet.clear();
  if (raioSheet) {
    // Manter cabeçalho, limpar dados
    var lastRow = raioSheet.getLastRow();
    if (lastRow > 1) {
      raioSheet.getRange(2, 1, lastRow - 1, raioSheet.getLastColumn()).clear();
    }
  }
  
  return jsonResponse({ok: true});
}

// ─── Helper ─────────────────────────────────────────────────────────────────
function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
