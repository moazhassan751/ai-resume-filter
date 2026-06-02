export function GlassCard({ title, subtitle, children, className = '' }) {
  return (
    <section className={`glass-card rounded-3xl p-5 md:p-6 ${className}`}>
      {(title || subtitle) && (
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title && <h3 className="text-base font-semibold text-slate-50">{title}</h3>}
            {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
          </div>
        </div>
      )}
      {children}
    </section>
  )
}