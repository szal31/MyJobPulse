import pandas as pd
import streamlit as st

from load import ROOT, footer, page, read_json

page("Methods & data", "Transparency",
     "Every source, method and known limitation behind the numbers, so results can be checked and reproduced.")

tab1, tab2, tab3 = st.tabs(["Data sources", "Methods", "Limitations"])
with tab1:
    man = pd.read_csv(ROOT / "data" / "raw" / "MANIFEST.csv")
    st.dataframe(man[["id", "rows", "min_date", "max_date"]].rename(
        columns={"id": "Dataset (data.gov.my / OpenDOSM)", "rows": "Rows", "min_date": "From", "max_date": "To"}),
        hide_index=True, use_container_width=True)
    att = read_json("attention")
    st.markdown(f"**Hansard Dewan Rakyat:** malaysia-ai crawl (Apache-2.0) to Jul 2024 + parlimen.gov.my PDFs; "
                f"{att.get('n_sittings', 0)} sittings used.")
with tab2:
    st.markdown("""
- **National forecasts:** naive, seasonal naive and drift benchmarks; ETS (damped); ARIMA (d=1, AIC); SARIMAX with
  industrial production, leading index and COVID / 2025-census dummies; equal-weight ensemble.
- **Validation:** rolling-origin backtests (monthly: 72-month start, 12-month horizon; quarterly: 20/4); MASE headline.
- **Uncertainty:** 80/95% ranges from each model's own backtest errors (split-conformal), widened by √(h/H) beyond the
  tested horizon.
- **State model:** LightGBM pooled over 16 states × 39 quarters with lagged unemployment, manufacturing share (previous
  year, as published) and drivers; exact TreeSHAP explanations; k-means risk profiles; reconciled to the national forecast.
- **Scenarios:** industrial production at 3.1%/yr (current), 8%/yr (NIMP 2030), −5% shock in 2027; TVET push illustrative.
- **Wages lost:** underemployed workers × share of the skilled vs semi-skilled median wage gap × 12 (25 / 50 / 100%).
- **Parliament:** keyword rates, lead/lag correlation, Granger tests; constituency speaker parsing; numeric commitment
  extraction with manual verification.
""")
with tab3:
    st.markdown("""
- No model meaningfully beats naive on these series; forecasts are shown as ranges and scenarios.
- State series are all-ages unemployment; no official youth or underemployment series by state is published quarterly.
- Scenario effects rely on historical driver relationships; the TVET effect is assumed, not estimated.
- Wages lost use constant 2025 wages and an assumed share of the wage gap.
- Hansard keyword counts miss paraphrases; speaker parsing matches most but not all seats.
""")
footer()
