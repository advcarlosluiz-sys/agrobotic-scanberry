import sys
import os

# Adiciona o diretório atual ao path para garantir que importe o app
sys.path.append(os.getcwd())

try:
    from app import app, db, Usuario
    from datetime import datetime

    print("Iniciando inicialização do banco de dados...")
    
    with app.app_context():
        # Cria as tabelas
        db.create_all()
        print("✅ Tabelas criadas com sucesso.")
        
        # Verifica se existe admin
        admin = Usuario.query.filter_by(whatsapp='0000').first()
        if not admin:
            admin = Usuario(
                nome='Administrador ScanBerry',
                whatsapp='0000',
                email='admin@scanberry.com',
                is_admin=True,
                aceitou_termos=True,
                data_consentimento=datetime.utcnow()
            )
            admin.set_senha('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário Admin padrão criado (0000 / admin123).")
        else:
            print("ℹ️ Usuário Admin já existente.")

    print("\n============================================")
    print("  BANCO DE DADOS ATUALIZADO COM SUCESSO!")
    print("============================================\n")

except Exception as e:
    print("\n❌ ERRO AO INICIALIZAR O BANCO DE DADOS:")
    print(str(e))
    print("\nCertifique-se de que todas as dependências estão instaladas (rode INSTALAR.bat).")
    sys.exit(1)
