"""
===========================================================
ANÁLISE DE VIAGENS (LAVRA → BRITADOR) COM GRÁFICOS
===========================================================

Este programa:
- Lê um arquivo Excel exportado do sistema Cobli
- Identifica viagens válidas (Lavra → Britador)
- Calcula toneladas transportadas por motorista usando NumPy
- Gera gráficos interativos com Plotly
- Mostra quais carros cada motorista trabalhou

Autor: Mateus barbosa
Data: 06/01/2026
Version: 2.0
===========================================================
"""

# =========================
# IMPORTAÇÕES
# =========================
import numpy as np                 # Cálculos numéricos
import plotly.express as px        # Visualização de dados (gráficos interativos)
import plotly.graph_objects as go  # Gráficos personalizados
import pandas as pd                # Manipulação de dados (Excel, DataFrame)
import tkinter as tk               # Interface gráfica
from tkinter import filedialog, messagebox  # Diálogos de arquivo e mensagens
from tkinter import ttk            # Componentes visuais modernos do Tkinter


# =========================
# CONFIGURAÇÃO DE TONELADAS POR VEÍCULO
# =========================
# Dicionário com capacidade de carga de cada placa
TONELADAS_POR_VEICULO = {
    'SK-01': 68,
    'SK-02': 68,
    'SK-03': 70,
    'SK-04': 70,
    'SK-05': 65,
    # Adicione mais placas conforme necessário
}

# Tonelagem padrão caso a placa não esteja no dicionário
TONELAGEM_PADRAO = 68


# =========================
# PROCESSAMENTO DO ARQUIVO
# =========================

def processar_arquivo(arquivo_excel):
    """
    Lê o arquivo Excel e identifica viagens válidas.
    Calcula toneladas transportadas usando NumPy.
    
    Uma viagem válida é definida como:
    - Saída de um local contendo "Lavra"
    - Entrada em um local contendo "Britador" ou "Descarga"
    - Mesmo motorista
    - Mesmo veículo (placa)
    - Mesma data
    
    Parâmetro:
        arquivo_excel (str): caminho do arquivo Excel
    
    Retorno:
        contagem_por_motorista (DataFrame): total de viagens por motorista
        viagens_completas (DataFrame): detalhes das viagens válidas
        total_viagens (int): quantidade total de viagens válidas
        analise_toneladas (DataFrame): análise de toneladas por motorista
        carros_por_motorista (DataFrame): carros utilizados por cada motorista
    """
    try:
        # Lê o Excel considerando a linha 4 como cabeçalho (header=3)
        cobli_df = pd.read_excel(arquivo_excel, header=3)

        # Seleciona apenas as colunas necessárias
        veiculos = cobli_df[
            [
                'Placa',
                'Motorista associado',
                'Data e horário de entrada no local',
                'Data e horário de saída no local',
                'Nome do local'
            ]
        ]

        # Converte colunas de data/hora para datetime
        veiculos['Data e horário de entrada no local'] = pd.to_datetime(
            veiculos['Data e horário de entrada no local'],
            format='mixed',
            dayfirst=True
        )

        veiculos['Data e horário de saída no local'] = pd.to_datetime(
            veiculos['Data e horário de saída no local'],
            format='mixed',
            dayfirst=True
        )

        # Cria uma coluna apenas com a data (sem horário)
        veiculos['Data'] = veiculos['Data e horário de entrada no local'].dt.date

        # Ordena os dados para manter a sequência correta das viagens
        veiculos_ordenados = veiculos.sort_values(
            ['Motorista associado', 'Placa', 'Data', 'Data e horário de entrada no local']
        ).reset_index(drop=True)

        # Classifica o tipo de local
        veiculos_ordenados['Tipo_Local'] = veiculos_ordenados['Nome do local'].apply(
            lambda x: 1 if 'Lavra' in str(x)
            else (0 if 'britador' in str(x).lower() or 'Descarga' in str(x) else None)
        )

        # Cria colunas com os dados da linha anterior
        veiculos_ordenados['Local_Anterior'] = veiculos_ordenados['Tipo_Local'].shift(1)
        veiculos_ordenados['Motorista_Anterior'] = veiculos_ordenados['Motorista associado'].shift(1)
        veiculos_ordenados['Placa_Anterior'] = veiculos_ordenados['Placa'].shift(1)
        veiculos_ordenados['Data_Anterior'] = veiculos_ordenados['Data'].shift(1)

        # Regra para identificar viagem válida
        viagem_valida = (
            (veiculos_ordenados['Local_Anterior'] == 1) &
            (veiculos_ordenados['Tipo_Local'] == 0) &
            (veiculos_ordenados['Motorista associado'] == veiculos_ordenados['Motorista_Anterior']) &
            (veiculos_ordenados['Placa'] == veiculos_ordenados['Placa_Anterior']) &
            (veiculos_ordenados['Data'] == veiculos_ordenados['Data_Anterior'])
        )

        # Marca as viagens válidas
        veiculos_ordenados['Viagem_Valida'] = viagem_valida

        # Filtra apenas viagens completas (válidas)
        viagens_completas = veiculos_ordenados[veiculos_ordenados['Viagem_Valida']].copy()

        # =========================
        # CÁLCULO DE TONELADAS COM NUMPY
        # =========================
        
        # Mapeia tonelagem para cada placa
        viagens_completas['Toneladas_Viagem'] = viagens_completas['Placa'].map(
            lambda x: TONELADAS_POR_VEICULO.get(x, TONELAGEM_PADRAO)
        )
        
        # Agrupa por motorista e placa para análise
        agrupamento = viagens_completas.groupby(['Motorista associado', 'Placa']).agg({
            'Viagem_Valida': 'count',
            'Toneladas_Viagem': 'first'
        }).reset_index()
        
        agrupamento.columns = ['Motorista', 'Placa', 'Num_Viagens', 'Toneladas_Por_Viagem']
        
        # Calcula total de toneladas usando NumPy (multiplicação vetorizada)
        viagens_array = np.array(agrupamento['Num_Viagens'])
        toneladas_array = np.array(agrupamento['Toneladas_Por_Viagem'])
        agrupamento['Total_Toneladas'] = np.multiply(viagens_array, toneladas_array)
        
        # Resumo por motorista
        analise_toneladas = agrupamento.groupby('Motorista').agg({
            'Num_Viagens': 'sum',
            'Total_Toneladas': 'sum'
        }).reset_index()
        analise_toneladas.columns = ['Motorista', 'Total_Viagens', 'Total_Toneladas']
        analise_toneladas = analise_toneladas.sort_values('Total_Toneladas', ascending=False)
        
        # Carros utilizados por motorista
        carros_por_motorista = agrupamento.groupby('Motorista').agg({
            'Placa': lambda x: ', '.join(sorted(set(x))),
            'Num_Viagens': 'sum'
        }).reset_index()
        carros_por_motorista.columns = ['Motorista', 'Carros_Utilizados', 'Total_Viagens']
        
        # Contagem por motorista
        contagem_por_motorista = (
            viagens_completas
            .groupby('Motorista associado')
            .size()
            .reset_index(name='Total de Viagens')
            .sort_values('Total de Viagens', ascending=False)
        )

        return (contagem_por_motorista, viagens_completas, len(viagens_completas), 
                analise_toneladas, carros_por_motorista, agrupamento)

    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao processar arquivo:\n{str(e)}")
        return None, None, None, None, None, None


# =========================
# GERAÇÃO DE GRÁFICOS PLOTLY
# =========================

def gerar_graficos(analise_toneladas, carros_por_motorista, agrupamento):
    """
    Gera gráficos interativos com Plotly.
    
    Parâmetros:
        analise_toneladas (DataFrame): dados de toneladas por motorista
        carros_por_motorista (DataFrame): carros utilizados por motorista
        agrupamento (DataFrame): dados detalhados por motorista e placa
    """
    
    # Gráfico 1: Barras - Total de Toneladas por Motorista
    fig1 = px.bar(
        analise_toneladas.head(15),
        x='Motorista',
        y='Total_Toneladas',
        title='Total de Toneladas Transportadas por Motorista (Top 15)',
        labels={'Total_Toneladas': 'Toneladas', 'Motorista': 'Motorista'},
        color='Total_Toneladas',
        color_continuous_scale='Blues'
    )
    fig1.update_layout(xaxis_tickangle=-45, height=500)
    fig1.show()
    
    # Gráfico 2: Pizza - Distribuição de Viagens por Motorista (Top 10)
    top10_viagens = analise_toneladas.head(10)
    fig2 = px.pie(
        top10_viagens,
        names='Motorista',
        values='Total_Viagens',
        title='Distribuição de Viagens - Top 10 Motoristas',
        hole=0.3
    )
    fig2.update_traces(textposition='inside', textinfo='percent+label')
    fig2.show()
    
    # Gráfico 3: Barras Agrupadas - Viagens por Motorista e Placa
    motoristas_top = analise_toneladas.head(5)['Motorista'].values
    dados_filtrados = agrupamento[agrupamento['Motorista'].isin(motoristas_top)]
    
    fig3 = px.bar(
        dados_filtrados,
        x='Motorista',
        y='Num_Viagens',
        color='Placa',
        title='Viagens por Motorista e Veículo (Top 5 Motoristas)',
        labels={'Num_Viagens': 'Número de Viagens', 'Motorista': 'Motorista'},
        barmode='group'
    )
    fig3.update_layout(xaxis_tickangle=-45, height=500)
    fig3.show()
    
    # Gráfico 4: Barras Empilhadas - Toneladas por Motorista e Placa
    fig4 = px.bar(
        dados_filtrados,
        x='Motorista',
        y='Total_Toneladas',
        color='Placa',
        title='Total de Toneladas por Motorista e Veículo (Top 5 Motoristas)',
        labels={'Total_Toneladas': 'Toneladas', 'Motorista': 'Motorista'},
        barmode='stack'
    )
    fig4.update_layout(xaxis_tickangle=-45, height=500)
    fig4.show()


# =========================
# SELEÇÃO DO ARQUIVO
# =========================

def selecionar_arquivo():
    """
    Abre a janela para seleção do arquivo Excel
    e inicia o processamento.
    """
    arquivo_excel = filedialog.askopenfilename(
        title="Selecione o arquivo Excel",
        filetypes=[("Arquivos Excel", "*.xlsx *.xls"), ("Todos os arquivos", "*.*")]
    )

    if not arquivo_excel:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado!")
        return

    # Processa o arquivo selecionado
    resultado = processar_arquivo(arquivo_excel)
    
    if resultado[0] is not None:
        contagem, viagens, total, analise_ton, carros_mot, agrup = resultado
        mostrar_resultados(contagem, viagens, total, arquivo_excel, analise_ton, carros_mot)
        
        # Gera os gráficos
        gerar_graficos(analise_ton, carros_mot, agrup)


# =========================
# JANELA DE RESULTADOS
# =========================

def mostrar_resultados(contagem_por_motorista, viagens_completas, total_viagens, 
                       arquivo, analise_toneladas, carros_por_motorista):
    """
    Cria uma nova janela exibindo resultados completos.
    """
    janela_resultado = tk.Toplevel()
    janela_resultado.title("Resultados da Análise de Viagens")
    janela_resultado.geometry("1200x700")

    # Frame principal
    main_frame = ttk.Frame(janela_resultado, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Título
    ttk.Label(
        main_frame,
        text="Análise Completa de Viagens e Toneladas",
        font=('Arial', 16, 'bold')
    ).grid(row=0, column=0, columnspan=2, pady=10)

    # Nome do arquivo
    ttk.Label(
        main_frame,
        text=f"Arquivo: {arquivo.split('/')[-1]}",
        font=('Arial', 10)
    ).grid(row=1, column=0, columnspan=2, pady=5)

    # Total de viagens
    ttk.Label(
        main_frame,
        text=f"Total de Viagens Válidas: {total_viagens}",
        font=('Arial', 12, 'bold'),
        foreground='blue'
    ).grid(row=2, column=0, columnspan=2, pady=10)

    # Abas (Notebook)
    notebook = ttk.Notebook(main_frame)
    notebook.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=10)

    # =========================
    # ABA 1 - ANÁLISE DE TONELADAS
    # =========================

    frame_toneladas = ttk.Frame(notebook, padding="10")
    notebook.add(frame_toneladas, text="Análise de Toneladas")

    tree_toneladas = ttk.Treeview(
        frame_toneladas,
        columns=('Motorista', 'Viagens', 'Toneladas'),
        show='headings',
        height=15
    )

    tree_toneladas.heading('Motorista', text='Motorista')
    tree_toneladas.heading('Viagens', text='Total de Viagens')
    tree_toneladas.heading('Toneladas', text='Total de Toneladas')

    tree_toneladas.column('Motorista', width=200)
    tree_toneladas.column('Viagens', width=150)
    tree_toneladas.column('Toneladas', width=150)

    for _, row in analise_toneladas.iterrows():
        tree_toneladas.insert(
            '',
            'end',
            values=(row['Motorista'], row['Total_Viagens'], f"{row['Total_Toneladas']:.2f} TN")
        )

    tree_toneladas.grid(row=0, column=0, sticky="nsew")

    # Scrollbar
    scrollbar_ton = ttk.Scrollbar(frame_toneladas, orient="vertical", command=tree_toneladas.yview)
    scrollbar_ton.grid(row=0, column=1, sticky="ns")
    tree_toneladas.configure(yscrollcommand=scrollbar_ton.set)

    # =========================
    # ABA 2 - CARROS POR MOTORISTA
    # =========================

    frame_carros = ttk.Frame(notebook, padding="10")
    notebook.add(frame_carros, text="Carros por Motorista")

    tree_carros = ttk.Treeview(
        frame_carros,
        columns=('Motorista', 'Carros', 'Viagens'),
        show='headings',
        height=15
    )

    tree_carros.heading('Motorista', text='Motorista')
    tree_carros.heading('Carros', text='Carros Utilizados')
    tree_carros.heading('Viagens', text='Total de Viagens')

    tree_carros.column('Motorista', width=200)
    tree_carros.column('Carros', width=300)
    tree_carros.column('Viagens', width=150)

    for _, row in carros_por_motorista.iterrows():
        tree_carros.insert(
            '',
            'end',
            values=(row['Motorista'], row['Carros_Utilizados'], row['Total_Viagens'])
        )

    tree_carros.grid(row=0, column=0, sticky="nsew")

    # Scrollbar
    scrollbar_carros = ttk.Scrollbar(frame_carros, orient="vertical", command=tree_carros.yview)
    scrollbar_carros.grid(row=0, column=1, sticky="ns")
    tree_carros.configure(yscrollcommand=scrollbar_carros.set)

    # =========================
    # ABA 3 - CONTAGEM SIMPLES
    # =========================

    frame_contagem = ttk.Frame(notebook, padding="10")
    notebook.add(frame_contagem, text="Viagens por Motorista")

    tree_contagem = ttk.Treeview(
        frame_contagem,
        columns=('Motorista', 'Total'),
        show='headings',
        height=15
    )

    tree_contagem.heading('Motorista', text='Motorista')
    tree_contagem.heading('Total', text='Total de Viagens')

    for _, row in contagem_por_motorista.iterrows():
        tree_contagem.insert(
            '',
            'end',
            values=(row['Motorista associado'], row['Total de Viagens'])
        )

    tree_contagem.grid(row=0, column=0, sticky="nsew")

    # =========================
    # ABA 4 - DETALHES
    # =========================

    frame_detalhes = ttk.Frame(notebook, padding="10")
    notebook.add(frame_detalhes, text="Detalhes das Viagens")

    tree_detalhes = ttk.Treeview(
        frame_detalhes,
        columns=('Motorista', 'Placa', 'Data', 'Local', 'Horário'),
        show='headings',
        height=15
    )

    tree_detalhes.heading('Motorista', text='Motorista')
    tree_detalhes.heading('Placa', text='Placa')
    tree_detalhes.heading('Data', text='Data')
    tree_detalhes.heading('Local', text='Local')
    tree_detalhes.heading('Horário', text='Horário de Entrada')

    for _, row in viagens_completas.iterrows():
        tree_detalhes.insert(
            '',
            'end',
            values=(
                row['Motorista associado'],
                row['Placa'],
                row['Data'],
                row['Nome do local'],
                row['Data e horário de entrada no local'].strftime('%d/%m/%Y %H:%M')
            )
        )

    tree_detalhes.grid(row=0, column=0, sticky="nsew")


# ========================= 
# FUNÇÃO PRINCIPAL
# =========================

def main():
    """
    Inicializa a aplicação e exibe a janela principal.
    """
    root = tk.Tk()
    root.title("Análise de Viagens com Toneladas")
    root.geometry("450x300")

    main_frame = ttk.Frame(root, padding="20")
    main_frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(
        main_frame,
        text="Análise de Viagens e Toneladas",
        font=('Arial', 18, 'bold')
    ).grid(row=0, column=0, pady=20)

    ttk.Label(
        main_frame,
        text="Selecione um arquivo Excel para analisar\nas viagens e calcular toneladas transportadas",
        font=('Arial', 10),
        justify='center'
    ).grid(row=1, column=0, pady=10)

    ttk.Button(
        main_frame,
        text="Selecionar Arquivo Excel",
        command=selecionar_arquivo,
        width=30
    ).grid(row=2, column=0, pady=20)

    ttk.Button(
        main_frame,
        text="Sair",
        command=root.quit,
        width=30
    ).grid(row=3, column=0, pady=10)

    root.mainloop()


# =========================
# PONTO DE ENTRADA
# =========================

if __name__ == "__main__":
    main()
