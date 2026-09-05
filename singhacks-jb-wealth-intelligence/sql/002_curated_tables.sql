-- Typed, normalized tables. No analytical views are created by this project.
CREATE TABLE clients (
    client_id VARCHAR PRIMARY KEY, client_name VARCHAR NOT NULL, age INTEGER,
    gender VARCHAR, nationality VARCHAR, country_of_residence VARCHAR,
    tax_domicile VARCHAR, booking_centre VARCHAR, rm_id VARCHAR, rm_name VARCHAR,
    rm_desk VARCHAR, base_currency VARCHAR, wealth_band VARCHAR,
    total_aum_usd DECIMAL(38,18), life_stage VARCHAR, source_of_wealth VARCHAR,
    risk_profile VARCHAR, risk_tolerance_score INTEGER,
    investment_horizon_years INTEGER, liquidity_needs VARCHAR, objectives VARCHAR,
    client_since DATE, kyc_review_due DATE, pep_status VARCHAR,
    reporting_language VARCHAR
);

CREATE TABLE portfolios (
    portfolio_id VARCHAR PRIMARY KEY, client_id VARCHAR NOT NULL,
    portfolio_name VARCHAR NOT NULL, mandate_code VARCHAR, mandate_name VARCHAR,
    service_model VARCHAR, base_currency VARCHAR, inception_date DATE,
    benchmark VARCHAR, aum_usd_current DECIMAL(38,18),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE instruments (
    instrument_id VARCHAR PRIMARY KEY, instrument_name VARCHAR NOT NULL,
    asset_class VARCHAR, sub_asset_class VARCHAR, sector VARCHAR, region VARCHAR,
    currency VARCHAR, liquidity_tier VARCHAR, underlying_reference VARCHAR,
    sustainability_excluded VARCHAR, concentration_limit_applies VARCHAR
);

CREATE TABLE mandate_rules (
    mandate_code VARCHAR NOT NULL, mandate_name VARCHAR, asset_class VARCHAR NOT NULL,
    min_pct DECIMAL(38,18), target_pct DECIMAL(38,18), max_pct DECIMAL(38,18),
    max_single_position_pct DECIMAL(38,18), mandate_notes VARCHAR,
    PRIMARY KEY (mandate_code, asset_class)
);

CREATE TABLE holdings_snapshots (
    snapshot_date DATE NOT NULL, portfolio_id VARCHAR NOT NULL,
    client_id VARCHAR NOT NULL, instrument_id VARCHAR NOT NULL,
    instrument_name VARCHAR, asset_class VARCHAR, sub_asset_class VARCHAR,
    sector VARCHAR, region VARCHAR, instrument_ccy VARCHAR,
    quantity DECIMAL(38,18), price_local DECIMAL(38,18),
    market_value_local DECIMAL(38,18), portfolio_ccy VARCHAR,
    market_value_base DECIMAL(38,18), market_value_usd DECIMAL(38,18),
    weight_pct DECIMAL(38,18), avg_cost_local DECIMAL(38,18),
    cost_basis_base DECIMAL(38,18), unrealised_pnl_base DECIMAL(38,18),
    unrealised_pnl_pct DECIMAL(38,18), lending_value_base DECIMAL(38,18),
    advance_rate_pct DECIMAL(38,18), liquidity_tier VARCHAR,
    valuation_date DATE, acquired_date DATE,
    PRIMARY KEY (snapshot_date, portfolio_id, instrument_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id)
);

CREATE TABLE transactions (
    transaction_id VARCHAR PRIMARY KEY, trade_date DATE, settlement_date DATE,
    portfolio_id VARCHAR NOT NULL, client_id VARCHAR NOT NULL,
    transaction_type VARCHAR, instrument_id VARCHAR, instrument_name VARCHAR,
    quantity DECIMAL(38,18), price_local DECIMAL(38,18), currency VARCHAR,
    amount DECIMAL(38,18), narrative VARCHAR,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id)
);

CREATE TABLE commitments (
    commitment_id VARCHAR PRIMARY KEY, client_id VARCHAR NOT NULL,
    portfolio_id VARCHAR NOT NULL, fund_name VARCHAR, currency VARCHAR,
    committed DECIMAL(38,18), called_to_date DECIMAL(38,18),
    uncalled DECIMAL(38,18), expected_call_window VARCHAR,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
);

CREATE TABLE credit_facilities (
    facility_id VARCHAR PRIMARY KEY, client_id VARCHAR NOT NULL,
    collateral_portfolio_id VARCHAR NOT NULL, facility_type VARCHAR,
    facility_ccy VARCHAR, credit_limit DECIMAL(38,18),
    interest_rate_pct DECIMAL(38,18), margin_call_ltv_pct DECIMAL(38,18),
    utilisation_pct_current DECIMAL(38,18),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (collateral_portfolio_id) REFERENCES portfolios(portfolio_id)
);

CREATE TABLE facility_snapshots (
    facility_id VARCHAR NOT NULL, snapshot_date DATE NOT NULL,
    drawn DECIMAL(38,18), collateral_market_value DECIMAL(38,18),
    lending_value DECIMAL(38,18), ltv_pct DECIMAL(38,18),
    headroom DECIMAL(38,18),
    PRIMARY KEY (facility_id, snapshot_date),
    FOREIGN KEY (facility_id) REFERENCES credit_facilities(facility_id)
);

CREATE TABLE planned_cash_needs (
    need_id VARCHAR PRIMARY KEY, client_id VARCHAR NOT NULL,
    description VARCHAR, currency VARCHAR, amount DECIMAL(38,18),
    due_from DATE, due_to DATE, recurrence VARCHAR, certainty VARCHAR,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE market_context (
    snapshot_date DATE NOT NULL, series_id VARCHAR NOT NULL, series_name VARCHAR,
    category VARCHAR, unit VARCHAR, value DECIMAL(38,18), snapshot_label VARCHAR,
    PRIMARY KEY (snapshot_date, series_id)
);

CREATE TABLE event_log (
    event_date DATE NOT NULL, event_type VARCHAR NOT NULL, region VARCHAR,
    description VARCHAR, primary_transmission VARCHAR, severity VARCHAR
);

CREATE TABLE rm_notes (
    note_id VARCHAR PRIMARY KEY, client_id VARCHAR NOT NULL, note_date DATE,
    rm_id VARCHAR, rm_name VARCHAR, channel VARCHAR, note VARCHAR,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE portfolio_valuations (
    portfolio_id VARCHAR NOT NULL, client_id VARCHAR NOT NULL,
    snapshot_date DATE NOT NULL, aum DECIMAL(38,18), currency VARCHAR,
    PRIMARY KEY (portfolio_id, snapshot_date),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE instrument_prices (
    instrument_id VARCHAR NOT NULL, snapshot_date DATE NOT NULL,
    price DECIMAL(38,18), currency VARCHAR,
    PRIMARY KEY (instrument_id, snapshot_date),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id)
);
