import sqlite3

def init_db():
    # Conecta ao arquivo de banco de dados (será criado automaticamente)
    conn = sqlite3.connect('crm_bot.db')
    cursor = conn.cursor()

    # 1. Tabela de Leads
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            status TEXT DEFAULT 'progress', -- 'hot' ou 'progress'
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Tabela de Configurações do Bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_sistema TEXT NOT NULL
        )
    ''')

    # 3. Tabela de Histórico de Chats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            papel TEXT, -- 'user' ou 'assistant'
            mensagem TEXT,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')

    # Inserir um prompt padrão inicial para o Bot se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM bot_config")
    if cursor.fetchone()[0] == 0:
        prompt_padrao = "Você é um assistente de vendas amigável. Seu objetivo é entender a necessidade do cliente e agendar uma chamada."
        cursor.execute("INSERT INTO bot_config (prompt_sistema) VALUES (?)", (prompt_padrao,))

    # Inserir alguns Leads de teste para o painel não ficar vazio de início
    cursor.execute("SELECT COUNT(*) FROM leads")
    if cursor.fetchone()[0] == 0:
        leads_teste = [
            ('Carlos Silva', '19999999999', 'hot'),
            ('Mariana Souza', '19988888888', 'progress'),
            ('Fernanda Lima', '19977777777', 'progress')
        ]
        cursor.executemany("INSERT INTO leads (nome, telefone, status) VALUES (?, ?, ?)", leads_teste)

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()