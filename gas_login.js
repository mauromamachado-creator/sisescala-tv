// GAS — SisGOPA Login System
// Planilha: 1xMJdQSTPR1KeH_TdqVVJEx0VEyBX4xbtxTEVB8Dl7ME
// Abas: Usuarios (SARAM, SenhaHash, Posto, NomeCompleto, NomeGuerra, CriadoEm)
//       Acessos (SARAM, NomeGuerra, DataHora, Dispositivo, IP)
// Validação: cruza com aba "dados" da planilha MP 2026 (1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao)

const LOGIN_SHEET_ID = '1xMJdQSTPR1KeH_TdqVVJEx0VEyBX4xbtxTEVB8Dl7ME';
const MP_SHEET_ID = '1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao';
const SALT = '_GTE_LOGIN_2026';

function doGet(e) {
  const p = e.parameter;
  const action = p.action || '';
  try {
    if (action === 'register') return j(doRegister(p));
    if (action === 'login') return j(doLogin(p));
    if (action === 'validate') return j(doValidate(p));
    return j({ ok: false, error: 'Ação inválida' });
  } catch (err) {
    return j({ ok: false, error: err.message });
  }
}

function j(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// O frontend envia o hash SHA-256 já calculado (senha + SALT).
// O GAS armazena e compara esse hash diretamente.
function hashPassword(senha) {
  // Se já vier como hex (64 chars), é hash do frontend — usa direto
  if (/^[0-9a-f]{64}$/.test(senha)) return senha;
  // Fallback: hash local
  const raw = senha + SALT;
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, raw, Utilities.Charset.UTF_8);
  return digest.map(b => ('0' + ((b + 256) % 256).toString(16)).slice(-2)).join('');
}

function normSaram(s) {
  return String(s || '').trim().replace(/[\.\-\s]/g, '');
}

function getBRTNow() {
  return Utilities.formatDate(new Date(), 'America/Sao_Paulo', 'dd/MM/yyyy HH:mm:ss');
}

function getOrCreateSheet(name, headers) {
  const ss = SpreadsheetApp.openById(LOGIN_SHEET_ID);
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    if (headers) sheet.appendRow(headers);
  }
  return sheet;
}

// Valida se SARAM existe na aba "dados" da planilha MP
function findInMP(saram) {
  const ss = SpreadsheetApp.openById(MP_SHEET_ID);
  const sheet = ss.getSheetByName('dados');
  if (!sheet) return null;
  const data = sheet.getDataRange().getValues();
  const norm = normSaram(saram);
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    // Procura SARAM nas colunas possíveis (32, 33, 34 — índice 0-based)
    for (let col = 32; col <= 35; col++) {
      const val = normSaram(row[col] || '');
      if (val && val === norm) {
        return {
          posto: row[20] || '',
          nomeCompleto: row[21] || '',
          nomeGuerra: row[22] || '',
          saram: norm
        };
      }
    }
    // Também checa coluna de SARAM se estiver em outro lugar
    const saramCol = normSaram(row[35] || row[34] || row[33] || row[32] || '');
    if (saramCol === norm) {
      return {
        posto: row[20] || '',
        nomeCompleto: row[21] || '',
        nomeGuerra: row[22] || '',
        saram: norm
      };
    }
  }
  return null;
}

// Valida SARAM (sem criar conta)
function doValidate(p) {
  const saram = normSaram(p.saram);
  if (!saram) return { ok: false, error: 'SARAM obrigatório' };
  const mp = findInMP(saram);
  if (!mp) return { ok: false, error: 'SARAM não encontrado na MP. Somente integrantes do GTE podem se cadastrar.' };
  return { ok: true, posto: mp.posto, nomeCompleto: mp.nomeCompleto, nomeGuerra: mp.nomeGuerra };
}

// Registrar novo usuário
function doRegister(p) {
  const saram = normSaram(p.saram);
  const senha = p.senha || '';
  if (!saram) return { ok: false, error: 'SARAM obrigatório' };
  if (!senha || senha.length < 4) return { ok: false, error: 'Senha deve ter pelo menos 4 caracteres' };

  // Valida na MP
  const mp = findInMP(saram);
  if (!mp) return { ok: false, error: 'SARAM não encontrado na MP. Somente integrantes do GTE podem se cadastrar.' };

  // Verifica se já existe
  const sheet = getOrCreateSheet('Usuarios', ['SARAM', 'SenhaHash', 'Posto', 'NomeCompleto', 'NomeGuerra', 'CriadoEm']);
  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (normSaram(data[i][0]) === saram) {
      return { ok: false, error: 'SARAM já cadastrado. Use o login.' };
    }
  }

  // Cria
  const hash = hashPassword(senha);
  sheet.appendRow([saram, hash, mp.posto, mp.nomeCompleto, mp.nomeGuerra, getBRTNow()]);
  return { ok: true, posto: mp.posto, nomeCompleto: mp.nomeCompleto, nomeGuerra: mp.nomeGuerra, saram: saram };
}

// Login
function doLogin(p) {
  const saram = normSaram(p.saram);
  const senha = p.senha || '';
  if (!saram || !senha) return { ok: false, error: 'SARAM e senha obrigatórios' };

  const sheet = getOrCreateSheet('Usuarios', ['SARAM', 'SenhaHash', 'Posto', 'NomeCompleto', 'NomeGuerra', 'CriadoEm']);
  const data = sheet.getDataRange().getValues();
  const hash = hashPassword(senha);

  for (let i = 1; i < data.length; i++) {
    if (normSaram(data[i][0]) === saram && data[i][1] === hash) {
      // Login OK — registra acesso
      logAccess(saram, data[i][4] || '', p.device || '');
      return {
        ok: true,
        saram: saram,
        posto: data[i][2] || '',
        nomeCompleto: data[i][3] || '',
        nomeGuerra: data[i][4] || ''
      };
    }
  }
  return { ok: false, error: 'SARAM ou senha incorretos' };
}

// Registra acesso na aba Acessos
function logAccess(saram, nomeGuerra, device) {
  const sheet = getOrCreateSheet('Acessos', ['SARAM', 'NomeGuerra', 'DataHora', 'Dispositivo']);
  sheet.appendRow([saram, nomeGuerra, getBRTNow(), device || 'N/A']);
}
