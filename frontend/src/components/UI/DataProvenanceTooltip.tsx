/**
 * SimpleMetricTooltip Component
 *
 * Simplified tooltip showing only metric name and definition.
 * Provides concise explanations for Risk Intelligence Overview cards.
 */
import { useState } from 'react';

interface SimpleMetricTooltipProps {
  children: React.ReactNode;
  metric: string;
  definition: string;
}

export default function SimpleMetricTooltip({
  children,
  metric,
  definition,
}: SimpleMetricTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
      >
        {children}
      </div>

      {isOpen && (
        <div className="absolute z-50 w-80 p-4 bg-white rounded-lg shadow-lg border border-slate-200 text-sm">
          <div className="space-y-2">
            {/* Metric Name */}
            <p className="font-semibold text-slate-900">{metric}</p>
            {/* Definition */}
            <p className="text-slate-600">{definition}</p>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Simple info icon for metric provenance
 */
export function MetricProvenanceIcon() {
  return (
    <span className="inline-flex items-center justify-center w-4 h-4 ml-1 text-slate-400 hover:text-slate-600 cursor-help">
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
          clipRule="evenodd"
        />
      </svg>
    </span>
  );
}
