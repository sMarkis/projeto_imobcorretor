// Função para alternar as abas do painel
function switchTab(tabName) {
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active-content'));

    if (tabName === 'leads') {
        document.getElementById('menu-leads').classList.add('active');
        document.getElementById('section-leads').classList.add('active-content');
    } else if (tabName === 'config') {
        document.getElementById('menu-config').classList.add('active');
        document.getElementById('section-config').classList.add('active-content');
    } else if (tabName === 'historico') {
        document.getElementById('menu-historico').classList.add('active');
        document.getElementById('section-historico').classList.add('active-content');
    }
}

// Função para salvar o prompt sem atualizar a página
// Função para salvar o prompt com confirmação e alerta temporário
function enviarPrompt() {
    const promptValue = document.getElementById('prompt-text').value;
    const alertMsg = document.getElementById('alert-msg');

    // 1. Pergunta ao usuário se ele realmente quer salvar
    const confirmacao = confirm("Você realmente gostaria de salvar as alterações do Bot?");
    
    // Se o usuário clicar em "Cancelar", interrompe a função aqui
    if (!confirmacao) {
        return; 
    }

    const formData = new FormData();
    formData.append('prompt', promptValue);

    // Envia os dados para o Python em segundo plano
    fetch('/salvar-prompt', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Estiliza e mostra o alerta com a frase encurtada
            alertMsg.style.backgroundColor = '#d4edda';
            alertMsg.style.color = '#155724';
            alertMsg.style.border = '1px solid #c3e6cb';
            alertMsg.style.display = 'block';
            alertMsg.innerText = '✅ Instrução foi Salva com Sucesso!';
            
            // Faz a mensagem SUMIR completamente depois de 3 segundos
            setTimeout(() => { 
                alertMsg.style.display = 'none'; 
            }, 3000);
        } else {
            throw new Error('Erro ao salvar');
        }
    })
    .catch(error => {
        alertMsg.style.backgroundColor = '#f8d7da';
        alertMsg.style.color = '#721c24';
        alertMsg.style.border = '1px solid #f5c6cb';
        alertMsg.style.display = 'block';
        alertMsg.innerText = '❌ Erro ao salvar o prompt. Tente novamente.';
        
        setTimeout(() => { 
            alertMsg.style.display = 'none'; 
        }, 3000);
    });
}