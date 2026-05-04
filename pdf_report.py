"""
Agrobotic ScanBerry — Gerador de Relatórios PDF
"""
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def gerar_pdf_analise(analise, output_path: str) -> str:
    """Gera relatório PDF profissional de uma análise."""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    styles.add(ParagraphStyle(name='TituloPrincipal', fontName='Helvetica-Bold',
                              fontSize=20, textColor=colors.HexColor('#2d6a4f'),
                              alignment=TA_CENTER, spaceAfter=6*mm))
    styles.add(ParagraphStyle(name='Subtitulo', fontName='Helvetica',
                              fontSize=11, textColor=colors.HexColor('#6c757d'),
                              alignment=TA_CENTER, spaceAfter=8*mm))
    styles.add(ParagraphStyle(name='SecaoTitulo', fontName='Helvetica-Bold',
                              fontSize=13, textColor=colors.HexColor('#2d6a4f'),
                              spaceBefore=6*mm, spaceAfter=3*mm))
    styles.add(ParagraphStyle(name='CorpoTexto', fontName='Helvetica',
                              fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=2*mm))
    styles.add(ParagraphStyle(name='ItemLista', fontName='Helvetica',
                              fontSize=10, leading=13, leftIndent=10*mm, spaceAfter=1*mm))
    styles.add(ParagraphStyle(name='Aviso', fontName='Helvetica-Oblique',
                              fontSize=9, textColor=colors.HexColor('#e63946'),
                              alignment=TA_CENTER, spaceBefore=6*mm))
    styles.add(ParagraphStyle(name='Rodape', fontName='Helvetica',
                              fontSize=8, textColor=colors.HexColor('#adb5bd'),
                              alignment=TA_CENTER))
    
    elements = []
    resposta = analise.get_resposta_ia()
    dados = analise.get_dados_lavoura()
    
    # Cabeçalho
    elements.append(Paragraph("🍓 Agrobotic ScanBerry", styles['TituloPrincipal']))
    elements.append(Paragraph("Relatório de Análise Agronômica", styles['Subtitulo']))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#52b788')))
    elements.append(Spacer(1, 4*mm))
    
    # Info geral
    data_analise = analise.created_at.strftime("%d/%m/%Y %H:%M") if analise.created_at else "N/A"
    
    # Adicionar info do produtor se houver
    info_data = []
    if analise.usuario:
        info_data.append(['Produtor:', analise.usuario.nome])
        info_data.append(['WhatsApp:', analise.usuario.whatsapp])
        if analise.usuario.cidade:
            local = f"{analise.usuario.cidade} - {analise.usuario.estado}" if analise.usuario.estado else analise.usuario.cidade
            info_data.append(['Endereço:', f"{analise.usuario.endereco}, {local}"])
        elif analise.usuario.endereco:
            info_data.append(['Endereço:', analise.usuario.endereco])
        info_data.append([Spacer(1, 2*mm), Spacer(1, 2*mm)]) # Separador visual

    info_data.extend([
        ['Data da Análise:', data_analise],
        ['Categoria:', _traduzir_categoria(resposta.get('categoria', ''))],
        ['Nível de Urgência:', _traduzir_urgencia(resposta.get('nivel_de_urgencia', ''))],
        ['Confiança:', f"{resposta.get('confianca', 0) * 100:.0f}%"],
        ['Parte Afetada:', resposta.get('parte_afetada', 'N/A').replace('_', ' ').title()],
    ])
    
    if dados.get('variedade'):
        info_data.append(['Variedade:', dados['variedade']])
    if dados.get('municipio'):
        info_data.append(['Localização:', dados['municipio']])
    if dados.get('tipo_cultivo'):
        info_data.append(['Tipo de Cultivo:', dados['tipo_cultivo']])
    
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2d6a4f')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#dee2e6')))
    
    # Diagnóstico
    elements.append(Paragraph("Diagnóstico Provável", styles['SecaoTitulo']))
    elements.append(Paragraph(resposta.get('diagnostico_provavel', 'N/A'), styles['CorpoTexto']))
    
    # Mensagem ao Produtor
    elements.append(Paragraph("Mensagem ao Produtor", styles['SecaoTitulo']))
    elements.append(Paragraph(resposta.get('mensagem_para_produtor', 'N/A'), styles['CorpoTexto']))
    
    # Sintomas Observados
    sintomas = resposta.get('sintomas_observados', [])
    if sintomas:
        elements.append(Paragraph("Sintomas Observados", styles['SecaoTitulo']))
        for s in sintomas:
            elements.append(Paragraph(f"• {s}", styles['ItemLista']))
    
    # Possíveis Causas
    causas = resposta.get('possiveis_causas', [])
    if causas:
        elements.append(Paragraph("Possíveis Causas", styles['SecaoTitulo']))
        for c in causas:
            elements.append(Paragraph(f"• {c}", styles['ItemLista']))
    
    # Ações Imediatas Seguras
    acoes = resposta.get('acoes_imediatas_seguras', [])
    if acoes:
        elements.append(Paragraph("Ações Imediatas Seguras", styles['SecaoTitulo']))
        for a in acoes:
            elements.append(Paragraph(f"✓ {a}", styles['ItemLista']))
    
    # Quando Chamar Agrônomo
    elements.append(Paragraph("Quando Chamar o Agrônomo", styles['SecaoTitulo']))
    elements.append(Paragraph(resposta.get('quando_chamar_agronomo', 'N/A'), styles['CorpoTexto']))
    
    # Fotos Adicionais
    fotos = resposta.get('fotos_adicionais_recomendadas', [])
    if fotos:
        elements.append(Paragraph("Fotos Adicionais Recomendadas", styles['SecaoTitulo']))
        for f in fotos:
            elements.append(Paragraph(f"📷 {f}", styles['ItemLista']))
    
    # Aviso Legal
    elements.append(Spacer(1, 6*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e63946')))
    elements.append(Paragraph(resposta.get('aviso_obrigatorio',
        'Esta análise é preliminar e não substitui a avaliação de um engenheiro agrônomo.'), styles['Aviso']))
    elements.append(Paragraph(resposta.get('alerta_legal', ''), styles['Aviso']))
    
    # Rodapé
    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph(f"Agrobotic ScanBerry v1.0 — Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Rodape']))
    
    doc.build(elements)
    return output_path


def _traduzir_categoria(cat: str) -> str:
    traducoes = {
        'doenca': '🦠 Doença', 'praga': '🐛 Praga', 'nutricao': '🧪 Nutrição',
        'manejo': '🔧 Manejo', 'irrigacao': '💧 Irrigação', 'solo': '🌍 Solo',
        'colheita': '🍓 Colheita', 'desconhecido': '❓ Não Identificado'
    }
    return traducoes.get(cat, cat)


def _traduzir_urgencia(urg: str) -> str:
    traducoes = {
        'baixo': '🟢 Baixo', 'medio': '🟡 Médio',
        'alto': '🟠 Alto', 'critico': '🔴 Crítico'
    }
    return traducoes.get(urg, urg)
