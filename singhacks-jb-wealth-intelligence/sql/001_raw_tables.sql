-- Raw landing tables. Values are kept as VARCHAR so source representation is
-- retained; typed interpretation happens only in the curated layer.
CREATE TABLE raw_clients (
    client_id VARCHAR, client_name VARCHAR, age VARCHAR, gender VARCHAR,
    nationality VARCHAR, country_of_residence VARCHAR, tax_domicile VARCHAR,
    booking_centre VARCHAR, rm_id VARCHAR, rm_name VARCHAR, rm_desk VARCHAR,
    base_currency VARCHAR, wealth_band VARCHAR, total_aum_usd VARCHAR,
    life_stage VARCHAR, source_of_wealth VARCHAR, risk_profile VARCHAR,
    risk_tolerance_score VARCHAR, investment_horizon_years VARCHAR,
    liquidity_needs VARCHAR, objectives VARCHAR, client_since VARCHAR,
    kyc_review_due VARCHAR, pep_status VARCHAR, reporting_language VARCHAR
);

CREATE TABLE raw_commitments (
    commitment_id VARCHAR, client_id VARCHAR, portfolio_id VARCHAR,
    fund_name VARCHAR, currency VARCHAR, committed VARCHAR,
    called_to_date VARCHAR, uncalled VARCHAR, expected_call_window VARCHAR
);

CREATE TABLE raw_credit_facilities (
    facility_id VARCHAR, client_id VARCHAR, collateral_portfolio_id VARCHAR,
    facility_type VARCHAR, facility_ccy VARCHAR, credit_limit VARCHAR,
    interest_rate_pct VARCHAR, margin_call_ltv_pct VARCHAR,
    "drawn_2025-12-31" VARCHAR, "collateral_market_value_2025-12-31" VARCHAR,
    "lending_value_2025-12-31" VARCHAR, "ltv_pct_2025-12-31" VARCHAR,
    "headroom_2025-12-31" VARCHAR, "drawn_2026-02-27" VARCHAR,
    "collateral_market_value_2026-02-27" VARCHAR, "lending_value_2026-02-27" VARCHAR,
    "ltv_pct_2026-02-27" VARCHAR, "headroom_2026-02-27" VARCHAR,
    "drawn_2026-03-31" VARCHAR, "collateral_market_value_2026-03-31" VARCHAR,
    "lending_value_2026-03-31" VARCHAR, "ltv_pct_2026-03-31" VARCHAR,
    "headroom_2026-03-31" VARCHAR, "drawn_2026-06-30" VARCHAR,
    "collateral_market_value_2026-06-30" VARCHAR, "lending_value_2026-06-30" VARCHAR,
    "ltv_pct_2026-06-30" VARCHAR, "headroom_2026-06-30" VARCHAR,
    "drawn_2026-08-26" VARCHAR, "collateral_market_value_2026-08-26" VARCHAR,
    "lending_value_2026-08-26" VARCHAR, "ltv_pct_2026-08-26" VARCHAR,
    "headroom_2026-08-26" VARCHAR, utilisation_pct_current VARCHAR
);

CREATE TABLE raw_event_log (
    event_date VARCHAR, event_type VARCHAR, region VARCHAR, description VARCHAR,
    primary_transmission VARCHAR, severity VARCHAR
);

CREATE TABLE raw_holdings (
    snapshot_date VARCHAR, portfolio_id VARCHAR, client_id VARCHAR,
    instrument_id VARCHAR, instrument_name VARCHAR, asset_class VARCHAR,
    sub_asset_class VARCHAR, sector VARCHAR, region VARCHAR, instrument_ccy VARCHAR,
    quantity VARCHAR, price_local VARCHAR, market_value_local VARCHAR,
    portfolio_ccy VARCHAR, market_value_base VARCHAR, market_value_usd VARCHAR,
    weight_pct VARCHAR, avg_cost_local VARCHAR, cost_basis_base VARCHAR,
    unrealised_pnl_base VARCHAR, unrealised_pnl_pct VARCHAR,
    lending_value_base VARCHAR, advance_rate_pct VARCHAR, liquidity_tier VARCHAR,
    valuation_date VARCHAR, acquired_date VARCHAR
);

CREATE TABLE raw_instruments (
    instrument_id VARCHAR, instrument_name VARCHAR, asset_class VARCHAR,
    sub_asset_class VARCHAR, sector VARCHAR, region VARCHAR, currency VARCHAR,
    liquidity_tier VARCHAR, underlying_reference VARCHAR,
    sustainability_excluded VARCHAR, concentration_limit_applies VARCHAR,
    "price_2025-12-31" VARCHAR, "price_2026-02-27" VARCHAR,
    "price_2026-03-31" VARCHAR, "price_2026-06-30" VARCHAR,
    "price_2026-08-26" VARCHAR
);

CREATE TABLE raw_mandates (
    mandate_code VARCHAR, mandate_name VARCHAR, asset_class VARCHAR,
    min_pct VARCHAR, target_pct VARCHAR, max_pct VARCHAR,
    max_single_position_pct VARCHAR, mandate_notes VARCHAR
);

CREATE TABLE raw_market_context (
    snapshot_date VARCHAR, series_id VARCHAR, series_name VARCHAR,
    category VARCHAR, unit VARCHAR, value VARCHAR, snapshot_label VARCHAR
);

CREATE TABLE raw_planned_cash_needs (
    need_id VARCHAR, client_id VARCHAR, description VARCHAR, currency VARCHAR,
    amount VARCHAR, due_from VARCHAR, due_to VARCHAR, recurrence VARCHAR,
    certainty VARCHAR
);

CREATE TABLE raw_portfolios (
    portfolio_id VARCHAR, client_id VARCHAR, portfolio_name VARCHAR,
    mandate_code VARCHAR, mandate_name VARCHAR, service_model VARCHAR,
    base_currency VARCHAR, inception_date VARCHAR, benchmark VARCHAR,
    "aum_2025-12-31" VARCHAR, "aum_2026-02-27" VARCHAR,
    "aum_2026-03-31" VARCHAR, "aum_2026-06-30" VARCHAR,
    "aum_2026-08-26" VARCHAR, aum_usd_current VARCHAR
);

CREATE TABLE raw_transactions (
    transaction_id VARCHAR, trade_date VARCHAR, settlement_date VARCHAR,
    portfolio_id VARCHAR, client_id VARCHAR, transaction_type VARCHAR,
    instrument_id VARCHAR, instrument_name VARCHAR, quantity VARCHAR,
    price_local VARCHAR, currency VARCHAR, amount VARCHAR, narrative VARCHAR
);

CREATE TABLE raw_rm_notes (
    note_id VARCHAR, client_id VARCHAR, note_date VARCHAR, rm_id VARCHAR,
    rm_name VARCHAR, channel VARCHAR, note VARCHAR
);

CREATE TABLE ingestion_metadata (
    source_file VARCHAR PRIMARY KEY,
    source_sha256 VARCHAR NOT NULL,
    loaded_at TIMESTAMP NOT NULL,
    row_count BIGINT NOT NULL
);
