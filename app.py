from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
import sqlite3
import os
import datetime
import secrets

app = FastAPI(title="ImobiAI - Engine de Qualificação")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

client = genai.Client()

# --- FUNÇÃO AUXILIAR DE SEGURANÇA POR COOKIE ---
def verificar_admin_cookie(request: Request):
    # Busca o cookie de login chamado "imobia_session"
    session = request.cookies.get("imobia_session")
    if session != "authenticated_admin_2026":
        # Se não estiver logado, lança o erro que redireciona para o login
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True

# Tratamento para quando o usuário tenta acessar o painel sem estar logado
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("error.html", {"request": request, "detail": exc.detail})

def get_db_connection():
    conn = sqlite3.connect('crm_bot.db')
    conn.row_factory = sqlite3.Row  
    return conn

def init_db_auto():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS imoveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT,
            bairro TEXT,
            preco TEXT,
            caracteristicas TEXT,
            descricao TEXT,
            imagem_url TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT UNIQUE,
            status TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            papel TEXT,
            mensagem TEXT,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bot_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_sistema TEXT
        )
    """)
    
    # Inicializa o prompt padrão com as Regras de Ouro se o banco estiver vazio
    check = conn.execute("SELECT count(*) as total FROM bot_config").fetchone()
    if check['total'] == 0:
        default_prompt = (
            "Você é um corretor de imóveis de alta performance, ágil e profissional. "
            "Sua missão é qualificar leads e ajudar na escolha de imóveis. "
            "REGRAS DE ATENDIMENTO: 1. O cliente já forneceu o nome e telefone. NUNCA peça essas informações novamente. "
            "2. Seja direto, cortês e objetivo. Evite textos longos. 3. Responda apenas sobre imóveis. "
            "4. Se o cliente demonstrar interesse em agendar visitas, identifique como um lead quente."
        )
        conn.execute("INSERT INTO bot_config (prompt_sistema) VALUES (?)", (default_prompt,))
        
    conn.commit()
    conn.close()

init_db_auto()


# ==========================================
# 🌍 ROTAS PÚBLICAS (VISÃO DO CLIENTE COMPRADOR)
# ==========================================

# Agora a Raiz do site (/) carrega a busca pública de imóveis!
@app.get("/")
async def serve_home_cliente(request: Request, q: str = None):
    conn = get_db_connection()
    if q:
        query = f"%{q}%"
        imoveis = conn.execute("""
            SELECT * FROM imoveis 
            WHERE titulo LIKE ? OR bairro LIKE ? OR categoria LIKE ? OR caracteristicas LIKE ? OR descricao LIKE ?
            ORDER BY data_cadastro DESC
        """, (query, query, query, query, query)).fetchall()
    else:
        imoveis = conn.execute("SELECT * FROM imoveis ORDER BY data_cadastro DESC").fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="cliente_busca.html",
        context={"imoveis": imoveis, "busca_atual": q or ""}
    )

# Rota para abrir a página de login
@app.get("/login")
async def serve_login_page(request: Request, error: str = None):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": error})

# Rota que valida os dados do formulário de login
@app.post("/login")
async def process_login(username: str = Form(...), password: str = Form(...)):
    # Validação com as suas credenciais solicitadas
    if username == "ADMimob" and password == "Adm@2026":
        response = RedirectResponse(url="/dashboard", status_code=303)
        # Salva o cookie de segurança que dá acesso ao painel
        response.set_cookie(key="imobia_session", value="authenticated_admin_2026", path="/", httponly=True)
        return response
    else:
        return RedirectResponse(url="/login?error=Usuario%20ou%20senha%20incorretos", status_code=303)

# Rota para o corretor sair do painel com segurança
@app.get("/logout")
async def process_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("imobia_session", path="/")
    return response


# ==========================================
# 🔒 ROTAS PROTEGIDAS (REQUEREM LOGIN DO ADM)
# ==========================================

# O painel com as abas de leads, histórico e prompt agora fica em /dashboard
@app.get("/dashboard")
async def serve_dashboard(request: Request, authenticated: bool = Depends(verificar_admin_cookie)):
    conn = get_db_connection()
    leads = conn.execute("SELECT * FROM leads ORDER BY data_criacao DESC").fetchall()
    config = conn.execute("SELECT prompt_sistema FROM bot_config ORDER BY id DESC LIMIT 1").fetchone()
    prompt_atual = config['prompt_sistema'] if config else "Você é um corretor de imóveis focado em qualificar leads."
    
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

@app.get("/imoveis")
async def serve_imoveis(request: Request, authenticated: bool = Depends(verificar_admin_cookie)):
    conn = get_db_connection()
    imoveis = conn.execute("SELECT * FROM imoveis ORDER BY data_cadastro DESC").fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="imoveis.html",
        context={"imoveis": imoveis}
    )

@app.post("/cadastrar-imovel")
async def cadastrar_imovel(
    id: str = Form(None),
    titulo: str = Form(...),
    tipo: str = Form(...),
    categoria: str = Form(...),
    bairro: str = Form(...),
    preco: str = Form(...),
    caracteristicas: str = Form(...),
    descricao: str = Form(...),
    imagem_url: str = Form(None),
    authenticated: bool = Depends(verificar_admin_cookie)
):
    conn = get_db_connection()
    if id and id.strip() != "":
        conn.execute("""
            UPDATE imoveis 
            SET titulo=?, tipo=?, categoria=?, bairro=?, preco=?, caracteristicas=?, descricao=?, imagem_url=?
            WHERE id=?
        """, (titulo, tipo, categoria, bairro, preco, caracteristicas, descricao, imagem_url, int(id)))
    else:
        data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO imoveis (titulo, tipo, categoria, bairro, preco, caracteristicas, descricao, imagem_url, data_cadastro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (titulo, tipo, categoria, bairro, preco, caracteristicas, descricao, imagem_url, data_atual))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/imoveis", status_code=303)

@app.get("/deletar-imovel/{imovel_id}")
async def deletar_imovel(imovel_id: int, authenticated: bool = Depends(verificar_admin_cookie)):
    conn = get_db_connection()
    conn.execute("DELETE FROM imoveis WHERE id = ?", (imovel_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/imoveis", status_code=303)

@app.post("/salvar-prompt")
async def salvar_prompt(prompt: str = Form(...), authenticated: bool = Depends(verificar_admin_cookie)):
    conn = get_db_connection()
    conn.execute("INSERT INTO bot_config (prompt_sistema) VALUES (?)", (prompt,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Prompt updated successfully!"}


# ==========================================
# 🤖 WEBHOOK INTEGRAÇÃO (WHATSAPP / BOT)
# ==========================================

class WhatsAppMessage(BaseModel):
    name: str  
    phone: str
    message: str

@app.post("/webhook")
async def receive_whatsapp_message(payload: WhatsAppMessage):
    user_name = payload.name
    user_phone = payload.phone
    user_message = payload.message
    
    conn = get_db_connection()
    try:
        config = conn.execute("SELECT prompt_sistema FROM bot_config ORDER BY id DESC LIMIT 1").fetchone()
        system_prompt = config['prompt_sistema'] if config else "Você é um assistente virtual."
        
        # Busca ou cria o lead com o nome fornecido
        lead = conn.execute("SELECT id FROM leads WHERE telefone = ?", (user_phone,)).fetchone()
        if not lead:
            data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.execute(
                "INSERT INTO leads (nome, telefone, status, data_criacao) VALUES (?, ?, 'progress', ?)", 
                (user_name, user_phone, data_atual)
            )
            lead_id = cursor.lastrowid
        else:
            lead_id = lead['id']
            
        conn.execute("INSERT INTO chat_history (lead_id, papel, mensagem) VALUES (?, 'user', ?)", 
                     (lead_id, user_message))
        
        # BUSCA HISTÓRICO PARA DAR MEMÓRIA À IA (Limitado às últimas 6 mensagens)
        historico_rows = conn.execute("""
            SELECT papel, mensagem FROM chat_history 
            WHERE lead_id = ? ORDER BY id DESC LIMIT 6
        """, (lead_id,)).fetchall()
        
        # Constrói o contexto da conversa para a IA
        contexto_conversa = "\n".join([f"{row['papel'].upper()}: {row['mensagem']}" for row in reversed(historico_rows)])
        
        # Chamada da IA com o histórico, contexto do nome e Regras de Ouro
        regras_ouro = (
            f"\n[HISTÓRICO RECENTE]: {contexto_conversa}\n"
            f"[REGRAS DE OURO]: 1. O cliente chama-se {user_name}. 2. Analise o histórico acima e NUNCA repita perguntas já respondidas. "
            "3. Seja extremamente direto, profissional e focado em vendas. 4. ESTA É UMA REGRA CRÍTICA: Você NÃO tem permissão para agendar visitas ou definir horários. "
            "Sempre que o cliente quiser agendar algo, diga: 'Um de nossos corretores entrará em contato em breve para realizar o agendamento pessoalmente'."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=f"{system_prompt} {regras_ouro}",
                temperature=0.5,
            ),
        )
        bot_reply = response.text
        
        # FILTRO DE SEGURANÇA: Trava de agendamento (Impede a IA de marcar horários)
        palavras_agendamento = ['agendar', 'visita', 'horário', 'data', 'marcar', 'quando posso']
        if any(palavra in bot_reply.lower() for palavra in palavras_agendamento):
            bot_reply = "Entendido! Vou repassar seu interesse para nossa equipe e um de nossos corretores entrará em contato em breve para realizar o agendamento pessoalmente."
        
        # Lógica de marcação de status
        if any(word in user_message.lower() for word in ['agendar', 'visita', 'interesse', 'queria saber']):
            conn.execute("UPDATE leads SET status = 'hot' WHERE id = ?", (lead_id,))
        
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