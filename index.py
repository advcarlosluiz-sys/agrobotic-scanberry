try:
    from app import app as application
except Exception as e:
    import traceback
    print("ERRO CRÍTICO NA INICIALIZAÇÃO DO APP:")
    print(traceback.format_exc())
    raise e
