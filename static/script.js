// ===== BASE DE DADOS =====
const usuariosDB = [
    { id: 1, email: 'ad', senha: '1120', nome: 'Administrador' },
    { id: 2, email: 'vendas', senha: '123456', nome: 'Gerente de Vendas' },
    { id: 3, email: 'operacao', senha: '123456', nome: 'Gerente de Operações' }
];

// ===== FUNÇÕES DE LOGIN =====
function handleLogin() {
    const email = document.getElementById('emailInput').value;
    const senha = document.getElementById('senhaInput').value;

    if (!email || !senha) {
        alert("Preencha usuário e senha");
        return;
    }

    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('mainNavbar').classList.remove('hidden');

    goToSectors(); // padrão após login
}

// ===== NAVEGAÇÃO DE TELAS =====
function goToSectors() {
    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
}

function goToCobli() {
    hideAllScreens();
    document.getElementById('cobliScreen').classList.remove('hidden');
}

// Esconde todas as telas
function hideAllScreens() {
    const screens = [
        'sectorsScreen',
        'indicatorsScreen',
        'cobliScreen'
    ];

    screens.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
}

// Função para lidar com logout
function handleLogout() {
    hideAllScreens();
    document.getElementById('mainNavbar').classList.add('hidden');
    document.getElementById('loginScreen').classList.remove('hidden');
}


const setores = [
    {
        id: 1,
        nome: 'Ambiental',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Custo mensal Transpedra (pneus + combustível) (R$/ton transportada) ', valor: '', unidade: 'R$/ton', meta: 150000 },
            { id: 2, nome: 'Número de ocorrencias ambientais', valor: '', unidade: 'un', meta: 50 },
            { id: 3, nome: 'Número de ocorrencias ambientais', valor: '', unidade: 'un', meta: 5 },
            { id: 4, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 2,
        nome: 'Balança',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'Tempo Médio de Atendimento ao cliente (minutos)', valor: '', unidade: 'min', meta: 5 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' },
        ]
    },
    {
        id: 3,
        nome: 'Betume - JN',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Consumo de energia Betume João Neiva (kwh/ton)', valor: '', unidade: 'kwh/ton', meta: 50 },
            { id: 2, nome: 'Consumo de oleo BPF (L/ton)', valor: '', unidade: 'L/ton', meta: 5 },
            { id: 3, nome: 'Economia de CAP Betume JN (%)', valor: '', unidade: '%', meta: 10 },
            { id: 4, nome: 'Faturamento Betume Joao Neiva (R$)', valor: '', unidade: 'R$', meta: 500000 },
            { id: 5, nome: 'Custo médio de manutenção R$/ton', valor: '', unidade: 'R$/ton', meta: 20 },
            { id: 6, nome: 'Turnover acumulado Betume João Neiva (%)', valor: '', unidade: '%', meta: 5 },
            { id: 7, nome: 'Laboratório - Tempo máx de envio de resultados (horas)', valor: '', unidade: 'horas', meta: 48 },
            { id: 8, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 4,
        nome: 'Betume - Matriz',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: 'Consumo de gás Betume Matriz (m³/ton)', valor: '', unidade: 'm³/ton', meta: 30 },
            { id: 2, nome: 'Consumo de energia Betume Matriz (kwh/ton)', valor: '', unidade: 'kwh/ton', meta: 40 },
            { id: 3, nome: 'Economia de CAP Betume Matriz (%)', valor: '', unidade: '%', meta: 8 },
            { id: 4, nome: 'Absenteísmo Operacional Betume Matriz (%)', valor: '', unidade: '%', meta: 3 },
            { id: 5, nome: 'Custo médio de manutenção Betume Matriz R$/ton', valor: '', unidade: 'R$/ton', meta: 25 },
            { id: 6, nome: '% de reclamações revertidas - lab Betume', valor: '', unidade: '%', meta: 5 },
            { id: 7, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }

        ]
    },
    {
        id: 5,
        nome: 'Comercial',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Quantidade vendida (ton) - Brasitalia', valor: '', unidade: 'ton', meta: 10000 },
            { id: 2, nome: 'Preço médio (R$) - Brasitalia', valor: '', unidade: 'R$', meta: 250 },
            { id: 3, nome: '% pó de pedra - Brasitalia', valor: '', unidade: '%', meta: 5 },
            { id: 4, nome: 'Número de clientes novos Brasitalia + Betume', valor: '', unidade: 'un', meta: 10 },
            { id: 5, nome: 'Número de clientes mantidos Brasitalia + Betume', valor: '', unidade: 'un', meta: 50 },
            { id: 6, nome: 'Preço médio (R$) - Produtos sem CAP convencional ou polímero - Betume', valor: '', unidade: 'R$', meta: 300 },
            { id: 7, nome: 'Preço médio (R$) - Produtos com CAP convencional - Betume', valor: '', unidade: 'R$', meta: 350 },
            { id: 8, nome: 'Quantidade vendida (ton) - Betume Matriz', valor: '', unidade: 'ton', meta: 8000 },
            { id: 9, nome: 'Faturamento (R$) - Betume joao neiva', valor: '', unidade: 'R$', meta: 400000 },
            { id: 10, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 6,
        nome: 'Compras',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'índice de economia em compras (%)', valor: '', unidade: '%', meta: 5 },
            { id: 2, nome: 'Tempo de colocação do pedido de compra (dias)', valor: '', unidade: 'dias', meta: 3 },
            { id: 3, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 7,
        nome: 'Compras - Paulão',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Consumo de combustível Paulão (L/Km)', valor: '', unidade: 'L/Km', meta: 10 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 8,
        nome: 'Conferencia ',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: 'Número de ocorrências de cliente levar produto errado (uni)', valor: '', unidade: 'un', meta: 2 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 9,
        nome: 'Desmonte',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Absenteísmo do desmonte (%)', valor: '', unidade: '%', meta: 3 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 10,
        nome: 'Estoque',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'sem indicador definido', valor: '', unidade: 'un', meta: 0 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 11,
        nome: 'Faxineiras',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Custo com material de limpeza (R$)', valor: '', unidade: 'R$', meta: 2000 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 12,
        nome: 'Financeiro',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: 'Número de pedidos de notas que financeiro pediu e já tinham descido' , valor: '', unidade: 'un', meta: 0 },
            { id: 2, nome: 'Turnover setor financeiro (%)', valor: '', unidade: '%', meta: 5 },
            { id: 3, nome: 'Número de títulos de inadimplência levados a cartório', valor: '', unidade: 'un', meta: 10 },
            { id: 4, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 13,
        nome: 'Lavador',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Custo lavador (R$)', valor: '', unidade: 'R$', meta: 5000 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 14,
        nome: 'Oficina Mecanica',
        classe: 'sector-green',
        indicadores: [ 
            { id: 1, nome: 'Absenteísmo oficina mecânica (%)', valor: '', unidade: '%', meta: 4 },
            { id: 2, nome: 'Custo mensal borracharia (R$/ton produzidas)', valor: '', unidade: 'R$/ton', meta: 15 },
            { id: 3, nome: 'Custo mensal com pneus Brasitalia (R$/ton produzida) ', valor: '', unidade: 'R$/ton', meta: 10 },
            { id: 4, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 15,
        nome: 'Oficina Solda',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Turnover Solda/caldeiraria (%)', valor: '', unidade: '%', meta: 5 },
            { id: 2, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 16,
        nome: 'Posto fiscal',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: '% de notas que desceram com atraso (%)', valor: '', unidade: '%', meta: 2 },
            { id: 2, nome: 'Índice de erro no lançamento de NF (%)', valor: '', unidade: '%', meta: 1 },
            { id: 3, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 17,
        nome: 'Recepçao',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Indice de pontos atualizados e enviado no prazo(%)', valor: '', unidade: '%', meta: 98 },
            { id: 2, nome: 'Número de erros na FOPAG relacionado ao ponto (uni)', valor: '', unidade: 'un', meta: 2 },
            { id: 3, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 18,
        nome: 'Suporte transpedra',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'Número de erros das paginas diárias (uni)', valor: '', unidade: 'un', meta: 5 },
            { id: 2, nome: 'Entregar páginas diárias da transpedra no dia/hora certa (%)', valor: '', unidade: '%', meta: 99 },
            { id: 3, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 19,
        nome: 'RH',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Índice de efetividade das contratações (%)', valor: '', unidade: '%', meta: 90 },
            { id: 2, nome: 'Absenteísmo mensal do setor RH + recepção + faxineiras (%)', valor: '', unidade: '%', meta: 3 },
            { id: 3, nome: 'Índice de erro na FOPAG/ticket alimentação (%)', valor: '', unidade: '%', meta: 1 },
            { id: 4, nome: 'Turnover acumulado do setor RH + recepção + faxineiras (%)', valor: '', unidade: '%', meta: 5 },
            { id: 5, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 20,
        nome: 'Segurança do Trabalho(SESMT)',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: 'Número de notificações de órgãos ', valor: '', unidade: 'un', meta: 0 },
            { id: 2, nome: 'Número de acidentes dentro da empresa (un)', valor: '', unidade: 'un', meta: 2 },
            { id: 3, nome: 'Número de acidentes dentro da empresa com afastamento (un)', valor: '', unidade: 'un', meta: 1 },
            { id: 4, nome: 'Absenteísmo viveiristas (%)', valor: '', unidade: '%', meta: 3 },
            { id: 5, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 21,
        nome: 'TI',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Nota de satisfação com qualidade do atendimento - TI (/10)', valor: '', unidade: '/10', meta: 9 },
            { id: 2, nome: 'Nota de satisfação com tempo de atendimento - TI (/10)', valor: '', unidade: '/10', meta: 9 },
            { id: 3, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 22,
        nome: 'Transpedra',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'Custo mensal com pneus Transpedra (R$/ton transportada) ', valor: '', unidade: 'R$/ton', meta: 10 },
            { id: 2, nome: 'Consumo mensal de combustivel Transpedra (R$/ton transportada) ', valor: '', unidade: 'R$/ton', meta: 140000 },
            { id: 3, nome: 'Produtividade - No de viagens totais motoristas Transpedra', valor: '', unidade: 'viagens', meta: 5000 },
            { id: 4, nome: 'Turnover acumulado Transpedra (%)', valor: '', unidade: '%', meta: 5 },
            { id: 5, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 23,
        nome : 'Transporte Interno',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Toneladas produzidas/dia (ton)', valor: '', unidade: 'ton', meta: 3000 },
            { id: 2, nome: 'Nota média de condução dos motoristas (un)', valor: '', unidade: 'un', meta: 95 },
            { id: 3, nome: 'Custo com combustível (R$/ton produzida)', valor: '', unidade: 'R$/ton', meta: 20 },
            { id: 4, nome: 'Custo de transporte (R$/ton produzida)', valor: '', unidade: 'R$/ton', meta: 30 },
            { id: 5, nome: 'Absenteísmo operadores Rodrigo (%)', valor: '', unidade: '%', meta: 3 },
            { id: 6, nome: 'Absenteísmo operadores Aloisio (%)', valor: '', unidade: '%', meta: 3 },
            { id: 7, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    }
];

// VARIÁVEIS GLOBAIS
let currentUser = null;
let currentSector = null;
let registrosDB = [];
let selectedFile = null;

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

function handleLogin() {
    const email = document.getElementById('emailInput').value;
    const senha = document.getElementById('senhaInput').value;
    if (!email || !senha) {
        alert('Por favor, preencha todos os campos!');
        return;
    }
    const usuario = usuariosDB.find(u => u.email === email && u.senha === senha);
    if (usuario) {
        currentUser = usuario;
        document.getElementById('userNameDisplay').textContent = usuario.nome;
        showSectorsScreen();
    } else {
        alert('Email ou senha inválidos!');
    }
}

function handleLogout() {
    currentUser = null;
    currentSector = null;
    document.getElementById('emailInput').value = '';
    document.getElementById('senhaInput').value = '';
    document.getElementById('senhaInput').type = 'password';
    showLoginScreen();
}

// ===== NAVEGAÇÃO DE TELAS =====
function hideAllScreens() {
    ['loginScreen', 'sectorsScreen', 'indicatorsScreen', 'cobliScreen'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
}

function showLoginScreen() {
    hideAllScreens();
    document.getElementById('loginScreen').classList.remove('hidden');
}

function showSectorsScreen() {
    loadSectors();
    updateHistoryDisplay();
    hideAllScreens();
    document.getElementById('sectorsScreen').classList.remove('hidden');
}

function showIndicatorsScreen() {
    hideAllScreens();
    document.getElementById('indicatorsScreen').classList.remove('hidden');
}

function backToSectors() {
    currentSector = null;
    hideAllScreens();
    const sectors = document.getElementById('sectorsScreen');
    if (sectors) sectors.classList.remove('hidden');
    loadSectors();
    updateHistoryDisplay();
}

// ===== FUNÇÕES COBLI =====
function openCobli() {
    hideAllScreens();
    const cobli = document.getElementById('cobliScreen');
    if (cobli) cobli.classList.remove('hidden');
}

// ===== CARREGAR SETORES =====
function loadSectors() {
    const grid = document.getElementById('sectorsGrid');
    grid.innerHTML = '';
    setores.forEach(setor => {
        const btn = document.createElement('button');
        btn.className = `sector-btn ${setor.classe}`;
        btn.innerHTML = `<h2>${setor.nome}</h2><p>${setor.indicadores.length} indicadores</p>`;
        btn.onclick = () => openSector(setor);
        grid.appendChild(btn);
    });
}

function openSector(setor) {
    currentSector = JSON.parse(JSON.stringify(setor));
    document.getElementById('sectorTitle').textContent = setor.nome;
    const form = document.getElementById('indicatorsForm');
    form.innerHTML = '';
    currentSector.indicadores.forEach(indicador => {
        const div = document.createElement('div');
        div.className = 'indicator-item';
        const isDateField = indicador.tipo === 'date' || indicador.unidade === 'date';
        let inputHtml = '';
        if (isDateField) {
            const valorBR = indicador.valor ? converterDataParaBR(indicador.valor) : '';
            inputHtml = `<input type="text" class="indicator-input" data-id="${indicador.id}" value="${valorBR}" placeholder="DD/MM/AAAA" maxlength="10" oninput="autoFormatarData(this)" onchange="updateIndicatorDate(${indicador.id}, this.value)" style="font-family: monospace; letter-spacing: 1px;">`;
        } else {
            inputHtml = `<input type="number" step="0.01" placeholder="Digite o valor" class="indicator-input" data-id="${indicador.id}" value="${indicador.valor}" onchange="updateIndicator(${indicador.id}, this.value)">`;
        }
        const metaHtml = isDateField ? '<div class="indicator-meta">Formato: DD/MM/AAAA</div>' : `<div class="indicator-meta">Meta: ${indicador.meta} ${indicador.unidade}</div>`;
        div.innerHTML = `<label class="indicator-label">${indicador.nome}</label>${metaHtml}${inputHtml}`;
        form.appendChild(div);
    });
    showIndicatorsScreen();
}

function updateIndicator(id, value) {
    const ind = currentSector.indicadores.find(i => i.id === id);
    if (ind) ind.valor = value;
}

function updateIndicatorDate(id, value) {
    const ind = currentSector.indicadores.find(i => i.id === id);
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
    const novoRegistro = {
        id: Date.now(),
        usuario: currentUser.nome,
        setor: currentSector.nome,
        timestamp: new Date().toLocaleString('pt-BR'),
        indicadores: currentSector.indicadores,
        status: 'Salvo Localmente'
    };
    registrosDB.unshift(novoRegistro);
    updateHistoryDisplay();
    alert('Dados salvos localmente com sucesso!');
}

function handleSendDB() {
    const novoRegistro = {
        id: Date.now(),
        usuario: currentUser.nome,
        setor: currentSector.nome,
        timestamp: new Date().toLocaleString('pt-BR'),
        indicadores: currentSector.indicadores,
        status: 'Enviado para DB'
    };
    registrosDB.unshift(novoRegistro);
    updateHistoryDisplay();
    alert('Dados enviados para banco de dados com sucesso!');
    backToSectors();
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

// ===== FUNÇÕES COBLI - UPLOAD =====
async function uploadFile() {
    if (!selectedFile) {
        alert('Selecione um arquivo Excel!');
        return;
    }
    document.getElementById('loadingCobli').classList.remove('hidden');
    document.getElementById('cobliResults').classList.add('hidden');
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        document.getElementById('loadingCobli').classList.add('hidden');
        if (data.success) {
            mostrarResultadosCobli(data);
        } else {
            alert(`Erro: ${data.error}`);
        }
    } catch (error) {
        document.getElementById('loadingCobli').classList.add('hidden');
        alert(`Erro: ${error.message}`);
    }
}

function mostrarResultadosCobli(data) {
    document.getElementById('cobliResults').classList.remove('hidden');
    const totalToneladas = data.analise_toneladas.reduce((sum, item) => sum + item.Total_Toneladas, 0);
    document.getElementById('totalViagens').textContent = data.total_viagens;
    document.getElementById('totalMotoristas').textContent = data.analise_toneladas.length;
    document.getElementById('totalToneladas').textContent = `${totalToneladas.toFixed(2)} TN`;
    preencherTabelaToneladas(data.analise_toneladas);
    preencherTabelaCarros(data.carros_por_motorista);
    preencherTabelaDetalhes(data.viagens_detalhes);
    renderizarGraficos(data.graficos);
}

function preencherTabelaToneladas(dados) {
    const tbody = document.getElementById('tabelaToneladas');
    tbody.innerHTML = '';
    dados.forEach(item => {
        tbody.innerHTML += `<tr><td>${item.Motorista}</td><td>${item.Total_Viagens}</td><td>${item.Total_Toneladas.toFixed(2)} TN</td></tr>`;
    });
}

function preencherTabelaCarros(dados) {
    const tbody = document.getElementById('tabelaCarros');
    tbody.innerHTML = '';
    dados.forEach(item => {
        tbody.innerHTML += `<tr><td>${item.Motorista}</td><td>${item.Carros_Utilizados}</td><td>${item.Total_Viagens}</td></tr>`;
    });
}

function preencherTabelaDetalhes(dados) {
    const tbody = document.getElementById('tabelaDetalhes');
    tbody.innerHTML = '';
    dados.forEach(item => {
        tbody.innerHTML += `<tr><td>${item['Motorista associado']}</td><td>${item.Placa}</td><td>${item.Data}</td><td>${item['Nome do local']}</td></tr>`;
    });
}

function renderizarGraficos(graficos) {
    Plotly.newPlot('grafico1', graficos.grafico1.data, graficos.grafico1.layout);
    Plotly.newPlot('grafico2', graficos.grafico2.data, graficos.grafico2.layout);
    Plotly.newPlot('grafico3', graficos.grafico3.data, graficos.grafico3.layout);
    Plotly.newPlot('grafico4', graficos.grafico4.data, graficos.grafico4.layout);
}

function showCobliTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));
    event.target.classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
}

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function() {
    showLoginScreen();
    const fileInput = document.getElementById('excelFile');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                selectedFile = file;
                document.getElementById('fileName').textContent = `Arquivo: ${file.name}`;
                document.getElementById('fileName').classList.remove('hidden');
                document.getElementById('uploadBtn').classList.remove('hidden');
            }
        });
    }
});