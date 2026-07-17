/**
 * Unified Design System Constants
 *
 * Enterprise SaaS design tokens for consistent UI across all pages.
 * Based on shadcn/ui design principles.
 */

// ============================================
// BORDER RADIUS
// ============================================
export const borderRadius = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-md',    // Small elements (inputs, buttons)
  lg: 'rounded-lg',    // Cards, containers
  xl: 'rounded-xl',    // Large containers, special emphasis
  full: 'rounded-full', // Pills, badges, circular elements
} as const;

// ============================================
// SPACING
// ============================================
export const spacing = {
  // Padding
  pNone: 'p-0',
  pSm: 'p-3',         // Small cards
  pMd: 'p-4',         // Standard cards
  pLg: 'p-6',         // Large cards, sections
  pXl: 'p-8',        // Extra large sections

  // Gap (flex/grid)
  gapNone: 'gap-0',
  gapSm: 'gap-2',      // Tight spacing
  gapMd: 'gap-3',      // Medium spacing
  gapLg: 'gap-4',      // Standard grid gap
  gapXl: 'gap-6',      // Large grid gap

  // Margin (for vertical spacing between sections)
  mbNone: 'mb-0',
  mbSm: 'mb-2',
  mbMd: 'mb-3',
  mbLg: 'mb-4',
  mbXl: 'mb-6',
  mb2xl: 'mb-8',
} as const;

// ============================================
// CARD STYLES
// ============================================
export const cardStyles = {
  // Standard card
  base: 'bg-white border border-slate-200 rounded-lg p-6',

  // Small card
  sm: 'bg-white border border-slate-200 rounded-lg p-4',

  // Large card
  lg: 'bg-white border border-slate-200 rounded-lg p-8',

  // Hover card
  hover: 'bg-white border border-slate-200 rounded-lg p-6 hover:shadow-sm transition-shadow',

  // KPI card (fixed height)
  kpi: 'border rounded-lg p-6 h-[180px] flex flex-col',

  // Chart card (fixed height)
  chart: 'bg-white border border-slate-200 rounded-lg p-6 h-[300px] flex flex-col',

  // Pipeline stage card (fixed height)
  pipeline: 'bg-white border rounded-lg p-4 h-[140px] flex flex-col',
} as const;

// ============================================
// TYPOGRAPHY
// ============================================
export const typography = {
  // Page title
  pageTitle: 'text-2xl font-semibold text-slate-900',

  // Section title
  sectionTitle: 'text-lg font-semibold text-slate-900',
  sectionSubtitle: 'text-sm text-slate-600',

  // Card title
  cardTitle: 'text-sm font-semibold text-slate-900',
  cardSubtitle: 'text-xs text-slate-500',

  // Label
  label: 'text-xs font-medium text-slate-500 uppercase tracking-wider',

  // Body text
  body: 'text-sm text-slate-600',
  bodyMuted: 'text-xs text-slate-500',

  // Value text
  valueLarge: 'text-3xl font-bold text-slate-900',
  valueMedium: 'text-xl font-bold text-slate-900',
  valueSmall: 'text-lg font-bold text-slate-900',
} as const;

// ============================================
// BADGE / PILL STYLES
// ============================================
export const badgeStyles = {
  // Standard pill badge
  base: 'px-2.5 py-1 text-xs font-semibold rounded-full border',

  // Small pill badge
  sm: 'px-2 py-0.5 text-xs font-medium rounded-full border',

  // Color variants
  colors: {
    green: 'bg-green-50 text-green-800 border-green-200',
    yellow: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    orange: 'bg-orange-50 text-orange-800 border-orange-200',
    red: 'bg-red-50 text-red-900 border-red-300',
    blue: 'bg-blue-50 text-blue-800 border-blue-200',
    purple: 'bg-purple-50 text-purple-800 border-purple-200',
    cyan: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    slate: 'bg-slate-50 text-slate-700 border-slate-200',
  },
} as const;

// ============================================
// BUTTON STYLES
// ============================================
export const buttonStyles = {
  // Standard button
  base: 'inline-flex items-center justify-center font-medium rounded-md border focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',

  // Size variants
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',

  // Color variants
  primary: 'bg-blue-600 hover:bg-blue-700 text-white border-transparent',
  secondary: 'bg-slate-200 hover:bg-slate-300 text-slate-800 border-transparent',
  danger: 'bg-red-600 hover:bg-red-700 text-white border-transparent',
  ghost: 'bg-transparent hover:bg-slate-50 text-slate-700 border-slate-300',
} as const;

// ============================================
// TABLE STYLES
// ============================================
export const tableStyles = {
  // Table container
  container: 'overflow-x-auto',

  // Table
  table: 'min-w-full divide-y divide-slate-200',

  // Header
  thead: 'bg-slate-50',
  th: 'px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider',

  // Body
  tbody: 'bg-white divide-y divide-slate-200',
  td: 'px-6 py-4 whitespace-nowrap text-sm text-slate-900',
  tdCenter: 'px-6 py-4 text-center text-sm text-slate-900',

  // Row hover
  rowHover: 'cursor-pointer hover:bg-slate-50',

  // Empty state
  empty: 'px-6 py-4 text-center text-sm text-slate-500',
} as const;

// ============================================
// STATUS COLORS (for model health, pipeline stages, etc.)
// ============================================
export const statusColors = {
  // Success/Completed/Healthy
  success: {
    bg: 'bg-green-50',
    text: 'text-green-800',
    border: 'border-green-200',
    dot: 'bg-green-500',
  },

  // Warning/Needs Attention
  warning: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-800',
    border: 'border-yellow-200',
    dot: 'bg-yellow-500',
  },

  // Error/Failed/Critical
  error: {
    bg: 'bg-red-50',
    text: 'text-red-800',
    border: 'border-red-200',
    dot: 'bg-red-500',
  },

  // Info/Running
  info: {
    bg: 'bg-blue-50',
    text: 'text-blue-800',
    border: 'border-blue-200',
    dot: 'bg-blue-500',
  },

  // Neutral/Pending
  neutral: {
    bg: 'bg-slate-50',
    text: 'text-slate-700',
    border: 'border-slate-200',
    dot: 'bg-slate-400',
  },
} as const;

// ============================================
// RISK LEVEL COLORS
// ============================================
export const riskLevelColors = {
  LOW: 'bg-green-100 text-green-700 border-green-200',
  MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  HIGH: 'bg-orange-100 text-orange-700 border-orange-200',
  CRITICAL: 'bg-red-100 text-red-900 border-red-300',
} as const;

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Get badge style by risk level
 */
export function getRiskLevelBadge(level: string): string {
  return riskLevelColors[level as keyof typeof riskLevelColors] || riskLevelColors.LOW;
}

/**
 * Get status color set
 */
export function getStatusColor(status: 'success' | 'warning' | 'error' | 'info' | 'neutral') {
  return statusColors[status];
}
