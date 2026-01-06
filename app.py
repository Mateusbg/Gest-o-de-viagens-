"""
===========================================================
ANÁLISE DE VIAGENS (LAVRA → BRITADOR)
===========================================================

Este programa:
- Lê um arquivo Excel exportado do sistema Cobli
- Identifica viagens válidas (Lavra → Britador)
- Agrupa as viagens por motorista
- Exibe os resultados em uma interface gráfica (Tkinter)

Autor: Mateus barbosa
Data: 03/01/2026 - 13:45
Version: 1.0
===========================================================
"""

# =========================
# IMPORTAÇÕES
# =========================

import pandas as pd                  # Manipulação de dados (Excel, DataFrame)
import tkinter as tk                 # Interface gráfica
from tkinter import filedialog, messagebox
from tkinter import ttk              # Componentes visuais modernos do Tkinter


# =========================
# PROCESSAMENTO DO ARQUIVO
# =========================

def processar_arquivo(arquivo_excel):
    """
    Lê o arquivo Excel e identifica viagens válidas.
    
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

        # Classifica o tipo de local:
        # 1 = Lavra
        # 0 = Britador / Descarga
        # None = Outros locais
        veiculos_ordenados['Tipo_Local'] = veiculos_ordenados['Nome do local'].apply(
            lambda x: 1 if 'Lavra' in str(x)
            else (0 if 'britador' in str(x).lower() or 'Descarga' in str(x) else None)
        )

        # Cria colunas com os dados da linha anterior
        veiculos_ordenados['Local_Anterior'] = veiculos_ordenados['Tipo_Local'].shift(1)
        veiculos_ordenados['Motorista_Anterior'] = veiculos_ordenados['Motorista associado'].shift(1)
        veiculos_ordenados['Placa_Anterior'] = veiculos_ordenados['Placa'].shift(1)
        veiculos_ordenados['Data_Anterior'] = veiculos_ordenados['Data'].shift(1)

        # Regra para identificar viagem válida:
        # Lavra (1) → Britador (0)
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
        viagens_completas = veiculos_ordenados[veiculos_ordenados['Viagem_Valida']]

        # Conta quantas viagens cada motorista realizou
        contagem_por_motorista = (
            viagens_completas
            .groupby('Motorista associado')
            .size()
            .reset_index(name='Total de Viagens')
            .sort_values('Total de Viagens', ascending=False)
        )

        return contagem_por_motorista, viagens_completas, len(viagens_completas)

    except Exception as e:
        # Exibe erro caso algo falhe no processamento
        messagebox.showerror("Erro", f"Erro ao processar arquivo:\n{str(e)}")
        return None, None, None


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
    contagem, viagens, total = processar_arquivo(arquivo_excel)

    if contagem is not None:
        mostrar_resultados(contagem, viagens, total, arquivo_excel)


# =========================
# JANELA DE RESULTADOS
# =========================

def mostrar_resultados(contagem_por_motorista, viagens_completas, total_viagens, arquivo):
    """
    Cria uma nova janela exibindo:
    - Total de viagens válidas
    - Viagens por motorista
    - Detalhes das viagens
    """
    janela_resultado = tk.Toplevel()
    janela_resultado.title("Resultados da Análise de Viagens")
    janela_resultado.geometry("1000x600")

    # Frame principal
    main_frame = ttk.Frame(janela_resultado, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Título
    ttk.Label(
        main_frame,
        text="Análise de Viagens Válidas",
        font=('Arial', 16, 'bold')
    ).grid(row=0, column=0, columnspan=2, pady=10)

    # Nome do arquivo analisado
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
    # ABA 1 - CONTAGEM
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
    # ABA 2 - DETALHES
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

    # Mostra apenas as primeiras 100 viagens
    for _, row in viagens_completas.iterrows(): #.head(100): sefor mostrar quantidade de viagens limitada colocar antes do iterrows
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
    root.title("Análise de Viagens")
    root.geometry("400x250")

    main_frame = ttk.Frame(root, padding="20")
    main_frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(
        main_frame,
        text="Análise de Viagens",
        font=('Arial', 18, 'bold')
    ).grid(row=0, column=0, pady=20)

    ttk.Label(
        main_frame,
        text="Selecione um arquivo Excel para analisar\nas viagens válidas (Lavra → Britador)",
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
