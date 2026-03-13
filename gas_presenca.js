/**
 * GAS — Sistema de Presença GTE
 * Planilha: 1E49Q1bPbhT2MlYjYXfpC5mbzuxTBAPzidY3DtZW2VAs
 * MP Dados: 1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao
 *
 * Abas na planilha de presença:
 *   "Registro" — ponto diário (Data, Posto, Nome Completo, Nome de Guerra, Entrada, Saída, SARAM, Horas)
 *   "Usuarios" — credenciais  (SARAM, SenhaHash, Posto, NomeCompleto, NomeGuerra, CriadoEm)
 *   "Indisponibilidade" — lançamentos (SARAM, Posto, NomeGuerra, Tipo, DataInicio, DataFim, Obs, CriadoEm)
 *
 * Actions: register, login, clockIn, clockOut, status, history, chamada, lancar_indisp, minhas_indisp, cancelar_indisp
 */

const PRESENCA_SHEET = '1E49Q1bPbhT2MlYjYXfpC5mbzuxTBAPzidY3DtZW2VAs';
const MP_SHEET       = '1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao';
const REG_HEADERS    = ['Data', 'Posto', 'Nome Completo', 'Nome de Guerra', 'Entrada', 'Saída', 'SARAM', 'Horas'];

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
      case 'chamada':       result = doChamada(p); break;
      case 'gerencial':     result = doGerencial(p); break;
      case 'lancar_indisp': result = doLancarIndisp(p); break;
      case 'minhas_indisp': result = doMinhasIndisp(p); break;
      case 'cancelar_indisp': result = doCancelarIndisp(p); break;
      default:              result = { ok: false, error: 'Ação inválida' };
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

function getBRTDatetime() {
  return Utilities.formatDate(new Date(), 'America/Sao_Paulo', "yyyy-MM-dd HH:mm");
}

function cellToDate(cell) {
  if (!cell) return '';
  if (cell instanceof Date) {
    return Utilities.formatDate(cell, 'America/Sao_Paulo', "yyyy-MM-dd");
  }
  return String(cell).trim();
}

function normalizeSaram(s) {
  return String(s || '').trim().replace(/[\.\-\s]/g, '');
}

function calcHoras(dataEntrada, horaEntrada, dataSaida, horaSaida) {
  // Monta datetimes completos e calcula diferença em horas
  try {
    // Parsear entrada
    const dtEntStr = cellToDate(dataEntrada) + ' ' + String(horaEntrada || '').trim();
    const dtSaiStr = (dataSaida ? cellToDate(dataSaida) : cellToDate(dataEntrada)) + ' ' + String(horaSaida || '').trim();
    
    const partes1 = dtEntStr.split(/[\s\-\:]/);
    const partes2 = dtSaiStr.split(/[\s\-\:]/);
    
    const d1 = new Date(partes1[0], partes1[1]-1, partes1[2], partes1[3], partes1[4]);
    const d2 = new Date(partes2[0], partes2[1]-1, partes2[2], partes2[3], partes2[4]);
    
    // Se saída < entrada, significa que cruzou meia-noite
    let diffMs = d2.getTime() - d1.getTime();
    if (diffMs < 0) {
      // Adiciona 24h (cruzou meia-noite)
      diffMs += 24 * 60 * 60 * 1000;
    }
    
    const totalMin = Math.round(diffMs / 60000);
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return h + ':' + ('0' + m).slice(-2);
  } catch(e) {
    return '';
  }
}

function getOrCreateSheet(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    if (headers) {
      sheet.appendRow(headers);
      // Filtro automático no cabeçalho
      sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
      sheet.setFrozenRows(1);
    }
  }
  // Garantir filtro automático
  try {
    if (!sheet.getFilter()) {
      const lastCol = sheet.getLastColumn() || headers.length;
      const lastRow = Math.max(sheet.getLastRow(), 1);
      sheet.getRange(1, 1, lastRow, lastCol).createFilter();
    }
  } catch(e) { /* filtro já existe */ }
  return sheet;
}

function findInMP(saram) {
  const ss = SpreadsheetApp.openById(MP_SHEET);
  const sheet = ss.getSheetByName('Dados');
  if (!sheet) return null;
  const data = sheet.getDataRange().getValues();
  const saramNorm = normalizeSaram(saram);
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const saramCell = normalizeSaram(row[32]);
    if (saramCell === saramNorm) {
      return {
        posto: String(row[20] || '').trim(),
        nomeCompleto: String(row[21] || '').trim(),
        nomeGuerra: String(row[22] || '').trim(),
        saramOriginal: String(row[32] || '').trim()
      };
    }
  }
  return null;
}

/* ---- Actions ---- */

function doRegister(p) {
  const saramInput = String(p.saram || '').trim();
  const saramNorm = normalizeSaram(saramInput);
  const senha = String(p.senha || '');
  if (!saramNorm || !senha) return { ok: false, error: 'SARAM e senha obrigatórios' };
  if (senha.length < 4) return { ok: false, error: 'Senha deve ter no mínimo 4 caracteres' };

  const militar = findInMP(saramInput);
  if (!militar) return { ok: false, error: 'SARAM não encontrado na base de dados. Somente militares do GTE podem se cadastrar.' };

  const saram = militar.saramOriginal || saramInput;

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const usSheet = getOrCreateSheet(ss, 'Usuarios', ['SARAM', 'SenhaHash', 'Posto', 'NomeCompleto', 'NomeGuerra', 'CriadoEm']);
  const usData = usSheet.getDataRange().getValues();
  for (let i = 1; i < usData.length; i++) {
    if (normalizeSaram(usData[i][0]) === saramNorm) {
      return { ok: false, error: 'SARAM já cadastrado. Use o login.' };
    }
  }

  const hash = hashPassword(senha);
  usSheet.appendRow([saram, hash, militar.posto, militar.nomeCompleto, militar.nomeGuerra, getBRTNow()]);

  return { ok: true, message: 'Cadastro realizado com sucesso!', militar: militar };
}

function doLogin(p) {
  const saramInput = String(p.saram || '').trim();
  const saramNorm = normalizeSaram(saramInput);
  const senha = String(p.senha || '');
  if (!saramNorm || !senha) return { ok: false, error: 'SARAM e senha obrigatórios' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const usSheet = ss.getSheetByName('Usuarios');
  if (!usSheet) return { ok: false, error: 'Nenhum usuário cadastrado ainda. Faça o cadastro.' };

  const usData = usSheet.getDataRange().getValues();
  const hash = hashPassword(senha);
  for (let i = 1; i < usData.length; i++) {
    if (normalizeSaram(usData[i][0]) === saramNorm && String(usData[i][1]).trim() === hash) {
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

function _authUser(p) {
  const saramInput = String(p.saram || '').trim();
  const saramNorm = normalizeSaram(saramInput);
  const senha = String(p.senha || '');
  if (!saramNorm) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const usSheet = ss.getSheetByName('Usuarios');
  if (!usSheet) return { ok: false, error: 'Usuário não encontrado' };
  const usData = usSheet.getDataRange().getValues();
  const hash = senha ? hashPassword(senha) : null;
  let mil = null;
  let saramStored = saramInput;
  for (let i = 1; i < usData.length; i++) {
    if (normalizeSaram(usData[i][0]) === saramNorm) {
      if (hash && String(usData[i][1]).trim() !== hash) {
        return { ok: false, error: 'Senha incorreta.' };
      }
      mil = { posto: usData[i][2], nomeCompleto: usData[i][3], nomeGuerra: usData[i][4] };
      saramStored = String(usData[i][0]).trim();
      break;
    }
  }
  if (!mil) return { ok: false, error: 'Usuário não cadastrado' };
  return { ok: true, ss: ss, mil: mil, saramNorm: saramNorm, saramStored: saramStored };
}

function doClockIn(p) {
  const auth = _authUser(p);
  if (!auth.ok) return auth;
  const { ss, mil, saramNorm, saramStored } = auth;

  // Verificar se já tem entrada aberta (qualquer dia, não só hoje)
  const regSheet = getOrCreateSheet(ss, 'Registro', REG_HEADERS);
  const regData = regSheet.getDataRange().getValues();
  for (let i = 1; i < regData.length; i++) {
    if (normalizeSaram(regData[i][6]) === saramNorm && !regData[i][5]) {
      const dataEnt = cellToDate(regData[i][0]);
      return { ok: false, error: 'Entrada aberta em ' + dataEnt + ' às ' + regData[i][4] + '. Registre a saída primeiro.' };
    }
  }

  const hora = getBRTTime();
  const hoje = getBRTDate();
  regSheet.appendRow([hoje, mil.posto, mil.nomeCompleto, mil.nomeGuerra, hora, '', saramStored, '']);

  return { ok: true, message: 'Entrada registrada: ' + hora, hora: hora };
}

function doClockOut(p) {
  const auth = _authUser(p);
  if (!auth.ok) return auth;
  const { ss, saramNorm } = auth;
  const regSheet = ss.getSheetByName('Registro');
  if (!regSheet) return { ok: false, error: 'Nenhum registro encontrado' };

  const regData = regSheet.getDataRange().getValues();

  // Encontrar a última entrada aberta (qualquer dia, não só hoje)
  for (let i = regData.length - 1; i >= 1; i--) {
    if (normalizeSaram(regData[i][6]) === saramNorm && !regData[i][5]) {
      const hora = getBRTTime();
      const hoje = getBRTDate();
      const dataEntrada = cellToDate(regData[i][0]);
      const horaEntrada = String(regData[i][4] || '');
      
      // Calcular horas trabalhadas
      const horas = calcHoras(dataEntrada, horaEntrada, hoje, hora);
      
      // Gravar saída + data saída (se diferente) + horas
      regSheet.getRange(i + 1, 6).setValue(hora);           // Coluna F = Saída
      regSheet.getRange(i + 1, 8).setValue(horas);           // Coluna H = Horas
      
      // Se a saída for em dia diferente da entrada, mostrar no retorno
      const cruzouDia = (dataEntrada !== hoje);
      const msg = cruzouDia 
        ? 'Saída registrada: ' + hora + ' (entrada foi em ' + dataEntrada + ')'
        : 'Saída registrada: ' + hora;
      
      return { ok: true, message: msg, hora: hora, horas: horas };
    }
  }

  return { ok: false, error: 'Nenhuma entrada aberta. Registre a entrada primeiro.' };
}

function doStatus(p) {
  const saramNorm = normalizeSaram(p.saram);
  if (!saramNorm) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const regSheet = ss.getSheetByName('Registro');
  if (!regSheet) return { ok: true, registros: [], aberto: false };

  const regData = regSheet.getDataRange().getValues();
  const hoje = getBRTDate();
  const registros = [];
  let aberto = false;

  for (let i = 1; i < regData.length; i++) {
    if (normalizeSaram(regData[i][6]) === saramNorm && cellToDate(regData[i][0]) === hoje) {
      registros.push({
        entrada: String(regData[i][4] || ''),
        saida: String(regData[i][5] || ''),
        horas: String(regData[i][7] || '')
      });
      if (!regData[i][5]) aberto = true;
    }
  }

  // Verificar também se tem entrada aberta de outro dia
  if (!aberto) {
    for (let i = 1; i < regData.length; i++) {
      if (normalizeSaram(regData[i][6]) === saramNorm && !regData[i][5]) {
        aberto = true;
        registros.unshift({
          data: cellToDate(regData[i][0]),
          entrada: String(regData[i][4] || ''),
          saida: '',
          horas: '',
          diaAnterior: true
        });
        break;
      }
    }
  }

  return { ok: true, registros: registros, aberto: aberto };
}

function doHistory(p) {
  const saramNorm = normalizeSaram(p.saram);
  const dias = parseInt(p.dias) || 7;
  if (!saramNorm) return { ok: false, error: 'SARAM obrigatório' };

  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const regSheet = ss.getSheetByName('Registro');
  if (!regSheet) return { ok: true, registros: [] };

  const regData = regSheet.getDataRange().getValues();
  const registros = [];

  for (let i = regData.length - 1; i >= 1; i--) {
    if (normalizeSaram(regData[i][6]) === saramNorm) {
      registros.push({
        data: cellToDate(regData[i][0]),
        entrada: String(regData[i][4] || ''),
        saida: String(regData[i][5] || ''),
        horas: String(regData[i][7] || '')
      });
      if (registros.length >= dias * 3) break;
    }
  }

  return { ok: true, registros: registros };
}

function doChamada(p) {
  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  
  // Buscar todos os usuários cadastrados
  const usSheet = ss.getSheetByName('Usuarios');
  if (!usSheet) return { ok: true, presentes: [], ausentes: [], total: 0 };
  
  const usData = usSheet.getDataRange().getValues();
  const usuarios = [];
  for (let i = 1; i < usData.length; i++) {
    const saram = String(usData[i][0] || '').trim();
    if (!saram) continue;
    usuarios.push({
      saram: saram,
      saramNorm: normalizeSaram(saram),
      posto: String(usData[i][2] || ''),
      nomeCompleto: String(usData[i][3] || ''),
      nomeGuerra: String(usData[i][4] || '')
    });
  }
  
  // Buscar registros de hoje
  const regSheet = ss.getSheetByName('Registro');
  const hoje = getBRTDate();
  const hojeMap = {}; // saramNorm → {entrada, saida, horas}
  
  if (regSheet) {
    const regData = regSheet.getDataRange().getValues();
    for (let i = 1; i < regData.length; i++) {
      if (cellToDate(regData[i][0]) === hoje) {
        const sn = normalizeSaram(regData[i][6]);
        hojeMap[sn] = {
          entrada: String(regData[i][4] || ''),
          saida: String(regData[i][5] || ''),
          horas: String(regData[i][7] || '')
        };
      }
    }
  }
  
  // Buscar indisponibilidades ativas hoje
  const indSheet = ss.getSheetByName('Indisponibilidade');
  const indispMap = {}; // saramNorm → {tipo, dataInicio, dataFim, obs}
  if (indSheet) {
    const indData = indSheet.getDataRange().getValues();
    for (let i = 1; i < indData.length; i++) {
      const sn = normalizeSaram(indData[i][0]);
      const inicio = cellToDate(indData[i][4]);
      const fim = cellToDate(indData[i][5]);
      const cancelado = String(indData[i][8] || '').trim();
      if (cancelado) continue;
      const fimEfetivo = fim || inicio; // sem data fim = só o dia de início
      if (inicio && inicio <= hoje && fimEfetivo >= hoje) {
        indispMap[sn] = {
          tipo: String(indData[i][3] || ''),
          dataInicio: inicio,
          dataFim: fim,
          obs: String(indData[i][6] || '')
        };
      }
    }
  }

  const presentes = [];
  const ausentes = [];

  for (const u of usuarios) {
    const reg = hojeMap[u.saramNorm];
    const indisp = indispMap[u.saramNorm] || null;
    if (reg) {
      presentes.push({
        posto: u.posto,
        nomeGuerra: u.nomeGuerra,
        nomeCompleto: u.nomeCompleto,
        entrada: reg.entrada,
        saida: reg.saida,
        horas: reg.horas
      });
    } else {
      ausentes.push({
        posto: u.posto,
        nomeGuerra: u.nomeGuerra,
        nomeCompleto: u.nomeCompleto,
        indisp: indisp
      });
    }
  }
  
  return { 
    ok: true, 
    data: hoje,
    presentes: presentes, 
    ausentes: ausentes, 
    totalPresentes: presentes.length,
    totalAusentes: ausentes.length,
    total: usuarios.length
  };
}

/* ---- Indisponibilidade ---- */
const INDISP_HEADERS = ['SARAM', 'Posto', 'NomeGuerra', 'Tipo', 'DataInicio', 'DataFim', 'Obs', 'CriadoEm', 'Cancelado'];
const TIPOS_INDISP = ['Serviço', 'Missão de Manutenção', 'Férias', 'Dispensa Chefia', 'Dispensa Médica', 'Outros'];

function doLancarIndisp(p) {
  const saram = String(p.saram || '').trim();
  const tipo = String(p.tipo || '').trim();
  const dataInicio = String(p.dataInicio || '').trim();
  const dataFim = String(p.dataFim || '').trim();
  const obs = String(p.obs || '').trim();
  
  if (!saram || !tipo || !dataInicio) return { ok: false, error: 'Preencha tipo e data de início.' };
  if (!TIPOS_INDISP.includes(tipo)) return { ok: false, error: 'Tipo inválido.' };
  
  const saramNorm = normalizeSaram(saram);
  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  
  // Verificar se é usuário cadastrado
  const usSheet = ss.getSheetByName('Usuarios');
  let mil = null;
  const usData = usSheet.getDataRange().getValues();
  for (let i = 1; i < usData.length; i++) {
    if (normalizeSaram(usData[i][0]) === saramNorm) {
      mil = { posto: String(usData[i][2] || ''), nomeGuerra: String(usData[i][4] || '') };
      break;
    }
  }
  if (!mil) return { ok: false, error: 'Usuário não encontrado.' };
  
  const indSheet = getOrCreateSheet(ss, 'Indisponibilidade', INDISP_HEADERS);
  indSheet.appendRow([saram, mil.posto, mil.nomeGuerra, tipo, dataInicio, dataFim, obs, getBRTNow(), '']);
  
  return { ok: true, tipo: tipo, dataInicio: dataInicio, dataFim: dataFim };
}

function doMinhasIndisp(p) {
  const saram = String(p.saram || '').trim();
  if (!saram) return { ok: false, error: 'SARAM obrigatório.' };
  
  const saramNorm = normalizeSaram(saram);
  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const indSheet = ss.getSheetByName('Indisponibilidade');
  if (!indSheet) return { ok: true, registros: [] };
  
  const data = indSheet.getDataRange().getValues();
  const hoje = getBRTDate();
  const registros = [];
  
  for (let i = 1; i < data.length; i++) {
    if (normalizeSaram(data[i][0]) !== saramNorm) continue;
    if (String(data[i][8] || '').trim()) continue; // cancelado
    const fim = cellToDate(data[i][5]);
    const inicio = cellToDate(data[i][4]);
    const fimEfetivo = fim || inicio; // sem data fim = só o dia de início
    if (fimEfetivo && fimEfetivo < hoje) continue;
    registros.push({
      linha: i + 1,
      tipo: String(data[i][3] || ''),
      dataInicio: cellToDate(data[i][4]),
      dataFim: cellToDate(data[i][5]),
      obs: String(data[i][6] || ''),
      criadoEm: String(data[i][7] || '')
    });
  }
  
  return { ok: true, registros: registros };
}

function doCancelarIndisp(p) {
  const saram = String(p.saram || '').trim();
  const linha = parseInt(p.linha || '0');
  if (!saram || !linha) return { ok: false, error: 'Parâmetros inválidos.' };
  
  const saramNorm = normalizeSaram(saram);
  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const indSheet = ss.getSheetByName('Indisponibilidade');
  if (!indSheet) return { ok: false, error: 'Aba não encontrada.' };
  
  const row = indSheet.getRange(linha, 1, 1, 9).getValues()[0];
  if (normalizeSaram(row[0]) !== saramNorm) return { ok: false, error: 'Registro não pertence a este usuário.' };
  
  indSheet.getRange(linha, 9).setValue(getBRTNow()); // Coluna "Cancelado"
  return { ok: true };
}

/* ---- Gerencial ---- */
function doGerencial(p) {
  const periodo = String(p.periodo || 'mes'); // semana, mes, ano
  const ss = SpreadsheetApp.openById(PRESENCA_SHEET);
  const hoje = getBRTDate(); // yyyy-MM-dd
  
  // Calcular intervalo
  const hojeParts = hoje.split('-').map(Number);
  let dataInicio, dataFim;
  
  if (periodo === 'semana') {
    // Última segunda-feira até hoje
    const d = new Date(hojeParts[0], hojeParts[1]-1, hojeParts[2]);
    const dow = d.getDay(); // 0=dom
    const diff = dow === 0 ? 6 : dow - 1;
    d.setDate(d.getDate() - diff);
    dataInicio = _fmtDate(d);
    dataFim = hoje;
  } else if (periodo === 'ano') {
    dataInicio = hojeParts[0] + '-01-01';
    dataFim = hoje;
  } else { // mes
    dataInicio = hoje.substring(0,8) + '01';
    dataFim = hoje;
  }
  
  // Buscar todos os usuários
  const usSheet = ss.getSheetByName('Usuarios');
  if (!usSheet) return { ok: true, militares: [], periodo: periodo, dataInicio: dataInicio, dataFim: dataFim };
  const usData = usSheet.getDataRange().getValues();
  const usuarios = [];
  for (let i = 1; i < usData.length; i++) {
    const saram = String(usData[i][0] || '').trim();
    if (!saram) continue;
    usuarios.push({
      saram: saram,
      saramNorm: normalizeSaram(saram),
      posto: String(usData[i][2] || ''),
      nomeGuerra: String(usData[i][4] || '')
    });
  }
  
  // Buscar registros no período
  const regSheet = ss.getSheetByName('Registro');
  // saramNorm → { dias: Set, totalMinutos: 0, registros: [...] }
  const horasMap = {};
  
  if (regSheet) {
    const regData = regSheet.getDataRange().getValues();
    for (let i = 1; i < regData.length; i++) {
      const data = cellToDate(regData[i][0]);
      if (data < dataInicio || data > dataFim) continue;
      
      const sn = normalizeSaram(regData[i][6]);
      if (!horasMap[sn]) horasMap[sn] = { dias: {}, totalMinutos: 0, registros: [] };
      
      const entrada = String(regData[i][4] || '');
      const saida = String(regData[i][5] || '');
      const horas = String(regData[i][7] || '');
      
      horasMap[sn].dias[data] = true;
      
      if (horas) {
        // Converter horas (formato "HH:MM") pra minutos
        const hp = horas.split(':');
        if (hp.length === 2) horasMap[sn].totalMinutos += parseInt(hp[0])*60 + parseInt(hp[1]);
      }
      
      horasMap[sn].registros.push({ data: data, entrada: entrada, saida: saida, horas: horas });
    }
  }
  
  // Buscar indisponibilidades ativas e futuras
  const indSheet = ss.getSheetByName('Indisponibilidade');
  const indispMap = {}; // saramNorm → [{tipo, inicio, fim, obs}]
  if (indSheet) {
    const indData = indSheet.getDataRange().getValues();
    for (let i = 1; i < indData.length; i++) {
      const cancelado = String(indData[i][8] || '').trim();
      if (cancelado) continue;
      const fim = cellToDate(indData[i][5]);
      const inicioInd = cellToDate(indData[i][4]);
      const fimEfetivo = fim || inicioInd; // sem data fim = só o dia de início
      if (fimEfetivo && fimEfetivo < hoje) continue;
      
      const sn = normalizeSaram(indData[i][0]);
      if (!indispMap[sn]) indispMap[sn] = [];
      indispMap[sn].push({
        tipo: String(indData[i][3] || ''),
        dataInicio: cellToDate(indData[i][4]),
        dataFim: fim,
        obs: String(indData[i][6] || '')
      });
    }
  }
  
  // Montar resultado
  const militares = [];
  for (const u of usuarios) {
    const h = horasMap[u.saramNorm] || { dias: {}, totalMinutos: 0, registros: [] };
    const totalH = Math.floor(h.totalMinutos / 60);
    const totalM = h.totalMinutos % 60;
    
    militares.push({
      posto: u.posto,
      nomeGuerra: u.nomeGuerra,
      diasTrabalhados: Object.keys(h.dias).length,
      totalHoras: totalH + ':' + String(totalM).padStart(2, '0'),
      totalMinutos: h.totalMinutos,
      indisponibilidades: indispMap[u.saramNorm] || [],
      registros: h.registros
    });
  }
  
  // Ordenar por total de horas (maior primeiro)
  militares.sort((a, b) => b.totalMinutos - a.totalMinutos);
  
  return {
    ok: true,
    periodo: periodo,
    dataInicio: dataInicio,
    dataFim: dataFim,
    militares: militares
  };
}

function _fmtDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const dd = String(d.getDate()).padStart(2,'0');
  return y + '-' + m + '-' + dd;
}
