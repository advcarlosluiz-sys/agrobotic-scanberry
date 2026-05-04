"""
Agrobotic ScanBerry — Entry Point para Vercel (Serverless)
O Vercel requer que 'app', 'application' ou 'handler' estejam
definidos no nível do módulo (fora de try/except).
"""
import sys
import os

# Garante que o diretório raiz está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

# Vercel busca por 'app', 'application' ou 'handler' no nível do módulo
application = app
