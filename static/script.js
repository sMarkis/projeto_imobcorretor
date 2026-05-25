// Função para alternar as abas do painel
function switchTab(tabName) {
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active-content'));

    if (tabName === 'leads') {
        const menu = document.getElementById('menu-leads');
        const sec = document.getElementById('section-leads');
        if (menu) menu.classList.add('active');
        if (sec) sec.classList.add('active-content');
    } else if (tabName === 'config') {
        const menu = document.getElementById('menu-config');
        const sec = document.getElementById('section-config');
        if (menu) menu.classList.add('active');
        if (sec) sec.classList.add('active-content');
    } else if (tabName === 'historico') {
        const menu = document.getElementById('menu-historico');
        const sec = document.getElementById('section-historico');
        if (menu) menu.classList.add('active');
        if (sec) sec.classList.add('active-content');
    }
}

// Escuta a URL ao carregar para chavear a aba certa vinda de outra página (Ex: /imoveis)
document.addEventListener("DOMContentLoaded", function () {
    // Limpa o parâmetro de busca vazio da URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('q') && urlParams.get('q') === "") {
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    const hash = window.location.hash;
    
    if (hash === '#config') {
        switchTab('config');
    } else if (hash === '#historico') {
        switchTab('historico');
    } else {
        if (document.getElementById('section-leads')) {
            switchTab('leads');
        }
    }
});

// Função para salvar o prompt com confirmação e alerta temporário
function enviarPrompt() {
    const promptValue = document.getElementById('prompt-text').value;
    const alertMsg = document.getElementById('alert-msg');

    const confirmacao = confirm("Você realmente gostaria de salvar as alterações do Bot?");
    
    if (!confirmacao) {
        return; 
    }

    const formData = new FormData();
    formData.append('prompt', promptValue);

    fetch('/salvar-prompt', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alertMsg.style.backgroundColor = '#d4edda';
            alertMsg.style.color = '#155724';
            alertMsg.style.border = '1px solid #c3e6cb';
            alertMsg.style.display = 'block';
            alertMsg.innerText = '✅ Instrução foi Salva com Sucesso!';
            
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

// --- MÁSCARA DE MOEDA AUTOMÁTICA E RECURSOS DE CARTEIRA ---
document.addEventListener("DOMContentLoaded", function () {
    const inputPreco = document.getElementById('preco');

    if (inputPreco) {
        inputPreco.addEventListener('input', function (e) {
            let valor = e.target.value.replace(/\D/g, '');
            
            if (!valor) {
                e.target.value = '';
                return;
            }

            valor = (parseFloat(valor) / 100).toLocaleString('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            });

            e.target.value = valor;
        });

        inputPreco.addEventListener('focus', function (e) {
            if (e.target.value === '') {
                e.target.value = 'R$ 0,00';
            }
        });
    }
});

// Resgata os dados do card e popula o formulário esquerdo
function prepararEdicao(botao, id) {
    const card = botao.closest('.imovel-card');
    
    const titulo = card.querySelector('h4').innerText;
    const preco = card.querySelector('.imovel-price').innerText;
    const bairro = card.querySelector('p').innerText.replace('📍 ', '');
    const id_carac = card.querySelector('.imovel-carac');
    const caracteristicas = id_carac ? id_carac.innerText.replace('📋 ', '') : '';
    const descricao = card.querySelector('p:nth-of-type(2)').innerText;
    const tipo = card.querySelector('.raw-tipo').innerText;
    const categoria = card.querySelector('.raw-categoria').innerText;
    const imgElement = card.querySelector('.imovel-thumb img');
    const imagem_url = imgElement ? imgElement.getAttribute('src') : '';

    document.getElementById('imovel-id').value = id;
    document.getElementById('titulo').value = titulo;
    document.getElementById('tipo').value = tipo;
    document.getElementById('categoria').value = categoria;
    document.getElementById('preco').value = preco;
    document.getElementById('bairro').value = bairro;
    document.getElementById('caracteristicas').value = caracteristicas;
    document.getElementById('imagem_url').value = imagem_url;
    document.getElementById('descricao').value = descricao;

    document.getElementById('form-title').innerText = "Editar Imóvel #" + id;
    document.getElementById('form-title').style.color = "#3182ce";
    document.getElementById('btn-submit').innerText = "Atualizar Imóvel";
    document.getElementById('btn-cancel-edit').style.display = "block";
    
    document.querySelector('.form-card').scrollIntoView({ behavior: 'smooth' });
}

// Limpa o formulário e aborta o modo de edição
function cancelarEdicao() {
    document.getElementById('imovel-id').value = "";
    document.getElementById('titulo').value = "";
    document.getElementById('tipo').value = "Planta";
    document.getElementById('categoria').value = "Casa";
    document.getElementById('preco').value = "";
    document.getElementById('bairro').value = "";
    document.getElementById('caracteristicas').value = "";
    document.getElementById('imagem_url').value = "";
    document.getElementById('descricao').value = "";
    
    document.getElementById('form-title').innerText = "Novo Imóvel";
    document.getElementById('form-title').style.color = "#4299e1";
    document.getElementById('btn-submit').innerText = "Salvar Imóvel";
    document.getElementById('btn-cancel-edit').style.display = "none";
}

// Caixa de confirmação antes de remover do SQLite
function confirmarExclusao(id, titulo) {
    const certeza = confirm(`Tem certeza que deseja remover o imóvel "${titulo}" da sua base ativa?`);
    if (certeza) {
        window.location.href = `/deletar-imovel/${id}`;
    }
}