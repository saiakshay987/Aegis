// Lightweight inline SVG icon set — no external dependency needed
const I = ({ d, className = 'w-5 h-5', fill = 'none', stroke = 'currentColor', ...p }) => (
  <svg viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={1.8}
       strokeLinecap="round" strokeLinejoin="round" className={className} {...p}>
    {Array.isArray(d) ? d.map((path, i) => <path key={i} d={path} />) : <path d={d} />}
  </svg>
)

export const ShieldIcon    = (p) => <I {...p} d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
export const TrendUpIcon   = (p) => <I {...p} d="M23 6l-9.5 9.5-5-5L1 18" />
export const TrendDownIcon = (p) => <I {...p} d="M23 18l-9.5-9.5-5 5L1 6" />
export const AlertIcon     = (p) => <I {...p} d={['M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z','M12 9v4','M12 17h.01']} />
export const CheckIcon     = (p) => <I {...p} d="M20 6L9 17l-5-5" />
export const UserIcon      = (p) => <I {...p} d={['M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2','M12 3a4 4 0 100 8 4 4 0 000-8z']} />
export const CashIcon      = (p) => <I {...p} d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
export const ChartIcon     = (p) => <I {...p} d={['M18 20V10','M12 20V4','M6 20v-6']} />
export const BankIcon      = (p) => <I {...p} d={['M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z','M9 22V12h6v10']} />
export const HeartIcon     = (p) => <I {...p} d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
export const WarnIcon      = (p) => <I {...p} d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
export const ClockIcon     = (p) => <I {...p} d={['M12 2a10 10 0 100 20A10 10 0 0012 2z','M12 6v6l4 2']} />
export const CalendarIcon  = (p) => <I {...p} d={['M4 5h16a2 2 0 012 2v13H2V7a2 2 0 012-2z','M8 3v4M16 3v4M2 10h20']} />
export const ArrowRightIcon= (p) => <I {...p} d="M5 12h14M12 5l7 7-7 7" />
export const XIcon         = (p) => <I {...p} d="M18 6L6 18M6 6l12 12" />
export const RefreshIcon   = (p) => <I {...p} d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
export const LockIcon      = (p) => <I {...p} d={['M19 11H5a2 2 0 00-2 2v7a2 2 0 002 2h14a2 2 0 002-2v-7a2 2 0 00-2-2z','M7 11V7a5 5 0 0110 0v4']} />
export const EyeIcon       = (p) => <I {...p} d={['M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z','M12 9a3 3 0 100 6 3 3 0 000-6z']} />
