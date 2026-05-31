// Layout utilities for consistent 8px spacing scale
// Base unit: 8px ( Tailwind: p-2 = 8px, p-4 = 16px, p-6 = 24px, p-8 = 32px )

export const layout = {
  // Container
  container: 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',
  containerNarrow: 'max-w-5xl mx-auto px-4 sm:px-6 lg:px-8',

  // Section spacing (vertical)
  section: 'py-6 sm:py-8',
  sectionSm: 'py-4 sm:py-6',
  sectionLg: 'py-8 sm:py-12',

  // Card styles
  card: 'bg-white border border-gray-200 rounded-2xl shadow-sm p-4 sm:p-6',
  cardHover: 'hover:shadow-md transition-shadow duration-200',

  // Grid gaps
  gapSm: 'gap-2',
  gapMd: 'gap-4',
  gapLg: 'gap-6',
  gapXl: 'gap-8',

  // Stack spacing (vertical)
  stackSm: 'space-y-3',
  stackMd: 'space-y-4',
  stackLg: 'space-y-6',

  // Header spacing
  header: 'mb-6 sm:mb-8',
  headerSm: 'mb-4 sm:mb-6',

  // Page header
  pageTitle: 'text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900',
  pageSubtitle: 'text-sm sm:text-base text-gray-500 mt-1',

  // Form spacing
  formGroup: 'space-y-2',
  formLabel: 'block text-sm font-medium text-gray-700',
  formInput: 'w-full min-h-[44px] px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200',

  // Table cell padding
  tableCell: 'px-4 py-4 sm:px-6 sm:py-5',
  tableHeader: 'px-4 py-3 sm:px-6 sm:py-4',

  // Button sizing (mobile-friendly)
  button: 'min-h-[44px] px-4 py-2.5 inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200',
  buttonSm: 'min-h-[36px] px-3 py-1.5 text-sm',

  // Tap targets (min 44px for accessibility)
  tapTarget: 'min-h-[44px] min-w-[44px]',
  tapTargetSm: 'min-h-[36px] min-w-[36px]',

  // List spacing
  listItem: 'py-3 px-4 sm:py-4 sm:px-6',

  // Responsive grid
  grid1: 'grid grid-cols-1',
  grid2: 'grid grid-cols-1 sm:grid-cols-2',
  grid3: 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  grid4: 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
} as const;

// CSS variable-based spacing (for use in CSS-in-JS or style props)
export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '2.5rem', // 40px
} as const;

export default layout;
