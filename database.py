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

    # 4. NOVA TABELA: Tabela de Imóveis (Usados e Lançamentos na Planta)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imoveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL, -- 'Planta' ou 'Usado'
            bairro TEXT,
            preco TEXT,
            caracteristicas TEXT, -- Ex: "3 qtos, 2 vagas, 85m²"
            descricao TEXT,
            imagem_url TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # Inserir alguns Imóveis de teste (Na Planta e Usados) para iniciar o catálogo
    cursor.execute("SELECT COUNT(*) FROM imoveis")
    if cursor.fetchone()[0] == 0:
        imoveis_teste = [
            (
                'Residencial Green View', 
                'Planta', 
                'Jardim Europa', 
                'R$ 380.000', 
                '2 qtos (1 suíte), Varanda Gourmet, 1 vaga', 
                'Lançamento na planta com excelente localização em Nova Odessa. Área de lazer completa com piscina e quiosque gourmet.',
                'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=500'
            ),
            (
                'Casa Térrea Clássica', 
                'Usado', 
                'Centro', 
                'R$ 550.000', 
                '3 qtos (1 suíte), 2 vagas, Quintal amplo', 
                'Linda casa térrea no centro de Nova Odessa, reformada, com armários planejados na cozinha e excelente espaço de terreno.',
                'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=500'
            )
        ]
        cursor.executemany(
            "INSERT INTO imoveis (titulo, tipo, bairro, preco, caracteristicas, descricao, imagem_url) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            imoveis_teste
        )

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()