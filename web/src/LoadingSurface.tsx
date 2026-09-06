export function InlineSpinner() {
  return <span className="inline-spinner" aria-hidden="true" />;
}

export function LoadingSurface({ message }: { message: string }) {
  return <section className="loading-surface" aria-live="polite"><InlineSpinner /><p className="loading">{message}</p><div className="loading-skeleton" aria-hidden="true"><i /><i /><i /></div></section>;
}
