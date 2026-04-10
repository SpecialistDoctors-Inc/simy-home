import { useI18n } from '../i18n/useI18n';

export default function Steps() {
  const { t } = useI18n();
  const steps = [1, 2, 3, 4].map((n) => ({
    n,
    h: t(`home.step${n}.h`, ''),
    p: t(`home.step${n}.p`, ''),
  }));
  return (
    <section className="py-20 md:py-28">
      <div className="max-w-6xl mx-auto px-5 md:px-8">
        <div className="text-center mb-12">
          <div
            className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted)]"
            style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
          >
            {t('home.steps.label', 'How It Works')}
          </div>
          <h2
            className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight"
            style={{ fontFamily: "'Geist', sans-serif" }}
          >
            {t('home.steps.title', 'From meeting to merged PR in 4 steps.')}
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {steps.map((s) => (
            <div
              key={s.n}
              className="rounded-2xl border border-black/10 bg-white/80 backdrop-blur p-6 hover:border-[color:var(--accent)]/40 hover:shadow-lg transition-all"
            >
              <div
                className="text-[11px] font-mono text-[color:var(--accent)]"
                style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
              >
                0{s.n}
              </div>
              <h3 className="mt-3 text-lg font-semibold">{s.h}</h3>
              <p className="mt-2 text-sm text-[color:var(--muted)] leading-relaxed">{s.p}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 text-center">
          <a
            href="/how-it-works.html"
            className="text-sm text-[color:var(--accent)] hover:underline"
          >
            {t('home.steps.more', 'See the full workflow →')}
          </a>
        </div>
      </div>
    </section>
  );
}
