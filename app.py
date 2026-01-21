"""
===========================================================
ANÁLISE DE VIAGENS (LAVRA → BRITADOR) - BACKEND FLASK
===========================================================

Autor: Mateus Barbosa
Data: 07/01/2026
Version: 3.1 (CORRIGIDO)
===========================================================
"""
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis do .env SEM depender do diretório em que o comando foi executado.
# (Quando roda via VSCode/serviço, o CWD pode ser diferente e o .env não é encontrado.)
_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_ROOT / ".env", override=False)
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import pandas as pd
import numpy as np
import plotly.express as px
import json
import traceback

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
    """Abre conexão com SQL Server usando variáveis de ambiente.
    Configure no Windows (PowerShell):
      $env:SQL_SERVER="NOME_DO_SERVIDOR"
      $env:SQL_DATABASE="NOME_DO_BANCO"
      $env:SQL_USER="usuario"
      $env:SQL_PASSWORD="senha"
      $env:SQL_DRIVER="ODBC Driver 18 for SQL Server"
    """
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("SQL_SERVER", "")
    database = os.getenv("SQL_DATABASE", "")
    user = os.getenv("SQL_USER", "")
    password = os.getenv("SQL_PASSWORD", "")
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "false").lower() in ("1","true","yes","y")

    # Driver 18 costuma exigir Encrypt; no SSMS você marcou "Certificado do Servidor de Confiança".
    # Mantemos configurável por env, mas com defaults seguros para ambiente corporativo.
    encrypt = os.getenv("SQL_ENCRYPT", "yes").lower() in ("1","true","yes","y")
    trust_cert = os.getenv("SQL_TRUST_CERT", "yes").lower() in ("1","true","yes","y")

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


def _get_or_create_setor(cur, setor_id, setor_nome):
    if setor_id:
        return int(setor_id)
    if not setor_nome:
        raise ValueError("setorId ou setorNome é obrigatório")
    cur.execute("SELECT TOP 1 ZSE_ID FROM ZSE WHERE ZSE_NOME = ?", setor_nome)
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute("INSERT INTO ZSE (ZSE_NOME, ZSE_ATIVO) VALUES (?, 1)", setor_nome)
    cur.execute("SELECT SCOPE_IDENTITY()")
    return int(cur.fetchone()[0])


def _get_or_create_funcionario(cur, funcionario_id, funcionario_email, funcionario_nome, setor_id=None, perfil=None):
    if funcionario_id:
        return int(funcionario_id)
    # email é o identificador mais estável
    if funcionario_email:
        cur.execute("SELECT TOP 1 ZFU_ID FROM ZFU WHERE ZFU_EMAIL = ?", funcionario_email)
        row = cur.fetchone()
        if row:
            return int(row[0])
    if not funcionario_nome and not funcionario_email:
        raise ValueError("funcionarioId ou funcionarioEmail/funcionarioNome é obrigatório")
    cur.execute(
        "INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_PERFIL, ZFU_ATIVO) VALUES (?, ?, ?, ?, 1)",
        funcionario_nome or funcionario_email,
        funcionario_email,
        setor_id,
        perfil,
    )
    cur.execute("SELECT SCOPE_IDENTITY()")
    return int(cur.fetchone()[0])


def _get_or_create_indicador(cur, indicador_id, setor_id, codigo, nome, tipo=None, unidade=None, meta=None):
    if indicador_id:
        return int(indicador_id)
    if not setor_id:
        raise ValueError("setorId é obrigatório para indicador")
    # código local por setor ajuda a manter estabilidade
    if codigo is None:
        raise ValueError("indicadorId ou indicadorCodigo é obrigatório")
    cur.execute(
        "SELECT TOP 1 ZIN_ID FROM ZIN WHERE ZIN_SETOR_ID = ? AND ZIN_CODIGO = ?",
        setor_id,
        str(codigo),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        "INSERT INTO ZIN (ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO) VALUES (?, ?, ?, ?, ?, ?, 1)",
        setor_id,
        str(codigo),
        nome,
        tipo,
        unidade,
        meta,
    )
    cur.execute("SELECT SCOPE_IDENTITY()")
    return int(cur.fetchone()[0])

def _rows_to_dicts(cursor, rows):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check simples (inclui teste de conexão opcional)."""
    test_db = request.args.get("db") == "1"
    if not test_db:
        return jsonify({"ok": True, "service": "indicadores"}), 200
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
        return jsonify({"ok": True, "db": True, "db_ok": int(row[0])}), 200
    except Exception as e:
        return jsonify({"ok": False, "db": False, "error": str(e)}), 500

@app.route('/api/setores', methods=['GET'])
def api_setores():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ZSE_ID, ZSE_NOME, ZSE_ATIVO
            FROM ZSE
            WHERE ZSE_ATIVO = 1
            ORDER BY ZSE_NOME
        """)
        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))

@app.route('/api/indicadores', methods=['GET'])
def api_indicadores():
    setor_id = request.args.get('setor_id', type=int)
    if not setor_id:
        return jsonify({"error": "setor_id é obrigatório"}), 400
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO
            FROM ZIN
            WHERE ZIN_SETOR_ID = ? AND ZIN_ATIVO = 1
            ORDER BY ZIN_ID
        """, setor_id)
        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))

@app.route('/api/valores', methods=['POST'])
def api_salvar_valores():
    """Salva valores (uso típico: líder/gestão)."""
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = payload.get("setorId")
    setor_nome = payload.get("setorNome")
    funcionario_id = payload.get("funcionarioId")
    funcionario_email = payload.get("funcionarioEmail")
    funcionario_nome = payload.get("funcionarioNome")
    funcionario_perfil = payload.get("funcionarioPerfil")
    periodo = payload.get("periodo")  # 'YYYY-MM-01' ou 'YYYY-MM'
    valores = payload.get("valores") or []

    if (not setor_id and not setor_nome) or (not funcionario_id and not (funcionario_email or funcionario_nome)) or not periodo or not isinstance(valores, list):
        return jsonify({"error": "Campos obrigatórios: setorId/setorNome, funcionarioId/funcionarioEmail, periodo, valores[]"}), 400

    # normaliza periodo para primeiro dia do mês
    try:
        if len(periodo) == 7:
            periodo_date = datetime.strptime(periodo + "-01", "%Y-%m-%d").date()
        else:
            periodo_date = datetime.strptime(periodo, "%Y-%m-%d").date()
        periodo_date = periodo_date.replace(day=1)
    except Exception:
        return jsonify({"error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    now = datetime.utcnow()

    with get_db_connection() as conn:
        cur = conn.cursor()
        setor_id_db = _get_or_create_setor(cur, setor_id, setor_nome)
        funcionario_id_db = _get_or_create_funcionario(
            cur,
            funcionario_id,
            funcionario_email,
            funcionario_nome,
            setor_id=setor_id_db,
            perfil=funcionario_perfil,
        )

        for item in valores:
            ind_id = item.get("indicadorId")
            ind_codigo = item.get("indicadorCodigo")
            ind_nome = item.get("indicadorNome")
            ind_tipo = item.get("tipo")
            ind_unidade = item.get("unidade")
            ind_meta = item.get("meta")
            valor = item.get("valor")

            if not ind_id and ind_codigo is None:
                continue

            ind_id_db = _get_or_create_indicador(
                cur,
                ind_id,
                setor_id_db,
                ind_codigo,
                ind_nome or f"Indicador {ind_codigo}",
                tipo=ind_tipo,
                unidade=ind_unidade,
                meta=ind_meta,
            )
            # upsert simples por indicador/setor/periodo
            cur.execute("""
                MERGE ZIV AS tgt
                USING (SELECT ? AS ZIV_INDICADOR_ID, ? AS ZIV_SETOR_ID, ? AS ZIV_PERIODO) AS src
                ON tgt.ZIV_INDICADOR_ID = src.ZIV_INDICADOR_ID AND tgt.ZIV_SETOR_ID = src.ZIV_SETOR_ID AND tgt.ZIV_PERIODO = src.ZIV_PERIODO
                WHEN MATCHED THEN
                    UPDATE SET ZIV_VALOR = ?, ZIV_ATUALIZADO_EM = ?, ZIV_FUNCIONARIO_ID = ?
                WHEN NOT MATCHED THEN
                    INSERT (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
            """, ind_id_db, setor_id_db, periodo_date, str(valor) if valor is not None else None, now, funcionario_id_db,
                 ind_id_db, setor_id_db, funcionario_id_db, periodo_date, str(valor) if valor is not None else None, now, now)
        conn.commit()

    return jsonify({"ok": True})

@app.route('/api/drafts', methods=['POST'])
def api_salvar_draft():
    """Salva rascunho (uso típico: usuário padrão)."""
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = payload.get("setorId")
    setor_nome = payload.get("setorNome")
    funcionario_id = payload.get("funcionarioId")
    funcionario_email = payload.get("funcionarioEmail")
    funcionario_nome = payload.get("funcionarioNome")
    funcionario_perfil = payload.get("funcionarioPerfil")
    periodo = payload.get("periodo")
    valores = payload.get("valores") or []

    if (not setor_id and not setor_nome) or (not funcionario_id and not (funcionario_email or funcionario_nome)) or not periodo or not isinstance(valores, list):
        return jsonify({"error": "Campos obrigatórios: setorId/setorNome, funcionarioId/funcionarioEmail, periodo, valores[]"}), 400

    try:
        if len(periodo) == 7:
            periodo_date = datetime.strptime(periodo + "-01", "%Y-%m-%d").date()
        else:
            periodo_date = datetime.strptime(periodo, "%Y-%m-%d").date()
        periodo_date = periodo_date.replace(day=1)
    except Exception:
        return jsonify({"error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    now = datetime.utcnow()

    with get_db_connection() as conn:
        cur = conn.cursor()
        setor_id_db = _get_or_create_setor(cur, setor_id, setor_nome)
        funcionario_id_db = _get_or_create_funcionario(
            cur,
            funcionario_id,
            funcionario_email,
            funcionario_nome,
            setor_id=setor_id_db,
            perfil=funcionario_perfil,
        )

        for item in valores:
            ind_id = item.get("indicadorId")
            ind_codigo = item.get("indicadorCodigo")
            ind_nome = item.get("indicadorNome")
            ind_tipo = item.get("tipo")
            ind_unidade = item.get("unidade")
            ind_meta = item.get("meta")
            valor = item.get("valor")

            if not ind_id and ind_codigo is None:
                continue

            ind_id_db = _get_or_create_indicador(
                cur,
                ind_id,
                setor_id_db,
                ind_codigo,
                ind_nome or f"Indicador {ind_codigo}",
                tipo=ind_tipo,
                unidade=ind_unidade,
                meta=ind_meta,
            )

            cur.execute(
                """
                INSERT INTO ZDR (ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID, ZDR_PERIODO, ZDR_VALOR, ZDR_CRIADO_EM)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ind_id_db,
                setor_id_db,
                funcionario_id_db,
                periodo_date,
                str(valor) if valor is not None else None,
                now,
            )
        conn.commit()

    return jsonify({"ok": True})

@app.route('/api/drafts', methods=['GET'])
def api_listar_drafts():
    setor_id = request.args.get('setor_id', type=int)
    periodo = request.args.get('periodo')
    if not setor_id:
        return jsonify({"error": "setor_id é obrigatório"}), 400

    periodo_date = None
    if periodo:
        try:
            if len(periodo) == 7:
                periodo_date = datetime.strptime(periodo + "-01", "%Y-%m-%d").date().replace(day=1)
            else:
                periodo_date = datetime.strptime(periodo, "%Y-%m-%d").date().replace(day=1)
        except Exception:
            return jsonify({"error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()
        if periodo_date:
            cur.execute("""
                SELECT ZDR_ID, ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID, ZDR_PERIODO, ZDR_VALOR, ZDR_CRIADO_EM
                FROM ZDR
                WHERE ZDR_SETOR_ID = ? AND ZDR_PERIODO = ?
                ORDER BY ZDR_CRIADO_EM DESC
            """, setor_id, periodo_date)
        else:
            cur.execute("""
                SELECT TOP 500 ZDR_ID, ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID, ZDR_PERIODO, ZDR_VALOR, ZDR_CRIADO_EM
                FROM ZDR
                WHERE ZDR_SETOR_ID = ?
                ORDER BY ZDR_CRIADO_EM DESC
            """, setor_id)
        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 SERVIDOR FLASK INICIADO")
    print("=" * 70)
    print("📍 Acesse: http://127.0.0.1:5000")
    print("🔧 Debug: ATIVO (sem reloader)")
    print("=" * 70)
    app.run(debug=True, port=5000, host='127.0.0.1', use_reloader=False)
 
## app = app  # Exporte a aplicação Flask como 'app' para Vercel