import streamlit as st
import numpy_financial as npf
import pandas as pd

try:
    import locale
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    pass  # Fallback para formatação manual
# ============================================
# 1️⃣ PRIMEIRO: Configuração da página (OBRIGATÓRIO SER O PRIMEIRO)
# ============================================
st.set_page_config(
    page_title="Valuation de Leilões GO", 
    layout="wide", 
    page_icon="🏛️"
)

# ============================================
# 2️⃣ SEGUNDO: CSS Customizado (antes de renderizar qualquer elemento)
# ============================================
st.markdown("""
<style>
    /* Contenedor principal mais compacto */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1100px;
    }
    
    /* Reduzir fonte global */
    html, body, [class*="css"] {
        font-size: 14px;
    }
    
    /* Títulos proporcionais */
    h1 { font-size: 1.8rem; margin-bottom: 0.8rem; }
    h2 { font-size: 1.4rem; margin-bottom: 0.6rem; margin-top: 0.8rem; }
    h3 { font-size: 1.1rem; margin-bottom: 0.4rem; }
    
    /* Métricas compactas */
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; }
    
    /* Sidebar otimizada */
    [data-testid="stSidebar"] {
        min-width: 260px;
        max-width: 280px;
    }
    
    /* Espaçamento entre elementos */
    .element-container { margin-bottom: 0.4rem; }
    
    /* Dividers */
    hr { margin: 0.8rem 0; }
    
    /* Tabelas */
    .dataframe { font-size: 0.85rem; }
    
    /* Info boxes */
    .stAlert { padding: 0.8rem; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# Adicione no INÍCIO do código, logo após os imports
def verificar_senha():
    """Retorna True se a senha estiver correta."""
    
    def password_entered():
        """Verifica se a senha inserida está correta."""
        if st.session_state["password"] == "investimento":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Não armazenar a senha
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primeira vez, mostrar input de senha
        st.text_input(
            "🔐 Senha de Acesso:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("ℹ️ Digite a senha para acessar o simulador.")
        return False
    elif not st.session_state["password_correct"]:
        # Senha incorreta
        st.text_input(
            "🔐 Senha de Acesso:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Senha incorreta. Tente novamente.")
        return False
    else:
        # Senha correta
        return True

# Verificar senha antes de mostrar o app
if not verificar_senha():
    st.stop()
    

# Constantes para taxas e impostos
TAXA_ITBI = 0.04
TAXA_ESCRITURA = 0.03
TAXA_FUNDOS = 0.01
TAXA_REGISTRO = 0.03
TAXA_COMISSAO_VENDA = 0.05
TAXA_IR_GCAP = 0.15
TAXA_JUROS_ANUAL_DEFAULT = 0.12


def formatar_moeda(valor):
    """
    Formata um valor numérico para moeda brasileira (R$).
    
    Tenta usar locale.currency() com agrupamento de milhares.
    Em caso de falha, utiliza formato manual 'R$ {valor:,.2f}' 
    com substituições para padrão brasileiro.
    
    Args:
        valor (float): Valor a ser formatado.
    
    Returns:
        str: Valor formatado como moeda.
    """
    try:
        return locale.currency(valor, grouping=True)
    except (locale.Error, ValueError):
        # Fallback para formato manual
        return f"R$ {valor:,.2f}".replace(',', 'temp').replace('.', ',').replace('temp', '.')


def validar_inputs(lance, revenda, meses, entrada_pct):
    """
    Valida os inputs fornecidos pelo usuário.
    
    Verifica se os valores estão dentro de faixas aceitáveis:
    - Lance deve ser maior que zero.
    - Revenda deve ser maior ou igual ao lance (aviso se menor).
    - Meses deve ser maior que zero.
    - Entrada_pct deve estar entre 0 e 100.
    
    Args:
        lance (float): Valor do lance.
        revenda (float): Valor estimado de revenda.
        meses (int): Número de meses.
        entrada_pct (float): Percentual de entrada.
    
    Returns:
        tuple: (bool, str) - Status de validação (True se válido) e mensagem de erro/aviso.
    """
    if lance <= 0:
        return False, "O valor de arremate deve ser maior que zero."
    if meses <= 0:
        return False, "O tempo de giro deve ser maior que zero."
    if not (0 <= entrada_pct <= 100):
        return False, "O percentual de entrada deve estar entre 0% e 100%."
    if revenda < lance:
        return True, "Atenção: O valor de revenda é menor que o valor de arremate. Isso pode indicar prejuízo."
    return True, ""


def calcular_custos_aquisicao(lance, taxa_leiloeiro_pct, reforma_extras):
    """
    Calcula os custos associados à aquisição do imóvel.
    
    Inclui ITBI, escritura, fundos, registro, comissão do leiloeiro,
    reforma e custos extras, resultando no custo total do ativo.
    
    Args:
        lance (float): Valor do lance.
        taxa_leiloeiro_pct (float): Percentual da comissão do leiloeiro.
        reforma_extras (float): Custos de reforma e extras.
    
    Returns:
        dict: Dicionário com 'itbi', 'escritura', 'fundos', 'registro',
              'total_taxas', 'comissao_leiloeiro', 'custo_total_ativo'.
    """
    # Cálculo do ITBI: 4% sobre o valor do lance
    itbi = lance * TAXA_ITBI
    
    # Cálculo da escritura: 3% sobre o valor do lance
    escritura = lance * TAXA_ESCRITURA
    
    # Cálculo dos fundos: 1% sobre o valor do lance
    fundos = lance * TAXA_FUNDOS
    
    # Cálculo do registro: 3% sobre o valor do lance
    registro = lance * TAXA_REGISTRO
    
    # Total das taxas
    total_taxas = itbi + escritura + fundos + registro
    
    # Comissão do leiloeiro
    comissao_leiloeiro = lance * taxa_leiloeiro_pct
    
    # Custo total do ativo: lance + taxas + comissão + reforma/extras
    custo_total_ativo = lance + total_taxas + comissao_leiloeiro + reforma_extras
    
    return {
        'itbi': itbi,
        'escritura': escritura,
        'fundos': fundos,
        'registro': registro,
        'total_taxas': total_taxas,
        'comissao_leiloeiro': comissao_leiloeiro,
        'custo_total_ativo': custo_total_ativo
    }


def calcular_estrutura_capital(lance, entrada_pct, total_taxas, comissao_leiloeiro, reforma_extras):
    """
    Calcula a estrutura de capital para o investimento.
    
    Determina o valor da entrada, valor financiado e capital próprio investido.
    
    Args:
        lance (float): Valor do lance.
        entrada_pct (float): Percentual de entrada (0-1).
        total_taxas (float): Total das taxas.
        comissao_leiloeiro (float): Comissão do leiloeiro.
        reforma_extras (float): Custos de reforma e extras.
    
    Returns:
        dict: Dicionário com 'valor_entrada', 'valor_financiado', 'capital_proprio_investido'.
    """
    # Valor da entrada: percentual sobre o lance
    valor_entrada = lance * entrada_pct
    
    # Valor financiado: lance - entrada
    valor_financiado = lance - valor_entrada
    
    # Capital próprio investido: entrada + taxas + comissão + extras
    capital_proprio_investido = valor_entrada + total_taxas + comissao_leiloeiro + reforma_extras
    
    return {
        'valor_entrada': valor_entrada,
        'valor_financiado': valor_financiado,
        'capital_proprio_investido': capital_proprio_investido
    }


def calcular_custos_financiamento(valor_financiado, taxa_juros_anual, prazo_total_meses, tempo_giro_meses, considerar_juros):
    """
    Calcula os custos associados ao financiamento durante o período de giro.
    
    SISTEMA SBPE (Caixa Econômica Federal) - Tabela PRICE
    
    CONVENÇÃO numpy_financial:
    - Você RECEBE o empréstimo: pv = +valor (positivo)
    - Você PAGA prestações: pmt = -valor (negativo)
    - Você DEVE no final: fv = -valor (negativo)
    
    Args:
        valor_financiado (float): Valor a ser financiado.
        taxa_juros_anual (float): Taxa de juros anual.
        prazo_total_meses (int): Prazo total do financiamento.
        tempo_giro_meses (int): Tempo até vender (giro).
        considerar_juros (bool): Se deve considerar juros.
    
    Returns:
        dict: Dicionário com detalhes do financiamento.
    """
    if not considerar_juros or valor_financiado == 0:
        return {
            'prestacao_mensal': 0,
            'total_prestacoes_pagas': 0,
            'saldo_devedor': 0,
            'juros_pagos_no_giro': 0,
            'amortizacao_no_giro': 0
        }
    
    # Taxa mensal: (1 + taxa_anual)^(1/12) - 1
    taxa_mensal = (1 + taxa_juros_anual)**(1/12) - 1
    
    # Prestação mensal (Sistema PRICE)
    # pv = +valor_financiado (você RECEBE o dinheiro)
    # Retorna NEGATIVO (você PAGA)
    pmt = npf.pmt(taxa_mensal, prazo_total_meses, valor_financiado)
    prestacao_mensal = -pmt  # Converter para positivo para exibição
    
    # Total pago em prestações DURANTE o tempo de giro
    total_prestacoes_pagas = prestacao_mensal * tempo_giro_meses
    
    # Saldo devedor após o tempo de giro
    # pv = +valor_financiado (você recebeu)
    # pmt = pmt (negativo, você paga)
    # Retorna NEGATIVO (você ainda deve)
    fv = npf.fv(taxa_mensal, tempo_giro_meses, pmt, valor_financiado)
    saldo_devedor = -fv  # Converter para positivo
    
    # Garantir que saldo devedor não seja negativo (proteção)
    saldo_devedor = max(0, saldo_devedor)
    
    # Amortização durante o giro = quanto a dívida diminuiu
    amortizacao_no_giro = valor_financiado - saldo_devedor
    
    # Juros pagos durante o giro = prestações pagas - amortização
    juros_pagos_no_giro = total_prestacoes_pagas - amortizacao_no_giro
    
    return {
        'prestacao_mensal': prestacao_mensal,
        'total_prestacoes_pagas': total_prestacoes_pagas,
        'saldo_devedor': saldo_devedor,
        'juros_pagos_no_giro': juros_pagos_no_giro,
        'amortizacao_no_giro': amortizacao_no_giro
    }

def calcular_lucros(revenda, capital_proprio_investido, saldo_devedor, juros_pagos_no_giro, quem_paga_custos_venda="Vendedor"):
    """
    Calcula os lucros associados à venda do imóvel.
    
    FLUXO DE CAIXA CORRETO (SBPE):
    
    CUSTOS FIXOS (SEMPRE pagos pelo vendedor):
    - Comissão de Venda (5% sobre valor de revenda)
    
    CUSTOS CONDICIONAIS (depende da negociação):
    - ITBI, Escritura e Registro (vendedor ou comprador)
    
    SAÍDAS (o que você paga do seu bolso):
    - Capital próprio investido no início (entrada + taxas + extras)
    - JUROS pagos durante o giro (custo efetivo)
    - Comissão de venda (5%) - SEMPRE
    - Custos de transferência (se vendedor pagar)
    
    ENTRADAS (o que você recebe):
    - Valor de revenda
    - Menos: Comissão (SEMPRE)
    - Menos: Custos de transferência (se vendedor pagar)
    - Menos: Saldo devedor a quitar no banco
    
    LUCRO = ENTRADAS - SAÍDAS - IR
    
    Args:
        revenda (float): Valor de revenda.
        capital_proprio_investido (float): Capital próprio inicial investido.
        saldo_devedor (float): Saldo devedor a quitar na venda.
        juros_pagos_no_giro (float): Juros pagos durante o giro (custo efetivo).
        quem_paga_custos_venda (str): "Vendedor" ou "Comprador".
    
    Returns:
        dict: Dicionário com detalhes dos lucros.
    """
    # Comissão de venda: 5% sobre o valor de revenda (SEMPRE paga pelo vendedor)
    comissao_venda = revenda * TAXA_COMISSAO_VENDA
    
    # Custos de transferência na VENDA (ITBI + Escritura + Registro sobre valor de revenda)
    itbi_venda = revenda * TAXA_ITBI
    escritura_venda = revenda * TAXA_ESCRITURA
    registro_venda = revenda * TAXA_REGISTRO
    total_custos_transferencia = itbi_venda + escritura_venda + registro_venda
    
    # Receita líquida: receita após pagar comissão, custos de transferência e quitar financiamento
    if quem_paga_custos_venda == "Comprador":
        # Comprador paga os custos de transferência
        # Vendedor paga APENAS a comissão
        receita_liquida_venda = revenda - comissao_venda - saldo_devedor
        custos_transferencia_vendedor = 0
    else:
        # Vendedor paga COMISSÃO + custos de transferência (ITBI + Escritura + Registro)
        receita_liquida_venda = revenda - comissao_venda - total_custos_transferencia - saldo_devedor
        custos_transferencia_vendedor = total_custos_transferencia
    
    # Lucro bruto = Receita líquida - Capital próprio - JUROS
    lucro_bruto = receita_liquida_venda - capital_proprio_investido - juros_pagos_no_giro
    
    # IR sobre ganho de capital: 15% sobre lucro bruto se positivo
    ir_gcap = lucro_bruto * TAXA_IR_GCAP if lucro_bruto > 0 else 0
    
    # Lucro líquido: lucro bruto - IR
    lucro_liquido = lucro_bruto - ir_gcap
    
    return {
        'comissao_venda': comissao_venda,
        'itbi_venda': itbi_venda,
        'escritura_venda': escritura_venda,
        'registro_venda': registro_venda,
        'total_custos_transferencia': total_custos_transferencia,
        'custos_transferencia_vendedor': custos_transferencia_vendedor,
        'receita_liquida_venda': receita_liquida_venda,
        'lucro_bruto': lucro_bruto,
        'ir_gcap': ir_gcap,
        'lucro_liquido': lucro_liquido,
        'quem_paga': quem_paga_custos_venda,
        'saldo_devedor_quitado': saldo_devedor
    }
    
def calcular_metricas_financeiras(lucro_liquido, custo_total_ativo, total_investido, meses):
    """
    Calcula métricas financeiras como ROI, ROE e TIR.
    
    ROI: Retorno sobre o ativo total.
    ROE: Retorno sobre o capital próprio investido (+ prestações).
    TIR: Taxa interna de retorno, calculada com fluxo de caixa.
    
    Args:
        lucro_liquido (float): Lucro líquido.
        custo_total_ativo (float): Custo total do ativo.
        total_investido (float): Total realmente investido (capital próprio + prestações).
        meses (int): Número de meses.
    
    Returns:
        dict: Dicionário com 'roi', 'roe', 'tir_anual'.
    """
    # ROI: (Lucro Líquido / Custo Total do Ativo) * 100
    roi = (lucro_liquido / custo_total_ativo * 100) if custo_total_ativo != 0 else None
    
    # ROE: (Lucro Líquido / Total Investido) * 100
    roe = (lucro_liquido / total_investido * 100) if total_investido != 0 else None
    
    # TIR: Fluxo de caixa com investimento inicial negativo
    # Considera que você investe no início e recebe o retorno no final
    fluxo_caixa = [-total_investido] + [0] * (meses - 1) + [total_investido + lucro_liquido]
    try:
        tir_mensal = npf.irr(fluxo_caixa)
        tir_anual = ((1 + tir_mensal)**12 - 1) * 100 if tir_mensal is not None else None
    except (ValueError, TypeError):
        tir_anual = None
    
    return {
        'roi': roi,
        'roe': roe,
        'tir_anual': tir_anual
    }


def criar_dataframe_detalhamento(custos_aquisicao, reforma_extras, comissao_venda, custos_transferencia_vendedor, ir_gcap, saldo_devedor, total_prestacoes_pagas, lance):
    """
    Cria um DataFrame com o detalhamento de custos e receitas.
    
    Inclui categorias como valor de arremate, taxas, comissão, prestações pagas,
    saldo devedor quitado, etc.
    
    Args:
        custos_aquisicao (dict): Dicionário com custos de aquisição.
        reforma_extras (float): Custos de reforma e extras.
        comissao_venda (float): Comissão de venda.
        ir_gcap (float): IR sobre ganho de capital.
        saldo_devedor (float): Saldo devedor quitado na venda.
        total_prestacoes_pagas (float): Total de prestações pagas durante o giro.
        lance (float): Valor do lance/arremate.
    
    Returns:
        pd.DataFrame: DataFrame com colunas 'Categoria de Custo/Receita' e 'Valor (R$)'.
    """
    dados = {
        'Categoria de Custo/Receita': [
            'Valor de Arremate',
            'ITBI (4%) - Aquisição',
            'Escritura (3%) - Aquisição',
            'Fundos (1%)',
            'Registro (3%) - Aquisição',
            'Comissão Leiloeiro',
            'Reforma e Custos Extras',
            'Prestações Pagas (Durante Giro)',
            'Saldo Devedor Quitado (Venda)',
            'Comissão de Venda (5% - SEMPRE)',
            'Custos de Transferência (Venda - Condicional)',
            'Imposto de Renda (GCAP)'
    ],
    'Valor (R$)': [
        lance,
        custos_aquisicao['itbi'],
        custos_aquisicao['escritura'],
        custos_aquisicao['fundos'],
        custos_aquisicao['registro'],
        custos_aquisicao['comissao_leiloeiro'],
        reforma_extras,
        total_prestacoes_pagas,
        saldo_devedor,
        comissao_venda,
        custos_transferencia_vendedor,
        ir_gcap
    ]
   }
    df = pd.DataFrame(dados)
    df['Valor (R$)'] = df['Valor (R$)'].apply(formatar_moeda)
    return df
def criar_demonstrativo_fluxo_caixa(capital_proprio, juros_pagos, receita_venda, comissao_venda, custos_transferencia, saldo_devedor_quitado, lucro_bruto, ir_gcap, lucro_liquido):
    """
    Cria um demonstrativo detalhado do fluxo de caixa da operação.
    
    Args:
        capital_proprio (float): Capital próprio investido.
        juros_pagos (float): Juros pagos durante o giro (custo efetivo).
        receita_venda (float): Valor de revenda.
        comissao_venda (float): Comissão de venda (SEMPRE paga).
        custos_transferencia (float): Custos de transferência (condicional).
        saldo_devedor_quitado (float): Saldo devedor quitado.
        lucro_bruto (float): Lucro bruto.
        ir_gcap (float): IR sobre ganho de capital.
        lucro_liquido (float): Lucro líquido.
    
    Returns:
        pd.DataFrame: DataFrame com o demonstrativo.
    """
    dados = {
        'Descrição': [
            '💸 SAÍDAS DE CAIXA (O que você pagou DO SEU BOLSO)',
            '   Capital Próprio Inicial',
            '   Juros Pagos Durante Giro',
            '   TOTAL INVESTIDO DO SEU BOLSO',
            '',
            '💰 ENTRADAS DE CAIXA (O que você recebeu)',
            '   Valor de Revenda',
            '   (-) Comissão de Venda (5% - SEMPRE)',
            '   (-) Custos de Transferência (ITBI+Escritura+Registro)',
            '   (-) Saldo Devedor Quitado no Banco',
            '   TOTAL LÍQUIDO RECEBIDO',
            '',
            '📊 RESULTADO',
            '   Lucro Bruto (Recebido - Investido)',
            '   (-) Imposto de Renda (15%)',
            '   LUCRO LÍQUIDO FINAL'
        ],
        'Valor (R$)': [
            '',
            formatar_moeda(capital_proprio),
            formatar_moeda(juros_pagos),
            formatar_moeda(capital_proprio + juros_pagos),
            '',
            '',
            formatar_moeda(receita_venda),
            formatar_moeda(-comissao_venda),
            formatar_moeda(-custos_transferencia),
            formatar_moeda(-saldo_devedor_quitado),
            formatar_moeda(receita_venda - comissao_venda - custos_transferencia - saldo_devedor_quitado),
            '',
            '',
            formatar_moeda(lucro_bruto),
            formatar_moeda(-ir_gcap),
            formatar_moeda(lucro_liquido)
        ]
    }
    return pd.DataFrame(dados)
    
# Configuração da página Streamlit
st.set_page_config(page_title="Valuation de Leilões GO", layout="wide", page_icon="🏛️")

# Título e descrição
st.title("🏛️ Simulador de Viabilidade: Leilão de Imóveis")
st.markdown("Análise completa de investimento em imóveis adquiridos por leilão com cálculos financeiros precisos")
st.divider()

# Barra lateral com inputs
st.sidebar.header("📊 Variáveis do Negócio")
lance = st.sidebar.number_input("Valor de Arremate (R$)", value=87000.0, step=1000.0, help="Valor do lance vencedor no leilão")
revenda = st.sidebar.number_input("Valor Estimado de Revenda (R$)", value=160000.0, step=5000.0, help="Preço estimado de venda do imóvel após reformas")
meses = st.sidebar.slider("Tempo de Giro (Meses)", 1, 36, 6, help="Período estimado entre aquisição e venda")

st.sidebar.subheader("💰 Custos e Financiamento")
taxa_leiloeiro_pct = st.sidebar.selectbox("Comissão Leiloeiro (%)", [0, 5, 10], index=0, help="Percentual de comissão do leiloeiro") / 100
reforma_extras = st.sidebar.number_input("Custos Extras (Reforma/Débitos) (R$)", value=12000.0, step=1000.0, help="Custos de reforma, débitos e outras despesas")
entrada_pct = st.sidebar.slider("% de Entrada (Financiamento)", 0, 100, 20, help="Percentual pago à vista na aquisição") / 100

st.sidebar.subheader("🏦 Parâmetros de Financiamento")
considerar_juros = st.sidebar.checkbox("Considerar Custos de Financiamento", value=True, help="Incluir juros do financiamento na análise")
taxa_juros_anual = st.sidebar.number_input("Taxa de Juros Anual (%)", value=12.0, step=0.5, min_value=0.0, help="Taxa de juros anual do financiamento") / 100 if considerar_juros else 0.12
prazo_financiamento_meses = st.sidebar.slider("Prazo do Financiamento (Meses)", 1, 420, 120, help="Prazo para quitação do financiamento bancário") if considerar_juros else meses

st.sidebar.subheader("💸 Custos de Venda")
quem_paga_custos_venda = st.sidebar.selectbox("Quem Paga os Custos de Venda?", ["Vendedor", "Comprador"], index=0, help="Define quem arca com comissão e taxas de venda")

# Validação de inputs
valido, mensagem = validar_inputs(lance, revenda, meses, entrada_pct * 100)
if not valido:
    st.error(f"❌ {mensagem}")
    st.stop()
if revenda < lance:
    st.warning("⚠️ Atenção: O valor de revenda é menor que o valor de arremate. Isso pode indicar prejuízo.")

# Cálculos principais
# Cálculos principais
custos_aquisicao = calcular_custos_aquisicao(lance, taxa_leiloeiro_pct, reforma_extras)

# AJUSTE: Se não considerar juros, pagamento é 100% à vista
if not considerar_juros:
    # Pagamento à vista: entrada = 100% do lance
    estrutura_capital = calcular_estrutura_capital(
        lance, 
        1.0,  # 100% de entrada
        custos_aquisicao['total_taxas'], 
        custos_aquisicao['comissao_leiloeiro'], 
        reforma_extras
    )
else:
    # Pagamento com financiamento: usa o percentual configurado
    estrutura_capital = calcular_estrutura_capital(
        lance, 
        entrada_pct, 
        custos_aquisicao['total_taxas'], 
        custos_aquisicao['comissao_leiloeiro'], 
        reforma_extras
    )

custos_financ = calcular_custos_financiamento(
    estrutura_capital['valor_financiado'], 
    taxa_juros_anual, 
    prazo_financiamento_meses if considerar_juros else meses,
    meses,  # tempo de giro
    considerar_juros
)

lucros = calcular_lucros(
    revenda, 
    estrutura_capital['capital_proprio_investido'],
    custos_financ['saldo_devedor'],
    custos_financ['juros_pagos_no_giro'],
    quem_paga_custos_venda
)

# Total investido = capital próprio + juros pagos (não prestações totais)
total_investido = estrutura_capital['capital_proprio_investido'] + custos_financ['juros_pagos_no_giro']

metricas = calcular_metricas_financeiras(
    lucros['lucro_liquido'], 
    custos_aquisicao['custo_total_ativo'], 
    total_investido,
    meses
)

# Exibição de resultados

# Resumo Executivo
st.subheader("📈 Resumo Executivo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_color = "normal" if lucros['lucro_liquido'] > 0 else "inverse"
    st.metric("Lucro Líquido Estimado", formatar_moeda(lucros['lucro_liquido']), delta=f"{lucros['lucro_liquido']:,.2f}", delta_color=delta_color)

with col2:
    st.metric("ROI (Retorno sobre Ativo)", f"{metricas['roi']:.2f}%" if metricas['roi'] is not None else "N/A")

with col3:
    st.metric("ROE (Retorno sobre Capital Próprio)", f"{metricas['roe']:.2f}%" if metricas['roe'] is not None else "N/A")

with col4:
    tir_display = f"{metricas['tir_anual']:.2f}%" if metricas['tir_anual'] is not None else "Inválida"
    st.metric("TIR (Anualizada)", tir_display)

# Adicione após a seção de métricas (col1, col2, col3, col4)
st.divider()

col_custo1, col_custo2 = st.columns(2)

with col_custo1:
    st.info(f"""
    **💼 Comissão de Venda (SEMPRE você paga):**
    
    Valor: **{formatar_moeda(lucros['comissao_venda'])}** (5% sobre revenda)
    
    ✅ Este valor **já está deduzido** do lucro líquido.
    """)

with col_custo2:
    if lucros.get('quem_paga') == "Comprador":
        st.success(f"""
        **📄 Custos de Transferência (Comprador paga):**
        
        - ITBI: {formatar_moeda(lucros['itbi_venda'])}
        - Escritura: {formatar_moeda(lucros['escritura_venda'])}
        - Registro: {formatar_moeda(lucros['registro_venda'])}
        - **Total:** {formatar_moeda(lucros['total_custos_transferencia'])}
        
        ✅ Estes custos **NÃO** afetam seu lucro (comprador paga).
        """)
    else:
        st.warning(f"""
        **📄 Custos de Transferência (Você paga):**
        
        - ITBI: {formatar_moeda(lucros['itbi_venda'])}
        - Escritura: {formatar_moeda(lucros['escritura_venda'])}
        - Registro: {formatar_moeda(lucros['registro_venda'])}
        - **Total:** {formatar_moeda(lucros['total_custos_transferencia'])}
        
        ⚠️ Estes custos **já estão deduzidos** do lucro líquido.
        """)
# Alerta para lucro negativo
if lucros['lucro_liquido'] < 0:
    st.warning("⚠️ **Atenção:** Esta operação apresenta prejuízo estimado. Revise os valores de entrada.")

st.divider()

# Informações de Investimento
st.subheader("💼 Informações de Investimento")
col_inv1, col_inv2, col_inv3 = st.columns(3)

with col_inv1:
    st.info(f"**Capital Próprio Investido:**\n\n{formatar_moeda(estrutura_capital['capital_proprio_investido'])}")

with col_inv2:
    st.info(f"**Valor Financiado:**\n\n{formatar_moeda(estrutura_capital['valor_financiado'])}")

with col_inv3:
    if estrutura_capital['valor_financiado'] > 0:
        st.info(f"**Tempo de Giro / Parcelas:**\n\n{meses} meses")
    else:
        st.info(f"**Tempo de Giro:**\n\n{meses} meses")

# Informações de Financiamento (se considerar juros)
if considerar_juros and estrutura_capital['valor_financiado'] > 0:
    st.divider()
    st.subheader("🏦 Detalhes do Financiamento")
    col_fin1, col_fin2, col_fin3, col_fin4, col_fin5 = st.columns(5)
    
    with col_fin1:
        st.metric("Prazo do Financiamento", f"{prazo_financiamento_meses} meses")
    
    with col_fin2:
        st.metric("Prestação Mensal", formatar_moeda(custos_financ['prestacao_mensal']))
    
    with col_fin3:
        st.metric("Prestações Pagas (Giro)", formatar_moeda(custos_financ['total_prestacoes_pagas']))
    
    with col_fin4:
        st.metric("Juros Pagos no Giro", formatar_moeda(custos_financ['juros_pagos_no_giro']))
    
    with col_fin5:
        st.metric("Saldo Devedor na Venda", formatar_moeda(custos_financ['saldo_devedor']))
    
    st.caption(f"""
💡 **Importante sobre o financiamento:**

Durante os **{meses} meses de giro**, você pagará **{meses} prestações** totalizando {formatar_moeda(custos_financ['total_prestacoes_pagas'])}.

Composição das prestações pagas:
- Juros: {formatar_moeda(custos_financ['juros_pagos_no_giro'])} (custo efetivo)
- Amortização: {formatar_moeda(custos_financ['total_prestacoes_pagas'] - custos_financ['juros_pagos_no_giro'])} (redução da dívida)

**Na venda do imóvel:**
O saldo devedor de {formatar_moeda(custos_financ['saldo_devedor'])} será quitado diretamente do valor recebido pelo imóvel.
Este valor **JÁ está descontado** no cálculo do lucro líquido apresentado acima.
""")

st.divider()

# Demonstrativo de Fluxo de Caixa
with st.expander("💵 Demonstrativo de Fluxo de Caixa Completo", expanded=True):
    st.markdown("### Análise Detalhada: De Onde Vem e Para Onde Vai Seu Dinheiro")
    
    df_fluxo = criar_demonstrativo_fluxo_caixa(
    estrutura_capital['capital_proprio_investido'],
    custos_financ['juros_pagos_no_giro'],
    revenda,
    lucros['comissao_venda'],  # SEMPRE paga
    lucros['custos_transferencia_vendedor'],  # Condicional
    custos_financ['saldo_devedor'],
    lucros['lucro_bruto'],
    lucros['ir_gcap'],
    lucros['lucro_liquido']
)
    
    st.dataframe(df_fluxo, use_container_width=True, hide_index=True)
    
    # Adicionar explicação sobre amortização
    st.markdown("---")
    st.markdown("#### 🔍 Entendendo as Prestações")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        st.metric("Total das Prestações", formatar_moeda(custos_financ['total_prestacoes_pagas']))
        st.caption("Valor total pago em prestações durante o período de giro")
    
    with col_exp2:
        st.metric("Juros Pagos", formatar_moeda(custos_financ['juros_pagos_no_giro']))
        st.caption("Parte das prestações que foram juros")
    
    with col_exp3:
        amortizacao_giro = custos_financ['total_prestacoes_pagas'] - custos_financ['juros_pagos_no_giro']
        st.metric("Amortização do Principal", formatar_moeda(amortizacao_giro))
        st.caption("Parte das prestações que reduziu a dívida")
    
    st.info(f"""
    💡 **Como funciona a prestação:**
    
    Cada prestação de {formatar_moeda(custos_financ['prestacao_mensal'])} é composta por:
    - **Juros**: A taxa de juros sobre o saldo devedor restante
    - **Amortização**: Pagamento do principal da dívida
    
    Durante os {meses} meses de giro:
    - Você pagou {formatar_moeda(custos_financ['juros_pagos_no_giro'])} em **juros** (custo real)
    - Você pagou {formatar_moeda(amortizacao_giro)} em **amortização** (redução da dívida)
    - O saldo devedor diminuiu de {formatar_moeda(estrutura_capital['valor_financiado'])} para {formatar_moeda(custos_financ['saldo_devedor'])}
    
    ⚠️ **Na venda:** O banco recebe {formatar_moeda(custos_financ['saldo_devedor'])} para quitar totalmente o financiamento.
    Este valor **já está descontado** do seu lucro líquido mostrado acima.
    """)
    
# Validação Matemática (para transparência)
with st.expander("🧮 Validação Matemática do Cálculo", expanded=False):
    st.markdown("### Conferência: O cálculo está correto?")
    
    st.markdown("**Método 1: Fluxo de Caixa Direto**")
    total_saidas = estrutura_capital['capital_proprio_investido'] + custos_financ['juros_pagos_no_giro']
    total_entradas = revenda - lucros['comissao_venda'] - lucros['custos_transferencia_vendedor'] - custos_financ['saldo_devedor']
    lucro_calculado_metodo1 = total_entradas - total_saidas - lucros['ir_gcap']
    
    col_v1, col_v2, col_v3 = st.columns(3)
    
    with col_v1:
        st.metric("Total de Saídas", formatar_moeda(total_saidas))
        st.caption("Capital inicial + Prestações pagas")
    
    with col_v2:
        st.metric("Total de Entradas", formatar_moeda(total_entradas))
        st.caption("Venda - Comissão - Saldo Devedor")
    
    with col_v3:
        st.metric("Lucro (Método 1)", formatar_moeda(lucro_calculado_metodo1))
        st.caption("Entradas - Saídas - IR")
    
    st.markdown("**Método 2: Calculado pelo Sistema**")
    st.metric("Lucro Líquido (Sistema)", formatar_moeda(lucros['lucro_liquido']))
    
    diferenca = abs(lucro_calculado_metodo1 - lucros['lucro_liquido'])
    
    if diferenca < 0.01:  # Tolerância de 1 centavo por arredondamento
        st.success(f"✅ **Validação OK!** Os dois métodos resultam no mesmo valor (diferença: {formatar_moeda(diferenca)}).")
    else:
        st.error(f"⚠️ **Atenção:** Há uma diferença de {formatar_moeda(diferenca)} entre os métodos. Revise os cálculos.")
        
# Detalhamento de Custos (com expander)
with st.expander("📋 Detalhamento Analítico de Custos", expanded=False):
    df_detalhamento = criar_dataframe_detalhamento(
    custos_aquisicao,
    reforma_extras,
    lucros['comissao_venda'],
    lucros['custos_transferencia_vendedor'],
    lucros['ir_gcap'],
    custos_financ['saldo_devedor'],
    custos_financ['total_prestacoes_pagas'],
    lance
)
    st.dataframe(df_detalhamento, use_container_width=True, hide_index=True)

# Informações Adicionais (com expander)
with st.expander("ℹ️ Informações e Premissas do Cálculo", expanded=False):
    st.markdown(f"""
    **Taxas e Impostos Utilizados:**
    - ITBI: {TAXA_ITBI*100}%
    - Escritura: {TAXA_ESCRITURA*100}%
    - Fundos: {TAXA_FUNDOS*100}%
    - Registro: {TAXA_REGISTRO*100}%
    - Comissão de Venda: {TAXA_COMISSAO_VENDA*100}%
    - IR sobre Ganho de Capital: {TAXA_IR_GCAP*100}%
    
    **Metodologia de Cálculo:**
    - **ROI** = (Lucro Líquido / Custo Total do Ativo) × 100
    - **ROE** = (Lucro Líquido / Total Investido) × 100
    - **TIR** = Taxa Interna de Retorno calculada com base no fluxo de caixa mensal
    - **Capital Próprio Investido** = Entrada + Taxas + Comissão Leiloeiro + Custos Extras
    - **Total Investido** = Capital Próprio + Prestações Pagas Durante o Giro
    - **Lucro Líquido** = Receita de Venda - Total Investido - Saldo Devedor - IR
    """)

# Rodapé
st.divider()

st.caption("💡 **Aviso:** Este simulador fornece estimativas baseadas nas informações fornecidas. Consulte profissionais especializados para análises detalhadas.")



