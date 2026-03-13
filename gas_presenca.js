/**
 * GAS — Sistema de Presença GTE
 * Planilha: 1E49Q1bPbhT2MlYjYXfpC5mbzuxTBAPzidY3DtZW2VAs
 * MP Dados: 1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao
 *
 * Abas na planilha de presença:
 *   "Registro" — ponto diário (Data, Posto, Nome Completo, Nome de Guerra, Entrada, Saída, SARAM)
 *   "Usuarios" — credenciais  (SARAM, SenhaHash, Posto, NomeCompleto, NomeGuerra, CriadoEm)
 *
 * Actions: register, login, clockIn, clockOut, status, history
 */

const PRESENCA_SHEET = '1E49Q1bPbhT2MlYjYXfpC5mbzuxTBAPzidY3DtZW2VAs';
const MP_SHEET       = '1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao';

function doGet(e)  { return handleRequest(e); }
function doPost(e) { return handleRequest(e); }

function handleRequest(e) {
  try {
    const p = e.parameter || {};
    const action = p.action || '';
    let result;
    switch (action) {
      case 'register':  result = doRegister(p); break;
      case 'login':     result = doLogin(p); break;
      case 'clockIn':   result = doClockIn(p); break;
      case 'clockOut':  result = doClockOut(p); break;
      case 'status':    result = doStatus(p); break;
      case 'history':   result = doHistory(p); break;
      default:          result = { ok: false, error: 'Ação inválida' };
    }
    return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message })).setMimeType(ContentService.MimeType.JSON);
  }
}

/* ---- Helpers ---- */
function hashPassword(pwd) {
  const raw = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, pwd + '_GTE_SALT_2026');
  return raw.map(b => ('0' + ((b + 256) % 256).toString(16)).slice(-2)).join('');
}

function getBRTNow() {
  return Utilities.formatDate(new Date(), 'America/Sao_Paulo', "yyyy-MM-dd HH:mm:ss");
}

function getBRTDate() {
  return Utilities.formatDate(new Date(), 'America/Sao_Paulo', "yyyy-MM-dd");
}

function getBRTTime() {
  return Utilities.formatDate(new Date(), 'America/Sao_Paulo', "HH:mm");
}

function getOrCreateSheet(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    if (headers) sheet.appendRow(headers);
  }
  return sheet;
}

function findInMP(saram) {
  const ss = SpreadsheetApp.openById(MP_SHEET);
  const sheet = ss.getSheetByName('Dados');
  if (!sheet) return null;
  const data = sheet.getDataRange().getValues();
  // Colunas: U(20)=Posto, V(21)=NomeCompleto, W(22)=Nome, AG(32)=Saram
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const saramCell = String(row[32] || '').trim().replace(/\s/g, '');
    if (saramCell === saram) {
      return {
        posto: String(row[20] || '').trim(),
        nomeCompleto: String(row[21] || '').trim(),
        nomeGuerra: String(row[22] || '').trim()
      };
    }
  }
  return null;
}

/* ---- Actions ---- */

function doRegister(p) {
  const saram = String(p.saram || '').trim().replace(/\s/g, '');
  const senha = String(p.senha || '');
  if (!saram || !senha) return { ok: false, error: 'SARAM e senha obrigatórios' };
  if (senha.length < 4) return { ok: false, error: 'Senha deve ter no mínimo 4 caracteres' };

  // Validar SARAM na MP
  const militar = findInMP(saram);
  if (!militar) return { ok: false, error: 'SARAM não encontrado na base de dados. Somente militares do GTE podem se cadastrar.' };

  // Verificar se já cadastrado
  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const usSheet = getOrCreateSheet(ss, 'Usuarios', ['SARAM', 'SenhaHash', 'Posto', 'NomeCompleto', 'NomeGuerra', 'CriadoEm']);
  const usData = usSheet.getDataRange().getValues();
  for (let i = 1; i < usData.length; i++) {
    if (String(usData[i][0]).trim() === saram) {
      return { ok: false, error: 'SARAM já cadastrado. Use o login.' };
    }
  }

  // Cadastrar
  const hash = hashPassword(senha);
  usSheet.appendRow([saram, hash, militar.posto, militar.nomeCompleto, militar.nomeGuerra, getBRTNow()]);

  return { ok: true, message: 'Cadastro realizado com sucesso!', militar: militar };
}

function doLogin(p) {
  const saram = String(p.saram || '').trim().replace(/\s/g, '');
  const senha = String(p.senha || '');
  if (!saram || !senha) return { ok: false, error: 'SARAM e senha obrigatórios' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const usSheet = ss.getSheetByName('Usuarios');
  if (!usSheet) return { ok: false, error: 'Nenhum usuário cadastrado ainda. Faça o cadastro.' };

  const usData = usSheet.getDataRange().getValues();
  const hash = hashPassword(senha);
  for (let i = 1; i < usData.length; i++) {
    if (String(usData[i][0]).trim() === saram && String(usData[i][1]).trim() === hash) {
      return {
        ok: true,
        militar: {
          posto: String(usData[i][2] || ''),
          nomeCompleto: String(usData[i][3] || ''),
          nomeGuerra: String(usData[i][4] || '')
        }
      };
    }
  }
  return { ok: false, error: 'SARAM ou senha incorretos.' };
}

function doClockIn(p) {
  const saram = String(p.saram || '').trim().replace(/\s/g, '');
  if (!saram) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);

  // Buscar dados do militar no Usuarios
  const usSheet = ss.getSheetByName('Usuarios');
  if (!usSheet) return { ok: false, error: 'Usuário não encontrado' };
  const usData = usSheet.getDataRange().getValues();
  let mil = null;
  for (let i = 1; i < usData.length; i++) {
    if (String(usData[i][0]).trim() === saram) {
      mil = { posto: usData[i][2], nomeCompleto: usData[i][3], nomeGuerra: usData[i][4] };
      break;
    }
  }
  if (!mil) return { ok: false, error: 'Usuário não cadastrado' };

  // Verificar se já tem entrada hoje sem saída
  const regSheet = getOrCreateSheet(ss, 'Registro', ['Data', 'Posto', 'Nome Completo', 'Nome de Guerra', 'Entrada', 'Saída', 'SARAM']);
  const regData = regSheet.getDataRange().getValues();
  const hoje = getBRTDate();
  for (let i = 1; i < regData.length; i++) {
    if (String(regData[i][6]).trim() === saram && String(regData[i][0]).trim() === hoje && !regData[i][5]) {
      return { ok: false, error: 'Entrada já registrada hoje. Registre a saída primeiro.' };
    }
  }

  // Registrar entrada
  const hora = getBRTTime();
  regSheet.appendRow([hoje, mil.posto, mil.nomeCompleto, mil.nomeGuerra, hora, '', saram]);

  return { ok: true, message: `Entrada registrada: ${hora}`, hora: hora };
}

function doClockOut(p) {
  const saram = String(p.saram || '').trim().replace(/\s/g, '');
  if (!saram) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const regSheet = ss.getSheetByName('Registro');
  if (!regSheet) return { ok: false, error: 'Nenhum registro encontrado' };

  const regData = regSheet.getDataRange().getValues();
  const hoje = getBRTDate();

  // Encontrar a última entrada de hoje sem saída
  for (let i = regData.length - 1; i >= 1; i--) {
    if (String(regData[i][6]).trim() === saram && String(regData[i][0]).trim() === hoje && !regData[i][5]) {
      const hora = getBRTTime();
      regSheet.getRange(i + 1, 6).setValue(hora); // Coluna F = Saída
      return { ok: true, message: `Saída registrada: ${hora}`, hora: hora };
    }
  }

  return { ok: false, error: 'Nenhuma entrada aberta hoje. Registre a entrada primeiro.' };
}

function doStatus(p) {
  const saram = String(p.saram || '').trim().replace(/\s/g, '');
  if (!saram) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const regSheet = ss.getSheetByName('Registro');
  if (!regSheet) return { ok: true, registros: [], aberto: false };

  const regData = regSheet.getDataRange().getValues();
  const hoje = getBRTDate();
  const registros = [];
  let aberto = false;

  for (let i = 1; i < regData.length; i++) {
    if (String(regData[i][6]).trim() === saram && String(regData[i][0]).trim() === hoje) {
      registros.push({
        entrada: String(regData[i][4] || ''),
        saida: String(regData[i][5] || '')
      });
      if (!regData[i][5]) aberto = true;
    }
  }

  return { ok: true, registros: registros, aberto: aberto };
}

function doHistory(p) {
  const saram = String(p.saram || '').trim().replace(/\s/g, '');
  const dias = parseInt(p.dias) || 7;
  if (!saram) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const regSheet = ss.getSheetByName('Registro');
  if (!regSheet) return { ok: true, registros: [] };

  const regData = regSheet.getDataRange().getValues();
  const registros = [];

  for (let i = regData.length - 1; i >= 1; i--) {
    if (String(regData[i][6]).trim() === saram) {
      registros.push({
        data: String(regData[i][0] || ''),
        entrada: String(regData[i][4] || ''),
        saida: String(regData[i][5] || '')
      });
      if (registros.length >= dias * 3) break; // max entries
    }
  }

  return { ok: true, registros: registros };
}
