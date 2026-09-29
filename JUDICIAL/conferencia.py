"""
Conferencia automatica do texto da IA antes de virar .docx:

1. Toda citacao de julgado (numero de processo/recurso), Sumula ou Tema que NAO esteja no
   BASE_CONHECIMENTO/DNA_PECAS.md nem nos documentos do caso ganha [CONFERIR: ...] em vermelho.
2. Tudo que o proprio DNA marcou como inconsistente (decreto 29.252 x 29.552, arroba de 2023,
   Res. CMN 5.220 x 5.229, Sumula 379, art. 9 x 10 do DL 167/67, art. 14 do DL 167/67, Sumula 93)
   ganha [CONFERIR] se a IA esqueceu de marcar.

A trava nao substitui a revisao do advogado: ela so garante que nada "novo" passe sem aviso.
"""
import re

MARCA_JULGADO = '[CONFERIR: citação não encontrada no DNA do escritório nem nos documentos do caso]'
MARCA_SUMULA = '[CONFERIR: súmula não usada nas peças do escritório (DNA)]'
MARCA_TEMA = '[CONFERIR: o escritório não cita Tema numerado (DNA §2.9)]'

# (padrao, aviso) - pontos que o DNA marca como inconsistentes
DIVERGENCIAS_DNA = [
    (r'29\.552(?:/2024)?', 'DNA aponta divergência: Decreto Estadual 29.252/2024 × 29.552/2024'),
    (r'[Ss]úmula\s*(?:n[º°.]*\s*)?379(?:\s*/?\s*(?:do\s+)?STJ)?',
     'Súmula 379/STJ trata de juros moratórios; o DNA marca o uso para juros remuneratórios'),
    (r'Res(?:olução|\.)?\s*(?:CMN\s*)?(?:n[º°.]*\s*)?5\.22[09](?:/2025)?',
     'DNA aponta divergência entre Res. CMN 5.220/2025 e 5.229/2025'),
    (r'arroba[^.\n]{0,160}?R\$\s*(?:217|265)(?:,00)?|R\$\s*(?:217|265)(?:,00)?[^.\n]{0,80}?arroba',
     'DNA aponta divergência na arroba média de 2023 (R$ 265 × R$ 217)'),
    (r'art(?:igo)?\.?\s*9[º°]?\s*,?\s*(?:do\s+)?(?:Decreto-Lei|DL)\s*(?:n[º°.]*\s*)?167',
     'DNA: a tese do "título civil de destinação" é do art. 10 do DL 167/67 (uma peça citou art. 9º)'),
    (r'art(?:igo)?\.?\s*14\s*,?\s*(?:do\s+)?(?:Decreto-Lei|DL)\s*(?:n[º°.]*\s*)?167',
     'DNA: conferir o texto legal do art. 14 do DL 167/67 antes de reutilizar'),
    (r'[Ss]úmula\s*(?:n[º°.]*\s*)?93(?!\d)(?:\s*/?\s*(?:do\s+)?STJ)?',
     'Súmula 93/STJ: capitalização mensal foi aceita numa peça e atacada em outra (DNA §2.8)'),
]

MARCADORES = (r'REsp|AREsp|AgInt|AgRg|EREsp|EDcl|ADI|ADPF|AI|Ap\.|ApCiv|Apelação(?:\s+Cível)?|Apelacao|'
              r'Agravo(?:\s+de\s+Instrumento|\s+Interno)?|AGT|AC|ED|MS|RE|Recurso\s+Especial|'
              r'Processo|Proc\.|processo|autos|Autos|TJ-?[A-Z]{2}|TRF-?\d?|STJ|STF')
CITACAO = re.compile(r'\b(?:' + MARCADORES + r')\b[^\n\d]{0,40}?(\d[\d.\-/]{3,}\d)(?:/[A-Z]{2}\b)?')
CNJ = re.compile(r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b|\b\d{20}\b')
SUMULA = re.compile(r'[Ss]úmulas?\s*(?:n[º°.]*\s*)?(\d{1,4})(?![\d.])(?:\s*/?\s*(?:do\s+)?(?:STJ|STF|TST))?')
TEMA = re.compile(r'\bTema\s*(?:n[º°.]*\s*)?(\d(?:[\d.]*\d)?)\b')


def _digitos(s):
    return re.sub(r'\D', '', s)


def numeros_conhecidos(*textos):
    """Todos os numeros 'de processo' (>= 5 digitos) que aparecem nos textos de referencia."""
    saida = set()
    for t in textos:
        for m in re.finditer(r'\d[\d.\-/]{3,}\d', t or ''):
            d = _digitos(m.group(0))
            if len(d) >= 5:
                saida.add(d)
    return saida


def sumulas_conhecidas(dna, *textos):
    saida = set()
    for t in (dna,) + textos:
        saida.update(int(n) for n in SUMULA.findall(t or ''))
    # a linha-resumo do DNA lista as sumulas usadas pelo escritorio
    for linha in (dna or '').splitlines():
        if 'Súmulas citadas pelo escritório' in linha:
            saida.update(int(n) for n in re.findall(r'\b(\d{1,3})\b', linha))
    return saida


def _conhecido(digitos, conhecidos):
    if len(digitos) < 5:
        return True
    return digitos in conhecidos or any(digitos in c for c in conhecidos if len(c) >= len(digitos))


def _ja_marcado(texto, fim):
    """Ja existe [CONFERIR] logo depois, na mesma frase?"""
    trecho = re.split(r'\n|\.\s', texto[fim:fim + 120], maxsplit=1)[0]
    return '[CONFERIR' in trecho


def conferir(texto, dna, *referencias):
    """Retorna (texto_com_marcas, lista_de_avisos)."""
    conhecidos = numeros_conhecidos(dna, *referencias)
    sumulas_ok = sumulas_conhecidas(dna, *referencias)
    temas_ok = {_digitos(n) for r in referencias for n in TEMA.findall(r or '')}
    insercoes, avisos = [], []
    ja_marcados = [(m.start(), m.end()) for m in re.finditer(r'\[(?:CONFERIR|PREENCHER)[^\]]*\]', texto)]

    def marca(fim, aviso, trecho):
        if any(a <= fim <= b for a, b in ja_marcados):
            return  # esta dentro de um [CONFERIR ...] que a IA ja escreveu
        if not _ja_marcado(texto, fim) and all(f != fim for f, _ in insercoes):
            insercoes.append((fim, f' {aviso}'))
            avisos.append(f'{trecho.strip()[:90]} -> {aviso}')

    vistos = set()
    for m in list(CITACAO.finditer(texto)) + list(CNJ.finditer(texto)):
        grupo = m.group(1) if m.re is CITACAO else m.group(0)
        d = _digitos(grupo)
        fim = m.end()
        if (fim, d) in vistos:
            continue
        vistos.add((fim, d))
        inicio = m.start(1) if m.re is CITACAO else m.start()
        if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{2,4}', grupo) or 'R$' in texto[max(0, inicio - 5):inicio]:
            continue  # data ou valor em reais, nao e numero de processo
        if not _conhecido(d, conhecidos):
            marca(fim, MARCA_JULGADO, m.group(0))
    for m in SUMULA.finditer(texto):
        if int(m.group(1)) not in sumulas_ok:
            marca(m.end(), MARCA_SUMULA, m.group(0))
    for m in TEMA.finditer(texto):
        if _digitos(m.group(1)) not in temas_ok:
            marca(m.end(), MARCA_TEMA, m.group(0))
    for padrao, aviso in DIVERGENCIAS_DNA:
        for m in re.finditer(padrao, texto):
            marca(m.end(), f'[CONFERIR: {aviso}]', m.group(0))

    for fim, inserir in sorted(insercoes, reverse=True):
        texto = texto[:fim] + inserir + texto[fim:]
    return texto, avisos
