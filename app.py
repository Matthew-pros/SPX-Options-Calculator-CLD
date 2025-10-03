import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time as time_module

# Import vlastních modulů
from calculator import OptionsCalculator
from data_fetcher import MarketDataFetcher
from option_finder import OptionFinder
from utils import format_currency, format_percentage, get_market_status
from config import CONFIG

# ===== KONFIGURACE STRÁNKY =====
st.set_page_config(
    page_title="SPX Options Calculator Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CUSTOM CSS PRO KRÁSNÝ DESIGN =====
st.markdown("""
<style>
    /* Hlavní barvy */
    :root {
        --primary-color: #1f77b4;
        --success-color: #2ecc71;
        --danger-color: #e74c3c;
        --warning-color: #f39c12;
        --dark-bg: #2c3e50;
        --light-bg: #ecf0f1;
    }
    
    /* Metriky */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    [data-testid="metric-container"] [data-testid="metric-label"] {
        color: rgba(255,255,255,0.9);
        font-weight: 600;
    }
    
    [data-testid="metric-container"] [data-testid="metric-value"] {
        color: white;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Boxy pro výsledky */
    .result-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .success-box {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        border-left: 5px solid #2ecc71;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fcb69f 0%, #ffecd2 100%);
        border-left: 5px solid #f39c12;
    }
    
    .info-box {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-left: 5px solid #3498db;
    }
    
    .danger-box {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        border-left: 5px solid #e74c3c;
    }
    
    /* Tlačítka */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 5px;
        font-weight: 600;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    /* Headers */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    h2, h3 {
        color: #2c3e50;
        font-weight: 700;
    }
    
    /* Tabulky */
    .dataframe {
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-radius: 5px;
    }
    
    /* Animace */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    
    .live-indicator {
        animation: pulse 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

# ===== INICIALIZACE =====
@st.cache_resource
def init_services():
    """Inicializuje služby s cachováním"""
    return MarketDataFetcher(), OptionsCalculator(), OptionFinder()

data_fetcher, calculator, option_finder = init_services()

# ===== SESSION STATE =====
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# ===== HLAVIČKA =====
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("📈 SPX Options Calculator Pro")
    st.markdown("**Real-time převod S&P 500 → SPY/ES/XSP s optimálním výběrem strike**")

with col2:
    market_status = get_market_status()
    if market_status['is_open']:
        st.markdown(f"""
        <div class="result-box success-box">
        <b>🟢 Market OPEN</b><br>
        Closes in: {market_status['time_to_close']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="result-box danger-box">
        <b>🔴 Market CLOSED</b><br>
        Opens in: {market_status['time_to_open']}
        </div>
        """, unsafe_allow_html=True)

with col3:
    if st.button("🔄 Refresh Data", key="refresh_main"):
        st.session_state.last_refresh = datetime.now()
        st.rerun()
    st.caption(f"Last update: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

# ===== SIDEBAR =====
with st.sidebar:
    st.header("⚙️ Trading Setup")
    
    # Směr obchodu s lepším UI
    trade_direction = st.radio(
        "📊 Směr obchodu:",
        ["📈 LONG (Call)", "📉 SHORT (Put)"],
        help="Vyber směr podle tvé analýzy"
    )
    is_call = "LONG" in trade_direction
    
    st.divider()
    
    # Aktuální ceny
    st.subheader("💹 Live Market Data")
    prices = data_fetcher.get_all_prices()
    
    if prices.get('SPX'):
        st.metric("S&P 500", f"${prices['SPX']:.2f}")
        current_spx = prices['SPX']
    else:
        current_spx = st.number_input("Zadej S&P 500 (manuálně):", value=5800.0)
    
    st.divider()
    
    # Trading úrovně
    st.subheader("🎯 Trading Levels (S&P 500)")
    
    col1, col2 = st.columns(2)
    with col1:
        entry_price = st.number_input(
            "Entry:",
            value=float(current_spx),
            step=1.0,
            format="%.2f"
        )
    
    with col2:
        if is_call:
            stop_loss = st.number_input(
                "Stop Loss:",
                value=entry_price - 20.0,
                step=1.0,
                format="%.2f"
            )
            take_profit = st.number_input(
                "Take Profit:",
                value=entry_price + 40.0,
                step=1.0,
                format="%.2f"
            )
        else:
            stop_loss = st.number_input(
                "Stop Loss:",
                value=entry_price + 20.0,
                step=1.0,
                format="%.2f"
            )
            take_profit = st.number_input(
                "Take Profit:",
                value=entry_price - 40.0,
                step=1.0,
                format="%.2f"
            )
    
    # RRR kalkulace
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    rrr = reward / risk if risk > 0 else 0
    
    st.metric("Risk/Reward Ratio", f"1:{rrr:.1f}")
    
    st.divider()
    
    # Risk management
    st.subheader("💰 Position Sizing")
    risk_amount = st.number_input(
        "Risk na obchod (USD):",
        min_value=100,
        max_value=25000,
        value=1000,
        step=100,
        help="Maximum ztráta na tento obchod"
    )
    
    st.divider()
    
    # Časové parametry
    st.subheader("⏰ Expirace")
    dte_choice = st.selectbox(
        "DTE (Days to Expiration):",
        options=[0, 1, 2, 3, 5, 7, 14, 21, 30],
        index=0,
        format_func=lambda x: f"Dnes (0DTE)" if x == 0 else f"{x} dnů"
    )
    
    # Advanced settings
    with st.expander("🔧 Pokročilé nastavení"):
        iv_override = st.slider(
            "Implied Volatility Override (%):",
            min_value=5,
            max_value=100,
            value=20,
            step=1
        )
        
        use_mid_price = st.checkbox("Použít mid price (bid/ask)", value=True)
        
        partial_exits = st.checkbox("Plánovat partial exits", value=True)
        
        if partial_exits:
            partial_1 = st.slider("1. partial exit (%)", 0, 100, 33)
            partial_2 = st.slider("2. partial exit (%)", 0, 100, 33)

# ===== HLAVNÍ OBSAH =====

# Získání dat a výpočty
conversions = calculator.convert_spx_levels(entry_price, stop_loss, take_profit)

# První řádek - Live data a konverze
st.markdown("### 📊 Real-time Market Overview")
col1, col2, col3, col4 = st.columns(4)

instruments = [
    ("SPY", "SPDR S&P 500 ETF", prices.get('SPY', 0)),
    ("ES", "E-mini Futures", prices.get('ES', 0)),
    ("XSP", "Mini-SPX Index", prices.get('XSP', 0)),
    ("VIX", "Volatility Index", prices.get('VIX', 0))
]

for col, (symbol, name, price) in zip([col1, col2, col3, col4], instruments):
    with col:
        if symbol == "VIX":
            color = "🔴" if price > 20 else "🟢"
            st.metric(
                name,
                f"{color} {price:.2f}",
                f"{'High' if price > 20 else 'Low'} volatility"
            )
        else:
            change = ((price / current_spx) - conversions.get(symbol, {}).get('multiplier', 1)) * 100 if symbol != "VIX" else 0
            st.metric(
                name,
                f"${price:.2f}",
                f"{change:+.3f}%" if symbol != "VIX" else None
            )

# Druhý řádek - Konvertované úrovně
st.markdown("### 🎯 Konvertované Trading Levels")

# Vytvoření tabulky s konverzemi
col1, col2 = st.columns([1, 2])

with col1:
    # Tabulka konverzí
    conv_data = []
    for inst in ['SPY', 'ES', 'XSP']:
        conv_data.append({
            'Instrument': inst,
            'Entry': f"${conversions[inst]['entry']:.2f}",
            'Stop Loss': f"${conversions[inst]['sl']:.2f}",
            'Take Profit': f"${conversions[inst]['tp']:.2f}",
            'Range': f"{abs(conversions[inst]['tp'] - conversions[inst]['entry']):.2f}"
        })
    
    conv_df = pd.DataFrame(conv_data)
    st.dataframe(conv_df, use_container_width=True, hide_index=True)

with col2:
    # Vizualizace úrovní
    fig = go.Figure()
    
    # Pro každý instrument
    for i, inst in enumerate(['SPY', 'ES', 'XSP']):
        y_pos = i
        
        # Entry point
        fig.add_trace(go.Scatter(
            x=[conversions[inst]['entry']],
            y=[y_pos],
            mode='markers',
            name=f'{inst} Entry',
            marker=dict(size=15, color='blue', symbol='diamond'),
            showlegend=False
        ))
        
        # Stop Loss
        fig.add_trace(go.Scatter(
            x=[conversions[inst]['sl']],
            y=[y_pos],
            mode='markers',
            name=f'{inst} SL',
            marker=dict(size=12, color='red', symbol='x'),
            showlegend=False
        ))
        
        # Take Profit
        fig.add_trace(go.Scatter(
            x=[conversions[inst]['tp']],
            y=[y_pos],
            mode='markers',
            name=f'{inst} TP',
            marker=dict(size=12, color='green', symbol='star'),
            showlegend=False
        ))
        
        # Range line
        fig.add_shape(
            type="line",
            x0=conversions[inst]['sl'], x1=conversions[inst]['tp'],
            y0=y_pos, y1=y_pos,
            line=dict(color="gray", width=3, dash="dot"),
        )
    
    fig.update_layout(
        title="Trading Levels Visualization",
        xaxis_title="Price",
        yaxis=dict(
            tickmode='array',
            tickvals=[0, 1, 2],
            ticktext=['SPY', 'ES', 'XSP']
        ),
        height=300,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Třetí řádek - Optimální opce
st.markdown("### 🎲 Optimální Opční Strategie")

# Výběr instrumentu pro opce
col1, col2 = st.columns([1, 2])

with col1:
    selected_instrument = st.selectbox(
        "Vyber instrument pro opce:",
        ["SPY", "XSP"],
        index=0,
        help="SPY = větší likvidita, XSP = cash-settled"
    )
    
    # Najdi optimální opci
    optimal_option = option_finder.find_best_strike(
        instrument=selected_instrument,
        current_price=prices.get(selected_instrument, conversions[selected_instrument]['entry']),
        entry=conversions[selected_instrument]['entry'],
        target=conversions[selected_instrument]['tp'],
        stop=conversions[selected_instrument]['sl'],
        risk_amount=risk_amount,
        is_call=is_call,
        dte=dte_choice,
        iv=iv_override/100
    )

with col2:
    if optimal_option and optimal_option['found']:
        st.markdown(f"""
        <div class="result-box success-box">
        <h4>✅ Optimální Opce Nalezena!</h4>
        <b>Strike:</b> ${optimal_option['strike']:.0f}<br>
        <b>Premium (vstup):</b> ${optimal_option['entry_price']:.2f}<br>
        <b>Počet kontraktů:</b> {optimal_option['contracts']}<br>
        <b>Celkový risk:</b> ${optimal_option['total_risk']:.0f}<br>
        <b>Max profit:</b> ${optimal_option['max_profit']:.0f}<br>
        <b>RRR:</b> 1:{optimal_option['rrr']:.1f}<br>
        <b>Break-even:</b> ${optimal_option['breakeven']:.2f}<br>
        <b>Pravděpodobnost zisku:</b> {optimal_option['probability']:.1%}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="result-box warning-box">
        <h4>⚠️ Optimální opce nenalezena</h4>
        Zkuste upravit parametry nebo počkejte na lepší setup.
        </div>
        """, unsafe_allow_html=True)

# Čtvrtý řádek - P/L Graf a Greeks
if optimal_option and optimal_option['found']:
    st.markdown("### 📈 Profit/Loss Analýza")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # P/L diagram
        spot_range = np.linspace(
            conversions[selected_instrument]['sl'] * 0.98,
            conversions[selected_instrument]['tp'] * 1.02,
            100
        )
        
        pl_data = []
        for spot in spot_range:
            pl = calculator.calculate_option_pl(
                spot_price=spot,
                strike=optimal_option['strike'],
                premium=optimal_option['entry_price'],
                contracts=optimal_option['contracts'],
                is_call=is_call
            )
            pl_data.append(pl)
        
        fig = go.Figure()
        
        # P/L křivka
        fig.add_trace(go.Scatter(
            x=spot_range,
            y=pl_data,
            mode='lines',
            name='P/L at Expiry',
            line=dict(color='blue', width=3)
        ))
        
        # Horizontální čáry
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break Even")
        fig.add_hline(y=-risk_amount, line_dash="dash", line_color="red", annotation_text="Max Loss")
        fig.add_hline(y=optimal_option['max_profit'], line_dash="dash", line_color="green", annotation_text="Max Profit")
        
        # Vertikální čáry
        fig.add_vline(x=conversions[selected_instrument]['entry'], line_dash="dot", line_color="blue", annotation_text="Entry")
        fig.add_vline(x=conversions[selected_instrument]['tp'], line_dash="dot", line_color="green", annotation_text="Target")
        fig.add_vline(x=conversions[selected_instrument]['sl'], line_dash="dot", line_color="red", annotation_text="Stop")
        
        fig.update_layout(
            title="P/L Diagram při expiraci",
            xaxis_title=f"{selected_instrument} Price",
            yaxis_title="Profit/Loss ($)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Greeks
        greeks = calculator.calculate_greeks(
            spot=prices.get(selected_instrument, conversions[selected_instrument]['entry']),
            strike=optimal_option['strike'],
            dte=dte_choice if dte_choice > 0 else 0.25,
            iv=iv_override/100,
            is_call=is_call
        )
        
        st.markdown("#### Greeks")
        
        greek_col1, greek_col2 = st.columns(2)
        with greek_col1:
            st.metric("Delta", f"{greeks['delta']:.3f}", 
                     help="Změna ceny opce při $1 pohybu podkladu")
            st.metric("Gamma", f"{greeks['gamma']:.4f}",
                     help="Změna delty při $1 pohybu podkladu")
        
        with greek_col2:
            st.metric("Theta", f"-${abs(greeks['theta']):.2f}",
                     help="Denní časový rozpad",
                     delta_color="inverse")
            st.metric("Vega", f"${greeks['vega']:.2f}",
                     help="Změna ceny při 1% změně IV")
        
        # Probability cone
        st.markdown("#### 📊 Probability Analysis")
        
        prob_df = pd.DataFrame({
            'Scénář': ['🎯 Dosažení TP', '🛑 Dosažení SL', '↔️ Mezi úrovněmi'],
            'Pravděpodobnost': [
                f"{optimal_option['probability']:.1%}",
                f"{optimal_option.get('prob_loss', 0.3):.1%}",
                f"{(1 - optimal_option['probability'] - optimal_option.get('prob_loss', 0.3)):.1%}"
            ],
            'Výsledek': [
                f"+${optimal_option['max_profit']:.0f}",
                f"-${risk_amount:.0f}",
                "Variabilní"
            ]
        })
        
        st.dataframe(prob_df, use_container_width=True, hide_index=True)

# Pátý řádek - Exekuční plán
st.markdown("### 📝 Exekuční Plán")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 1️⃣ Pre-Trade Checklist")
    
    checklist = [
        "Market momentum souhlasí",
        "Jsme v trading hours",
        "IV není extrémní",
        "Likvidita dostatečná",
        "Risk/Reward > 1:2"
    ]
    
    for item in checklist:
        st.checkbox(item, key=f"check_{item}")

with col2:
    st.markdown("#### 2️⃣ Entry Orders")
    
    if optimal_option and optimal_option['found']:
        st.code(f"""
Buy {optimal_option['contracts']}x {selected_instrument} {optimal_option['strike']} {'Call' if is_call else 'Put'}
Limit: ${optimal_option['entry_price']:.2f}
Max fill: ${optimal_option['entry_price'] * 1.02:.2f}
Risk: ${optimal_option['total_risk']:.0f}
        """)
    
    if st.button("📋 Kopírovat order", key="copy_order"):
        st.success("Order zkopírován!")

with col3:
    st.markdown("#### 3️⃣ Exit Strategy")
    
    if partial_exits and optimal_option and optimal_option['found']:
        exit_1_price = optimal_option['entry_price'] * 1.5
        exit_2_price = optimal_option['entry_price'] * 2.0
        exit_3_price = optimal_option['entry_price'] * 3.0
        
        st.markdown(f"""
        **Partial Exits:**
        - {partial_1}% @ ${exit_1_price:.2f} (1.5x)
        - {partial_2}% @ ${exit_2_price:.2f} (2x)
        - {100-partial_1-partial_2}% @ ${exit_3_price:.2f} (3x+)
        
        **Stop Loss:**
        - Cena opce: $0 (max loss)
        - Časový: 15 min před close
        """)
    else:
        st.info("Aktivujte partial exits v pokročilém nastavení")

# Šestý řádek - Live Order Book (pokud máme data)
if st.checkbox("📊 Zobrazit Live Option Chain", value=False):
    st.markdown("### 📊 Live Option Chain")
    
    with st.spinner("Načítám option chain..."):
        chain_data = data_fetcher.get_option_chain_live(selected_instrument, dte_choice)
        
        if chain_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Calls")
                calls_display = chain_data['calls'][['strike', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']]
                calls_display = calls_display[(calls_display['strike'] >= optimal_option['strike'] - 5) & 
                                             (calls_display['strike'] <= optimal_option['strike'] + 5)]
                st.dataframe(calls_display, use_container_width=True)
            
            with col2:
                st.markdown("#### Puts")
                puts_display = chain_data['puts'][['strike', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']]
                puts_display = puts_display[(puts_display['strike'] >= optimal_option['strike'] - 5) & 
                                           (puts_display['strike'] <= optimal_option['strike'] + 5)]
                st.dataframe(puts_display, use_container_width=True)

# Footer
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 📚 Vzdělávací zdroje")
    st.markdown("""
    - [Options Basics](https://www.optionseducation.org)
    - [Greeks Explained](https://www.investopedia.com/trading/greeks/)
    - [0DTE Strategy Guide](https://www.tastytrade.com)
    """)

with col2:
    st.markdown("#### ⚠️ Risk Warning")
    st.warning("""
    0DTE opce jsou extrémně rizikové!
    - Možná ztráta 100% prémia
    - Rychlý časový rozpad
    - Vyžaduje přesný timing
    """)

with col3:
    st.markdown("#### 📧 Support")
    st.info("""
    Pro dotazy a návrhy:
    - GitHub Issues
    - Email: support@example.com
    - Discord: #options-trading
    """)

# Auto-refresh
if st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False):
    time_module.sleep(30)
    st.rerun()
