import { ClientDossier, MacroIndicator, MarketImpactPillar, RMProfile } from '../types';

/**
 * ============================================================================
 * AURELIUS PRIVATE WEALTH - PROTOTYPE FIXTURE REPOSITORY
 * ============================================================================
 * This file is intentionally retained as a presentation fixture after the
 * prototype was moved into the challenge project. Replace it through the
 * connector boundary in src/services/; do not put credentials or provider
 * calls in this module.
 * ============================================================================
 */

export const currentRM: RMProfile = {
  name: 'Priscilla Ong',
  title: 'Relationship Manager',
  desk: 'Singapore / Hong Kong Asia Desk',
  bookingDesk: {
    name: 'Asia Booking Centres',
    metricLabel: 'Dataset as-of',
    metricValue: '26 Aug 2026',
    status: 'nominal',
  },
  totalDeskAUM: 'Synthetic book · 20 clients',
  activeAlertsCount: 4,
};

export const executiveBriefing = {
  title: 'Automated Portfolio Synthesis & Mandate Scan',
  syncTime: 'Prototype fixture · dataset as-of 26 Aug 2026',
  summary: '4 clients require attention today. The highest-priority issues are rising leverage, a near-term liquidity requirement and portfolio concentration.',
};

export const macroIndicators: MacroIndicator[] = [
  {
    id: 'snb',
    label: 'SNB POLICY',
    value: '1.25%',
    subtext: '(Hold)',
    highlightColor: 'neutral',
  },
  {
    id: 'fed',
    label: 'US FED FUNDS',
    value: '5.25–5.50%',
    highlightColor: 'neutral',
  },
  {
    id: 'tech_vol',
    label: 'TECH VOL (VXN)',
    value: '24.8',
    change: '+14.2%',
    isAlert: true,
    highlightColor: 'red',
  },
  {
    id: 'gold',
    label: 'GOLD (XAU)',
    value: '$2,514.80',
    change: '+1.2%',
    highlightColor: 'amber',
  },
  {
    id: 'brent',
    label: 'BRENT',
    value: '$82.40',
    change: '+1.85%',
    highlightColor: 'neutral',
  },
];

export const marketImpactPillars: MarketImpactPillar[] = [
  {
    id: 'pillar_tech',
    category: 'Equities & Valuation',
    affectedCount: 3,
    badgeStyle: 'red',
    title: 'Technology Sector Volatility & Multiple Compression',
    portfolioImpact:
      'Collateral headroom squeeze on tech founders. Multiple compression across listed tech is tightening Lombard collateral margins and increasing LTV trigger proximity.',
    deskContext:
      'Lombard lending haircuts on high-beta tech widened by 5–8 bps. Maintenance threshold buffers are actively shrinking.',
    affectedClientNames: ['Ravi Chandrasekaran', 'David Lim', 'Chen Wei'],
    affectedClientIds: ['ravi-chandrasekaran', 'david-lim', 'chen-wei'],
  },
  {
    id: 'pillar_energy',
    category: 'Commodities & FX',
    affectedCount: 1,
    badgeStyle: 'amber',
    title: 'Oil & Energy Commodity Price Surge',
    portfolioImpact:
      'Escalating hedge margins & FX cash requirements. Sharp Brent upswing (+1.85%) stresses unhedged transport exposures and calls for variation margin adjustments.',
    deskContext:
      'Middle East energy derivative hedges require USD cash collateral replenishment under ISDA CSAs before close of session.',
    affectedClientNames: ['Fahad Al-Hassan'],
    affectedClientIds: ['fahad-al-hassan'],
  },
  {
    id: 'pillar_gold',
    category: 'Precious Metals & Allocation',
    affectedCount: 4,
    badgeStyle: 'neutral',
    title: 'Gold Reaching Historic Highs',
    portfolioImpact:
      'Profit-taking window vs safe-haven mandate rebalancing. Physical and synthetic bullion holdings exceed conservative strategic caps by 3.5% to 6.2%.',
    deskContext:
      'Opportunity to trim allocation at cycle peak, harvest capital gains, or fund liquidity deficits in private asset commitments.',
    affectedClientNames: ['Henri de Montmirail', 'MVB', 'Sterling', 'Tan'],
    affectedClientIds: ['henri-de-montmirail', 'margarethe-voss-brenner', 'dr-alistair-sterling', 'tan-wei-ling'],
  },
];

export const placeholderClients: ClientDossier[] = [
  {
    id: 'ravi-chandrasekaran',
    ref: 'RC-9942',
    name: 'Ravi Chandrasekaran',
    initials: 'RC',
    tier: 'UHNW',
    mandate: 'Growth Mandate',
    aum: 'USD 46.7m',
    riskLevel: 'HIGH',
    headlineIssue: 'Leverage approaching collateral threshold',
    summary:
      'Ravi drew an additional USD 1.7m following the recent technology decline. Lombard utilisation is now elevated while much of his collateral remains exposed to volatile technology assets.',
    tags: ['72% credit utilisation', 'Technology concentration', 'USD 2m trust funding due'],
    suggestedNextStep: 'Review collateral resilience and bridge-liquidity plan.',

    about: {
      bio: 'Ravi is a technology entrepreneur approaching a potential secondary liquidity event later this year. He remains strongly bullish on technology and prefers borrowing rather than selling his listed positions before the expected sale. Recent additional borrowing has increased the importance of monitoring his collateral.',
      age: 41,
      occupation: 'Technology entrepreneur',
      clientSince: 2021,
    },
    portfolio: {
      totalValue: 'USD 46.7m',
      totalValueSubtext: 'Combined multi-currency assets',
      cashLiquidity: 'USD 3.8m',
      cashLiquidityPercent: '8.1%',
      cashLiquiditySubtext: 'Available overnight sweep',
      borrowingUtilisation: 'USD 11.2m',
      borrowingLtvPercent: 62,
      borrowingStatus: 'ELEVATED',
      allocation: [
        { label: 'Tech Equities', percentage: 64, color: '#1b1a18' },
        { label: 'Fixed Income', percentage: 14, color: '#5c6b73' },
        { label: 'Cash/Liquidity', percentage: 8, color: '#d4a359' },
        { label: 'Private', percentage: 14, color: '#dedcd7' },
      ],
      trajectory: {
        deltaPercent: '+18.4%',
        deltaPeriod: '1-Year Delta',
        startLabel: 'Oct 2023 (USD 39.4m)',
        troughLabel: 'Dip & Leverage Drawn (USD 36.1m)',
        endLabel: 'Current (USD 46.7m)',
        points: [
          { date: 'Oct 2023', value: 39.4 },
          { date: 'Jan 2024', value: 38.6 },
          { date: 'Apr 2024', value: 36.1 },
          { date: 'Jul 2024', value: 43.2 },
          { date: 'Sep 2024', value: 46.7 },
        ],
      },
      topHoldings: [
        {
          id: 'h1',
          name: 'Cloudflare Inc.',
          ticker: 'NYSE: NET · Enterprise Tech',
          sector: 'Enterprise Tech',
          value: 'USD 14.2m',
          percentage: 30.4,
        },
        {
          id: 'h2',
          name: 'Snowflake Inc.',
          ticker: 'NYSE: SNOW · Cloud Data',
          sector: 'Cloud Data',
          value: 'USD 9.6m',
          percentage: 20.5,
        },
        {
          id: 'h3',
          name: 'US 2Y Treasury Notes',
          ticker: 'Sovereign Debt · 4.85% YTM',
          sector: 'Sovereign Debt',
          value: 'USD 6.5m',
          percentage: 13.9,
        },
        {
          id: 'h4',
          name: 'Datadog Inc.',
          ticker: 'NASDAQ: DDOG · Infrastructure',
          sector: 'Infrastructure',
          value: 'USD 6.1m',
          percentage: 13.1,
        },
      ],
      remainingHoldingsNote:
        'Remaining USD 10.3m distributed across unlisted startup equity, cash equivalents, and alternative fund interests.',
    },
    portfolioExplanation: {
      generatedAt: '3 Hours Ago',
      title: 'What changed?',
      overview:
        'Ravi increased borrowing after the recent technology sell-off while keeping his technology positions largely unchanged. The portfolio has since recovered, but the combination of leverage and concentration means another technology decline could have a larger impact.',
      whatMovedAndWhy: [
        { title: 'Leverage and concentration', description: 'Borrowing depends on the value of the same volatile technology assets the client wants to continue holding.' },
      ],
      whatToWatch: [
        { title: 'Technology prices', description: 'Watch technology prices and the resulting collateral value.' },
        { title: 'Expected liquidity event', description: 'The anticipated Q4 liquidity event remains important to the client’s funding outlook.' },
      ],
    },
    advisory: {
      generatedAt: '3 Hours Ago',
      risks: [
        {
          title: 'Technology concentration',
          description: '64% of total asset base in four high-beta enterprise software equities.',
        },
        {
          title: 'Increased leverage',
          description: 'Facility drawdown increased by USD 3.5m, narrowing collateral buffer to 18% in a downside scenario.',
        },
        {
          title: 'Dependence on expected liquidity event',
          description: 'Debt service strategy assumes secondary share sale completes in Q4 without delay.',
        },
      ],
      opportunities: [
        {
          title: 'Plan diversification after the liquidity event',
          description: 'Structure pre-hedging and programmatic reallocation into multi-asset wealth preservation vehicles.',
        },
        {
          title: 'Review alternative bridge-liquidity options',
          description: 'Introduce private credit or uncalled commitment facilities with lower margin-call risk.',
        },
        {
          title: 'Prepare long-term trust allocation',
          description: 'Initiate Singapore VCC or Cayman family trust structure ahead of liquidity distribution.',
        },
      ],
    },
  },
  {
    id: 'margarethe-voss-brenner',
    ref: 'MV-1804',
    name: 'Margarethe Voss-Brenner',
    initials: 'MV',
    tier: 'UHNW',
    mandate: 'Conservative',
    aum: 'USD 38.2m',
    riskLevel: 'CRITICAL',
    headlineIssue: 'Portfolio drift conflicting with stated capital preservation mandate',
    summary:
      'Subordinated bond duration extension and equity allocation have drifted to 34% vs 15% maximum target following mandate revision. Yield seeking has introduced unapproved drawdown vulnerability.',
    tags: ['+19% risk asset deviation', 'Fixed income duration > 7.4y', 'Risk profile breach'],
    suggestedNextStep: 'Rebalance EUR 4.1m into sovereign short-duration notes before quarterly committee.',

    about: {
      bio: 'Margarethe is a third-generation family office principal with strict preservation requirements. Following low cash rates last year, an automated sleeve expanded into subordinated paper. Mandate compliance now requires immediate rebalancing before the upcoming European Investment Committee.',
      age: 58,
      occupation: 'Family Office Trustee',
      clientSince: 2017,
    },
    portfolio: {
      totalValue: 'USD 38.2m',
      totalValueSubtext: 'Custodied between Zurich & Luxembourg',
      cashLiquidity: 'USD 2.1m',
      cashLiquidityPercent: '5.5%',
      cashLiquiditySubtext: 'Multi-currency call deposits',
      borrowingUtilisation: 'USD 2.4m',
      borrowingLtvPercent: 22,
      borrowingStatus: 'NORMAL',
      allocation: [
        { label: 'Sovereign Debt', percentage: 48, color: '#1b1a18' },
        { label: 'Subordinated Debt', percentage: 22, color: '#7A1C28' },
        { label: 'European Blue Chips', percentage: 12, color: '#5c6b73' },
        { label: 'Cash & Gold', percentage: 18, color: '#d4a359' },
      ],
      trajectory: {
        deltaPercent: '+4.2%',
        deltaPeriod: '1-Year Delta',
        startLabel: 'Oct 2023 (USD 36.6m)',
        troughLabel: 'Yield Spread Widening (USD 35.8m)',
        endLabel: 'Current (USD 38.2m)',
        points: [
          { date: 'Oct 2023', value: 36.6 },
          { date: 'Jan 2024', value: 36.9 },
          { date: 'Apr 2024', value: 35.8 },
          { date: 'Jul 2024', value: 37.4 },
          { date: 'Sep 2024', value: 38.2 },
        ],
      },
      topHoldings: [
        {
          id: 'mv1',
          name: 'German Bund 10Y 2.6%',
          ticker: 'DE0001102580 · Sovereign',
          sector: 'Sovereign Debt',
          value: 'USD 11.4m',
          percentage: 29.8,
        },
        {
          id: 'mv2',
          name: 'Swiss Confederation 1.25%',
          ticker: 'CH0224396996 · Sovereign',
          sector: 'Sovereign Debt',
          value: 'USD 8.2m',
          percentage: 21.5,
        },
        {
          id: 'mv3',
          name: 'BNP Paribas Tier 2 Subordinated',
          ticker: 'XS2176714081 · Banking',
          sector: 'Subordinated Debt',
          value: 'USD 4.8m',
          percentage: 12.6,
        },
        {
          id: 'mv4',
          name: 'Nestlé SA Registered',
          ticker: 'SIX: NESN · Consumer Defensive',
          sector: 'Equities',
          value: 'USD 3.6m',
          percentage: 9.4,
        },
      ],
      remainingHoldingsNote:
        'Remaining USD 10.2m allocated in Swiss Franc time deposits, physical gold certificates, and liquidity reserves.',
    },
    portfolioExplanation: {
      generatedAt: '2 Hours Ago',
      title: 'What changed?',
      overview:
        'Subordinated bond yield expansion drove unintentional duration creep beyond the mandate ceiling of 5.0 years (currently 7.4 years). Additionally, equity outperformance shifted tactical equity weight to 34% versus the 15% mandate cap.',
      whatMovedAndWhy: [
        { title: 'Mandate threshold', description: 'The current positioning breaches a formal fiduciary mandate threshold.' },
        { title: 'Rate sensitivity', description: 'European rate volatility could create an unapproved mark-to-market drawdown.' },
      ],
      whatToWatch: [
        { title: 'Central-bank guidance', description: 'Monitor ECB forward guidance and the Swiss franc yield curve.' },
        { title: 'Compliance deadline', description: 'Track the Investment Committee compliance deadline.' },
      ],
    },
    advisory: {
      generatedAt: '2 Hours Ago',
      risks: [
        {
          title: 'Mandate compliance breach',
          description: 'Risk profile drift violates stated conservative preservation objectives.',
        },
        {
          title: 'Duration extension risk',
          description: 'Fixed income portfolio duration of 7.4 years exposes capital to rate shocks.',
        },
      ],
      opportunities: [
        {
          title: 'Trim subordinated credit into sovereign notes',
          description: 'Rebalance EUR 4.1m into 12-month Swiss and German paper to lock in yield with minimal duration risk.',
        },
        {
          title: 'Establish rule-based algorithmic collar',
          description: 'Protect equity gains with automated corridor collars before committee review.',
        },
      ],
    },
  },
  {
    id: 'david-lim',
    ref: 'DL-4012',
    name: 'David Lim',
    initials: 'DL',
    tier: 'HNW',
    mandate: 'Balanced',
    aum: 'USD 24.5m',
    riskLevel: 'HIGH',
    headlineIssue: 'Upcoming major cash requirement with illiquid private assets',
    summary:
      'Upcoming USD 3.5m capital call for Southeast Asia Tech Fund IV due in 12 days. Current unencumbered cash balance is USD 850k while liquid public allocation is restricted by lockup.',
    tags: ['USD 3.5m capital call due 16 Sep', 'USD 850k available cash', 'Private credit liquidity gap'],
    suggestedNextStep: 'Discuss partial secondary disposal or short-term Lombard liquidity facility.',

    about: {
      bio: 'David is a venture capitalist and angel investor based between Singapore and Hong Kong. With substantial capital deployed into private equity commitments, his cash flow needs require structured liquidity planning around discrete fund capital calls.',
      age: 49,
      occupation: 'Venture Capital Partner',
      clientSince: 2022,
    },
    portfolio: {
      totalValue: 'USD 24.5m',
      totalValueSubtext: 'Singapore Booking Center',
      cashLiquidity: 'USD 850k',
      cashLiquidityPercent: '3.5%',
      cashLiquiditySubtext: 'Immediate liquid cash reserves',
      borrowingUtilisation: 'USD 4.5m',
      borrowingLtvPercent: 44,
      borrowingStatus: 'NORMAL',
      allocation: [
        { label: 'Private Equity & VC', percentage: 52, color: '#1b1a18' },
        { label: 'Public Equities (Lockup)', percentage: 28, color: '#5c6b73' },
        { label: 'Fixed Income', percentage: 16.5, color: '#dedcd7' },
        { label: 'Cash', percentage: 3.5, color: '#d4a359' },
      ],
      trajectory: {
        deltaPercent: '+12.1%',
        deltaPeriod: '1-Year Delta',
        startLabel: 'Oct 2023 (USD 21.8m)',
        troughLabel: 'Private Asset Drawdown (USD 20.9m)',
        endLabel: 'Current (USD 24.5m)',
        points: [
          { date: 'Oct 2023', value: 21.8 },
          { date: 'Jan 2024', value: 22.4 },
          { date: 'Apr 2024', value: 20.9 },
          { date: 'Jul 2024', value: 23.8 },
          { date: 'Sep 2024', value: 24.5 },
        ],
      },
      topHoldings: [
        {
          id: 'dl1',
          name: 'SEA Tech Fund IV LP',
          ticker: 'Private Equity · Series IV',
          sector: 'Venture Capital',
          value: 'USD 7.2m',
          percentage: 29.4,
        },
        {
          id: 'dl2',
          name: 'Grab Holdings Class A',
          ticker: 'NASDAQ: GRAB (Restricted)',
          sector: 'Consumer Tech',
          value: 'USD 4.8m',
          percentage: 19.6,
        },
        {
          id: 'dl3',
          name: 'Singapore Govt Bond 3.25%',
          ticker: 'SG31A9000002 · Sovereign',
          sector: 'Fixed Income',
          value: 'USD 3.4m',
          percentage: 13.9,
        },
        {
          id: 'dl4',
          name: 'Sea Limited ADR',
          ticker: 'NYSE: SE · E-Commerce',
          sector: 'Tech',
          value: 'USD 2.8m',
          percentage: 11.4,
        },
      ],
      remainingHoldingsNote:
        'Remaining USD 6.3m held in early-stage convertible notes, regional growth equity funds, and escrow reserves.',
    },
    portfolioExplanation: {
      generatedAt: '4 Hours Ago',
      title: 'What changed?',
      overview:
        'A mandatory capital call of USD 3.5m was issued for SEA Tech Fund IV with settlement on 16 September. Available unencumbered cash is USD 850k, resulting in an unhedged USD 2.65m funding shortfall.',
      whatMovedAndWhy: [
        { title: 'Capital-call obligation', description: 'Defaulting on an LP capital call can incur heavy penalties and forfeiture clauses.' },
        { title: 'Restricted liquidity', description: 'Public-stock lockups prevent a direct secondary sale without a sponsor waiver.' },
      ],
      whatToWatch: [
        { title: 'Capital-call deadline', description: 'The settlement deadline is in 12 days.' },
        { title: 'Available funding', description: 'Monitor Lombard-line headroom and the lockup release calendar.' },
      ],
    },
    advisory: {
      generatedAt: '4 Hours Ago',
      risks: [
        {
          title: 'Liquidity shortfall on capital call',
          description: 'USD 2.65m gap must be funded within 12 banking days.',
        },
        {
          title: 'Public shares transfer restriction',
          description: '60% of liquid securities are restricted under founder lockup until Q1 2027.',
        },
      ],
      opportunities: [
        {
          title: 'Pre-approved bridge Lombard facility',
          description: 'Leverage unencumbered Singapore sovereign paper to provide an immediate USD 3.0m credit line.',
        },
        {
          title: 'Secondary LP stake tender',
          description: 'Facilitate an orderly private secondary transfer for a legacy 2018 vintage fund.',
        },
      ],
    },
  },
  {
    id: 'henri-de-montmirail',
    ref: 'HM-8201',
    name: 'Henri de Montmirail',
    initials: 'HM',
    tier: 'UHNW',
    mandate: 'Wealth Preservation',
    aum: 'USD 62.0m',
    riskLevel: 'MEDIUM',
    headlineIssue: 'Correlated commercial real estate exposure across operating holding and private mandate',
    summary:
      'Family office real estate syndicate refinancing pressures in Western Europe overlap with private mandate REIT and commercial paper holdings, compounding downside sensitivity.',
    tags: ['41% sector correlation', 'Debt maturity Q4 2026', 'Syndicate refinancing'],
    suggestedNextStep: 'Stress-test client portfolio under a 150 bps rate shock and propose sector diversification.',

    about: {
      bio: 'Henri manages a multi-generational European family estate with significant commercial property holdings in Paris, Frankfurt, and Geneva. His Aurelius mandate is wealth preservation, but cross-asset correlation has risen.',
      age: 63,
      occupation: 'Industrialist & Real Estate Principal',
      clientSince: 2015,
    },
    portfolio: {
      totalValue: 'USD 62.0m',
      totalValueSubtext: 'Zurich Booking Desk',
      cashLiquidity: 'USD 5.9m',
      cashLiquidityPercent: '9.5%',
      cashLiquiditySubtext: 'Cash and precious metals sweep',
      borrowingUtilisation: 'USD 8.1m',
      borrowingLtvPercent: 32,
      borrowingStatus: 'NORMAL',
      allocation: [
        { label: 'Real Estate & Infrastructure', percentage: 41, color: '#1b1a18' },
        { label: 'Physical Gold & Commodities', percentage: 26, color: '#d4a359' },
        { label: 'Sovereign Debt', percentage: 23.5, color: '#5c6b73' },
        { label: 'Cash Equivalents', percentage: 9.5, color: '#dedcd7' },
      ],
      trajectory: {
        deltaPercent: '+6.8%',
        deltaPeriod: '1-Year Delta',
        startLabel: 'Oct 2023 (USD 58.1m)',
        troughLabel: 'Real Estate Cap Rate Expansion (USD 56.4m)',
        endLabel: 'Current (USD 62.0m)',
        points: [
          { date: 'Oct 2023', value: 58.1 },
          { date: 'Jan 2024', value: 58.9 },
          { date: 'Apr 2024', value: 56.4 },
          { date: 'Jul 2024', value: 60.5 },
          { date: 'Sep 2024', value: 62.0 },
        ],
      },
      topHoldings: [
        {
          id: 'hm1',
          name: 'Swiss Prime Site AG',
          ticker: 'SIX: SPSN · Real Estate',
          sector: 'Commercial Real Estate',
          value: 'USD 14.8m',
          percentage: 23.9,
        },
        {
          id: 'hm2',
          name: 'Physical Bullion Custody (Zurich)',
          ticker: 'XAU Physical · Unallocated Allocated',
          sector: 'Precious Metals',
          value: 'USD 12.6m',
          percentage: 20.3,
        },
        {
          id: 'hm3',
          name: 'Gecina SA Commercial REIT',
          ticker: 'EPA: GFC · French Commercial',
          sector: 'Real Estate',
          value: 'USD 7.4m',
          percentage: 11.9,
        },
        {
          id: 'hm4',
          name: 'French OAT 10Y Benchmark',
          ticker: 'FR0014007L00 · Sovereign',
          sector: 'Fixed Income',
          value: 'USD 6.8m',
          percentage: 11.0,
        },
      ],
      remainingHoldingsNote:
        'Remaining USD 20.4m held in European logistics funds, Swiss cantonal paper, and USD/CHF liquidity accounts.',
    },
    portfolioExplanation: {
      generatedAt: '5 Hours Ago',
      title: 'What changed?',
      overview:
        'European office re-valuations and syndicate refinancing spreads widened. The client’s external family office debt maturing in late 2026 creates hidden correlation with his private banking mandate REIT positions.',
      whatMovedAndWhy: [
        { title: 'Correlated real-estate exposure', description: 'A commercial real-estate downturn could affect both operating cash flows and bankable portfolio collateral.' },
      ],
      whatToWatch: [
        { title: 'Property-market signals', description: 'Monitor European office occupancy data and German Pfandbriefe yields.' },
        { title: 'Refinancing terms', description: 'Track Q4 refinancing syndication terms.' },
      ],
    },
    advisory: {
      generatedAt: '5 Hours Ago',
      risks: [
        {
          title: 'High real estate concentration',
          description: '41% portfolio exposure coupled with operating business in identical sector.',
        },
        {
          title: 'Refinancing timeline pressure',
          description: 'Operating syndicate debt refinancing in Q4 2026.',
        },
      ],
      opportunities: [
        {
          title: 'Harvest gold cycle gains into global infrastructure',
          description: 'Take profit on gold holdings exceeding 20% cap to fund floating-rate global infrastructure assets.',
        },
        {
          title: 'Interest rate hedging swap',
          description: 'Execute forward Euribor interest rate caps to protect operating syndicate liabilities.',
        },
      ],
    },
  },
  {
    id: 'dr-alistair-sterling',
    ref: 'AS-5519',
    name: 'Dr. Alistair Sterling',
    initials: 'AS',
    tier: 'HNW',
    mandate: 'Growth',
    aum: 'USD 18.9m',
    riskLevel: 'MEDIUM',
    headlineIssue: 'Concentration in sector tied to operating business liquidity',
    summary:
      'Healthcare & biotech holdings account for 58% of liquid portfolio while primary surgical device business faces delayed regulatory clearance, creating dual-exposure risk.',
    tags: ['58% biotech concentration', 'Dual operating & portfolio risk', 'Mandate review pending'],
    suggestedNextStep: 'Propose phased hedging collar on listed holdings.',

    about: {
      bio: 'Dr. Sterling is a medical surgeon and founder of a specialist cardiovascular surgical device venture. With personal equity in early clinical trials, his liquid portfolio is also heavily tilted toward listed biotechnology stocks.',
      age: 52,
      occupation: 'Surgeon & Biotech Founder',
      clientSince: 2019,
    },
    portfolio: {
      totalValue: 'USD 18.9m',
      totalValueSubtext: 'London / Zurich Custody',
      cashLiquidity: 'USD 1.4m',
      cashLiquidityPercent: '7.4%',
      cashLiquiditySubtext: 'Operating liquidity buffer',
      borrowingUtilisation: 'USD 2.8m',
      borrowingLtvPercent: 28,
      borrowingStatus: 'NORMAL',
      allocation: [
        { label: 'Biotech & Pharma', percentage: 58, color: '#1b1a18' },
        { label: 'Global Equities', percentage: 22, color: '#5c6b73' },
        { label: 'Short-Term Paper', percentage: 12.6, color: '#dedcd7' },
        { label: 'Cash & Sweeps', percentage: 7.4, color: '#d4a359' },
      ],
      trajectory: {
        deltaPercent: '+9.3%',
        deltaPeriod: '1-Year Delta',
        startLabel: 'Oct 2023 (USD 17.3m)',
        troughLabel: 'Clinical Trial Readout Volatility (USD 16.1m)',
        endLabel: 'Current (USD 18.9m)',
        points: [
          { date: 'Oct 2023', value: 17.3 },
          { date: 'Jan 2024', value: 17.8 },
          { date: 'Apr 2024', value: 16.1 },
          { date: 'Jul 2024', value: 18.2 },
          { date: 'Sep 2024', value: 18.9 },
        ],
      },
      topHoldings: [
        {
          id: 'as1',
          name: 'Vertex Pharmaceuticals',
          ticker: 'NASDAQ: VRTX · Biotech',
          sector: 'Healthcare',
          value: 'USD 4.9m',
          percentage: 26.0,
        },
        {
          id: 'as2',
          name: 'Regeneron Pharmaceuticals',
          ticker: 'NASDAQ: REGN · Therapeutics',
          sector: 'Biotech',
          value: 'USD 3.8m',
          percentage: 20.1,
        },
        {
          id: 'as3',
          name: 'Novo Nordisk A/S ADR',
          ticker: 'NYSE: NVO · Healthcare',
          sector: 'Pharma',
          value: 'USD 2.3m',
          percentage: 12.2,
        },
        {
          id: 'as4',
          name: 'UK Treasury Gilt 4.25%',
          ticker: 'GB00B16NNR78 · Sovereign',
          sector: 'Fixed Income',
          value: 'USD 1.8m',
          percentage: 9.5,
        },
      ],
      remainingHoldingsNote:
        'Remaining USD 6.1m held in private medical device patents, med-tech venture funds, and multi-currency cash.',
    },
    portfolioExplanation: {
      generatedAt: '6 Hours Ago',
      title: 'What changed?',
      overview:
        'Regulatory review timeline for the client’s core venture was deferred by 6 months, slowing anticipated corporate dividend distribution while listed biotech volatility remains elevated.',
      whatMovedAndWhy: [
        { title: 'Linked operating and market risk', description: 'Further approval delays alongside a biotech-market correction could create simultaneous equity losses and operating cash strain.' },
      ],
      whatToWatch: [
        { title: 'Regulatory milestones', description: 'Monitor FDA and EMA device-panel review notices.' },
        { title: 'Biotech and cash signals', description: 'Watch XBI implied volatility and corporate cash burn.' },
      ],
    },
    advisory: {
      generatedAt: '6 Hours Ago',
      risks: [
        {
          title: 'Sector concentration & correlated lifestyle risk',
          description: '58% portfolio correlation to the exact sector of his operating business.',
        },
        {
          title: 'Extended trial regulatory timeline',
          description: 'Six-month regulatory delay defers anticipated corporate distributions.',
        },
      ],
      opportunities: [
        {
          title: 'Zero-cost collar on top holding',
          description: 'Hedge USD 4.9m Vertex position using 6-month out-of-the-money collars to limit downside.',
        },
        {
          title: 'Systematic rotation into uncorrelated dividend growers',
          description: 'Gradually transition 20% into infrastructure and consumer staple dividend champions.',
        },
      ],
    },
  },
];
