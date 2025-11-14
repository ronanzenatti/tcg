from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
import requests  # Importa a biblioteca requests
import random

app = Flask(__name__)


# --- Configuração do Banco de Dados ---
# String de conexão: 'mysql+mysqlclient://USUARIO:SENHA@SERVIDOR/NOME_DO_DB'
# Troque 'root:senha' pelo seu usuário e senha do MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/poke_tcg_db'
# Desativa avisos desnecessários
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Chave Secreta para Sessão ---
# Necessário para 'session' e 'flash'
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar'

bcrypt = Bcrypt(app)

# --- Inicializa a extensão ---
db = SQLAlchemy(app)


class Usuario(db.Model):
    """Modelo para armazenar informações dos usuários."""

    # Define explicitamente o nome da tabela no BD
    __tablename__ = 'usuarios'

    # Colunas da tabela
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    # Relação: Um Usuário pode ter muitas Cartas
    # 'backref' cria um atributo virtual 'usuario' na classe Carta
    cartas = db.relationship('Carta', backref='usuario', lazy=True)

    def set_senha(self, senha):
        """Cria hash da senha usando bcrypt."""
        self.password_hash = bcrypt.generate_password_hash(
            senha).decode('utf-8')

    def check_senha(self, senha):
        """Verifica se a senha está correta."""
        return bcrypt.check_password_hash(self.password_hash, senha)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Carta(db.Model):
    """Modelo para armazenar as cartas capturadas pelos usuários."""

    # Define explicitamente o nome da tabela no BD
    __tablename__ = 'cartas'

    # Colunas da tabela
    id = db.Column(db.Integer, primary_key=True)
    pokemon_id = db.Column(db.Integer, nullable=False)
    nome = db.Column(db.String(100), nullable=False)

    # Chave Estrangeira: Liga esta carta a um usuário
    user_id = db.Column(db.Integer, db.ForeignKey(
        'usuarios.id'), nullable=False)

    def __repr__(self):
        return f'<Carta {self.nome} (User {self.user_id})>'


# URL da PokeAPI para pegar os 151 primeiros Pokémon
POKEAPI_URL = "https://pokeapi.co/api/v2/pokemon?limit=151"


def carregar_dados_pokemon():
    """Busca os dados dos 151 Pokémon na PokeAPI."""
    try:
        response = requests.get(POKEAPI_URL)
        response.raise_for_status()  # Lança um erro se a requisição falhar

        data = response.json()  # Converte a resposta JSON em um dicionário Python
        resultados = data['results']  # Pega a lista de Pokémon

        lista_pokemon = []
        # Enumera os resultados para obter um índice (começando em 1)
        for i, poke in enumerate(resultados):
            pokemon_id = i + 1
            lista_pokemon.append({
                'id': pokemon_id,
                'nome': poke['name'].title(),  # 'bulbasaur' -> 'Bulbasaur'
                'capturado': False  # Por padrão, o usuário não tem nenhum
            })
        return lista_pokemon

    except requests.RequestException as e:
        print(f"Erro ao buscar dados da PokeAPI: {e}")
        return []  # Retorna lista vazia em caso de erro


LISTA_GLOBAL_POKEMON = carregar_dados_pokemon()


@app.route('/')
def index():
    nome_treinador = "Ash Ketchum"
    cidade = 'Fatec City'

    return render_template('index.html',
                           treinador=nome_treinador,
                           # lista_pokemon=LISTA_GLOBAL_POKEMON,
                           cidade=cidade)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Rota para registro de novos usuários."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        # Validações básicas
        if len(username) < 3:
            flash('Nome de usuário deve ter no mínimo 3 caracteres.', 'warning')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Senha deve ter no mínimo 6 caracteres.', 'warning')
            return redirect(url_for('register'))

        # Verifica se o usuário já existe
        usuario_existente = Usuario.query.filter_by(username=username).first()
        if usuario_existente:
            flash('Este nome de usuário já existe. Escolha outro.', 'warning')
            return redirect(url_for('register'))

        # Cria novo usuário
        novo_usuario = Usuario(username=username)
        novo_usuario.set_senha(password)

        try:
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Conta criada com sucesso! Faça o login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar conta. Tente novamente.', 'danger')
            print(f"Erro ao criar usuário: {e}")
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota para login de usuários."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        # Busca o usuário no banco
        usuario = Usuario.query.filter_by(username=username).first()

        # Verifica o usuário e a senha
        if usuario and usuario.check_senha(password):
            # Armazena o ID do usuário na 'session'
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            flash('Login bem-sucedido! Bem-vindo de volta!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Rota para logout de usuários."""
    # Remove o usuário da 'session'
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Você foi desconectado. Até logo!', 'info')
    return redirect(url_for('index'))


@app.route('/abrir_pacote', methods=['POST'])
def abrir_pacote():
    """Sorteia 4 cartas da lista global e as retorna como JSON."""
    try:
        if not LISTA_GLOBAL_POKEMON:
            # Caso a API tenha falhado na inicialização
            return jsonify({'erro': 'Falha ao carregar dados dos Pokémon'}), 500

        # Usamos random.sample para sortear 4 cartas ÚNICAS
        cartas_sorteadas = random.sample(LISTA_GLOBAL_POKEMON, 4)

        # Retornamos os dados das 4 cartas em formato JSON
        return jsonify({'cartas': cartas_sorteadas})

    except Exception as e:
        # Captura qualquer erro inesperado
        return jsonify({'erro': str(e)}), 500


@app.route('/api/pokemon')
def api_pokemon():
    """Retorna a lista completa de 151 Pokémon como JSON."""
    if not LISTA_GLOBAL_POKEMON:
        return jsonify({'erro': 'Falha ao carregar dados dos Pokémon'}), 500

    return jsonify(LISTA_GLOBAL_POKEMON)


@app.route('/api/migrar_para_nuvem', methods=['POST'])
def migrar_para_nuvem():
    """Migra a coleção do Local Storage para o banco de dados."""

    # 1. Verifica se o usuário está logado
    if 'user_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401

    try:
        user_id = session['user_id']

        # 2. Recebe a coleção do Local Storage (enviada pelo JS)
        colecao_local = request.json
        if not colecao_local:
            return jsonify({'erro': 'Nenhum dado recebido.'}), 400

        # Carrega a lista-mestre de nomes (para referência)
        mapa_nomes = {poke['id']: poke['nome']
                      for poke in LISTA_GLOBAL_POKEMON}

        novas_cartas_adicionadas = 0

        # 3. Processa a migração
        for poke_id_str in colecao_local.keys():
            poke_id = int(poke_id_str)

            # Verifica se o usuário JÁ possui esta carta no DB (Evita duplicatas)
            carta_existente = Carta.query.filter_by(
                user_id=user_id,
                pokemon_id=poke_id
            ).first()

            if not carta_existente:
                nome_pokemon = mapa_nomes.get(poke_id, 'Desconhecido')
                nova_carta = Carta(
                    pokemon_id=poke_id,
                    nome=nome_pokemon,
                    user_id=user_id
                )
                db.session.add(nova_carta)
                novas_cartas_adicionadas += 1

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'{novas_cartas_adicionadas} novas cartas salvas na sua conta.'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Erro na migração: {e}")
        return jsonify({'erro': 'Erro ao salvar dados.'}), 500


if __name__ == '__main__':
    app.run(debug=True)
