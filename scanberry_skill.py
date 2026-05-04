"""
Agrobotic ScanBerry — Skill de Análise Agronômica via IA
"""
import os, json, base64
from openai import OpenAI

PROMPT_SISTEMA = """Você é o Agrobotic ScanBerry — Assistente Agronômico para Morangos.

Sua função é analisar imagens de folhas, frutos, flores, raízes, solo, substrato, canteiros e plantas de morango, combinando a imagem com informações fornecidas pelo produtor.

Você deve agir com olhar técnico, como um agrônomo especialista em morangos, mas sempre deixar claro que sua análise é preliminar.

Regras obrigatórias:
1. Nunca diga que o diagnóstico é definitivo.
2. Use expressões como "possível", "compatível com", "sugere", "pode estar relacionado a".
3. Nunca prescreva defensivos agrícolas específicos, doses, misturas ou calendário de aplicação.
4. Sempre recomende consulta a agrônomo quando: o problema estiver avançando rapidamente; houver muitas plantas afetadas; houver risco de perda econômica; a imagem estiver ruim; houver dúvida entre doença, praga e deficiência nutricional; houver necessidade de decisão sobre defensivos.
5. Priorize ações imediatas seguras: observar, registrar, remover material comprometido quando adequado, melhorar ventilação, evitar excesso de umidade, revisar irrigação, enviar novas fotos, procurar orientação técnica.
6. Responda em linguagem simples para pequenos e médios produtores.
7. Sempre classifique o nível de urgência.
8. Sempre indique quais fotos adicionais ajudariam.
9. Sempre inclua o aviso: "Esta análise é preliminar e não substitui a avaliação de um engenheiro agrônomo."
10. Retorne a resposta EXCLUSIVAMENTE em JSON válido, sem texto adicional.

SCHEMA DE RESPOSTA OBRIGATÓRIO:
{"diagnostico_provavel":"string","categoria":"doenca|praga|nutricao|manejo|irrigacao|solo|colheita|desconhecido","confianca":0.0,"nivel_de_urgencia":"baixo|medio|alto|critico","parte_afetada":"folha|fruto|flor|raiz|solo|substrato|planta_inteira|desconhecido","sintomas_observados":["string"],"possiveis_causas":["string"],"acoes_imediatas_seguras":["string"],"perguntas_complementares":["string"],"fotos_adicionais_recomendadas":["string"],"quando_chamar_agronomo":"string","alerta_legal":"string","mensagem_para_produtor":"string","aviso_obrigatorio":"Esta análise é preliminar e não substitui a avaliação de um engenheiro agrônomo."}
"""

def montar_prompt_scanberry(dados_lavoura: dict) -> str:
    partes = ["Analise a imagem enviada considerando as seguintes informações da lavoura:\n"]
    campos = {
        'parte_planta': 'Parte da planta analisada', 'tipo_cultivo': 'Tipo de cultivo',
        'idade_planta': 'Idade da planta', 'variedade': 'Variedade cultivada',
        'municipio': 'Município/Estado', 'tipo_irrigacao': 'Tipo de irrigação',
        'ultima_irrigacao': 'Última irrigação', 'ultima_adubacao': 'Última adubação',
        'sintoma_percebido': 'Sintoma percebido', 'tempo_sintoma': 'Tempo do sintoma',
        'problema_aumentando': 'Problema aumentando?', 'plantas_afetadas': 'Plantas afetadas',
        'historico': 'Histórico de doenças/pragas', 'clima_recente': 'Clima recente',
    }
    for campo, label in campos.items():
        valor = dados_lavoura.get(campo, '').strip() if dados_lavoura.get(campo) else ''
        if valor:
            partes.append(f"- {label}: {valor}")
    if len(partes) == 1:
        partes.append("- Nenhuma informação adicional fornecida.")
    partes.append("\nRetorne a análise completa em JSON válido seguindo o schema especificado.")
    return "\n".join(partes)

def codificar_imagem_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def detectar_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    return {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.gif':'image/gif','.webp':'image/webp'}.get(ext, 'image/jpeg')

def analisar_imagem(image_path: str, dados_lavoura: dict, api_key: str, modelo: str = 'gpt-4o-mini') -> dict:
    if not api_key:
        return _resposta_demo()
    try:
        client = OpenAI(api_key=api_key)
        image_b64 = codificar_imagem_base64(image_path)
        mime_type = detectar_mime_type(image_path)
        prompt_usuario = montar_prompt_scanberry(dados_lavoura)
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt_usuario},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}", "detail": "high"}}
                ]}
            ],
            max_tokens=2000, temperature=0.3,
        )
        conteudo = response.choices[0].message.content.strip()
        if conteudo.startswith("```"):
            linhas = conteudo.split("\n")
            conteudo = "\n".join(linhas[1:-1]) if linhas[-1].strip() == "```" else "\n".join(linhas[1:])
        resposta = json.loads(conteudo)
        return _completar_resposta(resposta)
    except json.JSONDecodeError:
        return _resposta_erro("A IA retornou formato inválido. Tente novamente.")
    except Exception as e:
        return _resposta_erro(f"Erro na comunicação com a IA: {str(e)}")

def validar_resposta_skill(resposta: dict) -> bool:
    for campo in ['diagnostico_provavel','categoria','confianca','nivel_de_urgencia','parte_afetada','sintomas_observados','possiveis_causas','acoes_imediatas_seguras','mensagem_para_produtor','aviso_obrigatorio']:
        if campo not in resposta:
            return False
    if resposta.get('categoria') not in ['doenca','praga','nutricao','manejo','irrigacao','solo','colheita','desconhecido']:
        return False
    if resposta.get('nivel_de_urgencia') not in ['baixo','medio','alto','critico']:
        return False
    return True

def classificar_urgencia(resposta: dict) -> str:
    urgencia = resposta.get('nivel_de_urgencia', 'baixo')
    if resposta.get('confianca', 0.0) < 0.3 and urgencia in ('alto','critico'):
        return 'medio'
    return urgencia

def gerar_mensagem_produtor(resposta: dict) -> str:
    msg = resposta.get('mensagem_para_produtor', '')
    if not msg:
        diag = resposta.get('diagnostico_provavel', 'problema não identificado')
        msg = f"A análise sugere: {diag}. Acompanhe a evolução e procure orientação técnica."
    return msg

def _completar_resposta(resposta: dict) -> dict:
    defaults = {
        'diagnostico_provavel':'Não determinado','categoria':'desconhecido','confianca':0.0,
        'nivel_de_urgencia':'baixo','parte_afetada':'desconhecido','sintomas_observados':[],
        'possiveis_causas':[],'acoes_imediatas_seguras':[],'perguntas_complementares':[],
        'fotos_adicionais_recomendadas':[],'quando_chamar_agronomo':'Procure um agrônomo caso o problema persista.',
        'alerta_legal':'Não aplique defensivos sem orientação técnica.','mensagem_para_produtor':'',
        'aviso_obrigatorio':'Esta análise é preliminar e não substitui a avaliação de um engenheiro agrônomo.'
    }
    for k, v in defaults.items():
        if k not in resposta:
            resposta[k] = v
    resposta['nivel_de_urgencia'] = classificar_urgencia(resposta)
    if not resposta['mensagem_para_produtor']:
        resposta['mensagem_para_produtor'] = gerar_mensagem_produtor(resposta)
    return resposta

def _resposta_demo() -> dict:
    return {
        "diagnostico_provavel":"Modo demonstração — configure sua chave API OpenAI",
        "categoria":"desconhecido","confianca":0.0,"nivel_de_urgencia":"baixo",
        "parte_afetada":"desconhecido",
        "sintomas_observados":["Nenhum sintoma analisado — modo demonstração ativo"],
        "possiveis_causas":["Configure a API key nas Configurações para análise real"],
        "acoes_imediatas_seguras":["Acesse Configurações e insira sua chave API da OpenAI","Envie nova imagem após configurar"],
        "perguntas_complementares":[],"fotos_adicionais_recomendadas":[],
        "quando_chamar_agronomo":"Procure sempre um agrônomo para diagnóstico presencial.",
        "alerta_legal":"Modo demonstração. Configure a API para análise real.",
        "mensagem_para_produtor":"O ScanBerry está em modo demonstração. Configure sua chave API da OpenAI na página de Configurações para ativar a análise real por inteligência artificial.",
        "aviso_obrigatorio":"Esta análise é preliminar e não substitui a avaliação de um engenheiro agrônomo.",
        "_demo": True
    }

def _resposta_erro(mensagem: str) -> dict:
    return {
        "diagnostico_provavel":"Erro na análise","categoria":"desconhecido","confianca":0.0,
        "nivel_de_urgencia":"baixo","parte_afetada":"desconhecido",
        "sintomas_observados":[mensagem],
        "possiveis_causas":["Erro de comunicação com o serviço de IA"],
        "acoes_imediatas_seguras":["Tente novamente","Verifique a chave API","Verifique sua conexão"],
        "perguntas_complementares":[],"fotos_adicionais_recomendadas":[],
        "quando_chamar_agronomo":"Procure um agrônomo para avaliação presencial.",
        "alerta_legal":"Não foi possível realizar a análise automatizada.",
        "mensagem_para_produtor":f"Não foi possível analisar: {mensagem}",
        "aviso_obrigatorio":"Esta análise é preliminar e não substitui a avaliação de um engenheiro agrônomo.",
        "_erro": True
    }
