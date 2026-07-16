/**
 * Shared TypeScript type definitions
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type CaseStatus = 'NEW' | 'INVESTIGATING' | 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE' | 'CLOSED';

export interface MetricCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  color?: 'green' | 'yellow' | 'red' | 'blue';
}

export interface RiskEventTableRowProps {
  event: {
    user_id: string;
    risk_score: number;
    risk_level: RiskLevel;
    primary_reason: string | null;
    recommended_action: string | null;
    detected_at: string;
  };
  onClick: (userId: string) => void;
}

export interface MetricExplanationProps {
  metric: 'AUC' | 'KS' | 'PSI';
  value: number;
}

export const METRIC_EXPLANATIONS = {
  AUC: {
    title: 'AUC (Area Under ROC)',
    explanation: 'Overall discrimination ability - how well the model distinguishes risky from normal users.',
    range: '0.5 - 1.0',
    good: '> 0.75',
    interpretation: (value: number) => {
      if (value >= 0.8) return { status: 'good', text: 'Excellent discrimination' };
      if (value >= 0.75) return { status: 'good', text: 'Good discrimination' };
      if (value >= 0.7) return { status: 'warning', text: 'Fair discrimination' };
      return { status: 'poor', text: 'Poor discrimination - retrain recommended' };
    },
  },
  KS: {
    title: 'KS (Kolmogorov-Smirnov)',
    explanation: 'Maximum separation between risky and normal user score distributions.',
    range: '0 - 1',
    good: '> 0.30',
    interpretation: (value: number) => {
      if (value >= 0.4) return { status: 'good', text: 'Strong separation' };
      if (value >= 0.3) return { status: 'good', text: 'Good separation' };
      if (value >= 0.2) return { status: 'warning', text: 'Moderate separation' };
      return { status: 'poor', text: 'Weak separation' };
    },
  },
  PSI: {
    title: 'PSI (Population Stability)',
    explanation: 'Population Stability Index - detects model drift or data distribution changes.',
    range: '0 - ∞',
    good: '< 0.10',
    interpretation: (value: number) => {
      if (value < 0.1) return { status: 'good', text: 'Stable population' };
      if (value < 0.25) return { status: 'warning', text: 'Minor population shift' };
      return { status: 'poor', text: 'Significant drift detected - retrain required' };
    },
  },
};
