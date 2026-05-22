from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google import genai
from google.genai import types
import sqlite3
import os
import datetime

app = FastAPI(title="ImobiAI - Engine de Qualificação")

# Configurações de pastas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuração do Cliente Gemini (Busca a chave no cofre do Render)
client = genai.Client()

# Função auxiliar para conectar ao banco
def get_db_connection():
    conn = sqlite3.connect('crm_bot.db')
    conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
    return conn

# --- FUNÇÃO DE INICIALIZAÇÃO AUTOMÁTICA DO BANCO ---
def init_db_auto():
    conn = get_db_connection()
    # Garante que a tabela de imóveis exista no Render
    conn.execute("""
        CREATE TABLE IF NOT EXISTS imoveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            bairro TEXT,
            preco TEXT,
            caracteristicas TEXT,
            descricao TEXT,
            imagem_url TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Executa a checagem ao iniciar a aplicação
init_db_auto()

# Rota Principal - Busca os dados do banco de dados reais
@app.get("/")
async def serve_dashboard(request: Request):
    conn = get_db_connection()
    
    # 1. Busca todos os leads cadastrados
    leads = conn.execute("SELECT * FROM leads ORDER BY data_criacao DESC").fetchall()
    
    # 2. Busca o prompt do sistema atual
    config = conn.execute("SELECT prompt_sistema FROM bot_config ORDER BY id DESC LIMIT 1").fetchone()
    prompt_atual = config['prompt_sistema'] if config else "Sem prompt configurado."
    
    # 3. Busca o histórico de mensagens (para a aba de chats)
    historico = conn.execute("""
        SELECT h.*, l.nome as lead_nome 
        FROM chat_history h 
        JOIN leads l ON h.lead_id = l.id 
        ORDER BY h.data_envio DESC
    """).fetchall()
    
    conn.close()
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"leads": leads, "prompt_atual": prompt_atual, "historico": historico}
    )

# --- ROTA PARA VISUALIZAR A PÁGINA DE IMÓVEIS ---
@app.get("/imoveis")
async def serve_imoveis(request: Request):
    conn = get_db_connection()
    # Busca todos os imóveis cadastrados para renderizar no HTML
    imoveis = conn.execute("SELECT * FROM imoveis ORDER BY data_cadastro DESC").fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="imoveis.html",
        context={"imoveis": imoveis}
    )

# --- ROTA PARA CADASTRAR UM NOVO IMÓVEL ---
@app.post("/cadastrar-imovel")
async def cadastrar_imovel(
    titulo: str = Form(...),
    tipo: str = Form(...),
    bairro: str = Form(...),
    preco: str = Form(...),
    caracteristicas: str = Form(...),
    descricao: str = Form(...),
    imagem_url: str = Form(None)
):
    conn = get_db_connection()
    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute("""
        INSERT INTO imoveis (titulo, tipo, bairro, preco, caracteristicas, descricao, imagem_url, data_cadastro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (titulo, tipo, bairro, preco, caracteristicas, descricao, imagem_url, data_atual))
    
    conn.commit()
    conn.close()
    
    # Após cadastrar, redireciona o usuário de volta para a página de imóveis atualizada
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/imoveis", status_code=303)

# Rota para salvar um novo prompt enviado pela tela de configurações
@app.post("/salvar-prompt")
async def salvar_prompt(prompt: str = Form(...)):
    conn = get_db_connection()
    conn.execute("INSERT INTO bot_config (prompt_sistema) VALUES (?)", (prompt,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Prompt updated successfully!"}

class WhatsAppMessage(BaseModel):
    phone: str
    message: str

@app.post("/webhook")
async def receive_whatsapp_message(payload: WhatsAppMessage):
    user_phone = payload.phone
    user_message = payload.message
    
    conn = get_db_connection()
    try:
        config = conn.execute("SELECT prompt_sistema FROM bot_config ORDER BY id DESC LIMIT 1").fetchone()
        system_prompt = config['prompt_sistema'] if config else "Você é um assistente virtual."
        
        lead = conn.execute("SELECT id FROM leads WHERE telefone = ?", (user_phone,)).fetchone()
        if not lead:
            data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.execute(
                "INSERT INTO leads (nome, telefone, status, data_criacao) VALUES (?, ?, 'progress', ?)", 
                (f"Lead {user_phone[-4:]}", user_phone, data_atual)
            )
            lead_id = cursor.lastrowid
        else:
            lead_id = lead['id']
            
        conn.execute("INSERT INTO chat_history (lead_id, papel, mansion) VALUES (?, 'user', ?)", 
                     (lead_id, user_message))
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.5,
            ),
        )
        bot_reply = response.text
        
        conn.execute("INSERT INTO chat_history (lead_id, papel, mensagem) VALUES (?, 'assistant', ?)", 
                     (lead_id, bot_reply))
        
        conn.commit()
        return {"status": "success", "reply": bot_reply}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)