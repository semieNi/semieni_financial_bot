import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "data/finance.db"

def conectar():
    conn = sqlite3.connect(DB_PATH)
    return conn

def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tipo TEXT,
            valor REAL,
            categoria TEXT,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()

def adicionar_transacao(user_id, tipo, valor, categoria):
    criar_tabela()
    conn = conectar()
    cursor = conn.cursor()
    data = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT INTO transacoes (user_id, tipo, valor, categoria, data)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, tipo, valor, categoria, data))
    conn.commit()
    conn.close()

def obter_resumo(user_id):
    criar_tabela()
    conn = conectar()
    cursor = conn.cursor()
    sete_dias_atras = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    cursor.execute('''
        SELECT tipo, categoria, SUM(valor)
        FROM transacoes
        WHERE user_id = ? AND data >= ?
        GROUP BY tipo, categoria
    ''', (user_id, sete_dias_atras))

    resultado = cursor.fetchall()
    conn.close()
    return resultado

def obter_saldo(user_id):
    criar_tabela()
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT tipo, SUM(valor) FROM transacoes
        WHERE user_id = ?
        GROUP BY tipo
    ''', (user_id,))

    resultado = cursor.fetchall()
    conn.close()

    total_receitas = sum(v for t, v in resultado if t == "receita")
    total_gastos = sum(v for t, v in resultado if t == "gasto")
    saldo = total_receitas - total_gastos
    return saldo

def exportar_transacoes(user_id):
    criar_tabela()
    conn = conectar()
    query = '''
        SELECT data, tipo, valor, categoria
        FROM transacoes
        WHERE user_id = ?
        ORDER BY data DESC
    '''
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()

    if df.empty:
        return None

    caminho_csv = f"data/transacoes_{user_id}.csv"
    df.to_csv(caminho_csv, index=False, sep=";")
    return caminho_csv