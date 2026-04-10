import { motion } from 'framer-motion';
import { useI18n } from '../i18n/useI18n';

export default function Impact() {
  const { t } = useI18n();
  return (
    <section className="py-20 md:py-28">
      <div className="max-w-5xl mx-auto px-5 md:px-8 text-center">
        <div
          className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted)]"
          style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
        >
          {t('home.impact.label', 'Real Impact')}
        </div>
        <h2
          className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight"
          style={{ fontFamily: "'Geist', sans-serif" }}
        >
          {t('home.impact.title', '17.7× more pull requests per engineer, per day.')}
        </h2>
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-5 max-w-3xl mx-auto">
          <div className="rounded-2xl border border-black/10 bg-white/80 p-10">
            <div
              className="text-[11px] uppercase tracking-wide text-[color:var(--muted)]"
              style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
            >
              {t('home.impact.before', 'Before SIMY')}
            </div>
            <div className="mt-3 text-5xl font-semibold tabular-nums">0.42</div>
            <div className="mt-2 text-sm text-[color:var(--muted)]">
              {t('home.impact.unit', 'PRs / engineer / day')}
            </div>
          </div>
          <motion.div
            initial={{ scale: 0.98 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
            className="rounded-2xl p-10 text-white"
            style={{
              background:
                'linear-gradient(135deg, oklch(0.48 0.22 264) 0%, oklch(0.62 0.22 290) 100%)',
            }}
          >
            <div
              className="text-[11px] uppercase tracking-wide text-white/70"
              style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
            >
              {t('home.impact.after', 'With SIMY')}
            </div>
            <div className="mt-3 text-5xl font-semibold tabular-nums">7.44</div>
            <div className="mt-2 text-sm text-white/80">
              {t('home.impact.unit', 'PRs / engineer / day')}
            </div>
          </motion.div>
        </div>
        <p className="mt-8 text-sm text-[color:var(--muted)] max-w-2xl mx-auto">
          {t('home.impact.note', '')}
        </p>
      </div>
    </section>
  );
}
