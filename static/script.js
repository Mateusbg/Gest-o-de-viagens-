// VARIÁVEIS GLOBAIS
let currentUser = null;

<<<<<<< HEAD
function normalizeToken(token) {
    if (!token || typeof token !== 'string') return null;
    const trimmed = token.trim();
    if (!trimmed) return null;
    const lower = trimmed.toLowerCase();
    if (lower === 'null' || lower === 'undefined') return null;
    if (trimmed.split('.').length !== 3) return null;
    return trimmed;
}

let authToken = normalizeToken(localStorage.getItem('authToken'));
=======
let authToken = localStorage.getItem('authToken') || null;
>>>>>>> 95af3f15e4d54d5aa681c47e91abe2441e459716
let currentSector = null;
let registrosDB = [];
let setoresApi = [];
let adminIndicadoresCache = {};
const adminState = {
    users: [],
    setores: [],
    indicadores: [],
    selectedUserId: null,
    selectedIndicadorId: null,
    indicadorSetorId: null
};

// ===== PERFIL / REGRAS =====
function getUserPerfil(u) {
    return u?.perfil || 'LEITOR';
}

function isAdminUser(user) {
    const perfil = getUserPerfil(user);
    return perfil === 'GESTAO' || perfil === 'ADM';
}


function normalizeSetorFromApi(s, index) {
    const id = s?.ZSE_ID ?? s?.id ?? null;
    const nome = s?.ZSE_NOME ?? s?.nome ?? '';
    return {
        id: id,
        nome: nome,
        classe: sectorClassFromIndex(index)
    };
}

function sectorClassFromIndex(index) {
    const classes = ['sector-blue', 'sector-green', 'sector-purple', 'sector-red'];
    return classes[index % classes.length];
}

function normalizeIndicadorFromApi(i) {
    return {
        id: i?.ZIN_ID ?? i?.id ?? null,
        codigo: i?.ZIN_CODIGO ?? i?.codigo ?? null,
        nome: i?.ZIN_NOME ?? i?.nome ?? '',
        tipo: i?.ZIN_TIPO ?? i?.tipo ?? null,
        unidade: i?.ZIN_UNIDADE ?? i?.unidade ?? null,
        meta: i?.ZIN_META ?? i?.meta ?? null,
        responsavel_id: i?.ZIN_RESPONSAVEL_ID ?? i?.responsavel_id ?? i?.responsavelId ?? null,
        read_only: i?.read_only ?? false,
        valor: null
    };
}

function parseCodigoNumber(codigo) {
    if (codigo === null || codigo === undefined) return null;
    const str = String(codigo);
    const match = str.match(/(\d+)/g);
    if (!match || !match.length) return null;
    const last = match[match.length - 1];
    const num = Number(last);
    return Number.isNaN(num) ? null : num;
}

function getNextIndicadorCodigo(items) {
    let max = 0;
    let found = false;
    (items || []).forEach(i => {
        const codigo = i?.ZIN_CODIGO ?? i?.codigo ?? null;
        const num = parseCodigoNumber(codigo);
        if (num !== null) {
            found = true;
            if (num > max) max = num;
        }
    });
    const next = found ? max + 1 : (items?.length || 0) + 1;
    return String(next);
}

function setIndicadorCodigoInput(value) {
    const input = document.getElementById('adminIndicadorCodigo');
    if (input && value) input.value = value;
}

function isDateIndicator(ind) {
    const tipo = (ind?.tipo || '').toString().toLowerCase();
    const unidade = (ind?.unidade || '').toString().toLowerCase();
    return tipo === 'date' || unidade === 'date';
}


function getPeriodoAtualOuDoFormulario() {
    // procura um campo do tipo date ("Mês"/"Data") para extrair YYYY-MM
    const dateInd = currentSector?.indicadores?.find(i => isDateIndicator(i));
    if (dateInd?.valor && typeof dateInd.valor === 'string') {
        // valor em ISO: YYYY-MM-DD
        const parts = dateInd.valor.split('-');
        if (parts.length >= 2) return `${parts[0]}-${parts[1]}`;
    }
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
}

function buildValoresPayload() {
    // NÃO envia o campo date como indicador de valor
    return (currentSector?.indicadores || [])
        .filter(i => !isDateIndicator(i))
        .filter(i => !i.read_only)
        .map(i => ({
            indicadorId: i.id,
            indicadorCodigo: i.codigo ?? i.id,
            indicadorNome: i.nome,
            tipo: i.tipo || (i.unidade === 'date' ? 'date' : 'number'),
            unidade: i.unidade || null,
            meta: i.meta ?? null,
            valor: i.valor ?? null
        }));
}

async function apiPost(url, body) {
    const token = normalizeToken(authToken);
    const resp = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
<<<<<<< HEAD
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(body)
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        const msg = data?.error || `Erro HTTP ${resp.status}`;
        throw new Error(msg);
    }
    return data;
}

async function apiGet(url) {
    const token = normalizeToken(authToken);
    const resp = await fetch(url, {
        method: 'GET',
        headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        const msg = data?.error || `Erro HTTP ${resp.status}`;
        throw new Error(msg);
    }
    return data;
}

async function apiPut(url, body) {
    const token = normalizeToken(authToken);
    const resp = await fetch(url, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
=======
            ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
>>>>>>> 95af3f15e4d54d5aa681c47e91abe2441e459716
        },
        body: JSON.stringify(body)
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        const msg = data?.error || `Erro HTTP ${resp.status}`;
        throw new Error(msg);
    }
    return data;
}

// ===== FUNÇÕES DE AUTO-FORMATAÇÃO DE DATA =====
function autoFormatarData(input) {
    let valor = input.value.replace(/\D/g, '');
    if (valor.length >= 2) {
        valor = valor.substring(0, 2) + '/' + valor.substring(2);
    }
    if (valor.length >= 5) {
        valor = valor.substring(0, 5) + '/' + valor.substring(5, 9);
    }
    input.value = valor;
}

function validarData(dataString) {
    const regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    const match = dataString.match(regex);
    if (!match) return false;
    const dia = parseInt(match[1], 10);
    const mes = parseInt(match[2], 10);
    const ano = parseInt(match[3], 10);
    if (mes < 1 || mes > 12) return false;
    if (dia < 1 || dia > 31) return false;
    if (ano < 1900 || ano > 2100) return false;
    const diasPorMes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if ((ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0) {
        diasPorMes[1] = 29;
    }
    if (dia > diasPorMes[mes - 1]) return false;
    return true;
}

function converterDataParaISO(dataString) {
    const partes = dataString.split('/');
    return `${partes[2]}-${partes[1]}-${partes[0]}`;
}

function converterDataParaBR(dataISO) {
    if (!dataISO) return '';
    const partes = dataISO.split('-');
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

// ===== FUNÇÕES DE LOGIN =====
function togglePassword() {
    const input = document.getElementById('senhaInput');
    input.type = input.type === 'password' ? 'text' : 'password';
}

async function handleLogin() {
    const email = document.getElementById('emailInput').value;
    const senha = document.getElementById('senhaInput').value;

    if (!email || !senha) {
        alert('Por favor, preencha todos os campos!');
        return;
    }

    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, senha })
        });

        const data = await resp.json().catch(() => ({}));
        if (!resp.ok || !data?.ok) {
            throw new Error(data?.error || 'Login inválido');
        }

<<<<<<< HEAD
        authToken = normalizeToken(data.token);
        if (!authToken) {
            localStorage.removeItem('authToken');
            throw new Error('Token inválido retornado pelo servidor');
        }
=======
        authToken = data.token;
>>>>>>> 95af3f15e4d54d5aa681c47e91abe2441e459716
        localStorage.setItem('authToken', authToken);

        currentUser = {
            id: data.user.id,
            email: data.user.email,
            nome: data.user.nome,
            setor_id: data.user.setor_id,
            nivel: data.user.nivel,
            perfil: data.user.perfil
        };

        document.getElementById('userNameDisplay').textContent = currentUser.nome;
<<<<<<< HEAD
        updateAdminButton();
=======
>>>>>>> 95af3f15e4d54d5aa681c47e91abe2441e459716
        showSectorsScreen();

    } catch (err) {
        alert(err.message || 'Erro ao logar');
    }
}

function handleLogout() {
    currentUser = null;
    authToken = null;
    localStorage.removeItem('authToken');
    location.reload();
}

// ===== NAVEGAÇÃO DE TELAS =====
function hideAllScreens() {
    ['loginScreen', 'sectorsScreen', 'indicatorsScreen', 'adminScreen'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
}

function showLoginScreen() {
    hideAllScreens();
    document.getElementById('loginScreen').classList.remove('hidden');
}

function updateAdminButton() {
    const btn = document.getElementById('adminBtn');
    if (!btn) return;
    if (isAdminUser(currentUser)) {
        btn.classList.remove('hidden');
    } else {
        btn.classList.add('hidden');
    }
}

function showSectorsScreen() {
    loadSectors();
    updateHistoryDisplay();
    updateAdminButton();
    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
}

function showIndicatorsScreen() {
    hideAllScreens();
    document.getElementById('indicatorsScreen').classList.remove('hidden');
}

function showAdminScreen() {
    if (!isAdminUser(currentUser)) {
        alert('Acesso negado');
        return;
    }
    hideAllScreens();
    document.getElementById('adminScreen').classList.remove('hidden');
    showAdminSection('users');
    showUsersSection('createUser');
    loadAdminData();
}

function backToSectorsFromAdmin() {
    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
    updateHistoryDisplay();
}

function showAdminSection(section) {
    const users = document.getElementById('adminUsersSection');
    const indicadores = document.getElementById('adminIndicadoresSection');
    if (!users || !indicadores) return;
    if (section === 'indicators') {
        users.classList.add('hidden');
        indicadores.classList.remove('hidden');
    } else {
        indicadores.classList.add('hidden');
        users.classList.remove('hidden');
    }
}

function showUsersSection(section) {
    const createUser = document.getElementById('adminCreateUserCard');
    const editUser = document.getElementById('adminEditUserCard');
    const createSetor = document.getElementById('adminCreateSetorCard');
    const editSetor = document.getElementById('adminEditSetorCard');
    const usersTable = document.getElementById('adminUsersTableWrap');
    const setoresTable = document.getElementById('adminSetoresTableWrap');
    if (!createUser || !editUser || !createSetor || !editSetor || !usersTable || !setoresTable) return;

    createUser.classList.add('hidden');
    editUser.classList.add('hidden');
    createSetor.classList.add('hidden');
    editSetor.classList.add('hidden');
    usersTable.classList.add('hidden');
    setoresTable.classList.add('hidden');

    if (section === 'editUser') {
        editUser.classList.remove('hidden');
        usersTable.classList.remove('hidden');
        return;
    }
    if (section === 'listUsers') {
        usersTable.classList.remove('hidden');
        return;
    }
    if (section === 'createSetor') {
        createSetor.classList.remove('hidden');
        return;
    }
    if (section === 'editSetor') {
        editSetor.classList.remove('hidden');
        setoresTable.classList.remove('hidden');
        return;
    }
    createUser.classList.remove('hidden');
}

function backToSectors() {
    currentSector = null;
    hideAllScreens();
    const sectors = document.getElementById('sectorsScreen');
    if (sectors) sectors.classList.remove('hidden');
    loadSectors();
    updateHistoryDisplay();
}



// ===== CARREGAR SETORES =====
async function loadSectors() {
    const grid = document.getElementById('sectorsGrid');
    if (!grid) return;
    grid.innerHTML = '';

    try {
        const setoresData = await apiGet('/api/setores');
        const list = Array.isArray(setoresData) ? setoresData : [];
        setoresApi = list.map((s, idx) => normalizeSetorFromApi(s, idx));

        const counts = await Promise.all(
            setoresApi.map(s =>
                apiGet(`/api/indicadores?setorId=${encodeURIComponent(s.id)}`)
                    .then(items => ({ id: s.id, count: Array.isArray(items) ? items.length : 0 }))
                    .catch(() => ({ id: s.id, count: 0 }))
            )
        );
        const countMap = new Map(counts.map(c => [String(c.id), c.count]));

        setoresApi.forEach(setor => {
            const btn = document.createElement('button');
            const count = countMap.get(String(setor.id)) ?? 0;
            btn.className = `sector-btn ${setor.classe}`;
            btn.innerHTML = `<h2>${setor.nome}</h2><p>${count} indicadores</p>`;
            btn.onclick = () => openSector(setor);
            grid.appendChild(btn);
        });
    } catch (err) {
        alert(`Erro ao carregar setores: ${err.message}`);
    }
}

async function openSector(setor) {
    try {
        const data = await apiGet(`/api/indicadores?setorId=${encodeURIComponent(setor.id)}`);
        const indicadores = (Array.isArray(data) ? data : []).map(i => normalizeIndicadorFromApi(i));
        currentSector = {
            id: setor.id,
            nome: setor.nome,
            indicadores: indicadores
        };
        document.getElementById('sectorTitle').textContent = setor.nome;
        const form = document.getElementById('indicatorsForm');
        form.innerHTML = '';
        currentSector.indicadores.forEach(indicador => {
            const div = document.createElement('div');
            div.className = 'indicator-item';
            const isDateField = isDateIndicator(indicador);
            const readOnly = indicador.read_only || (currentUser?.nivel === 1);
            const readonlyAttr = readOnly ? 'disabled' : '';
            let inputHtml = '';
            if (isDateField) {
                const valorBR = indicador.valor ? converterDataParaBR(indicador.valor) : '';
                inputHtml = `<input type="text" class="indicator-input" data-id="${indicador.id}" value="${valorBR}" placeholder="DD/MM/AAAA" maxlength="10" oninput="autoFormatarData(this)" onchange="updateIndicatorDate(${indicador.id}, this.value)" style="font-family: monospace; letter-spacing: 1px;" ${readonlyAttr}>`;
            } else {
                inputHtml = `<input type="number" step="0.01" placeholder="Digite o valor" class="indicator-input" data-id="${indicador.id}" value="${indicador.valor ?? ''}" onchange="updateIndicator(${indicador.id}, this.value)" ${readonlyAttr}>`;
            }
            const metaHtml = isDateField
                ? '<div class="indicator-meta">Formato: DD/MM/AAAA</div>'
                : `<div class="indicator-meta">Meta: ${indicador.meta ?? '-'} ${indicador.unidade ?? ''}</div>`;
            div.innerHTML = `<label class="indicator-label">${indicador.nome}</label>${metaHtml}${inputHtml}`;
            form.appendChild(div);
        });
    } catch (err) {
        alert(`Erro ao carregar indicadores: ${err.message}`);
        return;
    }

    // Ajusta botoes conforme perfil
    const perfil = getUserPerfil(currentUser);
    const sendBtn = document.getElementById('sendBtn');
    const saveBtn = document.getElementById('saveBtn');
    if (sendBtn) {
        if (perfil === 'LIDER' || perfil === 'GESTAO') {
            sendBtn.classList.remove('hidden');
        } else {
            sendBtn.classList.add('hidden');
        }
    }
    if (saveBtn) {
        if (currentUser?.nivel === 1) {
            saveBtn.classList.add('hidden');
            if (sendBtn) sendBtn.classList.add('hidden');
        } else {
            saveBtn.classList.remove('hidden');
        }
    }
    showIndicatorsScreen();
}

function updateIndicator(id, value) {
    const ind = currentSector.indicadores.find(i => Number(i.id) === Number(id));
    if (ind) ind.valor = value;
}

function updateIndicatorDate(id, value) {
    const ind = currentSector.indicadores.find(i => Number(i.id) === Number(id));
    if (!ind) return;
    if (!value) {
        ind.valor = '';
        return;
    }
    if (value.length === 10) {
        if (!validarData(value)) {
            alert('Data inválida! Use o formato DD/MM/AAAA');
            return;
        }
        ind.valor = converterDataParaISO(value);
    }
}

function handleSave() {
    // Regra: usuário padrão salva como rascunho no banco (ZDR);
    // líder/gestão podem salvar também como rascunho (para continuar depois).
    const periodo = getPeriodoAtualOuDoFormulario();
    const valores = buildValoresPayload();

    const body = {
        setorId: currentSector.id,
        setorNome: currentSector.nome,
        funcionarioEmail: currentUser.email,
        funcionarioNome: currentUser.nome,
        funcionarioPerfil: getUserPerfil(currentUser),
        periodo,
        valores
    };

    apiPost('/api/drafts', body)
        .then(() => {
            registrosDB.unshift({
                id: Date.now(),
                usuario: currentUser.nome,
                setor: currentSector.nome,
                timestamp: new Date().toLocaleString('pt-BR'),
                indicadores: currentSector.indicadores,
                status: 'Rascunho (DB)'
            });
            updateHistoryDisplay();
            alert('Rascunho salvo no banco com sucesso!');
        })
        .catch(err => alert(`Erro ao salvar rascunho: ${err.message}`));
}

function handleSendDB() {
    const perfil = getUserPerfil(currentUser);
    if (perfil !== 'LIDER' && perfil !== 'GESTAO') {
        alert('Apenas LÍDER ou GESTÃO podem enviar valores definitivos para o banco. Use "Salvar" para rascunho.');
        return;
    }

    const periodo = getPeriodoAtualOuDoFormulario();
    const valores = buildValoresPayload();

    const body = {
        setorId: currentSector.id,
        setorNome: currentSector.nome,
        funcionarioEmail: currentUser.email,
        funcionarioNome: currentUser.nome,
        funcionarioPerfil: perfil,
        periodo,
        valores
    };

    apiPost('/api/valores', body)
        .then(() => {
            registrosDB.unshift({
                id: Date.now(),
                usuario: currentUser.nome,
                setor: currentSector.nome,
                timestamp: new Date().toLocaleString('pt-BR'),
                indicadores: currentSector.indicadores,
                status: 'Enviado para DB'
            });
            updateHistoryDisplay();
            alert('Dados enviados para banco de dados com sucesso!');
            backToSectors();
        })
        .catch(err => alert(`Erro ao enviar para DB: ${err.message}`));
}

function updateHistoryDisplay() {
    if (registrosDB.length > 0) {
        document.getElementById('historySection').classList.remove('hidden');
        document.getElementById('recentRecords').classList.remove('hidden');
        const tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';
        registrosDB.slice(0, 5).forEach(registro => {
            const row = document.createElement('tr');
            row.innerHTML = `<td>${registro.usuario}</td><td>${registro.setor}</td><td>${registro.timestamp}</td><td><span class="status-badge ${registro.status === 'Enviado para DB' ? 'status-sent' : 'status-saved'}">${registro.status}</span></td>`;
            tbody.appendChild(row);
        });
        const recordsList = document.getElementById('recordsList');
        recordsList.innerHTML = '';
        registrosDB.slice(0, 3).forEach(registro => {
            const div = document.createElement('div');
            div.className = 'record-item';
            div.innerHTML = `<div class="record-info"><p>${registro.setor}</p><div class="timestamp">${registro.timestamp}</div></div><span class="status-badge ${registro.status === 'Enviado para DB' ? 'status-sent' : 'status-saved'}">${registro.status}</span>`;
            recordsList.appendChild(div);
        });
    }
}

// ===== ADMIN =====
function getSetorIdValue(s) {
    return s?.ZSE_ID ?? s?.id ?? null;
}

function getSetorNomeValue(s) {
    return s?.ZSE_NOME ?? s?.nome ?? '';
}

function fillSetorSelect(selectEl, setoresList, includeEmpty) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    if (includeEmpty) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Sem setor';
        selectEl.appendChild(opt);
    }
    setoresList.forEach(s => {
        const opt = document.createElement('option');
        opt.value = getSetorIdValue(s);
        opt.textContent = getSetorNomeValue(s);
        selectEl.appendChild(opt);
    });
}

function fillNivelSelect(selectEl) {
    if (!selectEl) return;
    const levels = [
        { v: 1, t: 'LEITOR' },
        { v: 2, t: 'EDITOR' },
        { v: 3, t: 'LIDER' },
        { v: 4, t: 'GESTAO' },
        { v: 5, t: 'ADM' }
    ];
    selectEl.innerHTML = '';
    levels.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.v;
        opt.textContent = `${l.v} - ${l.t}`;
        selectEl.appendChild(opt);
    });
}

function fillUserSelect(selectEl, usersList, includeEmpty) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    if (includeEmpty) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Sem responsavel';
        selectEl.appendChild(opt);
    }
    usersList.forEach(u => {
        const id = u?.ZFU_ID ?? u?.id ?? '';
        const nome = u?.ZFU_NOME ?? u?.nome ?? '';
        const email = u?.ZFU_EMAIL ?? u?.email ?? '';
        const opt = document.createElement('option');
        opt.value = id;
        opt.textContent = email ? `${nome} (${email})` : nome;
        selectEl.appendChild(opt);
    });
}

function setSelectValue(selectEl, value) {
    if (!selectEl) return;
    const val = value === null || value === undefined ? '' : String(value);
    selectEl.value = val;
}

async function loadAdminData() {
    try {
        const [setoresData, usersData] = await Promise.all([
            apiGet('/api/setores'),
            apiGet('/api/users')
        ]);
        adminState.setores = Array.isArray(setoresData) ? setoresData : [];
        adminState.users = Array.isArray(usersData) ? usersData : [];
        renderAdminSetores();
        renderAdminUsers();
        fillUserSelect(document.getElementById('adminIndicadorResponsavel'), adminState.users, true);
        fillUserSelect(document.getElementById('adminIndicadorResponsavelEdit'), adminState.users, true);

        const setorCreateSelect = document.getElementById('adminIndicadorSetor');
        if (setorCreateSelect) {
            setorCreateSelect.onchange = async () => {
                const nextId = setorCreateSelect.value;
                if (nextId) await refreshIndicadorCodigoForSetor(nextId);
            };
        }

        const setorSelect = document.getElementById('adminIndicadorSetorEdit');
        if (setorSelect) {
            setorSelect.onchange = () => {
                const nextId = setorSelect.value;
                if (nextId) loadAdminIndicadores(nextId);
            };
        }

        const defaultSetorId = getSetorIdValue(adminState.setores[0]);
        if (defaultSetorId) {
            setSelectValue(document.getElementById('adminIndicadorSetorEdit'), defaultSetorId);
            setSelectValue(document.getElementById('adminIndicadorSetor'), defaultSetorId);
            await loadAdminIndicadores(defaultSetorId);
            await refreshIndicadorCodigoForSetor(defaultSetorId);
        }
    } catch (err) {
        alert(`Erro ao carregar admin: ${err.message}`);
    }
}

function renderAdminSetores() {
    fillSetorSelect(document.getElementById('adminUserSetor'), adminState.setores, true);
    fillSetorSelect(document.getElementById('adminUserSetorEdit'), adminState.setores, true);
    fillSetorSelect(document.getElementById('adminIndicadorSetor'), adminState.setores, false);
    fillSetorSelect(document.getElementById('adminIndicadorSetorEdit'), adminState.setores, false);
    fillNivelSelect(document.getElementById('adminUserNivel'));
    fillNivelSelect(document.getElementById('adminUserNivelEdit'));
    renderAdminSetoresTable();
}

function renderAdminSetoresTable() {
    const tbody = document.getElementById('adminSetoresBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    adminState.setores.forEach(s => {
        const id = getSetorIdValue(s);
        const nome = getSetorNomeValue(s);
        const ativo = s?.ZSE_ATIVO ?? s?.ativo ?? 0;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${id ?? ''}</td>
            <td>${nome}</td>
            <td>${ativo ? 'Sim' : 'Nao'}</td>
            <td><button class="btn btn-save admin-btn-row" data-setor-id="${id}">Selecionar</button></td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('button[data-setor-id]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-setor-id');
            selectAdminSetor(id);
        });
    });
}

function selectAdminSetor(setorId) {
    const sid = Number(setorId);
    const setor = adminState.setores.find(s => Number(getSetorIdValue(s)) === sid);
    if (!setor) return;
    document.getElementById('adminSetorId').value = getSetorIdValue(setor) ?? '';
    document.getElementById('adminSetorNomeEdit').value = getSetorNomeValue(setor) ?? '';
    const ativo = setor?.ZSE_ATIVO ?? setor?.ativo ?? 0;
    document.getElementById('adminSetorAtivoEdit').checked = !!ativo;
}

function renderAdminUsers() {
    const tbody = document.getElementById('adminUsersBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    adminState.users.forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${u.ZFU_NOME ?? ''}</td>
            <td>${u.ZFU_EMAIL ?? ''}</td>
            <td>${u.ZFU_NIVEL ?? ''}</td>
            <td>
                <button class="btn btn-save admin-btn-row" data-user-id="${u.ZFU_ID}" data-user-action="perm">Editar permissao</button>
                <button class="btn btn-save admin-btn-row" data-user-id="${u.ZFU_ID}" data-user-action="edit">Alterar cadastro</button>
                <button class="btn btn-send admin-btn-row" data-user-id="${u.ZFU_ID}" data-user-action="block">Bloquear</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('button[data-user-id]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-user-id');
            const action = btn.getAttribute('data-user-action');
            if (action === 'block') {
                adminBlockUser(id);
                return;
            }
            selectAdminUser(id);
            showUsersSection('editUser');
        });
    });
}

function selectAdminUser(userId) {
    const uid = Number(userId);
    const user = adminState.users.find(u => Number(u.ZFU_ID) === uid);
    if (!user) return;
    adminState.selectedUserId = uid;
    document.getElementById('adminUserId').value = user.ZFU_ID ?? '';
    document.getElementById('adminUserNomeEdit').value = user.ZFU_NOME ?? '';
    document.getElementById('adminUserEmailEdit').value = user.ZFU_EMAIL ?? '';
    setSelectValue(document.getElementById('adminUserSetorEdit'), user.ZFU_SETOR_ID);
    setSelectValue(document.getElementById('adminUserNivelEdit'), user.ZFU_NIVEL);
    document.getElementById('adminUserAtivoEdit').checked = !!user.ZFU_ATIVO;
}

async function adminCreateUser() {
    try {
        const nome = document.getElementById('adminUserNome').value.trim();
        const email = document.getElementById('adminUserEmail').value.trim();
        const setorId = document.getElementById('adminUserSetor').value;
        const nivel = document.getElementById('adminUserNivel').value;
        const senha = document.getElementById('adminUserSenha').value.trim() || '1234';

        if (!nome || !email) {
            alert('Informe nome e email');
            return;
        }

        await apiPost('/api/users', {
            nome,
            email,
            senha,
            setor_id: setorId || null,
            nivel: Number(nivel || 1)
        });
        await loadAdminData();
        document.getElementById('adminUserNome').value = '';
        document.getElementById('adminUserEmail').value = '';
        document.getElementById('adminUserSenha').value = '';
        alert('Usuario criado');
    } catch (err) {
        alert(`Erro ao criar usuario: ${err.message}`);
    }
}

async function adminUpdateUser() {
    try {
        const id = document.getElementById('adminUserId').value;
        if (!id) {
            alert('Selecione um usuario');
            return;
        }
        const body = {
            nome: document.getElementById('adminUserNomeEdit').value.trim(),
            email: document.getElementById('adminUserEmailEdit').value.trim(),
            setor_id: document.getElementById('adminUserSetorEdit').value || null,
            nivel: Number(document.getElementById('adminUserNivelEdit').value || 1),
            ativo: document.getElementById('adminUserAtivoEdit').checked ? 1 : 0
        };
        await apiPut(`/api/users/${id}`, body);
        await loadAdminData();
        alert('Usuario atualizado');
    } catch (err) {
        alert(`Erro ao atualizar usuario: ${err.message}`);
    }
}

async function adminResetUserPassword() {
    try {
        const id = document.getElementById('adminUserId').value;
        if (!id) {
            alert('Selecione um usuario');
            return;
        }
        const senhaRaw = prompt('Nova senha (deixe vazio para 1234):');
        if (senhaRaw === null) return;
        const senha = senhaRaw.trim() || '1234';
        await apiPost(`/api/users/${id}/reset-password`, { senha });
        alert('Senha redefinida');
    } catch (err) {
        alert(`Erro ao resetar senha: ${err.message}`);
    }
}

async function adminBlockUser(userId) {
    try {
        const id = Number(userId);
        if (!id) {
            alert('Usuario invalido');
            return;
        }
        await apiPut(`/api/users/${id}`, { ativo: 0 });
        await loadAdminData();
        alert('Usuario bloqueado');
    } catch (err) {
        alert(`Erro ao bloquear usuario: ${err.message}`);
    }
}

async function loadAdminIndicadores(setorId) {
    try {
        const data = await apiGet(`/api/indicadores?setorId=${encodeURIComponent(setorId)}`);
        adminState.indicadores = Array.isArray(data) ? data : [];
        adminIndicadoresCache[String(setorId)] = adminState.indicadores;
        renderAdminIndicadores();
    } catch (err) {
        alert(`Erro ao carregar indicadores: ${err.message}`);
    }
}

async function adminCreateSetor() {
    try {
        const nome = document.getElementById('adminSetorNome').value.trim();
        if (!nome) {
            alert('Informe nome do setor');
            return;
        }
        await apiPost('/api/setores', { nome });
        document.getElementById('adminSetorNome').value = '';
        await loadAdminData();
        alert('Setor criado');
    } catch (err) {
        alert(`Erro ao criar setor: ${err.message}`);
    }
}

async function adminUpdateSetor() {
    try {
        const id = document.getElementById('adminSetorId').value;
        if (!id) {
            alert('Selecione um setor');
            return;
        }
        const nome = document.getElementById('adminSetorNomeEdit').value.trim();
        const ativo = document.getElementById('adminSetorAtivoEdit').checked ? 1 : 0;
        await apiPut(`/api/setores/${id}`, { nome, ativo });
        await loadAdminData();
        alert('Setor atualizado');
    } catch (err) {
        alert(`Erro ao atualizar setor: ${err.message}`);
    }
}

async function adminDisableSetor() {
    try {
        const id = document.getElementById('adminSetorId').value;
        if (!id) {
            alert('Selecione um setor');
            return;
        }
        await apiPut(`/api/setores/${id}`, { ativo: 0 });
        await loadAdminData();
        alert('Setor inativado');
    } catch (err) {
        alert(`Erro ao inativar setor: ${err.message}`);
    }
}

async function refreshIndicadorCodigoForSetor(setorId) {
    if (!setorId) return;
    const key = String(setorId);
    let items = adminIndicadoresCache[key];
    if (!items) {
        try {
            const data = await apiGet(`/api/indicadores?setorId=${encodeURIComponent(setorId)}`);
            items = Array.isArray(data) ? data : [];
            adminIndicadoresCache[key] = items;
        } catch (err) {
            alert(`Erro ao carregar indicadores para codigo: ${err.message}`);
            return;
        }
    }
    setIndicadorCodigoInput(getNextIndicadorCodigo(items));
}

function renderAdminIndicadores() {
    const tbody = document.getElementById('adminIndicadoresBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    adminState.indicadores.forEach(i => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${i.ZIN_ID ?? ''}</td>
            <td>${i.ZIN_CODIGO ?? ''}</td>
            <td>${i.ZIN_NOME ?? ''}</td>
            <td>${i.ZIN_TIPO ?? ''}</td>
            <td>${i.ZIN_UNIDADE ?? ''}</td>
            <td>${i.ZIN_META ?? ''}</td>
            <td>${i.ZIN_RESPONSAVEL_ID ?? ''}</td>
            <td>${i.ZIN_ATIVO ? 'Sim' : 'Nao'}</td>
            <td><button class="btn btn-save admin-btn-row" data-ind-id="${i.ZIN_ID}">Selecionar</button></td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('button[data-ind-id]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-ind-id');
            selectAdminIndicador(id);
        });
    });
}

function selectAdminIndicador(indId) {
    const iid = Number(indId);
    const indicador = adminState.indicadores.find(i => Number(i.ZIN_ID) === iid);
    if (!indicador) return;
    adminState.selectedIndicadorId = iid;
    document.getElementById('adminIndicadorId').value = indicador.ZIN_ID ?? '';
    document.getElementById('adminIndicadorNomeEdit').value = indicador.ZIN_NOME ?? '';
    document.getElementById('adminIndicadorTipoEdit').value = indicador.ZIN_TIPO ?? '';
    document.getElementById('adminIndicadorUnidadeEdit').value = indicador.ZIN_UNIDADE ?? '';
    document.getElementById('adminIndicadorMetaEdit').value = indicador.ZIN_META ?? '';
    setSelectValue(document.getElementById('adminIndicadorResponsavelEdit'), indicador.ZIN_RESPONSAVEL_ID);
    document.getElementById('adminIndicadorAtivoEdit').checked = !!indicador.ZIN_ATIVO;
}

async function adminCreateIndicador() {
    try {
        const setorId = document.getElementById('adminIndicadorSetor').value;
        const codigo = document.getElementById('adminIndicadorCodigo').value.trim();
        const nome = document.getElementById('adminIndicadorNome').value.trim();
        const tipo = document.getElementById('adminIndicadorTipo').value.trim() || null;
        const unidade = document.getElementById('adminIndicadorUnidade').value.trim() || null;
        const metaVal = document.getElementById('adminIndicadorMeta').value;
        const meta = metaVal === '' ? null : Number(metaVal);
        const responsavelRaw = document.getElementById('adminIndicadorResponsavel').value;
        const responsavel_id = responsavelRaw ? Number(responsavelRaw) : null;

        if (!setorId || !codigo || !nome) {
            alert('Informe setor, codigo e nome');
            return;
        }

        await apiPost('/api/indicadores', {
            setor_id: Number(setorId),
            codigo,
            nome,
            tipo,
            unidade,
            meta,
            responsavel_id
        });

        await loadAdminIndicadores(setorId);
        document.getElementById('adminIndicadorCodigo').value = '';
        document.getElementById('adminIndicadorNome').value = '';
        document.getElementById('adminIndicadorTipo').value = '';
        document.getElementById('adminIndicadorUnidade').value = '';
        document.getElementById('adminIndicadorMeta').value = '';
        setSelectValue(document.getElementById('adminIndicadorResponsavel'), '');
        alert('Indicador criado');
    } catch (err) {
        alert(`Erro ao criar indicador: ${err.message}`);
    }
}

async function adminUpdateIndicador() {
    try {
        const id = document.getElementById('adminIndicadorId').value;
        if (!id) {
            alert('Selecione um indicador');
            return;
        }
        const body = {
            nome: document.getElementById('adminIndicadorNomeEdit').value.trim(),
            tipo: document.getElementById('adminIndicadorTipoEdit').value.trim() || null,
            unidade: document.getElementById('adminIndicadorUnidadeEdit').value.trim() || null,
            meta: (() => {
                const v = document.getElementById('adminIndicadorMetaEdit').value;
                return v === '' ? null : Number(v);
            })(),
            responsavel_id: (() => {
                const v = document.getElementById('adminIndicadorResponsavelEdit').value;
                return v === '' ? null : Number(v);
            })(),
            ativo: document.getElementById('adminIndicadorAtivoEdit').checked ? 1 : 0
        };
        await apiPut(`/api/indicadores/${id}`, body);
        const setorId = document.getElementById('adminIndicadorSetorEdit').value;
        if (setorId) await loadAdminIndicadores(setorId);
        alert('Indicador atualizado');
    } catch (err) {
        alert(`Erro ao atualizar indicador: ${err.message}`);
    }
}

// ===== INICIALIZACAO =====
document.addEventListener('DOMContentLoaded', function() {
    showLoginScreen();
});
