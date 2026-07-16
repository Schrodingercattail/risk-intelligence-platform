/**
 * MetricCard Component
 *
 * Displays a key metric with optional trend indicator.
 * Supports both standard and premium variants.
 */
import React from 'react';

interface MetricCardProps {
  title: string | React.ReactNode;
  value: number | string;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
  };
  color?: 'green' | 'yellow' | 'red' | 'blue' | 'purple' | 'gray';
  variant?: 'standard' | 'premium';
  size?: 'sm' | 'md' | 'lg';
  target?: {
    value: string;
    achieved?: boolean;
  };
}

const colorStyles = {
  green: 'bg-green-50 border-green-200 text-green-800',
  yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  red: 'bg-red-50 border-red-200 text-red-800',
  blue: 'bg-blue-50 border-blue-200 text-blue-800',
  purple: 'bg-purple-50 border-purple-200 text-purple-800',
  gray: 'bg-gray-50 border-gray-200 text-gray-800',
};

const premiumColorStyles = {
  green: 'bg-gradient-to-br from-green-50 to-green-100/50 border-green-200 text-green-900',
  yellow: 'bg-gradient-to-br from-yellow-50 to-yellow-100/50 border-yellow-200 text-yellow-900',
  red: 'bg-gradient-to-br from-red-50 to-red-100/50 border-red-200 text-red-900',
  blue: 'bg-gradient-to-br from-blue-50 to-blue-100/50 border-blue-200 text-blue-900',
  purple: 'bg-gradient-to-br from-purple-50 to-purple-100/50 border-purple-200 text-purple-900',
  gray: 'bg-gradient-to-br from-gray-50 to-gray-100/50 border-gray-200 text-gray-900',
};

const trendColorStyles = {
  up: 'text-red-600',
  down: 'text-green-600',
  neutral: 'text-gray-600',
};

const sizeStyles = {
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const valueSizeStyles = {
  sm: 'text-2xl',
  md: 'text-3xl',
  lg: 'text-4xl',
};

export default function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  color = 'blue',
  variant = 'standard',
  size = 'md',
  target,
}: MetricCardProps) {
  const isPremium = variant === 'premium';
  const baseClasses = `${sizeStyles[size]} rounded-lg border transition-all duration-200 ${
    isPremium
      ? `${premiumColorStyles[color]} shadow-sm hover:shadow-md`
      : `${colorStyles[color]}`
  }`;

  return (
    <div className={baseClasses}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className={`font-medium ${isPremium ? 'text-gray-700' : 'opacity-80'}`}>
            {title}
          </p>
          <p className={`font-bold mt-2 ${valueSizeStyles[size]}`}>{value}</p>
          {subtitle && (
            <p className={`mt-1 ${isPremium ? 'text-gray-600' : 'text-sm opacity-70'}`}>
              {subtitle}
            </p>
          )}
          {trend && (
            <div className={`mt-2 flex items-center gap-2 ${isPremium ? 'text-sm' : ''}`}>
              <span className={trendColorStyles[trend.direction]}>
                {trend.direction === 'up' && '↑'}
                {trend.direction === 'down' && '↓'}
                {trend.direction === 'neutral' && '→'}
                {' '}
                {trend.direction !== 'neutral' ? Math.abs(trend.value) : ''}%
              </span>
              <span className={isPremium ? 'text-gray-600' : 'opacity-70'}>
                {trend.label || 'vs last period'}
              </span>
            </div>
          )}
          {target && (
            <div className={`mt-2 flex items-center gap-2 text-xs ${isPremium ? 'text-gray-600' : 'opacity-70'}`}>
              <span>Target: {target.value}</span>
              {target.achieved !== undefined && (
                <span className={target.achieved ? 'text-green-600' : 'text-yellow-600'}>
                  {target.achieved ? '✓ On track' : '⚠ Attention'}
                </span>
              )}
            </div>
          )}
        </div>
        {icon && (
          <div className={`text-3xl ${isPremium ? 'opacity-40' : 'opacity-50'} ml-2`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
