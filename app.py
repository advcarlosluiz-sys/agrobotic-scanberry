"""
Agrobotic ScanBerry — Aplicação Flask Principal
================================================
Assistente agronômico para morangos via IA (OpenAI GPT-4o Vision).
"""
import os
import uuid
import json
import csv
import io
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_file, send_from_directory, jsonify, session, Response)
from werkzeug.utils import secure_filename
from config import Config
from models import db, Analise, Configuracao, Usuario
from scanberry_skill import analisar_imagem
from pdf_report import gerar_pdf_analise
import markdown

# ── App Factory ──────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    # Criar admin padrão se não existir
    if not Usuario.query.filter_by(is_admin=True).first():
        admin = Usuario(
            nome='Administrador', 
            whatsapp='0000', 
            is_admin=True,
            aceitou_termos=True,
            data_consentimento=datetime.utcnow()
        )
        admin.set_senha('admin123')
        db.session.add(admin)
        db.session.commit()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def get_api_key():
    """Obtém a API key: primeiro do banco, depois do ambiente."""
    with app.app_context():
        db_key = Configuracao.get_valor('openai_api_key', '')
    return db_key or app.config.get('OPENAI_API_KEY', '')


def get_usuario_logado():
    """Retorna o usuário logado ou None se não existir no banco."""
    uid = session.get('usuario_id')
    if uid:
        user = Usuario.query.get(uid)
        if not user:
            # Limpa sessão órfã se o usuário foi deletado do banco
            session.pop('usuario_id', None)
        return user
    return None


def login_required(f):
    """Decorator que exige login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Faça login para acessar.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator que exige admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_usuario_logado()
        if not user or not user.is_admin:
            flash('Acesso restrito ao administrador.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_user():
    """Injeta usuário logado em todos os templates."""
    return dict(usuario_logado=get_usuario_logado())


# ── ROTAS DE AUTENTICAÇÃO ────────────────────────────────

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Cadastro de novo usuário."""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        endereco = request.form.get('endereco', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        
        if not nome or not whatsapp or not senha:
            flash('Nome, WhatsApp e senha são obrigatórios.', 'error')
            return redirect(url_for('cadastro'))
            
        termos = request.form.get('termos')
        if not termos:
            flash('Você precisa aceitar os Termos de Uso para continuar.', 'error')
            return redirect(url_for('cadastro'))
            
        if len(senha) < 4:
            flash('A senha deve ter pelo menos 4 caracteres.', 'error')
            return redirect(url_for('cadastro'))
        if Usuario.query.filter_by(whatsapp=whatsapp).first():
            flash('Já existe uma conta com este WhatsApp.', 'error')
            return redirect(url_for('cadastro'))
        
        user = Usuario(nome=nome, whatsapp=whatsapp, endereco=endereco,
                       cidade=cidade, estado=estado, email=email,
                       aceitou_termos=True, data_consentimento=datetime.utcnow())
        user.set_senha(senha)
        db.session.add(user)
        db.session.commit()
        
        session.permanent = True
        session['usuario_id'] = user.id
        flash(f'Bem-vindo(a), {user.nome}! Cadastro realizado.', 'success')
        return redirect(url_for('index'))
    
    return render_template('cadastro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuário."""
    if request.method == 'POST':
        whatsapp = request.form.get('whatsapp', '').strip()
        senha = request.form.get('senha', '')
        
        user = Usuario.query.filter_by(whatsapp=whatsapp).first()
        if user and user.verificar_senha(senha) and user.ativo:
            session.permanent = True
            session['usuario_id'] = user.id
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Bem-vindo(a), {user.nome}!', 'success')
            return redirect(url_for('index'))
        
        flash('WhatsApp ou senha incorretos.', 'error')
        return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout do usuário."""
    session.pop('usuario_id', None)
    flash('Você saiu da sua conta.', 'success')
    return redirect(url_for('index'))


# ── ROTAS PRINCIPAIS ─────────────────────────────────────

@app.route('/')
def index():
    """Página Inicial (Landing Page)."""
    if session.get('usuario_id'):
        return redirect(url_for('dashboard_produtor'))
    return render_template('landing.html')


@app.route('/dashboard')
@login_required
def dashboard_produtor():
    """Painel do Produtor logado."""
    user = get_usuario_logado()
    if not user:
        return redirect(url_for('logout'))
        
    # Se for admin, manda para o painel admin
    if user.is_admin:
        return redirect(url_for('admin_dashboard'))
        
    recentes = Analise.query.filter_by(usuario_id=user.id).order_by(Analise.created_at.desc()).limit(5).all()
    
    total = Analise.query.filter_by(usuario_id=user.id).count()
    stats = {
        'total': total,
        'critico': Analise.query.filter_by(usuario_id=user.id, nivel_urgencia='critico').count(),
        'alto': Analise.query.filter_by(usuario_id=user.id, nivel_urgencia='alto').count(),
        'medio': Analise.query.filter_by(usuario_id=user.id, nivel_urgencia='medio').count(),
        'baixo': Analise.query.filter_by(usuario_id=user.id, nivel_urgencia='baixo').count(),
    }
    return render_template('index.html', recentes=recentes, stats=stats)


@app.route('/analise', methods=['GET'])
@login_required
def analise_form():
    """Formulário de análise."""
    has_api = bool(get_api_key())
    return render_template('analise.html', has_api=has_api)


@app.route('/analise', methods=['POST'])
@login_required
def analise_processar():
    """Processa imagem + dados da lavoura via IA."""
    # Verificar imagem
    if 'imagem' not in request.files:
        flash('Nenhuma imagem enviada.', 'error')
        return redirect(url_for('analise_form'))
    
    arquivo = request.files['imagem']
    if arquivo.filename == '':
        flash('Selecione uma imagem.', 'error')
        return redirect(url_for('analise_form'))
    
    if not allowed_file(arquivo.filename):
        flash('Formato de imagem não suportado. Use JPG, PNG, GIF ou WebP.', 'error')
        return redirect(url_for('analise_form'))
    
    # Salvar imagem
    ext = arquivo.filename.rsplit('.', 1)[1].lower()
    nome_arquivo = f"{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
    arquivo.save(caminho)
    
    # Coletar dados da lavoura
    dados_lavoura = {
        'parte_planta': request.form.get('parte_planta', ''),
        'tipo_cultivo': request.form.get('tipo_cultivo', ''),
        'idade_planta': request.form.get('idade_planta', ''),
        'variedade': request.form.get('variedade', ''),
        'municipio': request.form.get('municipio', ''),
        'tipo_irrigacao': request.form.get('tipo_irrigacao', ''),
        'ultima_irrigacao': request.form.get('ultima_irrigacao', ''),
        'ultima_adubacao': request.form.get('ultima_adubacao', ''),
        'sintoma_percebido': request.form.get('sintoma_percebido', ''),
        'tempo_sintoma': request.form.get('tempo_sintoma', ''),
        'problema_aumentando': request.form.get('problema_aumentando', ''),
        'plantas_afetadas': request.form.get('plantas_afetadas', ''),
        'historico': request.form.get('historico', ''),
        'clima_recente': request.form.get('clima_recente', ''),
    }
    
    # Analisar via IA
    api_key = get_api_key()
    modelo = app.config.get('OPENAI_MODEL', 'gpt-4o-mini')
    resposta = analisar_imagem(caminho, dados_lavoura, api_key, modelo)
    
    # Salvar no banco
    user = get_usuario_logado()
    analise = Analise(
        usuario_id=user.id if user else None,
        imagem_path=nome_arquivo,
        imagem_nome=secure_filename(arquivo.filename),
        diagnostico_provavel=resposta.get('diagnostico_provavel', ''),
        categoria=resposta.get('categoria', 'desconhecido'),
        nivel_urgencia=resposta.get('nivel_de_urgencia', 'baixo'),
        confianca=resposta.get('confianca', 0.0),
        parte_afetada=resposta.get('parte_afetada', 'desconhecido'),
    )
    analise.set_dados_lavoura(dados_lavoura)
    analise.set_resposta_ia(resposta)
    
    db.session.add(analise)
    db.session.commit()
    
    return redirect(url_for('resultado', id=analise.id))


@app.route('/resultado/<int:id>')
@login_required
def resultado(id):
    """Exibe resultado da análise (seguro)."""
    analise = Analise.query.get_or_404(id)
    user = get_usuario_logado()
    
    # Segurança: apenas dono ou admin vê o resultado
    if not user.is_admin and analise.usuario_id != user.id:
        flash('Você não tem permissão para ver esta análise.', 'error')
        return redirect(url_for('index'))
        
    resposta = analise.get_resposta_ia()
    dados = analise.get_dados_lavoura()
    return render_template('resultado.html', analise=analise, resposta=resposta, dados=dados)


@app.route('/historico')
@login_required
def historico():
    """Lista histórico de análises (filtrado por usuário)."""
    page = request.args.get('page', 1, type=int)
    filtro = request.args.get('filtro', '')
    user = get_usuario_logado()
    
    query = Analise.query.order_by(Analise.created_at.desc())
    
    # Se não for admin, vê apenas as próprias
    if not user.is_admin:
        query = query.filter_by(usuario_id=user.id)
        
    if filtro:
        query = query.filter(
            (Analise.categoria == filtro) |
            (Analise.nivel_urgencia == filtro)
        )
    
    analises = query.paginate(page=page, per_page=12, error_out=False)
    return render_template('historico.html', analises=analises, filtro=filtro)


@app.route('/historico/<int:id>/pdf')
def download_pdf(id):
    """Gera e baixa PDF do resultado."""
    analise = Analise.query.get_or_404(id)
    pdf_dir = os.path.join(app.root_path, 'static', 'reports')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"analise_{analise.id}.pdf")
    gerar_pdf_analise(analise, pdf_path)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"ScanBerry_Analise_{analise.id}.pdf")


@app.route('/configuracoes', methods=['GET', 'POST'])
@admin_required
def configuracoes():
    """Página de configurações da API key e Senha Admin."""
    if request.method == 'POST':
        # Caso seja alteração de API Key
        if 'api_key' in request.form:
            api_key = request.form.get('api_key', '').strip()
            Configuracao.set_valor('openai_api_key', api_key)
            flash('Chave API salva com sucesso!' if api_key else 'Chave API removida.', 'success')
            
        # Caso seja alteração de Senha Admin
        elif 'nova_senha' in request.form:
            nova_senha = request.form.get('nova_senha', '').strip()
            confirma_senha = request.form.get('confirma_senha', '').strip()
            
            if not nova_senha or len(nova_senha) < 4:
                flash('A nova senha deve ter pelo menos 4 caracteres.', 'error')
            elif nova_senha != confirma_senha:
                flash('As senhas não coincidem.', 'error')
            else:
                admin = get_usuario_logado()
                admin.set_senha(nova_senha)
                db.session.commit()
                flash('Senha do administrador alterada com sucesso!', 'success')
                
        return redirect(url_for('configuracoes'))
    
    current_key = Configuracao.get_valor('openai_api_key', '')
    masked = f"{current_key[:8]}...{current_key[-4:]}" if len(current_key) > 12 else ('••••••••' if current_key else '')
    return render_template('configuracoes.html', masked_key=masked, has_key=bool(current_key))


@app.route('/sobre')
def sobre():
    """Página sobre o projeto."""
    return render_template('sobre.html')


@app.route('/termos')
def termos():
    """Página de Termos de Uso e LGPD."""
    termos_path = os.path.join(app.root_path, 'TERMOS_DE_USO.md')
    conteudo = ""
    if os.path.exists(termos_path):
        with open(termos_path, 'r', encoding='utf-8') as f:
            conteudo = markdown.markdown(f.read())
    return render_template('termos.html', conteudo=conteudo)


@app.route('/download/skill')
def download_skill():
    """Download do arquivo skill.md."""
    skill_path = os.path.join(app.root_path, 'scanberry_skill.md')
    if os.path.exists(skill_path):
        return send_file(skill_path, as_attachment=True, download_name='scanberry_skill.md')
    flash('Arquivo não encontrado.', 'error')
    return redirect(url_for('sobre'))


@app.route('/download/relatorio')
def download_relatorio():
    """Download do relatório PDF original."""
    pdf_path = os.path.join(app.root_path, 'Relatorio_Completo_Agrobotic_ScanBerry.pdf')
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True,
                         download_name='Relatorio_Completo_Agrobotic_ScanBerry.pdf')
    flash('Arquivo não encontrado.', 'error')
    return redirect(url_for('sobre'))


@app.route('/api/analise', methods=['POST'])
def api_analise():
    """Endpoint API REST para análise programática."""
    if 'imagem' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400
    
    arquivo = request.files['imagem']
    if not allowed_file(arquivo.filename):
        return jsonify({'error': 'Formato não suportado'}), 400
    
    ext = arquivo.filename.rsplit('.', 1)[1].lower()
    nome_arquivo = f"{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
    arquivo.save(caminho)
    
    dados_lavoura = {}
    if request.form.get('dados_lavoura'):
        try:
            dados_lavoura = json.loads(request.form['dados_lavoura'])
        except json.JSONDecodeError:
            pass
    
    api_key = get_api_key()
    resposta = analisar_imagem(caminho, dados_lavoura, api_key)
    return jsonify(resposta)


# ── PAINEL ADMIN ─────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Dashboard do administrador."""
    total_usuarios = Usuario.query.filter_by(is_admin=False).count()
    total_analises = Analise.query.count()
    usuarios_recentes = Usuario.query.filter_by(is_admin=False).order_by(Usuario.created_at.desc()).limit(10).all()
    analises_recentes = Analise.query.order_by(Analise.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                           total_usuarios=total_usuarios, total_analises=total_analises,
                           usuarios_recentes=usuarios_recentes, analises_recentes=analises_recentes)


@app.route('/admin/clientes')
@admin_required
def admin_clientes():
    """Lista todos os clientes cadastrados."""
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '').strip()
    query = Usuario.query.filter_by(is_admin=False).order_by(Usuario.created_at.desc())
    if busca:
        query = query.filter(
            (Usuario.nome.ilike(f'%{busca}%')) |
            (Usuario.whatsapp.ilike(f'%{busca}%')) |
            (Usuario.cidade.ilike(f'%{busca}%'))
        )
    clientes = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/clientes.html', clientes=clientes, busca=busca)


@app.route('/admin/clientes/<int:id>')
@admin_required
def admin_cliente_detalhe(id):
    """Detalhes de um cliente."""
    cliente = Usuario.query.get_or_404(id)
    analises = Analise.query.filter_by(usuario_id=id).order_by(Analise.created_at.desc()).all()
    return render_template('admin/cliente_detalhe.html', cliente=cliente, analises=analises)


@app.route('/admin/clientes/exportar')
@admin_required
def admin_exportar_clientes():
    """Exporta clientes em CSV."""
    clientes = Usuario.query.filter_by(is_admin=False).order_by(Usuario.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nome', 'WhatsApp', 'Email', 'Cidade', 'Estado', 'Endereço', 'Análises', 'Cadastro'])
    for c in clientes:
        writer.writerow([c.id, c.nome, c.whatsapp, c.email, c.cidade, c.estado,
                         c.endereco, c.total_analises, c.created_at.strftime('%d/%m/%Y %H:%M')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=clientes_scanberry.csv'})


@app.route('/admin/clientes/novo', methods=['GET', 'POST'])
@admin_required
def admin_cliente_novo():
    """Cria um novo cliente manualmente pelo admin."""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        endereco = request.form.get('endereco', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '1234') # Senha padrão
        
        if Usuario.query.filter_by(whatsapp=whatsapp).first():
            flash('WhatsApp já cadastrado.', 'error')
            return redirect(url_for('admin_cliente_novo'))
            
        user = Usuario(nome=nome, whatsapp=whatsapp, endereco=endereco,
                       cidade=cidade, estado=estado, email=email)
        user.set_senha(senha)
        db.session.add(user)
        db.session.commit()
        flash(f'Cliente {nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('admin_clientes'))
    return render_template('admin/cliente_form.html', titulo="Novo Cliente")


@app.route('/admin/clientes/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def admin_cliente_editar(id):
    """Edita dados de um cliente."""
    cliente = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        cliente.nome = request.form.get('nome', '').strip()
        cliente.whatsapp = request.form.get('whatsapp', '').strip()
        cliente.endereco = request.form.get('endereco', '').strip()
        cliente.cidade = request.form.get('cidade', '').strip()
        cliente.estado = request.form.get('estado', '').strip()
        cliente.email = request.form.get('email', '').strip()
        
        nova_senha = request.form.get('senha', '').strip()
        if nova_senha:
            cliente.set_senha(nova_senha)
            
        db.session.commit()
        flash('Dados do cliente atualizados!', 'success')
        return redirect(url_for('admin_cliente_detalhe', id=cliente.id))
    return render_template('admin/cliente_form.html', cliente=cliente, titulo="Editar Cliente")


@app.route('/admin/clientes/<int:id>/excluir', methods=['POST'])
@admin_required
def admin_cliente_excluir(id):
    """Exclui um cliente e suas análises."""
    cliente = Usuario.query.get_or_404(id)
    # Deletar análises associadas
    Analise.query.filter_by(usuario_id=id).delete()
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído com sucesso.', 'success')
    return redirect(url_for('admin_clientes'))


# ── Filtros Jinja2 ───────────────────────────────────────

@app.template_filter('urgencia_cor')
def urgencia_cor(valor):
    return {'baixo':'#2d6a4f','medio':'#e9c46a','alto':'#f4845f','critico':'#e63946'}.get(valor, '#6c757d')

@app.template_filter('urgencia_icone')
def urgencia_icone(valor):
    return {'baixo':'✅','medio':'⚠️','alto':'🔶','critico':'🚨'}.get(valor, '❓')

@app.template_filter('categoria_nome')
def categoria_nome(valor):
    return {'doenca':'Doença','praga':'Praga','nutricao':'Nutrição','manejo':'Manejo',
            'irrigacao':'Irrigação','solo':'Solo','colheita':'Colheita','desconhecido':'Não Identificado'}.get(valor, valor)

@app.template_filter('categoria_icone')
def categoria_icone(valor):
    return {'doenca':'🦠','praga':'🐛','nutricao':'🧪','manejo':'🔧',
            'irrigacao':'💧','solo':'🌍','colheita':'🍓','desconhecido':'❓'}.get(valor, '❓')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
