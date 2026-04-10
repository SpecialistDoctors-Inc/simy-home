import { useI18n } from '../i18n/useI18n';

export default function Cta() {
  const { t } = useI18n();
  return (
    <section className="py-24 md:py-32">
      <div className="max-w-4xl mx-auto px-5 md:px-8">
        <div
          className="rounded-3xl p-12 md:p-16 text-center text-white overflow-hidden relative"
          style={{
            background:
              'radial-gradient(ellipse at top, oklch(0.62 0.22 290) 0%, oklch(0.36 0.2 264) 80%)',
          }}
        >
          <h2
            className="text-3xl md:text-5xl font-semibold tracking-tight"
            style={{ fontFamily: "'Geist', sans-serif" }}
          >
            {t('home.cta.h', 'Ready to ship faster?')}
          </h2>
          <p className="mt-4 text-white/80 max-w-xl mx-auto">{t('home.cta.p', '')}</p>
          <div className="mt-8">
            <a
              href="/contact.html"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-white text-[color:var(--fg)] text-sm font-semibold hover:-translate-y-0.5 transition-transform"
            >
              {t('home.cta.btn', 'Request Access')}
              <span aria-hidden>→</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
