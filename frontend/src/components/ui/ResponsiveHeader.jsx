import { useState } from 'react'
import Link from 'next/link'
import { AnimatePresence, motion } from 'framer-motion'

function NavLink({ href, label, onClick }) {
  return (
    <Link href={href} onClick={onClick} className="rounded-full border border-white/10 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white">
      {label}
    </Link>
  )
}

export function ResponsiveHeader({ eyebrow = 'TalentLens AI', title, links = [], onLogout, logoutLabel = 'Logout' }) {
  const [open, setOpen] = useState(false)

  const closeMenu = () => setOpen(false)

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/70 backdrop-blur-2xl">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-[0.32em] text-cyan-200/80">{eyebrow}</div>
          <h1 className="text-xl font-semibold text-white sm:text-2xl">{title}</h1>
        </div>

        <div className="flex items-center gap-2 lg:hidden">
          {onLogout && (
            <button onClick={onLogout} className="rounded-full border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:bg-white/5">
              {logoutLabel}
            </button>
          )}
          <button
            type="button"
            onClick={() => setOpen((current) => !current)}
            aria-expanded={open}
            aria-label="Toggle navigation menu"
            className="rounded-full bg-cyan-300 px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200"
          >
            {open ? 'Close' : 'Menu'}
          </button>
        </div>

        <nav className="hidden items-center gap-2 lg:flex">
          {links.map((link) => <NavLink key={link.href} href={link.href} label={link.label} />)}
          {onLogout && (
            <button onClick={onLogout} className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200">
              {logoutLabel}
            </button>
          )}
        </nav>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="border-t border-white/10 bg-slate-950/95 px-4 py-4 lg:hidden"
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-2 sm:flex-row sm:flex-wrap">
              {links.map((link) => <NavLink key={link.href} href={link.href} label={link.label} onClick={closeMenu} />)}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}