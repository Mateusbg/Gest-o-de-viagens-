/**
 * Usuário logado no momento.
 * Estrutura típica:
 * { id, email, nome, setor_id, nivel, perfil }
 */
let currentUser = null;

/**
 * Tenta normalizar/validar token JWT:
 * - Deve ser string não vazia
 * - Não pode ser "null"/"undefined"
 * - Deve ter 3 partes separadas por ponto (header.payload.signature)
 */
function normalizeToken(token) {
    if (!token || typeof token !== 'string') return null;

    const trimmed = token.trim();
    if (!trimmed) return null;

    const lower = trimmed.toLowerCase();
    if (lower === 'null' || lower === 'undefined') return null;

    if (trimmed.split('.').length !== 3) return null;
    return trimmed;
}

function isStrongPassword(password) {
    if (!password || password.length < 8) return false;
    const hasLetter = /[A-Za-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    return hasLetter && hasNumber;
}

const tokenStorage = sessionStorage;

/**
 * Token de autenticação em memória.
 * Carregado do sessionStorage para manter sessão.
 */
let authToken = normalizeToken(tokenStorage.getItem('authToken'));

/**
 * Setor aberto no momento na tela de indicadores.
 * Estrutura típica:
 * { id, nome, indicadores: [...] }
 */
let currentSector = null;

/**
 * Registro local de ações "salvar" / "enviar" para exibir histórico na UI.
 * Observação: esse array é apenas para UI. Os dados reais estão no banco via API.
 */
let registrosDB = [];

/**
 * Cache do retorno da API de setores, já normalizados.
 */
let setoresApi = [];

/**
 * Cache: indicadores por setor no admin (para evitar GET repetido)
 * formato: { "setorId": [indicadores...] }
 */
let adminIndicadoresCache = {};
let pendingAdminSetorId = null;

/**
 * Estado do Admin em memória:
 * - users: usuários carregados
 * - setores: setores carregados
 * - indicadores: indicadores do setor selecionado (admin)
 */
const adminState = {
    users: [],
    setores: [],
    indicadores: []
};

/**
 * Retorna o perfil do usuário:
 * - LEITOR, EDITOR, LIDER, GESTAO, ADM
 * Observação: fallback para 'LEITOR' se vier vazio.
 */
function getUserPerfil(u) {
    return u?.perfil || 'LEITOR';
}

/**
 * Define se o usuário tem acesso ao Admin.
 */
function isAdminUser(user) {
    const perfil = getUserPerfil(user);
    return perfil === 'GESTAO' || perfil === 'ADM';
}

function isManagerUser(user) {
    const nivel = Number(user?.nivel || 1);
    return nivel >= 3;
}
/**
 * Normaliza setor vindo da API para o formato usado no front.
 * Aceita campos alternativos (compatibilidade).
 */
function normalizeSetorFromApi(s, index) {
    const id = s?.ZSE_ID ?? s?.id ?? null;
    const nome = s?.ZSE_NOME ?? s?.nome ?? '';
    return {
        id,
        nome,
        classe: sectorClassFromIndex(index)
    };
}

/**
 * Define classes de cor para setores (cíclico).
 */
function sectorClassFromIndex(index) {
    const classes = ['sector-blue', 'sector-green', 'sector-purple', 'sector-red'];
    return classes[index % classes.length];
}

/**
 * Normaliza indicador vindo da API para o formato usado no front.
 */
function normalizeIndicadorFromApi(i) {
    return {
        id: i?.ZIN_ID ?? i?.id ?? null,
        codigo: i?.ZIN_CODIGO ?? i?.codigo ?? null,
        nome: i?.ZIN_NOME ?? i?.nome ?? '',
        tipo: 'text',
        unidade: i?.ZIN_UNIDADE ?? i?.unidade ?? null,
        meta: i?.ZIN_META ?? i?.meta ?? null,
        responsavel_id: i?.ZIN_RESPONSAVEL_ID ?? i?.responsavel_id ?? i?.responsavelId ?? null,
        read_only: i?.read_only ?? false,
        valor: null
    };
}

/**
 * Extrai o último grupo numérico encontrado em um código.
 * Ex.: "COD12" -> 12, "IND-003" -> 3
 */
function parseCodigoNumber(codigo) {
    if (codigo === null || codigo === undefined) return null;

    const str = String(codigo);
    const match = str.match(/(\d+)/g);
    if (!match || !match.length) return null;

    const last = match[match.length - 1];
    const num = Number(last);
    return Number.isNaN(num) ? null : num;
}

/**
 * Calcula o próximo código com base no maior número existente.
 * Retorna string (ex.: "7").
 */
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

/**
 * Preenche o input de "Código" do indicador (admin).
 */
function setIndicadorCodigoInput(value) {
    const input = document.getElementById('adminIndicadorCodigo');
    if (input && value) input.value = value;
}

/**
 * Determina se um indicador é do tipo data.
 * Aceita tipo='date' ou unidade='date'.
 */
function isDateIndicator(ind) {
    return false;
}

/**
 * Define o período a ser gravado:
 * - Se existir indicador "date" preenchido, extrai YYYY-MM
 * - Senão, usa mês/ano atual.
 */
function getPeriodoAtualOuDoFormulario() {
    const rawPeriodo = currentSector?.periodo;
    if (rawPeriodo && typeof rawPeriodo === 'string') {
        const raw = rawPeriodo.trim();
        if (raw.includes('/')) {
            if (validarData(raw)) {
                return converterDataParaISO(raw);
            }
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
            return raw;
        }
    }

    return '';
}

/**
 * Monta payload de valores (exclui data, exclui read_only).
 */
function buildValoresPayload() {
    return (currentSector?.indicadores || [])
        .filter(i => !i.read_only)
        .map(i => ({
            indicadorId: i.id,
            indicadorCodigo: i.codigo ?? i.id,
            indicadorNome: i.nome,
            tipo: 'text',
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
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(body)
    });

    if (resp.status === 401) handleUnauthorized();

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

    if (resp.status === 401) handleUnauthorized();

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
        },
        body: JSON.stringify(body)
    });

    if (resp.status === 401) handleUnauthorized();

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        const msg = data?.error || `Erro HTTP ${resp.status}`;
        throw new Error(msg);
    }

    return data;
}

/**
 * Quando API retorna 401:
 * - Limpa token
 * - Força usuário voltar ao login
 */
function handleUnauthorized() {
    authToken = null;
    tokenStorage.removeItem('authToken');
    alert('Sessão expirada. Faça login novamente.');
    showLoginScreen();
}

function setButtonLoading(btn, isLoading, loadingText) {
    if (!btn) return;
    if (isLoading) {
        if (!btn.dataset.originalText) btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = loadingText || 'Carregando...';
        btn.disabled = true;
        btn.classList.add('btn-loading');
    } else {
        if (btn.dataset.originalText) btn.innerHTML = btn.dataset.originalText;
        btn.disabled = false;
        btn.classList.remove('btn-loading');
    }
}

/**
 * Autoformata input text para DD/MM/AAAA enquanto digita.
 */
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

/**
 * Valida data no formato DD/MM/AAAA.
 * - Checa formato
 * - Checa intervalo (1900..2100)
 * - Checa dias por mês com ano bissexto
 */
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
    const bissexto = (ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0;
    if (bissexto) diasPorMes[1] = 29;

    if (dia > diasPorMes[mes - 1]) return false;
    return true;
}

/**
 * Converte DD/MM/AAAA -> YYYY-MM-DD
 */
function converterDataParaISO(dataString) {
    const partes = dataString.split('/');
    return `${partes[2]}-${partes[1]}-${partes[0]}`;
}

/**
 * Converte YYYY-MM-DD -> DD/MM/AAAA
 */
function converterDataParaBR(dataISO) {
    if (!dataISO) return '';
    const partes = dataISO.split('-');
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

/**
 * Alterna visibilidade da senha (input password/text).
 */
function togglePassword() {
    const input = document.getElementById('senhaInput');
    input.type = input.type === 'password' ? 'text' : 'password';
}

/**
 * Realiza login via API:
 * - POST /api/auth/login
 * - Salva token no sessionStorage
 * - Salva currentUser em memória
 * - Vai para tela de setores
 */
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

        authToken = normalizeToken(data.token);
        if (!authToken) {
            tokenStorage.removeItem('authToken');
            throw new Error('Token inválido retornado pelo servidor');
        }
        tokenStorage.setItem('authToken', authToken);

        currentUser = {
            id: data.user.id,
            email: data.user.email,
            nome: data.user.nome,
            setor_id: data.user.setor_id,
            nivel: data.user.nivel,
            perfil: data.user.perfil
        };

        document.getElementById('userNameDisplay').textContent = currentUser.nome;

        updateAdminButton();
        updateManagerButton();
        showSectorsScreen();
    } catch (err) {
        alert(err.message || 'Erro ao logar');
    }
}

/**
 * Logout simples:
 * - Limpa estado
 * - Remove token
 * - Recarrega página (reinicia JS)
 */
function handleLogout() {
    currentUser = null;
    authToken = null;
    tokenStorage.removeItem('authToken');
    location.reload();
}

async function tryRestoreSession() {
    const token = normalizeToken(tokenStorage.getItem('authToken'));
    if (!token) {
        showLoginScreen();
        return;
    }

    authToken = token;
    try {
        const resp = await fetch('/api/me', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!resp.ok) throw new Error('Sessão expirada');
        const data = await resp.json().catch(() => ({}));
        if (!data?.ok || !data?.user) throw new Error('Sessão expirada');

        currentUser = {
            id: data.user.id,
            email: data.user.email,
            nome: data.user.nome,
            setor_id: data.user.setor_id,
            nivel: data.user.nivel,
            perfil: data.user.perfil
        };

        document.getElementById('userNameDisplay').textContent = currentUser.nome;
        showSectorsScreen();
    } catch (err) {
        authToken = null;
        tokenStorage.removeItem('authToken');
        showLoginScreen();
    }
}

/**
 * Oculta todas as telas principais.
 */
function hideAllScreens() {
    ['loginScreen', 'sectorsScreen', 'indicatorsScreen', 'adminScreen', 'managerScreen'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
}

/**
 * Mostra tela de login.
 */
function showLoginScreen() {
    hideAllScreens();
    document.getElementById('loginScreen').classList.remove('hidden');
}

/**
 * Atualiza visibilidade do botão Admin conforme perfil.
 */
function updateAdminButton() {
    const btn = document.getElementById('adminBtn');
    if (!btn) return;

    if (isAdminUser(currentUser)) {
        btn.classList.remove('hidden');
    } else {
        btn.classList.add('hidden');
    }
}

function updateManagerButton() {
    const btn = document.getElementById('managerBtn');
    if (!btn) return;

    if (isManagerUser(currentUser)) {
        btn.classList.remove('hidden');
    } else {
        btn.classList.add('hidden');
    }
}

/**
 * Mostra tela de setores e atualiza dados.
 */
function showSectorsScreen() {
    loadSectors();
    updateHistoryDisplay();
    updateAdminButton();
    updateManagerButton();

    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
}

/**
 * Mostra tela de indicadores.
 */
function showIndicatorsScreen() {
    hideAllScreens();
    document.getElementById('indicatorsScreen').classList.remove('hidden');
}

/**
 * Mostra tela Admin (apenas GESTAO/ADM).
 */
function showAdminScreen() {
    if (!isAdminUser(currentUser)) {
        alert('Acesso negado');
        return;
    }

    hideAllScreens();
    document.getElementById('adminScreen').classList.remove('hidden');

    showAdminSection('users');
    showUsersSection('createUser');
    showIndicatorsSection('createIndicador');
    loadAdminData();
}

function openAdminEditSetor(setorId) {
    pendingAdminSetorId = Number(setorId);
    showAdminScreen();
    showUsersSection('editSetor');
}

/**
 * Volta do admin para setores.
 */
function backToSectorsFromAdmin() {
    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
    updateHistoryDisplay();
}

function showManagerScreen() {
    if (!isManagerUser(currentUser)) {
        alert('Acesso negado');
        return;
    }

    hideAllScreens();
    document.getElementById('managerScreen').classList.remove('hidden');
    showManagerSection('funcionarios');
    loadManagerData();
}

function backToSectorsFromManager() {
    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
    updateHistoryDisplay();
}

function showManagerSection(section) {
    const funcionarios = document.getElementById('managerFuncionariosSection');
    const indicadores = document.getElementById('managerIndicadoresSection');
    if (!funcionarios || !indicadores) return;

    if (section === 'indicadores') {
        funcionarios.classList.add('hidden');
        indicadores.classList.remove('hidden');
    } else {
        indicadores.classList.add('hidden');
        funcionarios.classList.remove('hidden');
    }
}

/**
 * Troca entre seções do Admin (users / indicators).
 */
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

function showIndicatorsSection(section) {
    const createCard = document.getElementById('adminCreateIndicadorCard');
    const editCard = document.getElementById('adminEditIndicadorCard');
    if (!createCard || !editCard) return;

    createCard.classList.add('hidden');
    editCard.classList.add('hidden');

    if (section === 'editIndicador') {
        editCard.classList.remove('hidden');
        return;
    }

    createCard.classList.remove('hidden');
}

/**
 * Troca blocos internos da seção Usuários no Admin.
 */
function showUsersSection(section) {
    const createUser = document.getElementById('adminCreateUserCard');
    const editUser = document.getElementById('adminEditUserCard');
    const createSetor = document.getElementById('adminCreateSetorCard');
    const editSetor = document.getElementById('adminEditSetorCard');
    const usersTable = document.getElementById('adminUsersTableWrap');
    const setoresTable = document.getElementById('adminSetoresTableWrap');

    if (!createUser || !editUser || !createSetor || !editSetor || !usersTable || !setoresTable) return;

    // Reseta tudo como hidden
    createUser.classList.add('hidden');
    editUser.classList.add('hidden');
    createSetor.classList.add('hidden');
    editSetor.classList.add('hidden');
    usersTable.classList.add('hidden');
    setoresTable.classList.add('hidden');

    // Mostra conforme seção
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

    // Default: createUser
    createUser.classList.remove('hidden');
}

/**
 * Volta da tela de indicadores para setores.
 */
function backToSectors() {
    currentSector = null;

    hideAllScreens();
    const sectors = document.getElementById('sectorsScreen');
    if (sectors) sectors.classList.remove('hidden');

    loadSectors();
    updateHistoryDisplay();
}

/**
 * Carrega setores via API:
 * - GET /api/setores
 * - Para cada setor, busca contagem de indicadores
 * - Renderiza botões em #sectorsGrid
 */
async function loadSectors() {
    const grid = document.getElementById('sectorsGrid');
    if (!grid) return;

    grid.innerHTML = '';

    try {
        const setoresData = await apiGet('/api/setores');
        const list = Array.isArray(setoresData) ? setoresData : [];

        setoresApi = list.map((s, idx) => normalizeSetorFromApi(s, idx));

        // Busca contagem de indicadores por setor em paralelo
        const counts = await Promise.all(
            setoresApi.map(s =>
                apiGet(`/api/indicadores?setorId=${encodeURIComponent(s.id)}`)
                    .then(items => ({ id: s.id, count: Array.isArray(items) ? items.length : 0 }))
                    .catch(() => ({ id: s.id, count: 0 }))
            )
        );
        const countMap = new Map(counts.map(c => [String(c.id), c.count]));

        const isAdmin = isAdminUser(currentUser);

        // Renderiza cart?es
        setoresApi.forEach(setor => {
            const count = countMap.get(String(setor.id)) ?? 0;
            const card = document.createElement('div');
            card.className = `sector-btn ${setor.classe}${isAdmin ? ' has-actions' : ''}`;

            if (isAdmin) {
                card.innerHTML = `
                    <div class="sector-content">
                        <h2>${setor.nome}</h2>
                        <p>${count} indicadores</p>
                    </div>
                    <div class="sector-actions">
                        <button type="button" class="btn btn-save sector-action" data-action="edit">Editar cartao</button>
                        <button type="button" class="btn btn-send sector-action" data-action="open">Abrir indicador</button>
                    </div>
                `;
                card.querySelectorAll('button[data-action]').forEach(btn => {
                    btn.addEventListener('click', (ev) => {
                        ev.stopPropagation();
                        const action = btn.getAttribute('data-action');
                        if (action === 'open') {
                            openSector(setor);
                        } else if (action === 'edit') {
                            openAdminEditSetor(setor.id);
                        }
                    });
                });
            } else {
                card.innerHTML = `<h2>${setor.nome}</h2><p>${count} indicadores</p>`;
                card.onclick = () => openSector(setor);
            }

            grid.appendChild(card);
        });
    } catch (err) {
        alert(`Erro ao carregar setores: ${err.message}`);
    }
}

/**
 * Abre um setor:
 * - GET /api/indicadores?setorId=...
 * - Renderiza inputs no formulário
 * - Aplica regras de read-only por nível/perfil
 * - Mostra tela de indicadores
 */
async function openSector(setor) {
    try {
        const data = await apiGet(`/api/indicadores?setorId=${encodeURIComponent(setor.id)}`);
        const indicadores = (Array.isArray(data) ? data : []).map(i => normalizeIndicadorFromApi(i));

        currentSector = {
            id: setor.id,
            nome: setor.nome,
            indicadores,
            periodo: ''
        };

        document.getElementById('sectorTitle').textContent = setor.nome;

        const form = document.getElementById('indicatorsForm');
        const indicatorsContent = document.querySelector('.indicators-content');
        let layout = document.querySelector('.indicators-layout');
        let periodPanel = document.getElementById('periodPanel');

        // Fallback: monta layout lateral caso o HTML antigo ainda esteja em uso
        if (!layout && indicatorsContent) {
            layout = document.createElement('div');
            layout.className = 'indicators-layout';

            const main = document.createElement('div');
            main.className = 'indicators-main';

            if (form) main.appendChild(form);
            const actions = document.querySelector('.action-buttons');
            if (actions) main.appendChild(actions);

            layout.appendChild(main);
            indicatorsContent.insertBefore(layout, indicatorsContent.firstChild);
        }

        if (!periodPanel && layout) {
            periodPanel = document.createElement('aside');
            periodPanel.id = 'periodPanel';
            periodPanel.className = 'period-panel hidden';
            layout.appendChild(periodPanel);
        }
        form.innerHTML = '';
        if (periodPanel) periodPanel.classList.add('hidden');

        const dateIndicator = currentSector.indicadores.find(i => isDateIndicator(i));
        if (dateIndicator?.valor) {
            currentSector.periodo = dateIndicator.valor;
        }

        if (!currentSector.periodo) {
            const today = new Date();
            const y = today.getFullYear();
            const m = String(today.getMonth() + 1).padStart(2, '0');
            const d = String(today.getDate()).padStart(2, '0');
            currentSector.periodo = `${y}-${m}-${d}`;
        }

        if (periodPanel) {
            const valueISO = currentSector.periodo || '';
            periodPanel.innerHTML = `
                <h3>Periodo</h3>
                <div class="period-label">${dateIndicator?.nome ?? 'Data do periodo'}</div>
                <input
                    type="date"
                    class="indicator-input"
                    data-id="${dateIndicator?.id ?? ''}"
                    value="${valueISO}"
                    onchange="updateIndicatorDate(${dateIndicator?.id ?? 0}, this.value)"
                    lang="pt-BR"
                >
                <div class="period-help">Selecione a data (DD/MM/AAAA)</div>
            `;
            periodPanel.classList.remove('hidden');
        }

        currentSector.indicadores.forEach(indicador => {
            if (dateIndicator && Number(indicador.id) === Number(dateIndicator.id)) return;
            const div = document.createElement('div');
            div.className = 'indicator-item';

            const isDateField = false;

            // readOnly se:
            // - indicador marcado read_only
            // - OU usuário nível 1 (LEITOR)
            const readOnly = indicador.read_only || (currentUser?.nivel === 1);
            const readonlyAttr = readOnly ? 'disabled' : '';

            let inputHtml = '';

            // Campo de texto (todos indicadores agora são texto)
            inputHtml = `
                <input
                    type="text"
                    placeholder="Digite o valor"
                    class="indicator-input"
                    data-id="${indicador.id}"
                    value="${indicador.valor ?? ''}"
                    onchange="updateIndicator(${indicador.id}, this.value)"
                    ${readonlyAttr}
                >
            `;

            const unidadeText = indicador.unidade ? ` | Unidade: ${indicador.unidade}` : '';
            const metaHtml = `<div class="indicator-meta">Meta: ${indicador.meta ?? '-'}${unidadeText}</div>`;

            div.innerHTML = `
                <label class="indicator-label">${indicador.nome}</label>
                ${metaHtml}
                ${inputHtml}
            `;

            form.appendChild(div);
        });
    } catch (err) {
        alert(`Erro ao carregar indicadores: ${err.message}`);
        return;
    }

    // Ajusta botões conforme perfil/nivel
    const perfil = getUserPerfil(currentUser);

    const sendBtn = document.getElementById('sendBtn');
    const saveBtn = document.getElementById('saveBtn');

    // Enviar DB: apenas LIDER / GESTAO / ADM
    if (sendBtn) {
        if (perfil === 'LIDER' || perfil === 'GESTAO' || perfil === 'ADM') {
            sendBtn.classList.remove('hidden');
        } else {
            sendBtn.classList.add('hidden');
        }
    }

    // Salvar: esconde para LEITOR (nivel 1)
    if (saveBtn) {
        if (currentUser?.nivel === 1) {
            saveBtn.classList.add('hidden');
            if (sendBtn) sendBtn.classList.add('hidden');
        } else {
            saveBtn.classList.remove('hidden');
        }
    }

    if (perfil === 'EDITOR') {
        await loadRejectedDrafts(currentSector.id);
    } else {
        const rejectedSection = document.getElementById('rejectedSection');
        if (rejectedSection) rejectedSection.classList.add('hidden');
    }

    showIndicatorsScreen();
}

async function loadRejectedDrafts(setorId) {
    const rejectedSection = document.getElementById('rejectedSection');
    const rejectedBody = document.getElementById('rejectedBody');
    if (!rejectedSection || !rejectedBody) return;

    try {
        const data = await apiGet(`/api/drafts/rejected?setorId=${encodeURIComponent(setorId)}`);
        const items = Array.isArray(data) ? data : [];
        rejectedBody.innerHTML = '';

        if (!items.length) {
            rejectedSection.classList.add('hidden');
            return;
        }

        items.forEach(i => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${i.INDICADOR_NOME ?? ''}</td>
                <td>${i.ZDR_REJEITADO_MOTIVO ?? ''}</td>
                <td>${i.ZDR_REJEITADO_EM ?? ''}</td>
            `;
            rejectedBody.appendChild(tr);
        });

        rejectedSection.classList.remove('hidden');
    } catch (err) {
        rejectedSection.classList.add('hidden');
    }
}

/**
 * Atualiza valor em memória para indicador numérico.
 */
function updateIndicator(id, value) {
    const ind = currentSector.indicadores.find(i => Number(i.id) === Number(id));
    if (ind) ind.valor = value;
}

/**
 * Atualiza valor em memória para indicador data:
 * - recebe BR (DD/MM/AAAA)
 * - valida
 * - converte para ISO
 */
function updateIndicatorDate(id, value) {
    const ind = currentSector.indicadores.find(i => Number(i.id) === Number(id));

    if (!value) {
        if (ind) ind.valor = '';
        currentSector.periodo = '';
        return;
    }

    const raw = String(value).trim();
    if (raw.includes('/')) {
        if (!validarData(raw)) {
            alert('Data inválida! Use o formato DD/MM/AAAA');
            return;
        }
        const iso = converterDataParaISO(raw);
        if (ind) ind.valor = iso;
        currentSector.periodo = iso;
        return;
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        if (ind) ind.valor = raw;
        currentSector.periodo = raw;
        return;
    }
    alert('Data inválida!');
}

/**
 * Salva rascunho no banco:
 * - POST /api/drafts
 * - Permitido para: padrão/lider/gestao (exceto nível 1)
 */
async function handleSave() {
    const periodo = getPeriodoAtualOuDoFormulario();
    const valores = buildValoresPayload();
    const saveBtn = document.getElementById('saveBtn');
    const perfil = getUserPerfil(currentUser);

    if (perfil === 'LEITOR') {
        alert('Seu perfil nao pode salvar indicadores.');
        return;
    }

    if (!periodo) {
        alert('Selecione a data do periodo antes de salvar.');
        return;
    }

    const confirmed = await showConfirmModal({
        title: 'Confirmar salvamento',
        message: 'Deseja salvar este rascunho?'
    });
    if (!confirmed) return;

    const body = {
        setorId: currentSector.id,
        setorNome: currentSector.nome,
        funcionarioEmail: currentUser.email,
        funcionarioNome: currentUser.nome,
        funcionarioPerfil: getUserPerfil(currentUser),
        periodo,
        valores
    };

    try {
        setButtonLoading(saveBtn, true, 'Salvando...');
        await apiPost('/api/drafts', body);
        registrosDB.unshift({
            id: Date.now(),
            usuario: currentUser.nome,
            setor: currentSector.nome,
            timestamp: new Date().toLocaleString('pt-BR'),
            indicadores: currentSector.indicadores,
            status: perfil === 'EDITOR' ? 'Aguardando aprovacao' : 'Rascunho (DB)'
        });
        updateHistoryDisplay();
        alert('Rascunho salvo no banco com sucesso!');
    } catch (err) {
        alert(`Erro ao salvar rascunho: ${err.message}`);
    } finally {
        setButtonLoading(saveBtn, false);
    }
}

async function handleSendDB() {
    const perfil = getUserPerfil(currentUser);
    const sendBtn = document.getElementById('sendBtn');

    if (perfil !== 'LIDER' && perfil !== 'GESTAO' && perfil !== 'ADM') {
        alert('Apenas LIDER, GESTAO ou ADM podem enviar valores definitivos para o banco. Use "Salvar" para rascunho.');
        return;
    }

    const confirmed = await showConfirmModal({
        title: 'Confirmar envio',
        message: 'Deseja enviar os indicadores para o banco de dados?'
    });
    if (!confirmed) return;

    const periodo = getPeriodoAtualOuDoFormulario();
    const valores = buildValoresPayload();
    if (!periodo) {
        alert('Selecione a data do periodo antes de enviar.');
        return;
    }

    const body = {
        setorId: currentSector.id,
        setorNome: currentSector.nome,
        funcionarioEmail: currentUser.email,
        funcionarioNome: currentUser.nome,
        funcionarioPerfil: perfil,
        periodo,
        valores
    };

    try {
        setButtonLoading(sendBtn, true, 'Enviando...');
        await apiPost('/api/valores', body);
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
    } catch (err) {
        alert(`Erro ao enviar para DB: ${err.message}`);
    } finally {
        setButtonLoading(sendBtn, false);
    }
}

/**
 * Atualiza histórico e últimos registros na UI.
 * Observação: hoje só renderiza quando registrosDB > 0.
 */
function updateHistoryDisplay() {
    if (registrosDB.length > 0) {
        document.getElementById('historySection').classList.remove('hidden');
        document.getElementById('recentRecords').classList.remove('hidden');

        // Tabela "Histórico"
        const tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';

        registrosDB.slice(0, 5).forEach(registro => {
            const row = document.createElement('tr');

            const badgeClass = (registro.status === 'Enviado para DB')
                ? 'status-sent'
                : 'status-saved';

            row.innerHTML = `
                <td>${registro.usuario}</td>
                <td>${registro.setor}</td>
                <td>${registro.timestamp}</td>
                <td><span class="status-badge ${badgeClass}">${registro.status}</span></td>
            `;

            tbody.appendChild(row);
        });

        // Cards "Últimos Registros"
        const recordsList = document.getElementById('recordsList');
        recordsList.innerHTML = '';

        registrosDB.slice(0, 3).forEach(registro => {
            const div = document.createElement('div');
            div.className = 'record-item';

            const badgeClass = (registro.status === 'Enviado para DB')
                ? 'status-sent'
                : 'status-saved';

            div.innerHTML = `
                <div class="record-info">
                    <p>${registro.setor}</p>
                    <div class="timestamp">${registro.timestamp}</div>
                </div>
                <span class="status-badge ${badgeClass}">${registro.status}</span>
            `;

            recordsList.appendChild(div);
        });
    }
}

/**
 * Compat: pega id do setor independente do nome do campo.
 */
function getSetorIdValue(s) {
    return s?.ZSE_ID ?? s?.id ?? null;
}

/**
 * Compat: pega nome do setor independente do nome do campo.
 */
function getSetorNomeValue(s) {
    return s?.ZSE_NOME ?? s?.nome ?? '';
}

/**
 * Preenche um select de setores.
 */
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

/**
 * Preenche select de níveis (1..5).
 */
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

/**
 * Preenche select de usuários para "Responsável" do indicador.
 */
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

/**
 * Set seguro de valor em <select> (converte null/undefined -> '').
 */
function setSelectValue(selectEl, value) {
    if (!selectEl) return;
    const val = value === null || value === undefined ? '' : String(value);
    selectEl.value = val;
}

function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast${type === 'error' ? ' error' : ''}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function showConfirmModal({ title, message }) {
    const modal = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmTitle');
    const messageEl = document.getElementById('confirmMessage');
    const okBtn = document.getElementById('confirmOkBtn');
    const cancelBtn = document.getElementById('confirmCancelBtn');

    if (!modal || !titleEl || !messageEl || !okBtn || !cancelBtn) {
        return Promise.resolve(false);
    }

    titleEl.textContent = title || 'Confirmar';
    messageEl.textContent = message || 'Tem certeza?';
    modal.classList.remove('hidden');

    return new Promise(resolve => {
        const cleanup = () => {
            modal.classList.add('hidden');
            okBtn.onclick = null;
            cancelBtn.onclick = null;
        };
        okBtn.onclick = () => {
            cleanup();
            resolve(true);
        };
        cancelBtn.onclick = () => {
            cleanup();
            resolve(false);
        };
    });
}

function showPromptModal({ title, message, placeholder, type }) {
    const modal = document.getElementById('promptModal');
    const titleEl = document.getElementById('promptTitle');
    const messageEl = document.getElementById('promptMessage');
    const inputEl = document.getElementById('promptInput');
    const okBtn = document.getElementById('promptOkBtn');
    const cancelBtn = document.getElementById('promptCancelBtn');

    if (!modal || !titleEl || !messageEl || !inputEl || !okBtn || !cancelBtn) {
        return Promise.resolve(null);
    }

    titleEl.textContent = title || 'Informe';
    messageEl.textContent = message || '';
    inputEl.value = '';
    inputEl.type = type || 'text';
    inputEl.placeholder = placeholder || '';
    modal.classList.remove('hidden');
    inputEl.focus();

    return new Promise(resolve => {
        const cleanup = () => {
            modal.classList.add('hidden');
            okBtn.onclick = null;
            cancelBtn.onclick = null;
        };
        okBtn.onclick = () => {
            const value = inputEl.value;
            cleanup();
            resolve(value);
        };
        cancelBtn.onclick = () => {
            cleanup();
            resolve(null);
        };
    });
}

async function loadManagerData() {
    try {
        const [funcionariosData, pendentesData] = await Promise.all([
            apiGet('/api/gestor/funcionarios'),
            apiGet('/api/drafts/pending')
        ]);

        renderManagerFuncionarios(Array.isArray(funcionariosData) ? funcionariosData : []);
        renderManagerIndicadores(Array.isArray(pendentesData) ? pendentesData : []);
    } catch (err) {
        alert(`Erro ao carregar painel gestor: ${err.message}`);
    }
}

function renderManagerFuncionarios(items) {
    const tbody = document.getElementById('managerFuncionariosBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!items.length) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="3">Nenhum funcionario encontrado</td>';
        tbody.appendChild(tr);
        return;
    }

    items.forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${u.ZFU_NOME ?? ''}</td>
            <td>${u.ZFU_EMAIL ?? ''}</td>
            <td>${u.ZFU_NIVEL ?? ''}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderManagerIndicadores(items) {
    const tbody = document.getElementById('managerIndicadoresBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!items.length) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="7">Nenhum indicador pendente</td>';
        tbody.appendChild(tr);
        return;
    }

    items.forEach(i => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${i.INDICADOR_NOME ?? ''}</td>
            <td>${i.SETOR_NOME ?? ''}</td>
            <td>${i.FUNCIONARIO_NOME ?? ''}</td>
            <td>${i.ZDR_PERIODO ?? ''}</td>
            <td>${i.ZDR_VALOR ?? ''}</td>
            <td>${i.ZDR_STATUS ?? ''}</td>
            <td>
                <button class="btn btn-save admin-btn-row" data-gestor-action="approve" data-draft-id="${i.ZDR_ID}">Aprovar</button>
                <button class="btn btn-send admin-btn-row" data-gestor-action="reject" data-draft-id="${i.ZDR_ID}">Recusar</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('button[data-gestor-action]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const id = btn.getAttribute('data-draft-id');
            const action = btn.getAttribute('data-gestor-action');
            if (action === 'approve') {
                await approveDraft(id);
            } else {
                await rejectDraft(id);
            }
        });
    });
}

async function approveDraft(draftId) {
    try {
        const confirmed = await showConfirmModal({
            title: 'Aprovar indicador',
            message: 'Deseja aprovar este indicador?'
        });
        if (!confirmed) return;

        await apiPost(`/api/drafts/${draftId}/approve`, {});
        await loadManagerData();
        showToast('Indicador aprovado');
    } catch (err) {
        showToast(`Erro ao aprovar: ${err.message}`, 'error');
    }
}

async function rejectDraft(draftId) {
    const motivo = await showPromptModal({
        title: 'Recusar indicador',
        message: 'Informe o motivo da recusa',
        placeholder: 'Motivo da recusa'
    });
    if (motivo === null) return;
    if (!motivo.trim()) {
        showToast('Informe o motivo', 'error');
        return;
    }
    const confirmed = await showConfirmModal({
        title: 'Confirmar recusa',
        message: 'Deseja recusar este indicador?'
    });
    if (!confirmed) return;
    try {
        await apiPost(`/api/drafts/${draftId}/reject`, { motivo: motivo.trim() });
        await loadManagerData();
        showToast('Indicador recusado');
    } catch (err) {
        showToast(`Erro ao recusar: ${err.message}`, 'error');
    }
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

        // Selects de responsável
        fillUserSelect(document.getElementById('adminIndicadorResponsavel'), adminState.users, true);
        fillUserSelect(document.getElementById('adminIndicadorResponsavelEdit'), adminState.users, true);

        // Ao trocar setor no "Criar indicador", recalcula sugestão de código
        const setorCreateSelect = document.getElementById('adminIndicadorSetor');
        if (setorCreateSelect) {
            setorCreateSelect.onchange = async () => {
                const nextId = setorCreateSelect.value;
                if (nextId) await refreshIndicadorCodigoForSetor(nextId);
            };
        }

        // Ao trocar setor no "Editar indicador", carrega indicadores do setor
        const setorSelect = document.getElementById('adminIndicadorSetorEdit');
        if (setorSelect) {
            setorSelect.onchange = () => {
                const nextId = setorSelect.value;
                if (nextId) loadAdminIndicadores(nextId);
            };
        }

        // Setor padrão (primeiro da lista)
        const defaultSetorId = getSetorIdValue(adminState.setores[0]);
        if (defaultSetorId) {
            setSelectValue(document.getElementById('adminIndicadorSetorEdit'), defaultSetorId);
            setSelectValue(document.getElementById('adminIndicadorSetor'), defaultSetorId);

            await loadAdminIndicadores(defaultSetorId);
            await refreshIndicadorCodigoForSetor(defaultSetorId);
        }

        if (pendingAdminSetorId) {
            selectAdminSetor(pendingAdminSetorId);
            showUsersSection('editSetor');
            pendingAdminSetorId = null;
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
                <button class="btn btn-send admin-btn-row" data-user-id="${u.ZFU_ID}" data-user-action="toggle" data-user-active="${u.ZFU_ATIVO ? 1 : 0}">
                    ${u.ZFU_ATIVO ? 'Bloquear' : 'Desbloquear'}
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('button[data-user-id]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-user-id');
            const action = btn.getAttribute('data-user-action');

            if (action === 'toggle') {
                const active = Number(btn.getAttribute('data-user-active') || '0');
                adminToggleUser(id, active ? 0 : 1);
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
        const senha = document.getElementById('adminUserSenha').value.trim();

        if (!nome || !email) {
            showToast('Informe nome e email', 'error');
            return;
        }
        if (!senha) {
            showToast('Informe uma senha', 'error');
            return;
        }
        if (!isStrongPassword(senha)) {
            showToast('Senha fraca (min 8 caracteres, letras e numeros)', 'error');
            return;
        }

        const confirmed = await showConfirmModal({
            title: 'Confirmar criacao',
            message: `Criar usuario ${nome}?`
        });
        if (!confirmed) return;

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

        showToast('Usuario criado');
    } catch (err) {
        showToast(`Erro ao criar usuario: ${err.message}`, 'error');
    }
}

async function adminUpdateUser() {
    try {
        const id = document.getElementById('adminUserId').value;
        if (!id) {
            showToast('Selecione um usuario', 'error');
            return;
        }

        const body = {
            nome: document.getElementById('adminUserNomeEdit').value.trim(),
            email: document.getElementById('adminUserEmailEdit').value.trim(),
            setor_id: document.getElementById('adminUserSetorEdit').value || null,
            nivel: Number(document.getElementById('adminUserNivelEdit').value || 1),
            ativo: document.getElementById('adminUserAtivoEdit').checked ? 1 : 0
        };

        const confirmed = await showConfirmModal({
            title: 'Confirmar alteracao',
            message: `Alterar cadastro do usuario ${body.nome || id}?`
        });
        if (!confirmed) return;

        await apiPut(`/api/users/${id}`, body);
        await loadAdminData();

        showToast('Usuario atualizado');
    } catch (err) {
        showToast(`Erro ao atualizar usuario: ${err.message}`, 'error');
    }
}

async function adminResetUserPassword() {
    try {
        const id = document.getElementById('adminUserId').value;
        if (!id) {
            showToast('Selecione um usuario', 'error');
            return;
        }

        const senhaRaw = await showPromptModal({
            title: 'Redefinir senha',
            message: 'Digite a nova senha',
            placeholder: 'Nova senha',
            type: 'password'
        });
        if (senhaRaw === null) return;

        const senha = senhaRaw.trim();
        if (!senha) {
            showToast('Informe uma senha', 'error');
            return;
        }
        if (!isStrongPassword(senha)) {
            showToast('Senha fraca (min 8 caracteres, letras e numeros)', 'error');
            return;
        }

        const confirmed = await showConfirmModal({
            title: 'Confirmar redefinicao',
            message: 'Deseja redefinir a senha deste usuario?'
        });
        if (!confirmed) return;

        await apiPost(`/api/users/${id}/reset-password`, { senha });

        showToast('Senha redefinida');
    } catch (err) {
        showToast(`Erro ao resetar senha: ${err.message}`, 'error');
    }
}

async function adminToggleUser(userId, nextActive) {
    try {
        const id = Number(userId);
        if (!id) {
            showToast('Usuario invalido', 'error');
            return;
        }

        const isBlocking = Number(nextActive) === 0;
        const confirmed = await showConfirmModal({
            title: isBlocking ? 'Bloquear usuario' : 'Desbloquear usuario',
            message: isBlocking
                ? 'Tem certeza que deseja bloquear este usuario?'
                : 'Tem certeza que deseja desbloquear este usuario?'
        });
        if (!confirmed) return;

        await apiPut(`/api/users/${id}`, { ativo: nextActive ? 1 : 0 });
        await loadAdminData();

        showToast(isBlocking ? 'Usuario bloqueado com sucesso' : 'Usuario desbloqueado com sucesso');
    } catch (err) {
        showToast(`Erro ao atualizar usuario: ${err.message}`, 'error');
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

        const confirmed = await showConfirmModal({
            title: 'Confirmar criacao',
            message: `Criar setor ${nome}?`
        });
        if (!confirmed) return;

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

        const confirmed = await showConfirmModal({
            title: 'Confirmar alteracao',
            message: `Alterar setor ${nome || id}?`
        });
        if (!confirmed) return;

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

        const confirmed = await showConfirmModal({
            title: 'Confirmar inativacao',
            message: 'Deseja inativar este setor?'
        });
        if (!confirmed) return;

        await apiPut(`/api/setores/${id}`, { ativo: 0 });
        await loadAdminData();

        alert('Setor inativado');
    } catch (err) {
        alert(`Erro ao inativar setor: ${err.message}`);
    }
}

/**
 * Atualiza sugestão de código do indicador com base no setor selecionado.
 */
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

function fillUnidadeSelect(selectEl, indicadores, allowEmpty = true) {
    if (!selectEl) return;
    const valores = new Set();
    (indicadores || []).forEach(i => {
        const v = (i?.ZIN_UNIDADE ?? i?.unidade ?? '').toString().trim();
        if (v) valores.add(v);
    });

    const options = [];
    if (allowEmpty) options.push({ value: '', label: '-- selecione --' });
    Array.from(valores).sort((a, b) => a.localeCompare(b)).forEach(v => {
        options.push({ value: v, label: v });
    });
    options.push({ value: '__new__', label: 'Outra (digitar)' });

    selectEl.innerHTML = '';
    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        selectEl.appendChild(option);
    });
}

function setupUnidadeSelect(selectId, inputId) {
    const selectEl = document.getElementById(selectId);
    const inputEl = document.getElementById(inputId);
    if (!selectEl || !inputEl) return;
    if (selectEl.dataset.bound === '1') return;
    selectEl.dataset.bound = '1';

    const toggle = () => {
        const isNew = selectEl.value === '__new__';
        inputEl.classList.toggle('hidden', !isNew);
        if (!isNew) inputEl.value = '';
    };
    selectEl.addEventListener('change', toggle);
    toggle();
}

function getUnidadeValue(selectId, inputId) {
    const selectEl = document.getElementById(selectId);
    const inputEl = document.getElementById(inputId);
    if (!selectEl) return '';
    if (selectEl.value === '__new__') {
        return (inputEl?.value || '').trim();
    }
    return (selectEl.value || '').trim();
}

function setUnidadeValue(selectId, inputId, value) {
    const selectEl = document.getElementById(selectId);
    const inputEl = document.getElementById(inputId);
    if (!selectEl) return;
    const v = (value || '').toString().trim();
    const hasOption = Array.from(selectEl.options).some(o => o.value === v);
    if (v && !hasOption) {
        selectEl.value = '__new__';
        if (inputEl) inputEl.value = v;
    } else {
        selectEl.value = v || '';
        if (inputEl) inputEl.value = '';
    }
    if (inputEl) {
        inputEl.classList.toggle('hidden', selectEl.value !== '__new__');
    }
}

function renderAdminIndicadores() {
    const tbody = document.getElementById('adminIndicadoresBody');
    if (!tbody) return;

    tbody.innerHTML = '';

    fillUnidadeSelect(document.getElementById('adminIndicadorUnidade'), adminState.indicadores, true);
    fillUnidadeSelect(document.getElementById('adminIndicadorUnidadeEdit'), adminState.indicadores, true);
    setupUnidadeSelect('adminIndicadorUnidade', 'adminIndicadorUnidadeCustom');
    setupUnidadeSelect('adminIndicadorUnidadeEdit', 'adminIndicadorUnidadeCustomEdit');

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

    document.getElementById('adminIndicadorId').value = indicador.ZIN_ID ?? '';
    document.getElementById('adminIndicadorNomeEdit').value = indicador.ZIN_NOME ?? '';
    setUnidadeValue('adminIndicadorUnidadeEdit', 'adminIndicadorUnidadeCustomEdit', indicador.ZIN_UNIDADE ?? '');
    document.getElementById('adminIndicadorMetaEdit').value = indicador.ZIN_META ?? '';

    setSelectValue(document.getElementById('adminIndicadorResponsavelEdit'), indicador.ZIN_RESPONSAVEL_ID);
    document.getElementById('adminIndicadorAtivoEdit').checked = !!indicador.ZIN_ATIVO;
}

async function adminCreateIndicador() {
    try {
        const setorId = document.getElementById('adminIndicadorSetor').value;
        const codigo = document.getElementById('adminIndicadorCodigo').value.trim();
        const nome = document.getElementById('adminIndicadorNome').value.trim();
        const unidade = getUnidadeValue('adminIndicadorUnidade', 'adminIndicadorUnidadeCustom') || null;

        const metaVal = document.getElementById('adminIndicadorMeta').value;
        const meta = metaVal === '' ? null : Number(metaVal);

        const responsavelRaw = document.getElementById('adminIndicadorResponsavel').value;
        const responsavel_id = responsavelRaw ? Number(responsavelRaw) : null;

        if (!setorId || !codigo || !nome) {
            alert('Informe setor, codigo e nome');
            return;
        }
        if (!unidade) {
            alert('Informe a unidade');
            return;
        }

        const confirmed = await showConfirmModal({
            title: 'Confirmar criacao',
            message: `Criar indicador ${nome}?`
        });
        if (!confirmed) return;

        await apiPost('/api/indicadores', {
            setor_id: Number(setorId),
            codigo,
            nome,
            unidade,
            meta,
            responsavel_id
        });

        await loadAdminIndicadores(setorId);

        // Limpa form
        document.getElementById('adminIndicadorCodigo').value = '';
        document.getElementById('adminIndicadorNome').value = '';
        setUnidadeValue('adminIndicadorUnidade', 'adminIndicadorUnidadeCustom', '');
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
            unidade: getUnidadeValue('adminIndicadorUnidadeEdit', 'adminIndicadorUnidadeCustomEdit') || null,
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
        if (!body.unidade) {
            alert('Informe a unidade');
            return;
        }

        const confirmed = await showConfirmModal({
            title: 'Confirmar alteracao',
            message: `Alterar indicador ${body.nome || id}?`
        });
        if (!confirmed) return;

        await apiPut(`/api/indicadores/${id}`, body);

        const setorId = document.getElementById('adminIndicadorSetorEdit').value;
        if (setorId) await loadAdminIndicadores(setorId);

        alert('Indicador atualizado');
    } catch (err) {
        alert(`Erro ao atualizar indicador: ${err.message}`);
    }
}

/**
 * Ao carregar a página:
 * - Exibe tela de login.
 * Obs.: Você pode evoluir aqui para "auto-login" se houver token válido
 * e quiser validar /api/me antes de liberar a UI.
 */
document.addEventListener('DOMContentLoaded', function () {
    tryRestoreSession();
});
