import { motion } from 'framer-motion';
import { useI18n } from '../i18n/useI18n';

export default function Hero() {
  const { t } = useI18n();
  return (
    <section className="relative pt-24 md:pt-32 pb-10 md:pb-14">
      <div className="max-w-5xl mx-auto px-5 md:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-black/10 bg-white/60 backdrop-blur text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted)]"
          style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--accent)]" />
          {t('home.eyebrow', 'Action Intelligence')}
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="mt-6 text-5xl md:text-7xl font-semibold tracking-tight leading-[1.05]"
          style={{ fontFamily: "'Geist', sans-serif" }}
        >
          <span className="block">{t('home.h1a', 'Meetings end.')}</span>
          <span
            className="block bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(90deg, oklch(0.48 0.22 264), oklch(0.62 0.22 300))',
            }}
          >
            {t('home.h1b', 'Code ships.')}
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.12 }}
          className="mt-6 text-base md:text-lg text-[color:var(--muted)] max-w-2xl mx-auto leading-relaxed"
        >
          {t('home.sub', '')}
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <a
            href="/contact.html"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[color:var(--fg)] text-white text-sm font-medium hover:-translate-y-0.5 transition-transform"
          >
            {t('home.cta1', 'Request Access')}
            <span aria-hidden>→</span>
          </a>
          <a
            href="/how-it-works.html"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-full border border-black/10 bg-white/80 text-sm font-medium hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] transition-colors"
          >
            {t('home.cta2', 'See How It Works')}
          </a>
        </motion.div>
      </div>
    </section>
  );
}
