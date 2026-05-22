from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI
import sqlite3
import os

app = FastAPI(title="ImobiAI - Engine de Qualificação")

# Configurações de pastas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Chave da OpenAI
API_KEY = os.getenv("OPENAI_API_KEY", "sua_chave_aqui")

# Função auxiliar para conectar ao banco
def get_db_connection():
    conn = sqlite3.connect('crm_bot.db')
    conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome (ex: row['nome'])
    return conn

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
    
    # Envia os dados reais para o arquivo HTML renderizar
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"leads": leads, "prompt_atual": prompt_atual, "historico": historico}
    )

# Rota para salvar um novo prompt enviado pela tela de configurações
@app.post("/salvar-prompt")
async def salvar_prompt(prompt: str = Form(...)):
    conn = get_db_connection()
    conn.execute("INSERT INTO bot_config (prompt_sistema) VALUES (?)", (prompt,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Prompt atualizado com sucesso!"}

class WhatsAppMessage(BaseModel):
    phone: str
    message: str

@app.post("/webhook")
async def receive_whatsapp_message(payload: WhatsAppMessage):
    user_phone = payload.phone
    user_message = payload.message
    
    conn = get_db_connection()
    try:
        # Busca o prompt do sistema que está salvo no banco
        config = conn.execute("SELECT prompt_sistema FROM bot_config ORDER BY id DESC LIMIT 1").fetchone()
        system_prompt = config['prompt_sistema'] if config else "Você é um assistente virtual."
        
        # Cria ou localiza o lead pelo telefone
        lead = conn.execute("SELECT id FROM leads WHERE telefone = ?", (user_phone,)).fetchone()
        if not lead:
            cursor = conn.execute("INSERT INTO leads (nome, telefone, status) VALUES (?, ?, 'progress')", 
                                 (f"Lead {user_phone[-4:]}", user_phone))
            lead_id = cursor.lastrowid
        else:
            lead_id = lead['id']
            
        # Salva a mensagem que o usuário enviou no histórico do banco
        conn.execute("INSERT INTO chat_history (lead_id, papel, mensagem) VALUES (?, 'user', ?)", 
                     (lead_id, user_message))
        
        # Envia para a OpenAI
        client = OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.5
        )
        bot_reply = response.choices[0].message.content
        
        # Salva a resposta do bot no histórico do banco
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