/** Provisional wordmark (PRD v1.1: final logo pending brand approval). */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg aria-hidden="true" viewBox="0 0 32 32" className="size-8 shrink-0">
        <rect x="4" y="4" width="24" height="24" rx="4" transform="rotate(45 16 16)" fill="var(--vb-primary)" />
        <rect x="10" y="10" width="12" height="12" rx="2" transform="rotate(45 16 16)" fill="none" stroke="var(--vb-gold-500)" strokeWidth="2" />
        <circle cx="16" cy="16" r="2.5" fill="var(--vb-gold-500)" />
      </svg>
      <span className="font-serif text-lg font-bold tracking-[0.12em] text-primary sm:text-xl">VAIBHAV</span>
    </span>
  );
}
