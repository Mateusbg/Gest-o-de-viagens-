"""
===========================================================
ANÁLISE DE VIAGENS (LAVRA → BRITADOR) - BACKEND FLASK
===========================================================

Autor: Mateus Barbosa
Data: 07/01/2026
Version: 3.1 (CORRIGIDO)
===========================================================
"""

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

@app.route('/upload', methods=['POST'])
def upload_file():
    """Processa upload do arquivo Excel"""
    try:
        print("[DEBUG] Recebendo requisição de upload")

        if 'file' not in request.files:
            print("[ERRO] Nenhum arquivo na requisição")
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            print("[ERRO] Nome de arquivo vazio")
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

        if not allowed_file(file.filename):
            print(f"[ERRO] Tipo de arquivo não permitido: {file.filename}")
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido. Use .xlsx ou .xls'}), 400

        # Salva o arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"[DEBUG] Arquivo salvo em: {filepath}")

        # Processa o arquivo
        resultado = processar_arquivo(filepath)

        if resultado['success']:
            # Gera gráficos
            print("[DEBUG] Gerando gráficos...")
            graficos = gerar_graficos(
                resultado['analise_toneladas'],
                resultado['agrupamento']
            )
            resultado['graficos'] = graficos
            print("[DEBUG] Retornando resultado com sucesso")
        else:
            print(f"[ERRO] Falha no processamento: {resultado.get('error')}")

        # Remove arquivo após processar
        try:
            os.remove(filepath)
            print("[DEBUG] Arquivo temporário removido")
        except Exception as e:
            print(f"[AVISO] Não foi possível remover arquivo: {e}")

        return jsonify(resultado), 200

    except Exception as e:
        print(f"[ERRO CRÍTICO] {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Erro no servidor: {str(e)}'
        }), 500
## if __name__ == '__main__':
   # print("=" * 70)
   # print("🚀 SERVIDOR FLASK INICIADO")
   # print("=" * 70)
   # print("📍 Acesse: http://127.0.0.1:5000")
   # print("🔧 Debug: ATIVO (sem reloader)")
   # print("=" * 70)
   # app.run(debug=True, port=5000, host='127.0.0.1', use_reloader=False)
 
app = app  # Exporte a aplicação Flask como 'app' para Vercel