// ==========================================
// CONSTANTES E VARIÁVEIS GLOBAIS
// ==========================================

// Chaves do Local Storage
const CHAVE_COLECAO = 'poke_colecao';
const CHAVE_TIMER = 'poke_timer';

// Variável global para guardar o estado da coleção
let minhaColecao = {};

// ==========================================
// FUNÇÕES DE LÓGICA DA COLEÇÃO
// ==========================================

function carregarColecaoDoStorage() {
    console.log("Carregando coleção do Local Storage...");
    const colecaoSalva = localStorage.getItem(CHAVE_COLECAO);

    if (colecaoSalva) {
        minhaColecao = JSON.parse(colecaoSalva);
    } else {
        minhaColecao = {};
    }
}

function salvarColecaoNoStorage() {
    console.log("Salvando coleção...");
    localStorage.setItem(CHAVE_COLECAO, JSON.stringify(minhaColecao));
}

function criarCardHTML(carta, capturado = false) {
    // Classe CSS dinâmica para o card (cinza se não capturado)
    const classeCapturado = capturado ? "shadow-sm" : "nao-capturado";

    // Badge dinâmico (selo)
    const badge = capturado
        ? '<span class="badge bg-success">Capturado</span>'
        : '<span class="badge bg-secondary">Não Capturado</span>';

    return `
        <div class="col-md-3 mb-4">
            <div class="card text-center ${classeCapturado}">
                <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${carta.id}.png" 
                     class="card-img-top p-3" 
                     alt="${carta.nome}">
                <div class="card-body">
                    <h5 class="card-title">${carta.nome}</h5>
                    <p class="card-text small text-muted">ID: #${carta.id}</p>
                    ${badge}
                </div>
            </div>
        </div>
    `;
}

async function renderizarGaleriaPrincipal() {
    console.log("Renderizando galeria principal...");
    const galeria = document.getElementById('galeria-principal');
    if (!galeria) return;

    // Limpa a galeria (remove o "Carregando...")
    galeria.innerHTML = '';

    try {
        // 1. Busca a lista-mestre de 151 Pokémon
        const response = await fetch('/api/pokemon');
        if (!response.ok) throw new Error('Falha ao buscar /api/pokemon');
        const listaMestre = await response.json();

        // 2. Constrói o HTML
        let htmlGaleria = '';
        for (const poke of listaMestre) {
            // 3. Verifica se o ID do poke está na 'minhaColecao'
            const capturado = minhaColecao.hasOwnProperty(poke.id);
            htmlGaleria += criarCardHTML(poke, capturado);
        }

        // 4. Insere todo o HTML de uma vez (mais rápido)
        galeria.innerHTML = htmlGaleria;

    } catch (error) {
        console.error("Erro ao renderizar galeria:", error);
        galeria.innerHTML = '<p class="text-danger">Erro ao carregar a Pokédex. Tente recarregar a página.</p>';
    }
}

// ==========================================
// LÓGICA DO MODAL DE CARTAS
// ==========================================

function exibirCartasNoModal(cartas) {
    const corpoModal = document.getElementById('corpo-modal-cartas');
    corpoModal.innerHTML = '';
    const row = document.createElement('div');
    row.className = 'row';

    let novasCartasCapturadas = false;

    cartas.forEach(carta => {
        // Verifica se a carta JÁ estava na coleção
        const ehNova = !minhaColecao.hasOwnProperty(carta.id);

        if (ehNova) {
            console.log(`Nova captura: ${carta.nome}`);
            minhaColecao[carta.id] = true;  // Adiciona à coleção
            novasCartasCapturadas = true;
        }

        const cardHTML = `
            <div class="col-md-6 mb-3">
                <div class="card text-center shadow-sm">
                    <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${carta.id}.png" 
                         class="card-img-top p-3" alt="${carta.nome}">
                    <div class="card-body">
                        <h5 class="card-title">${carta.nome}</h5>
                        ${ehNova
                ? '<span class="badge bg-primary">Nova!</span>'
                : '<span class="badge bg-warning">Duplicata</span>'}
                    </div>
                </div>
            </div>
        `;
        row.innerHTML += cardHTML;
    });

    corpoModal.appendChild(row);

    // Se houveram cartas novas, salva e re-renderiza a galeria
    if (novasCartasCapturadas) {
        salvarColecaoNoStorage();
        renderizarGaleriaPrincipal();  // Atualiza a galeria principal em tempo real
    }
}

function salvarNaNuvem() {
    console.log("Iniciando salvamento na nuvem...");
    const btnSalvar = document.getElementById('btn-salvar-nuvem');

    // Pega a coleção atual do Local Storage
    const colecaoSalva = localStorage.getItem(CHAVE_COLECAO);
    if (!colecaoSalva || colecaoSalva === '{}') {
        alert('Sua coleção local está vazia. Abra alguns pacotes primeiro!');
        return;
    }

    btnSalvar.disabled = true;
    const textoOriginal = btnSalvar.innerHTML;
    btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';

    fetch('/api/migrar_para_nuvem', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: colecaoSalva  // Envia a string JSON do Local Storage
    })
        .then(response => response.json())
        .then(data => {
            if (data.erro) {
                throw new Error(data.erro);
            }

            alert(data.mensagem);  // Ex: "5 novas cartas salvas na sua conta."

            // Opcional: Limpar o Local Storage após salvar na nuvem?
            // localStorage.removeItem(CHAVE_COLECAO);
            // location.reload();
        })
        .catch(error => {
            console.error('Erro ao salvar na nuvem:', error);
            alert(`Erro ao salvar: ${error.message}`);
        })
        .finally(() => {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = textoOriginal;
        });
}


// ==========================================
// LÓGICA PRINCIPAL (DOMContentLoaded)
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // 1. Carrega a coleção salva
    carregarColecaoDoStorage();

    // 2. Renderiza a galeria principal
    renderizarGaleriaPrincipal();

    const btnAbrir = document.getElementById('btn-abrir-pacote');
    const modalElement = document.getElementById('modal-cartas-reveladas');
    if (!btnAbrir || !modalElement) return;

    if (btnAbrir && modalElement) {
        const meuModal = new bootstrap.Modal(modalElement);

        // 3. Evento de clique no botão
        btnAbrir.addEventListener('click', () => {
            btnAbrir.disabled = true;
            btnAbrir.textContent = "Sorteando...";

            fetch('/abrir_pacote', { method: 'POST' })
                .then(response => {
                    if (!response.ok) throw new Error('Falha na requisição');
                    return response.json();
                })
                .then(data => {
                    if (data.erro) throw new Error(data.erro);

                    console.log("Cartas recebidas:", data.cartas);
                    exibirCartasNoModal(data.cartas);
                    meuModal.show();
                })
                .catch(error => {
                    console.error('Erro ao abrir pacote:', error);
                    alert('Não foi possível abrir o pacote. Tente novamente.');
                })
                .finally(() => {
                    btnAbrir.disabled = false;
                    btnAbrir.textContent = "Abrir Pacote!";
                });
        });
    }
    // --- LIGA O BOTÃO DE SALVAR NA NUVEM ---
    const btnSalvar = document.getElementById('btn-salvar-nuvem');
    if (btnSalvar) {
        btnSalvar.addEventListener('click', salvarNaNuvem);
    }
});