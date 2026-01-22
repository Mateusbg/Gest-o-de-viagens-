"""
===========================================================
ANÁLISE DE VIAGENS (LAVRA → BRITADOR) - BACKEND FLASK
===========================================================

Autor: Mateus Barbosa
Data: 07/01/2026
Version: 3.1 (CORRIGIDO + API INDICADORES ROBUSTA)
===========================================================
"""
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis do .env SEM depender do diretório em que o comando foi executado.
_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import pandas as pd
import json
import traceback

# IMPORTS QUE FALTAVAM (você usa np e px)
import numpy as np
import plotly.express as px

# AUTH / RBAC
from functools import wraps
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext


app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

# Criar pasta de uploads
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuração de toneladas por veículo
TONELADAS_POR_VEICULO = {
    'SK-01': 68,
    'SK-02': 68,
    'SK-03': 68,
    'SK-04': 68,
    'SK-05': 68,
}
TONELAGEM_PADRAO = 68


def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def processar_arquivo(arquivo_path):
    """Processa o arquivo Excel e retorna análise completa"""
    try:
        print(f"[DEBUG] Processando arquivo: {arquivo_path}")

        # Verifica se o arquivo existe
        if not os.path.exists(arquivo_path):
            return {'success': False, 'error': 'Arquivo não encontrado'}

        # Lê o Excel
        cobli_df = pd.read_excel(arquivo_path, header=3)
        print(f"[DEBUG] DataFrame lido com {len(cobli_df)} linhas")

        # Verifica se as colunas existem
        colunas_necessarias = [
            'Placa',
            'Motorista associado',
            'Data e horário de entrada no local',
            'Data e horário de saída no local',
            'Nome do local'
        ]

        colunas_faltando = [col for col in colunas_necessarias if col not in cobli_df.columns]
        if colunas_faltando:
            return {
                'success': False,
                'error': f'Colunas faltando no Excel: {", ".join(colunas_faltando)}'
            }

        # Seleciona colunas
        veiculos = cobli_df[colunas_necessarias].copy()

        # Converte datas
        veiculos['Data e horário de entrada no local'] = pd.to_datetime(
            veiculos['Data e horário de entrada no local'],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )

        veiculos['Data e horário de saída no local'] = pd.to_datetime(
            veiculos['Data e horário de saída no local'],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )

        # Remove linhas com datas inválidas
        veiculos = veiculos.dropna(subset=['Data e horário de entrada no local'])

        veiculos['Data'] = veiculos['Data e horário de entrada no local'].dt.date

        # Ordena dados
        veiculos_ordenados = veiculos.sort_values(
            ['Motorista associado', 'Placa', 'Data', 'Data e horário de entrada no local']
        ).reset_index(drop=True)

        # Classifica tipo de local
        veiculos_ordenados['Tipo_Local'] = veiculos_ordenados['Nome do local'].apply(
            lambda x: 1 if 'Lavra' in str(x)
            else (0 if 'britador' in str(x).lower() or 'Descarga' in str(x) else None)
        )

        # Cria colunas com dados da linha anterior
        veiculos_ordenados['Local_Anterior'] = veiculos_ordenados['Tipo_Local'].shift(1)
        veiculos_ordenados['Motorista_Anterior'] = veiculos_ordenados['Motorista associado'].shift(1)
        veiculos_ordenados['Placa_Anterior'] = veiculos_ordenados['Placa'].shift(1)
        veiculos_ordenados['Data_Anterior'] = veiculos_ordenados['Data'].shift(1)

        # Identifica viagens válidas
        viagem_valida = (
            (veiculos_ordenados['Local_Anterior'] == 1) &
            (veiculos_ordenados['Tipo_Local'] == 0) &
            (veiculos_ordenados['Motorista associado'] == veiculos_ordenados['Motorista_Anterior']) &
            (veiculos_ordenados['Placa'] == veiculos_ordenados['Placa_Anterior']) &
            (veiculos_ordenados['Data'] == veiculos_ordenados['Data_Anterior'])
        )

        veiculos_ordenados['Viagem_Valida'] = viagem_valida
        viagens_completas = veiculos_ordenados[veiculos_ordenados['Viagem_Valida']].copy()

        print(f"[DEBUG] Viagens válidas encontradas: {len(viagens_completas)}")

        if len(viagens_completas) == 0:
            return {
                'success': False,
                'error': 'Nenhuma viagem válida (Lavra → Britador) encontrada no arquivo'
            }

        # Calcula toneladas
        viagens_completas['Toneladas_Viagem'] = viagens_completas['Placa'].map(
            lambda x: TONELADAS_POR_VEICULO.get(x, TONELAGEM_PADRAO)
        )

        # Agrupa dados
        agrupamento = viagens_completas.groupby(['Motorista associado', 'Placa']).agg({
            'Viagem_Valida': 'count',
            'Toneladas_Viagem': 'first'
        }).reset_index()

        agrupamento.columns = ['Motorista', 'Placa', 'Num_Viagens', 'Toneladas_Por_Viagem']

        # Calcula total com NumPy
        viagens_array = np.array(agrupamento['Num_Viagens'])
        toneladas_array = np.array(agrupamento['Toneladas_Por_Viagem'])
        agrupamento['Total_Toneladas'] = np.multiply(viagens_array, toneladas_array)

        # Análise por motorista
        analise_toneladas = agrupamento.groupby('Motorista').agg({
            'Num_Viagens': 'sum',
            'Total_Toneladas': 'sum'
        }).reset_index()
        analise_toneladas.columns = ['Motorista', 'Total_Viagens', 'Total_Toneladas']
        analise_toneladas = analise_toneladas.sort_values('Total_Toneladas', ascending=False)

        # Carros por motorista
        carros_por_motorista = agrupamento.groupby('Motorista').agg({
            'Placa': lambda x: ', '.join(sorted(set(x))),
            'Num_Viagens': 'sum'
        }).reset_index()
        carros_por_motorista.columns = ['Motorista', 'Carros_Utilizados', 'Total_Viagens']

        # Converte Data para string (JSON serializable)
        viagens_detalhes = viagens_completas[['Motorista associado', 'Placa', 'Data', 'Nome do local']].head(100).copy()
        viagens_detalhes['Data'] = viagens_detalhes['Data'].astype(str)

        print("[DEBUG] Processamento concluído com sucesso")

        return {
            'success': True,
            'total_viagens': int(len(viagens_completas)),
            'analise_toneladas': analise_toneladas.to_dict('records'),
            'carros_por_motorista': carros_por_motorista.to_dict('records'),
            'agrupamento': agrupamento.to_dict('records'),
            'viagens_detalhes': viagens_detalhes.to_dict('records')
        }

    except Exception as e:
        print(f"[ERRO] {str(e)}")
        print(traceback.format_exc())
        return {'success': False, 'error': f'Erro ao processar arquivo: {str(e)}'}


def gerar_graficos(analise_toneladas, agrupamento):
    """Gera gráficos Plotly e retorna como JSON"""
    try:
        graficos = {}

        # Converte para DataFrame
        df_toneladas = pd.DataFrame(analise_toneladas)
        df_agrupamento = pd.DataFrame(agrupamento)

        # Gráfico 1: Barras - Total de Toneladas
        fig1 = px.bar(
            df_toneladas.head(15),
            x='Motorista',
            y='Total_Toneladas',
            title='Total de Toneladas Transportadas por Motorista (Top 15)',
            labels={'Total_Toneladas': 'Toneladas', 'Motorista': 'Motorista'},
            color='Total_Toneladas',
            color_continuous_scale='Blues'
        )
        fig1.update_layout(xaxis_tickangle=-45, height=500)
        graficos['grafico1'] = json.loads(fig1.to_json())

        # Gráfico 2: Pizza - Distribuição de Viagens
        fig2 = px.pie(
            df_toneladas.head(10),
            names='Motorista',
            values='Total_Viagens',
            title='Distribuição de Viagens - Top 10 Motoristas',
            hole=0.3
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        graficos['grafico2'] = json.loads(fig2.to_json())

        # Gráfico 3: Barras Agrupadas
        motoristas_top = df_toneladas.head(5)['Motorista'].values
        dados_filtrados = df_agrupamento[df_agrupamento['Motorista'].isin(motoristas_top)]

        fig3 = px.bar(
            dados_filtrados,
            x='Motorista',
            y='Num_Viagens',
            color='Placa',
            title='Viagens por Motorista e Veículo (Top 5 Motoristas)',
            labels={'Num_Viagens': 'Número de Viagens'},
            barmode='group'
        )
        fig3.update_layout(xaxis_tickangle=-45, height=500)
        graficos['grafico3'] = json.loads(fig3.to_json())

        # Gráfico 4: Barras Empilhadas
        fig4 = px.bar(
            dados_filtrados,
            x='Motorista',
            y='Total_Toneladas',
            color='Placa',
            title='Total de Toneladas por Motorista e Veículo (Top 5)',
            labels={'Total_Toneladas': 'Toneladas'},
            barmode='stack'
        )
        fig4.update_layout(xaxis_tickangle=-45, height=500)
        graficos['grafico4'] = json.loads(fig4.to_json())

        print("[DEBUG] Gráficos gerados com sucesso")
        return graficos

    except Exception as e:
        print(f"[ERRO] Erro ao gerar gráficos: {str(e)}")
        return {}


@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


# ===========================================================
# BANCO DE DADOS (SQL SERVER) - INDICADORES
# ===========================================================
import pyodbc
from datetime import datetime, date


def get_db_connection():
    """Abre conexão com SQL Server usando variáveis de ambiente."""
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("SQL_SERVER", "")
    database = os.getenv("SQL_DATABASE", "")
    user = os.getenv("SQL_USER", "")
    password = os.getenv("SQL_PASSWORD", "")
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "false").lower() in ("1", "true", "yes", "y")

    encrypt = os.getenv("SQL_ENCRYPT", "yes").lower() in ("1", "true", "yes", "y")
    trust_cert = os.getenv("SQL_TRUST_CERT", "yes").lower() in ("1", "true", "yes", "y")

    if not server or not database:
        raise RuntimeError("SQL_SERVER e SQL_DATABASE não configurados.")

    enc_part = "Encrypt=yes;" if encrypt else "Encrypt=no;"
    trust_part = "TrustServerCertificate=yes;" if trust_cert else "TrustServerCertificate=no;"

    if trusted:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            + enc_part + trust_part
        )
    else:
        if not user or not password:
            raise RuntimeError("SQL_USER e SQL_PASSWORD não configurados.")

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};PWD={password};"
            + enc_part + trust_part
        )

    return pyodbc.connect(conn_str)




# ===========================================================
# AUTH / RBAC (NÍVEIS 1..5)
# ===========================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_MAP = {
    1: "LEITOR",
    2: "EDITOR",
    3: "LIDER",
    4: "GESTAO",
    5: "ADM",
}

def _jwt_secret():
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET não configurado no .env")
    return secret

def _issue_token(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "nivel": int(user["nivel"]),
        "setor_id": int(user["setor_id"]) if user.get("setor_id") is not None else None,
        "nome": user.get("nome"),
        "email": user.get("email"),
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "12")))).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")

def _decode_token(token: str) -> dict:
    return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])

def _get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None

def get_current_user(optional: bool = False):
    token = _get_bearer_token()
    if not token:
        if optional:
            return None
        raise PermissionError("Token ausente")
    try:
        data = _decode_token(token)
        return {
            "id": int(data["sub"]),
            "nivel": int(data["nivel"]),
            "setor_id": data.get("setor_id"),
            "nome": data.get("nome"),
            "email": data.get("email"),
        }
    except Exception:
        if optional:
            return None
        raise PermissionError("Token inválido/expirado")

def require_level(min_level: int):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                user = get_current_user(optional=False)
            except PermissionError as e:
                return jsonify({"ok": False, "error": str(e)}), 401

            if int(user["nivel"]) < int(min_level):
                return jsonify({"ok": False, "error": f"Permissão insuficiente (requer nível >= {min_level})"}), 403

            request.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return deco

def _is_gestao_or_admin(user: dict) -> bool:
    return int(user["nivel"]) >= 4

def _enforce_setor_access(user: dict, setor_id: int):
    if _is_gestao_or_admin(user):
        return
    if user.get("setor_id") is None:
        raise PermissionError("Usuário sem setor associado")
    if int(user["setor_id"]) != int(setor_id):
        raise PermissionError("Acesso negado a este setor")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def _fetch_user_by_email(cur, email: str):
    cur.execute(
        "SELECT ZFU_ID, ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO "
        "FROM ZFU WHERE ZFU_EMAIL = ?",
        (email,)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "nome": row[1],
        "email": row[2],
        "setor_id": row[3],
        "nivel": int(row[4] or 1),
        "senha_hash": row[5],
        "ativo": bool(row[6]),
    }

def ensure_seed_admin():
    """Cria um ADM inicial se não existir nenhum usuário com nível 5."""
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@empresa.com")
    admin_pass = os.getenv("SEED_ADMIN_PASSWORD", "1234")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM ZFU WHERE ISNULL(ZFU_NIVEL,1) = 5 AND ZFU_ATIVO = 1")
        has_admin = cur.fetchone()[0]
        if has_admin:
            return
        cur.execute(
            "INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO, ZFU_CRIADO_EM) "
            "VALUES (?, ?, NULL, 5, ?, 1, SYSUTCDATETIME())",
            ("Administrador", admin_email, hash_password(admin_pass))
        )
        conn.commit()

def _get_or_create_setor(cur, setor_id, setor_nome):
    # 1) Se veio ID e existe
    if setor_id is not None:
        cur.execute("SELECT ZSE_ID FROM ZSE WHERE ZSE_ID = ?", (setor_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])

    # 2) precisa de nome
    if not setor_nome or not str(setor_nome).strip():
        raise ValueError("setor_nome não informado (não foi possível criar/achar o setor).")

    setor_nome = str(setor_nome).strip()

    # 3) tenta achar por nome
    cur.execute("SELECT ZSE_ID FROM ZSE WHERE ZSE_NOME = ?", (setor_nome,))
    row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0])

    # 4) insere retornando ID
    cur.execute(
        "INSERT INTO ZSE (ZSE_NOME) OUTPUT INSERTED.ZSE_ID VALUES (?)",
        (setor_nome,)
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        raise RuntimeError("Falha ao inserir setor (OUTPUT INSERTED.ZSE_ID não retornou valor).")
    return int(row[0])



def _get_or_create_funcionario(cur, funcionario_id, funcionario_email, funcionario_nome, setor_id=None, perfil=None):
    if funcionario_id:
        return int(funcionario_id)

    if funcionario_email:
        cur.execute("SELECT TOP 1 ZFU_ID FROM ZFU WHERE ZFU_EMAIL = ?", funcionario_email)
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])

    if not funcionario_nome and not funcionario_email:
        raise ValueError("funcionarioId ou funcionarioEmail/funcionarioNome é obrigatório")

    cur.execute(
        """
        INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_ATIVO)
        OUTPUT INSERTED.ZFU_ID
        VALUES (?, ?, ?, 1)
        """,
        funcionario_nome or funcionario_email,
        funcionario_email,
        setor_id
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        raise RuntimeError("Falha ao inserir funcionário (OUTPUT INSERTED.ZFU_ID não retornou valor).")
    return int(row[0])




def _get_or_create_indicador(cur, indicador_id, setor_id, codigo, nome, tipo=None, unidade=None, meta=None):
    if indicador_id:
        return int(indicador_id)

    if not setor_id:
        raise ValueError("setorId é obrigatório para indicador")

    if codigo is None:
        raise ValueError("indicadorId ou indicadorCodigo é obrigatório")

    codigo = str(codigo)

    cur.execute(
        "SELECT TOP 1 ZIN_ID FROM ZIN WHERE ZIN_SETOR_ID = ? AND ZIN_CODIGO = ?",
        setor_id,
        codigo
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0])

    cur.execute(
        """
        INSERT INTO ZIN (ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO)
        OUTPUT INSERTED.ZIN_ID
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        setor_id,
        codigo,
        nome or f"Indicador {codigo}",
        tipo,
        unidade,
        meta
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        raise RuntimeError("Falha ao inserir indicador (OUTPUT INSERTED.ZIN_ID não retornou valor).")
    return int(row[0])

@app.route('/api/setores', methods=['GET'])
def api_setores():
    user = get_current_user(optional=True)

    with get_db_connection() as conn:
        cur = conn.cursor()

        if user and not _is_gestao_or_admin(user):
            if user.get("setor_id") is None:
                return jsonify([])

            cur.execute(
                "SELECT ZSE_ID, ZSE_NOME, ZSE_ATIVO FROM ZSE WHERE ZSE_ATIVO = 1 AND ZSE_ID = ? ORDER BY ZSE_NOME",
                (int(user["setor_id"]),)
            )
        else:
            cur.execute(
                "SELECT ZSE_ID, ZSE_NOME, ZSE_ATIVO FROM ZSE WHERE ZSE_ATIVO = 1 ORDER BY ZSE_NOME"
            )

        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))


@app.route('/api/indicadores', methods=['GET'])
def api_indicadores():
    user = get_current_user(optional=True)

    setor_id = request.args.get("setorId") or request.args.get("setor_id")
    with get_db_connection() as conn:
        cur = conn.cursor()

        if setor_id:
            setor_id_int = int(setor_id)
            if user and not _is_gestao_or_admin(user):
                try:
                    _enforce_setor_access(user, setor_id_int)
                except PermissionError as e:
                    return jsonify({"ok": False, "error": str(e)}), 403

            cur.execute(
                "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO "
                "FROM ZIN WHERE ZIN_ATIVO = 1 AND ZIN_SETOR_ID = ? ORDER BY ZIN_CODIGO",
                (setor_id_int,)
            )
        else:
            if user and not _is_gestao_or_admin(user):
                return jsonify({"ok": False, "error": "Informe setorId/setor_id"}), 400

            cur.execute(
                "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO "
                "FROM ZIN WHERE ZIN_ATIVO = 1 ORDER BY ZIN_SETOR_ID, ZIN_CODIGO"
            )

        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))

def _pick(d: dict, *keys, default=None):
    """
    Pega o primeiro valor não-nulo do dict para as chaves informadas.
    Ex: _pick(payload, "setorId", "setor_id", "setorID")
    """
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return default


# ✅ SUBSTITUÍDO: /api/valores robusto
@app.route('/api/valores', methods=['POST'])
def api_salvar_valores():
    user = get_current_user(optional=False)
    if int(user['nivel']) < 3:
        return jsonify({'ok': False, 'error': 'Somente LÍDER (nível 3+) pode salvar definitivo no banco'}), 403
    payload = request.get_json(force=True, silent=True) or {}

    setor_id = _pick(payload, "setorId", "setor_id", "setorID")
    setor_nome = _pick(payload, "setorNome", "setor_nome", "setor", "nomeSetor", "nome_setor")

    funcionario_id = _pick(payload, "funcionarioId", "funcionario_id", "usuarioId", "usuario_id")
    funcionario_email = _pick(payload, "funcionarioEmail", "funcionario_email", "email")
    funcionario_nome = _pick(payload, "funcionarioNome", "funcionario_nome", "nome", "usuarioNome", "usuario_nome")
    funcionario_perfil = _pick(payload, "funcionarioPerfil", "funcionario_perfil", "perfil", "role")

    periodo = _pick(payload, "periodo", "competencia", "mes", "period")
    valores = _pick(payload, "valores", "itens", "items", default=[]) or []

    if (not setor_id and not setor_nome):
        return jsonify({"ok": False, "error": "Envie setorId/setor_id ou setorNome/setor_nome"}), 400

    if (not funcionario_id and not (funcionario_email or funcionario_nome)):
        return jsonify({"ok": False, "error": "Envie funcionarioId/funcionario_id ou funcionarioEmail/email ou funcionarioNome/nome"}), 400

    if not periodo:
        return jsonify({"ok": False, "error": "Envie periodo (YYYY-MM ou YYYY-MM-01)"}), 400

    if not isinstance(valores, list):
        return jsonify({"ok": False, "error": "valores precisa ser uma lista"}), 400

    try:
        p = str(periodo)
        if len(p) == 7:
            periodo_date = datetime.strptime(p + "-01", "%Y-%m-%d").date()
        else:
            periodo_date = datetime.strptime(p, "%Y-%m-%d").date()
        periodo_date = periodo_date.replace(day=1)
    except Exception:
        return jsonify({"ok": False, "error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    now = datetime.utcnow()

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            setor_id_db = _get_or_create_setor(cur, setor_id, setor_nome)

            # RBAC: valida acesso ao setor
            try:
                _enforce_setor_access(user, int(setor_id_db))
            except PermissionError as e:
                return jsonify({'ok': False, 'error': str(e)}), 403

            funcionario_id_db = _get_or_create_funcionario(
                cur, funcionario_id, funcionario_email, funcionario_nome,
                setor_id=setor_id_db, perfil=funcionario_perfil
            )

            for item in valores:
                if not isinstance(item, dict):
                    continue

                ind_id = _pick(item, "indicadorId", "indicador_id", "id")
                ind_codigo = _pick(item, "indicadorCodigo", "indicador_codigo", "codigo", "code")
                ind_nome = _pick(item, "indicadorNome", "indicador_nome", "nome", "name")
                ind_tipo = _pick(item, "tipo", "type")
                ind_unidade = _pick(item, "unidade", "unit")
                ind_meta = _pick(item, "meta", "target")
                valor = _pick(item, "valor", "value")

                if not ind_id and ind_codigo is None:
                    continue

                ind_id_db = _get_or_create_indicador(
                    cur, ind_id, setor_id_db, ind_codigo,
                    ind_nome or f"Indicador {ind_codigo}",
                    tipo=ind_tipo, unidade=ind_unidade, meta=ind_meta
                )

                cur.execute("""
                    MERGE ZIV AS tgt
                    USING (SELECT ? AS ZIV_INDICADOR_ID, ? AS ZIV_SETOR_ID, ? AS ZIV_PERIODO) AS src
                    ON tgt.ZIV_INDICADOR_ID = src.ZIV_INDICADOR_ID AND tgt.ZIV_SETOR_ID = src.ZIV_SETOR_ID AND tgt.ZIV_PERIODO = src.ZIV_PERIODO
                    WHEN MATCHED THEN
                        UPDATE SET ZIV_VALOR = ?, ZIV_ATUALIZADO_EM = ?, ZIV_FUNCIONARIO_ID = ?
                    WHEN NOT MATCHED THEN
                        INSERT (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                ind_id_db, setor_id_db, periodo_date,
                str(valor) if valor is not None else None, now, funcionario_id_db,
                ind_id_db, setor_id_db, funcionario_id_db, periodo_date,
                str(valor) if valor is not None else None, now, now)

            conn.commit()

        return jsonify({"ok": True})

    except Exception as e:
        print("[ERRO] /api/valores:", str(e))
        print(traceback.format_exc())
        return jsonify({"ok": False, "error": str(e)}), 500


# ✅ SUBSTITUÍDO: /api/drafts POST robusto
@app.route('/api/drafts', methods=['POST'])
def api_salvar_draft():
    user = get_current_user(optional=False)
    if int(user['nivel']) < 2:
        return jsonify({'ok': False, 'error': 'Somente nível 2+ pode editar/enviar rascunhos'}), 403
    payload = request.get_json(force=True, silent=True) or {}

    setor_id = _pick(payload, "setorId", "setor_id", "setorID")
    setor_nome = _pick(payload, "setorNome", "setor_nome", "setor", "nomeSetor", "nome_setor")

    funcionario_id = _pick(payload, "funcionarioId", "funcionario_id", "usuarioId", "usuario_id")
    funcionario_email = _pick(payload, "funcionarioEmail", "funcionario_email", "email")
    funcionario_nome = _pick(payload, "funcionarioNome", "funcionario_nome", "nome", "usuarioNome", "usuario_nome")
    funcionario_perfil = _pick(payload, "funcionarioPerfil", "funcionario_perfil", "perfil", "role")

    periodo = _pick(payload, "periodo", "competencia", "mes", "period")
    valores = _pick(payload, "valores", "itens", "items", default=[]) or []

    if (not setor_id and not setor_nome):
        return jsonify({"ok": False, "error": "Envie setorId/setor_id ou setorNome/setor_nome"}), 400

    if (not funcionario_id and not (funcionario_email or funcionario_nome)):
        return jsonify({"ok": False, "error": "Envie funcionarioId/funcionario_id ou funcionarioEmail/email ou funcionarioNome/nome"}), 400

    if not periodo:
        return jsonify({"ok": False, "error": "Envie periodo (YYYY-MM ou YYYY-MM-01)"}), 400

    if not isinstance(valores, list):
        return jsonify({"ok": False, "error": "valores precisa ser uma lista"}), 400

    try:
        p = str(periodo)
        if len(p) == 7:
            periodo_date = datetime.strptime(p + "-01", "%Y-%m-%d").date()
        else:
            periodo_date = datetime.strptime(p, "%Y-%m-%d").date()
        periodo_date = periodo_date.replace(day=1)
    except Exception:
        return jsonify({"ok": False, "error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    now = datetime.utcnow()

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            setor_id_db = _get_or_create_setor(cur, setor_id, setor_nome)

            # RBAC: valida acesso ao setor
            try:
                _enforce_setor_access(user, int(setor_id_db))
            except PermissionError as e:
                return jsonify({'ok': False, 'error': str(e)}), 403

            funcionario_id_db = _get_or_create_funcionario(
                cur, funcionario_id, funcionario_email, funcionario_nome,
                setor_id=setor_id_db, perfil=funcionario_perfil
            )

            for item in valores:
                if not isinstance(item, dict):
                    continue

                ind_id = _pick(item, "indicadorId", "indicador_id", "id")
                ind_codigo = _pick(item, "indicadorCodigo", "indicador_codigo", "codigo", "code")
                ind_nome = _pick(item, "indicadorNome", "indicador_nome", "nome", "name")
                ind_tipo = _pick(item, "tipo", "type")
                ind_unidade = _pick(item, "unidade", "unit")
                ind_meta = _pick(item, "meta", "target")
                valor = _pick(item, "valor", "value")

                if not ind_id and ind_codigo is None:
                    continue

                ind_id_db = _get_or_create_indicador(
                    cur, ind_id, setor_id_db, ind_codigo,
                    ind_nome or f"Indicador {ind_codigo}",
                    tipo=ind_tipo, unidade=ind_unidade, meta=ind_meta
                )

                cur.execute(
                    """
                    INSERT INTO ZDR (ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID, ZDR_PERIODO, ZDR_VALOR, ZDR_CRIADO_EM)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ind_id_db, setor_id_db, funcionario_id_db, periodo_date,
                    str(valor) if valor is not None else None, now
                )

            conn.commit()

        return jsonify({"ok": True})

    except Exception as e:
        print("[ERRO] /api/drafts:", str(e))
        print(traceback.format_exc())
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/drafts', methods=['GET'])
@require_level(2)
def api_listar_drafts():
    user = request.current_user

    setor_id = request.args.get("setorId") or request.args.get("setor_id")
    periodo = request.args.get("periodo")

    with get_db_connection() as conn:
        cur = conn.cursor()

        where = ["1=1"]
        params = []

        if setor_id:
            where.append("ZDR_SETOR_ID = ?")
            params.append(int(setor_id))

        if periodo:
            p = str(periodo)
            if len(p) == 7:
                p = p + "-01"
            where.append("ZDR_PERIODO = ?")
            params.append(p)

        if not _is_gestao_or_admin(user):
            if int(user["nivel"]) == 2:
                where.append("ZDR_FUNCIONARIO_ID = ?")
                params.append(int(user["id"]))
            else:
                if user.get("setor_id") is not None:
                    where.append("ZDR_SETOR_ID = ?")
                    params.append(int(user["setor_id"]))
                else:
                    where.append("1=0")

        sql = f"""
            SELECT
                ZDR_ID, ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID,
                ZDR_PERIODO, ZDR_VALOR, ZDR_STATUS,
                ZDR_CRIADO_EM, ZDR_ENVIADO_EM, ZDR_APROVADO_EM, ZDR_APROVADO_POR
            FROM ZDR
            WHERE {' AND '.join(where)}
            ORDER BY ZDR_CRIADO_EM DESC
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 SERVIDOR FLASK INICIADO")
    print("=" * 70)
    print("📍 Acesse: http://127.0.0.1:5000")
    print("🔧 Debug: ATIVO (sem reloader)")
    print("=" * 70)
    app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)


# ===========================================================
# NOVAS ROTAS: LOGIN / USUÁRIOS / INDICADORES / APROVAÇÃO
# ===========================================================

@app.before_request
def _seed_admin_once():
    try:
        ensure_seed_admin()
    except Exception:
        pass


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    payload = request.get_json(force=True, silent=True) or {}
    email = (payload.get("email") or "").strip()
    senha = payload.get("senha") or payload.get("password") or ""

    if not email or not senha:
        return jsonify({"ok": False, "error": "Informe email e senha"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            user = _fetch_user_by_email(cur, email)
            if not user or not user["ativo"]:
                return jsonify({"ok": False, "error": "Usuário/senha inválidos"}), 401
            if not user.get("senha_hash") or not verify_password(senha, user["senha_hash"]):
                return jsonify({"ok": False, "error": "Usuário/senha inválidos"}), 401

            token = _issue_token(user)
            return jsonify({
                "ok": True,
                "token": token,
                "user": {
                    "id": user["id"],
                    "nome": user["nome"],
                    "email": user["email"],
                    "setor_id": user["setor_id"],
                    "nivel": user["nivel"],
                    "perfil": ROLE_MAP.get(user["nivel"], str(user["nivel"]))
                }
            })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/users", methods=["POST"])
@require_level(4)
def api_create_user():
    admin = request.current_user
    payload = request.get_json(force=True, silent=True) or {}

    nome = (payload.get("nome") or "").strip()
    email = (payload.get("email") or "").strip()
    senha = payload.get("senha") or payload.get("password") or "1234"
    setor_id = payload.get("setor_id") or payload.get("setorId")
    nivel = int(payload.get("nivel") or 1)

    if not nome or not email:
        return jsonify({"ok": False, "error": "Informe nome e email"}), 400

    if int(admin["nivel"]) < 5 and nivel >= int(admin["nivel"]):
        return jsonify({"ok": False, "error": "Você só pode criar usuários abaixo do seu nível"}), 403

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM ZFU WHERE ZFU_EMAIL = ?", (email,))
            if cur.fetchone():
                return jsonify({"ok": False, "error": "Email já cadastrado"}), 409

            cur.execute(
                "INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO, ZFU_CRIADO_EM) "
                "VALUES (?, ?, ?, ?, ?, 1, SYSUTCDATETIME())",
                (nome, email, setor_id, nivel, hash_password(senha))
            )
            conn.commit()
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/users/<int:user_id>/reset-password", methods=["POST"])
@require_level(4)
def api_reset_password(user_id: int):
    admin = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    new_pass = payload.get("senha") or payload.get("password") or "1234"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute("SELECT ZFU_NIVEL FROM ZFU WHERE ZFU_ID = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"ok": False, "error": "Usuário não encontrado"}), 404
            target_level = int(row[0] or 1)

            if int(admin["nivel"]) < 5 and target_level >= int(admin["nivel"]):
                return jsonify({"ok": False, "error": "Você não pode redefinir senha de usuário do mesmo nível ou acima"}), 403

            cur.execute(
                "UPDATE ZFU SET ZFU_SENHA_HASH = ?, ZFU_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZFU_ID = ?",
                (hash_password(new_pass), user_id)
            )
            conn.commit()
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/indicadores", methods=["POST"])
@require_level(4)
def api_create_indicador():
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = int(payload.get("setor_id") or payload.get("setorId") or 0)
    codigo = (payload.get("codigo") or "").strip()
    nome = (payload.get("nome") or "").strip()
    tipo = payload.get("tipo")
    unidade = payload.get("unidade")
    meta = payload.get("meta")

    if not setor_id or not codigo or not nome:
        return jsonify({"ok": False, "error": "Informe setor_id, codigo e nome"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO ZIN (ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_CRIADO_EM) "
                "VALUES (?, ?, ?, ?, ?, ?, 1, SYSUTCDATETIME())",
                (setor_id, codigo, nome, tipo, unidade, meta)
            )
            conn.commit()
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/indicadores/<int:indicador_id>", methods=["PUT"])
@require_level(4)
def api_update_indicador(indicador_id: int):
    payload = request.get_json(force=True, silent=True) or {}
    fields = []
    params = []

    for col, key in [
        ("ZIN_NOME", "nome"),
        ("ZIN_TIPO", "tipo"),
        ("ZIN_UNIDADE", "unidade"),
        ("ZIN_META", "meta"),
        ("ZIN_ATIVO", "ativo"),
    ]:
        if key in payload:
            fields.append(f"{col} = ?")
            params.append(payload[key])

    if not fields:
        return jsonify({"ok": False, "error": "Nada para atualizar"}), 400

    params.append(indicador_id)

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE ZIN SET {', '.join(fields)}, ZIN_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZIN_ID = ?", params)
            conn.commit()
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/drafts/submit", methods=["POST"])
@require_level(2)
def api_submit_drafts():
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = payload.get("setor_id") or payload.get("setorId")
    periodo = payload.get("periodo")
    if not setor_id or not periodo:
        return jsonify({"ok": False, "error": "Informe setor_id e periodo"}), 400

    setor_id = int(setor_id)

    try:
        _enforce_setor_access(user, setor_id)
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403

    p = str(periodo)
    if len(p) == 7:
        p = p + "-01"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            where = "ZDR_SETOR_ID = ? AND ZDR_PERIODO = ? AND ZDR_STATUS IN ('DRAFT','REJECTED')"
            params = [setor_id, p]
            if int(user["nivel"]) == 2:
                where += " AND ZDR_FUNCIONARIO_ID = ?"
                params.append(int(user["id"]))

            cur.execute(f"UPDATE ZDR SET ZDR_STATUS='PENDING', ZDR_ENVIADO_EM = SYSUTCDATETIME() WHERE {where}", params)

            conn.commit()
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/drafts/approve", methods=["POST"])
@require_level(3)
def api_approve_drafts():
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = int(payload.get("setor_id") or payload.get("setorId") or 0)
    periodo = payload.get("periodo")

    if not setor_id or not periodo:
        return jsonify({"ok": False, "error": "Informe setor_id e periodo"}), 400

    try:
        _enforce_setor_access(user, setor_id)
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403

    p = str(periodo)
    if len(p) == 7:
        p = p + "-01"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                "SELECT ZDR_INDICADOR_ID, ZDR_VALOR, ZDR_FUNCIONARIO_ID "
                "FROM ZDR WHERE ZDR_SETOR_ID = ? AND ZDR_PERIODO = ? AND ZDR_STATUS = 'PENDING'",
                (setor_id, p)
            )
            items = cur.fetchall()

            if not items:
                return jsonify({"ok": False, "error": "Não há rascunhos PENDING para aprovar"}), 400

            for ind_id, valor, func_id in items:
                cur.execute(
                    "SELECT ZIV_ID FROM ZIV WHERE ZIV_INDICADOR_ID = ? AND ZIV_SETOR_ID = ? AND ZIV_PERIODO = ?",
                    (ind_id, setor_id, p)
                )
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "UPDATE ZIV SET ZIV_VALOR = ?, ZIV_FUNCIONARIO_ID = ?, ZIV_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZIV_ID = ?",
                        (valor, func_id, row[0])
                    )
                else:
                    cur.execute(
                        "INSERT INTO ZIV (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM) "
                        "VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME(), SYSUTCDATETIME())",
                        (ind_id, setor_id, func_id, p, valor)
                    )

            cur.execute(
                "UPDATE ZDR SET ZDR_STATUS='APPROVED', ZDR_APROVADO_EM = SYSUTCDATETIME(), ZDR_APROVADO_POR = ? "
                "WHERE ZDR_SETOR_ID = ? AND ZDR_PERIODO = ? AND ZDR_STATUS = 'PENDING'",
                (int(user["id"]), setor_id, p)
            )

            conn.commit()
            return jsonify({"ok": True, "aprovados": len(items)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/valores", methods=["GET"])
@require_level(1)
def api_listar_valores():
    user = request.current_user
    setor_id = request.args.get("setorId") or request.args.get("setor_id")
    periodo = request.args.get("periodo")

    if not setor_id or not periodo:
        return jsonify({"ok": False, "error": "Informe setor_id e periodo"}), 400

    setor_id = int(setor_id)
    try:
        _enforce_setor_access(user, setor_id)
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403

    p = str(periodo)
    if len(p) == 7:
        p = p + "-01"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ZIV_ID, ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM "
                "FROM ZIV WHERE ZIV_SETOR_ID = ? AND ZIV_PERIODO = ? ORDER BY ZIV_INDICADOR_ID",
                (setor_id, p)
            )
            rows = cur.fetchall()
            return jsonify(_rows_to_dicts(cur, rows))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
