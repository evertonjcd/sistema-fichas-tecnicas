# app.py
import streamlit as st
import pandas as pd
import tempfile
import base64
from datetime import datetime
import hashlib
import json
import os

# Configuração da página
st.set_page_config(
    page_title="Sistema de Fichas Técnicas",
    page_icon="🍳",
    layout="wide"
)

# Sistema de autenticação
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f)

def init_admin_user():
    users = load_users()
    if 'admin' not in users:
        users['admin'] = {
            'password': hash_password('admin123'),
            'active': True,
            'created_at': datetime.now().isoformat()
        }
        save_users(users)

def check_login(username, password):
    users = load_users()
    if username in users and users[username]['active']:
        return users[username]['password'] == hash_password(password)
    return False

def is_user_active(username):
    users = load_users()
    return users.get(username, {}).get('active', False)

# Inicializar dados
if 'df_ingredientes' not in st.session_state:
    st.session_state.df_ingredientes = pd.DataFrame(columns=['Ingrediente', 'Custo', 'Unidade'])
if 'df_fichas' not in st.session_state:
    st.session_state.df_fichas = pd.DataFrame(columns=['Nome', 'Ingredientes', 'ModoPreparo', 'RendimentoKg', 'RendimentoUn', 'CustoTotal'])
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'ingredientes_ficha' not in st.session_state:
    st.session_state.ingredientes_ficha = []

# Página de login
def login_page():
    st.title("🍳 Sistema de Fichas Técnicas")
    st.subheader("Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            if check_login(username, password):
                st.session_state.current_user = username
                st.success(f"Bem-vindo, {username}!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos, ou usuário está bloqueado")
    
    # Área administrativa (apenas para admin)
    st.markdown("---")
    st.subheader("Área Administrativa")
    admin_password = st.text_input("Senha de Administrador", type="password", key="admin_pass")
    
    if st.button("Acessar Área Admin"):
        if admin_password == "admin123":  # Senha master para configurar usuários
            st.session_state.show_admin = True
            st.rerun()

# Página administrativa
def admin_page():
    st.title("👨‍💼 Área Administrativa")
    
    users = load_users()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Gerenciar Usuários")
        
        with st.form("add_user"):
            st.write("Adicionar Novo Usuário")
            new_user = st.text_input("Nome de usuário")
            new_pass = st.text_input("Senha", type="password")
            add_user = st.form_submit_button("Adicionar Usuário")
            
            if add_user and new_user and new_pass:
                if new_user in users:
                    st.error("Usuário já existe!")
                else:
                    users[new_user] = {
                        'password': hash_password(new_pass),
                        'active': True,
                        'created_at': datetime.now().isoformat()
                    }
                    save_users(users)
                    st.success(f"Usuário {new_user} criado com sucesso!")
    
    with col2:
        st.subheader("Usuários Existentes")
        for username, user_data in users.items():
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                st.write(f"**{username}**")
            with col_b:
                status = "Ativo" if user_data['active'] else "Bloqueado"
                st.write(status)
            with col_c:
                if username != 'admin':
                    if user_data['active']:
                        if st.button("Bloquear", key=f"block_{username}"):
                            users[username]['active'] = False
                            save_users(users)
                            st.rerun()
                    else:
                        if st.button("Ativar", key=f"activate_{username}"):
                            users[username]['active'] = True
                            save_users(users)
                            st.rerun()
    
    if st.button("Voltar ao Sistema"):
        st.session_state.show_admin = False
        st.rerun()

# Função para calcular custo
def calcular_custo_ficha(ingredientes):
    custo_total = 0
    for ing in ingredientes:
        if ing['ingrediente'] and ing['quantidade']:
            try:
                ingrediente_data = st.session_state.df_ingredientes[
                    st.session_state.df_ingredientes['Ingrediente'] == ing['ingrediente']
                ]
                if not ingrediente_data.empty:
                    custo_unit = ingrediente_data['Custo'].values[0]
                    custo_total += float(custo_unit) * float(ing['quantidade'])
            except:
                pass
    return custo_total

# Página principal do sistema
def main_system():
    st.sidebar.title(f"👋 Bem-vindo, {st.session_state.current_user}")
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.current_user = None
        st.session_state.show_admin = False
        st.rerun()
    
    if st.session_state.current_user == 'admin':
        if st.sidebar.button("👨‍💼 Área Administrativa"):
            st.session_state.show_admin = True
            st.rerun()
    
    aba1, aba2, aba3 = st.tabs(["📝 Ingredientes", "🍽️ Fichas Técnicas", "📊 Relatórios"])
    
    with aba1:
        st.header("Cadastro de Ingredientes")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("ingrediente_form"):
                st.subheader("Novo Ingrediente")
                ingrediente = st.text_input("Nome do Ingrediente")
                custo = st.number_input("Custo (R$/unidade)", min_value=0.0, step=0.01)
                unidade = st.selectbox("Unidade de Medida", ["kg", "L", "un", "g", "ml"])
                submit_ingrediente = st.form_submit_button("Adicionar Ingrediente")
                
                if submit_ingrediente and ingrediente:
                    novo_ingrediente = pd.DataFrame({
                        'Ingrediente': [ingrediente],
                        'Custo': [custo],
                        'Unidade': [unidade]
                    })
                    st.session_state.df_ingredientes = pd.concat([
                        st.session_state.df_ingredientes, 
                        novo_ingrediente
                    ], ignore_index=True)
                    st.success(f"Ingrediente {ingrediente} adicionado!")
        
        with col2:
            st.subheader("Ingredientes Cadastrados")
            if not st.session_state.df_ingredientes.empty:
                st.dataframe(st.session_state.df_ingredientes, use_container_width=True)
                
                # Opção para excluir ingrediente
                ingredientes_list = st.session_state.df_ingredientes['Ingrediente'].tolist()
                ingrediente_excluir = st.selectbox("Selecionar ingrediente para excluir:", [""] + ingredientes_list)
                if st.button("Excluir Ingrediente") and ingrediente_excluir:
                    st.session_state.df_ingredientes = st.session_state.df_ingredientes[
                        st.session_state.df_ingredientes['Ingrediente'] != ingrediente_excluir
                    ]
                    st.success(f"Ingrediente {ingrediente_excluir} excluído!")
                    st.rerun()
            else:
                st.info("Nenhum ingrediente cadastrado ainda.")
    
    with aba2:
        st.header("Fichas Técnicas")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("ficha_form"):
                st.subheader("Nova Ficha Técnica")
                nome_produto = st.text_input("Nome do Produto")
                
                st.write("**Ingredientes:**")
                ingredientes_ficha = []
                
                # Linhas dinâmicas para ingredientes
                if 'num_ingredientes' not in st.session_state:
                    st.session_state.num_ingredientes = 1
                
                for i in range(st.session_state.num_ingredientes):
                    col_ing, col_qtd = st.columns(2)
                    with col_ing:
                        ingrediente = st.selectbox(
                            f"Ingrediente {i+1}",
                            [""] + st.session_state.df_ingredientes['Ingrediente'].tolist(),
                            key=f"ing_{i}"
                        )
                    with col_qtd:
                        quantidade = st.number_input(
                            "Quantidade",
                            min_value=0.0,
                            step=0.1,
                            key=f"qtd_{i}"
                        )
                    ingredientes_ficha.append({
                        'ingrediente': ingrediente,
                        'quantidade': quantidade
                    })
                
                if st.button("+ Adicionar mais ingredientes"):
                    st.session_state.num_ingredientes += 1
                    st.rerun()
                
                if st.session_state.num_ingredientes > 1 and st.button("- Remover último ingrediente"):
                    st.session_state.num_ingredientes -= 1
                    st.rerun()
                
                modo_preparo = st.text_area("Modo de Preparo", height=100)
                rendimento_kg = st.number_input("Rendimento (kg)", min_value=0.0, step=0.1)
                rendimento_un = st.number_input("Rendimento (unidades)", min_value=0, step=1)
                
                submit_ficha = st.form_submit_button("Salvar Ficha Técnica")
                
                if submit_ficha and nome_produto and ingredientes_ficha:
                    # Calcular custo total
                    custo_total = calcular_custo_ficha(ingredientes_ficha)
                    
                    # Formatar lista de ingredientes
                    ingredientes_str = "; ".join([
                        f"{ing['ingrediente']}: {ing['quantidade']}" 
                        for ing in ingredientes_ficha 
                        if ing['ingrediente']
                    ])
                    
                    nova_ficha = pd.DataFrame({
                        'Nome': [nome_produto],
                        'Ingredientes': [ingredientes_str],
                        'ModoPreparo': [modo_preparo],
                        'RendimentoKg': [rendimento_kg],
                        'RendimentoUn': [rendimento_un],
                        'CustoTotal': [custo_total]
                    })
                    
                    st.session_state.df_fichas = pd.concat([
                        st.session_state.df_fichas, 
                        nova_ficha
                    ], ignore_index=True)
                    
                    st.success(f"Ficha técnica {nome_produto} salva!")
                    st.session_state.num_ingredientes = 1
                    st.rerun()
        
        with col2:
            st.subheader("Fichas Salvas")
            if not st.session_state.df_fichas.empty:
                for idx, ficha in st.session_state.df_fichas.iterrows():
                    with st.expander(f"🍽️ {ficha['Nome']} - R$ {ficha['CustoTotal']:.2f}"):
                        st.write(f"**Ingredientes:** {ficha['Ingredientes']}")
                        st.write(f"**Modo de Preparo:** {ficha['ModoPreparo']}")
                        st.write(f"**Rendimento:** {ficha['RendimentoKg']} kg | {ficha['RendimentoUn']} unidades")
                        st.write(f"**Custo Total:** R$ {ficha['CustoTotal']:.2f}")
                        
                        # Botão de impressão
                        if st.button(f"🖨️ Imprimir", key=f"print_{idx}"):
                            generate_printable_html(ficha)
            
            else:
                st.info("Nenhuma ficha técnica cadastrada ainda.")
    
    with aba3:
        st.header("Relatórios e Estatísticas")
        
        if not st.session_state.df_fichas.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Resumo de Custos")
                custo_total = st.session_state.df_fichas['CustoTotal'].sum()
                media_custo = st.session_state.df_fichas['CustoTotal'].mean()
                st.metric("Custo Total Todas as Fichas", f"R$ {custo_total:.2f}")
                st.metric("Custo Médio por Ficha", f"R$ {media_custo:.2f}")
            
            with col2:
                st.subheader("Ficha Mais Cara")
                idx_mais_cara = st.session_state.df_fichas['CustoTotal'].idxmax()
                ficha_mais_cara = st.session_state.df_fichas.loc[idx_mais_cara]
                st.write(f"**{ficha_mais_cara['Nome']}**")
                st.write(f"Custo: R$ {ficha_mais_cara['CustoTotal']:.2f}")
        
        else:
            st.info("Nenhuma ficha técnica para mostrar relatórios.")

# Função para gerar HTML para impressão
def generate_printable_html(ficha):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ficha Técnica - {ficha['Nome']}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #333;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            .section {{
                margin-bottom: 20px;
            }}
            .ingredientes {{
                border: 1px solid #ddd;
                padding: 15px;
                background-color: #f9f9f9;
            }}
            .custo {{
                background-color: #e8f5e8;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }}
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>FICHA TÉCNICA</h1>
            <h2>{ficha['Nome']}</h2>
        </div>
        
        <div class="section">
            <h3>📋 INGREDIENTES</h3>
            <div class="ingredientes">
                {ficha['Ingredientes'].replace(';', '<br>')}
            </div>
        </div>
        
        <div class="section">
            <h3>👨‍🍳 MODO DE PREPARO</h3>
            <p>{ficha['ModoPreparo'].replace('\n', '<br>')}</p>
        </div>
        
        <div class="section">
            <h3>⚖️ RENDIMENTO</h3>
            <p><strong>Peso:</strong> {ficha['RendimentoKg']} kg</p>
            <p><strong>Unidades:</strong> {ficha['RendimentoUn']} unidades</p>
        </div>
        
        <div class="custo">
            <h3>💰 CUSTO TOTAL: R$ {ficha['CustoTotal']:.2f}</h3>
        </div>
        
        <div class="no-print" style="margin-top: 30px; text-align: center;">
            <button onclick="window.print()">🖨️ Imprimir</button>
            <button onclick="window.close()">❌ Fechar</button>
        </div>
    </body>
    </html>
    """
    
    # Criar arquivo temporário e fornecer download
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(html_content)
        temp_path = f.name
    
    # Ler o arquivo e codificar em base64 para download
    with open(temp_path, 'rb') as f:
        bytes_data = f.read()
        b64 = base64.b64encode(bytes_data).decode()
    
    href = f'<a href="data:file/html;base64,{b64}" download="ficha_tecnica_{ficha["Nome"]}.html">📥 Baixar Ficha para Impressão</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    # Também mostrar preview
    with st.expander("👁️ Visualizar Ficha"):
        st.components.v1.html(html_content, height=600, scrolling=True)

# App principal
def main():
    init_admin_user()
    
    if st.session_state.get('show_admin', False):
        admin_page()
    elif st.session_state.current_user is None:
        login_page()
    else:
        main_system()

if __name__ == "__main__":
    main()
