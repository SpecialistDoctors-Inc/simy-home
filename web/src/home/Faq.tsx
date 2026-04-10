import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useI18n } from '../i18n/useI18n';

export default function Faq() {
  const { t } = useI18n();
  const [open, setOpen] = useState<number | null>(0);
  const items = [1, 2, 3, 4].map((n) => ({
    n,
    q: t(`home.faq.q${n}`, ''),
    a: t(`home.faq.a${n}`, ''),
  }));
  return (
    <section className="py-20 md:py-28">
      <div className="max-w-3xl mx-auto px-5 md:px-8">
        <div className="text-center mb-10">
          <div
            className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted)]"
            style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
          >
            {t('home.faq.label', 'FAQ')}
          </div>
          <h2
            className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight"
            style={{ fontFamily: "'Geist', sans-serif" }}
          >
            {t('home.faq.title', 'Frequently asked questions.')}
          </h2>
        </div>
        <div className="space-y-3">
          {items.map((it) => {
            const isOpen = open === it.n;
            return (
              <div
                key={it.n}
                className="rounded-2xl border border-black/10 bg-white/80 overflow-hidden"
              >
                <button
                  onClick={() => setOpen(isOpen ? null : it.n)}
                  className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
                  aria-expanded={isOpen}
                >
                  <span className="text-base font-semibold">{it.q}</span>
                  <span
                    className="text-[color:var(--muted)] transition-transform"
                    style={{ transform: isOpen ? 'rotate(45deg)' : 'rotate(0deg)' }}
                    aria-hidden
                  >
                    +
                  </span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden"
                    >
                      <div className="px-6 pb-5 text-sm text-[color:var(--muted)] leading-relaxed">
                        {it.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
