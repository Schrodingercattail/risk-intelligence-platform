/**
 * DataProvenanceTooltip Component
 *
 * Enterprise-style tooltip showing data source, definition, and metadata.
 * MVP-appropriate: reflects CSV upload workflow instead of fake production infrastructure.
 */
import { useState } from 'react';

interface DataProvenanceTooltipProps {
  children: React.ReactNode;
  metric: string;
  definition: string;
  dataSource: string;
  processingMethod: string;
  updateMethod: string;
  generated?: string;
}

export default function DataProvenanceTooltip({
  children,
  metric,
  definition,
  dataSource,
  processingMethod,
  updateMethod,
  generated,
}: DataProvenanceTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        className="cursor-help"
      >
        {children}
      </div>

      {isOpen && (
        <div className="absolute z-50 w-80 p-4 bg-white rounded-lg shadow-lg border border-slate-200 text-sm">
          <div className="space-y-3">
            {/* Metric Name */}
            <div>
              <p className="font-semibold text-slate-900">{metric}</p>
              <p className="text-slate-600 mt-1">{definition}</p>
            </div>

            {/* Data Source */}
            <div className="flex items-center justify-between py-2 border-t border-slate-100">
              <span className="text-slate-500">Data Source</span>
              <span className="font-medium text-slate-900">{dataSource}</span>
            </div>

            {/* Processing Method */}
            <div className="flex items-center justify-between py-2 border-t border-slate-100">
              <span className="text-slate-500">Processing</span>
              <span className="font-medium text-slate-900">{processingMethod}</span>
            </div>

            {/* Update Method */}
            <div className="flex items-center justify-between py-2 border-t border-slate-100">
              <span className="text-slate-500">Update Method</span>
              <span className="font-medium text-slate-900">{updateMethod}</span>
            </div>

            {/* Generated */}
            {generated && (
              <div className="flex items-center justify-between py-2 border-t border-slate-100">
                <span className="text-slate-500">Generated</span>
                <span className="font-medium text-slate-900">{generated}</span>
              </div>
            )}
          </div>

          {/* Data pipeline indicator */}
          <div className="mt-3 pt-3 border-t border-slate-100">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>Analysis from uploaded datasets via Risk Analytics Pipeline</span>
            </div>
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
