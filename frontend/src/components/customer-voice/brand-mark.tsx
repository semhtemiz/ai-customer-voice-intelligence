import type { SVGProps } from 'react';

export function BrandMark(props: SVGProps<SVGSVGElement>) {
  return <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" {...props}>
    <rect width="32" height="32" rx="9" fill="#0f172a" />
    <path d="M9 8.5h14a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9l-5 3v-3a3 3 0 0 1-3-3v-9a3 3 0 0 1 3-3Z" stroke="white" strokeWidth="1.7" strokeLinejoin="round" />
    <path d="M12 14v4m4-6v8m4-6v4" stroke="white" strokeWidth="1.7" strokeLinecap="round" />
  </svg>;
}
