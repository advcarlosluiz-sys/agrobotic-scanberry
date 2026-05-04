"""
Agrobotic ScanBerry — Modelos de Banco de Dados
"""
import json
from datetime import datetime
from hashlib import sha256
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Usuario(db.Model):
    """Modelo para usuários da plataforma."""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(500), default='')
    cidade = db.Column(db.String(100), default='')
    estado = db.Column(db.String(2), default='')
    email = db.Column(db.String(200), default='')
    senha_hash = db.Column(db.String(64), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    aceitou_termos = db.Column(db.Boolean, default=False)
    data_consentimento = db.Column(db.DateTime, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=None)
    
    # Relacionamento com análises
    analises = db.relationship('Analise', backref='usuario', lazy='dynamic')
    
    def set_senha(self, senha):
        self.senha_hash = sha256(senha.encode('utf-8')).hexdigest()
    
    def verificar_senha(self, senha):
        return self.senha_hash == sha256(senha.encode('utf-8')).hexdigest()
    
    @property
    def total_analises(self):
        return self.analises.count()
    
    def __repr__(self):
        return f'<Usuario {self.id} - {self.nome}>'


class Analise(db.Model):
    """Modelo para armazenar análises realizadas."""
    __tablename__ = 'analises'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    imagem_path = db.Column(db.String(500), nullable=False)
    imagem_nome = db.Column(db.String(200), nullable=False)
    
    # Dados da lavoura (JSON)
    dados_lavoura = db.Column(db.Text, default='{}')
    
    # Resposta da IA (JSON completo)
    resposta_ia = db.Column(db.Text, default='{}')
    
    # Campos extraídos para busca rápida
    diagnostico_provavel = db.Column(db.String(500), default='')
    categoria = db.Column(db.String(50), default='desconhecido')
    nivel_urgencia = db.Column(db.String(20), default='baixo')
    confianca = db.Column(db.Float, default=0.0)
    parte_afetada = db.Column(db.String(50), default='desconhecido')
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_dados_lavoura(self):
        """Retorna dados da lavoura como dicionário."""
        try:
            return json.loads(self.dados_lavoura) if self.dados_lavoura else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_dados_lavoura(self, dados):
        """Salva dados da lavoura como JSON."""
        self.dados_lavoura = json.dumps(dados, ensure_ascii=False)
    
    def get_resposta_ia(self):
        """Retorna resposta da IA como dicionário."""
        try:
            return json.loads(self.resposta_ia) if self.resposta_ia else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_resposta_ia(self, resposta):
        """Salva resposta da IA como JSON."""
        self.resposta_ia = json.dumps(resposta, ensure_ascii=False)
    
    def get_urgencia_cor(self):
        """Retorna a cor CSS baseada no nível de urgência."""
        cores = {
            'baixo': '#2d6a4f',
            'medio': '#e9c46a',
            'alto': '#f4845f',
            'critico': '#e63946'
        }
        return cores.get(self.nivel_urgencia, '#6c757d')
    
    def get_urgencia_icone(self):
        """Retorna ícone baseado no nível de urgência."""
        icones = {
            'baixo': '✅',
            'medio': '⚠️',
            'alto': '🔶',
            'critico': '🚨'
        }
        return icones.get(self.nivel_urgencia, '❓')
    
    def __repr__(self):
        return f'<Analise {self.id} - {self.categoria} - {self.nivel_urgencia}>'


class Configuracao(db.Model):
    """Modelo para armazenar configurações do sistema (chave-valor)."""
    __tablename__ = 'configuracoes'
    
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_valor(chave, default=''):
        """Busca um valor de configuração pela chave."""
        config = Configuracao.query.filter_by(chave=chave).first()
        return config.valor if config else default
    
    @staticmethod
    def set_valor(chave, valor):
        """Define ou atualiza um valor de configuração."""
        config = Configuracao.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
        else:
            config = Configuracao(chave=chave, valor=valor)
            db.session.add(config)
        db.session.commit()
    
    def __repr__(self):
        return f'<Configuracao {self.chave}>'
