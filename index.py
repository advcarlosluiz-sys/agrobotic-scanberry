"""
Agrobotic ScanBerry — Entry Point para Vercel (Serverless)
===========================================================
O Vercel procura por um objeto WSGI chamado 'app' ou 'application' neste arquivo.
"""
import sys
import os

# Garante que o diretório raiz está no path para imports relativos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app as application
    # Alias adicional para compatibilidade máxima com o handler do Vercel
    app = application
except Exception as e:
    import traceback
    print("=" * 60)
    print("ERRO CRÍTICO NA INICIALIZAÇÃO DO AGROBOTIC SCANBERRY:")
    print("=" * 60)
    print(traceback.format_exc())
    raise e
