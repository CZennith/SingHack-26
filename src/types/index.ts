export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface RMProfile {
  name: string;
  title: string;
  desk: string;
  bookingDesk: {
    name: string;
    metricLabel: string;
    metricValue: string;
    status: 'nominal' | 'warning' | 'critical';
  };
  totalDeskAUM: string;
  activeAlertsCount: number;
}

export interface MacroIndicator {
  id: string;
  label: string;
  value: string;
  change?: string;
  subtext?: string;
  isAlert?: boolean;
  highlightColor?: 'red' | 'amber' | 'neutral';
}

export interface MarketImpactPillar {
  id: string;
  category: string;
  affectedCount: number;
  badgeStyle: 'red' | 'amber' | 'neutral';
  title: string;
  portfolioImpact: string;
  deskContext: string;
  affectedClientNames: string[];
  affectedClientIds: string[];
}

export interface AssetAllocationItem {
  label: string;
  percentage: number;
  color: string;
}

export interface PortfolioHolding {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  value: string;
  percentage: number;
}

export interface TrajectoryPoint {
  date: string;
  value: number;
  label?: string;
}

export interface TrajectoryConfig {
  deltaPercent: string;
  deltaPeriod: string;
  startLabel: string;
  troughLabel: string;
  endLabel: string;
  points: TrajectoryPoint[];
}

export interface StrategicPoint {
  title: string;
  description: string;
}

export interface ClientDossier {
  id: string;
  ref: string;
  name: string;
  initials: string;
  tier: string;
  mandate: string;
  aum: string;
  riskLevel: RiskSeverity | null;
  riskProfile?: string | null;
  headlineIssue: string;
  summary: string;
  tags: string[];
  suggestedNextStep: string;
  
  // Detailed client profile fields (for Image 3 client page)
  about: {
    bio: string;
    age: number;
    occupation: string;
    clientSince: number;
  };
  portfolio: {
    totalValue: string;
    totalValueSubtext: string;
    cashLiquidity: string;
    cashLiquidityPercent: string;
    cashLiquiditySubtext: string;
    borrowingUtilisation: string;
    borrowingLtvPercent: number | null;
    borrowingStatus: string;
    allocation: AssetAllocationItem[];
    trajectory: TrajectoryConfig;
    topHoldings: PortfolioHolding[];
    remainingHoldingsNote: string;
  };
  synthesisedAnalysis: {
    syncTime: string;
    headline: string;
    narrative: string;
    whyItMatters: string;
    monitor: string;
  };
  strategicMatrix: {
    risks: StrategicPoint[];
    opportunities: StrategicPoint[];
  };
}
