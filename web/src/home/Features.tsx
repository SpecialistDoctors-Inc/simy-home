import { useI18n } from '../i18n/useI18n';

export default function Features() {
  const { t } = useI18n();
  const feats = [1, 2, 3, 4].map((n) => ({
    n,
    h: t(`home.feat${n}.h`, ''),
    p: t(`home.feat${n}.p`, ''),
  }));
  return (
    <section className="py-20 md:py-28 bg-[color:var(--fg)] text-white">
      <div className="max-w-6xl mx-auto px-5 md:px-8">
        <div className="text-center mb-12">
          <div
            className="text-[11px] uppercase tracking-[0.18em] text-white/50"
            style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
          >
            {t('home.feat.label', 'Why SIMY')}
          </div>
          <h2
            className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight"
            style={{ fontFamily: "'Geist', sans-serif" }}
          >
            {t('home.feat.title', 'Stop translating. Start shipping.')}
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {feats.map((f) => (
            <div
              key={f.n}
              className="rounded-2xl border border-white/10 bg-white/[0.04] p-7 hover:border-white/25 hover:bg-white/[0.06] transition-all"
            >
              <h3 className="text-xl font-semibold">{f.h}</h3>
              <p className="mt-2 text-sm text-white/60 leading-relaxed">{f.p}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
