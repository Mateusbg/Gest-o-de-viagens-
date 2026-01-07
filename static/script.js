// ===== BASE DE DADOS =====
const usuariosDB = [
    { id: 1, email: 'admin', senha: '1120', nome: 'Administrador' },
    { id: 2, email: 'vendas', senha: '123456', nome: 'Gerente de Vendas' },
    { id: 3, email: 'operacao', senha: '123456', nome: 'Gerente de Operações' }
];

const setores = [
    {
        id: 1,
        nome: 'Ambiental',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Custo mensal Transpedra(pneus + combustivel)', valor: '', unidade: 'R$/ton', meta: 150000 },
            { id: 2, nome: 'Número de ocorrencias ambientais', valor: '', unidade: 'un', meta: 50 },
            { id: 3, nome: 'Mês', valor: '', unidade: 'date', meta: null, tipo: 'date' }
        ]
    },
    {
        id: 2,
        nome: 'Operações',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'Tempo Médio de Atendimento', valor: '', unidade: 'min', meta: 5 },
            { id: 2, nome: 'Taxa de Erro', valor: '', unidade: '%', meta: 2 },
            { id: 3, nome: 'Produtividade', valor: '', unidade: '%', meta: 95 },
            { id: 4, nome: 'Custo Operacional', valor: '', unidade: 'R$', meta: 50000 }
        ]
    },
    {
        id: 3,
        nome: 'Marketing',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Leads Gerados', valor: '', unidade: 'un', meta: 100 },
            { id: 2, nome: 'CTR (Click Through Rate)', valor: '', unidade: '%', meta: 8 },
            { id: 3, nome: 'ROI Campanhas', valor: '', unidade: '%', meta: 400 },
            { id: 4, nome: 'Custo por Lead', valor: '', unidade: 'R$', meta: 50 }
        ]
    },
    {
        id: 4,
        nome: 'RH',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: 'Turnover', valor: '', unidade: '%', meta: 5 },
            { id: 2, nome: 'Taxa de Absenteísmo', valor: '', unidade: '%', meta: 2 },
            { id: 3, nome: 'Satisfação Colaboradores', valor: '', unidade: '/10', meta: 8 },
            { id: 4, nome: 'Treinamentos Realizados', valor: '', unidade: 'un', meta: 20 }
        ]
    },
    {
        id: 5,
        nome: 'Financeiro',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Fluxo de Caixa', valor: '', unidade: 'R$', meta: 100000 },
            { id: 2, nome: 'Margem de Lucro', valor: '', unidade: '%', meta: 20 },
            { id: 3, nome: 'Contas a Pagar', valor: '', unidade: 'R$', meta: 30000 },
            { id: 4, nome: 'Contas a Receber', valor: '', unidade: 'R$', meta: 80000 }
        ]
    },
    {
        id: 6,
        nome: 'Posto Fiscal',
        classe: 'sector-green',
        indicadores: [
            { id: 1, nome: 'Tempo de Entrega', valor: '', unidade: 'dias', meta: 3 },
            { id: 2, nome: 'Custo de Transporte', valor: '', unidade: 'R$', meta: 20000 },
            { id: 3, nome: 'Índice de Devolução', valor: '', unidade: '%', meta: 1 },
            { id: 4, nome: 'Nível de Estoque', valor: '', unidade: 'un', meta: 5000 }
        ]
    },
    {
        id: 7,
        nome: 'TI',
        classe: 'sector-purple',
        indicadores: [
            { id: 1, nome: 'Tempo de Resolução de Incidentes', valor: '', unidade: 'horas', meta: 4 },
            { id: 2, nome: 'Uptime dos Sistemas', valor: '', unidade: '%', meta: 99.9 },
            { id: 3, nome: 'Satisfação dos Usuários', valor: '', unidade: '/10', meta: 9 },
            { id: 4, nome: 'Número de Incidentes', valor: '', unidade: 'un', meta: 10 }
        ]
    },
    {
        id: 8,
        nome: 'Balança',
        classe: 'sector-red',
        indicadores: [
            { id: 1, nome: 'NPS (Net Promoter Score)', valor: '', unidade: '/10', meta: 8 },
            { id: 2, nome: 'Tempo Médio de Resposta', valor: '', unidade: 'min', meta: 2 },
            { id: 3, nome: 'Taxa de Resolução na Primeira Chamada', valor: '', unidade: '%', meta: 85 },
            { id: 4, nome: 'Volume de Chamadas', valor: '', unidade: 'un', meta: 1000 }
        ]
    },
    {
        id: 9,
        nome: 'Compras',
        classe: 'sector-blue',
        indicadores: [
            { id: 1, nome: 'Custo por Envio', valor: '', unidade: 'R$', meta: 15 },
            { id: 2, nome: 'Taxa de Entrega no Prazo', valor: '', unidade: '%', meta: 98 },
            { id: 3, nome: 'Índice de Danos na Entrega', valor: '', unidade: '%', meta: 0.5 },
            { id: 4, nome: 'Eficiência de Roteirização', valor: '', unidade: '%', meta: 90 }
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