import { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useI18n } from '../i18n/useI18n';

const SCENE_HOLD_MS = 3000;
const SCENE_FADE_MS = 500;
const TICK_MS = 50;

interface Scene {
  img: string;
  cursor: { from: [number, number]; to: [number, number] };
}

const SCENES: Scene[] = [
  {
    img: '/assets/demo-shots/01-twin.png',
    cursor: { from: [8, 82], to: [38, 56] },
  },
  {
    img: '/assets/demo-shots/02-meetings.png',
    cursor: { from: [94, 12], to: [62, 44] },
  },
  {
    img: '/assets/demo-shots/03-actions.png',
    cursor: { from: [92, 86], to: [36, 42] },
  },
  {
    img: '/assets/demo-shots/04-dashboard.png',
    cursor: { from: [6, 14], to: [48, 48] },
  },
];

const SCENE_COUNT = SCENES.length;
const SCENE_TOTAL_MS = SCENE_HOLD_MS + SCENE_FADE_MS;

function CursorSVG() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <path
        d="M3 2 L3 18 L7.5 14 L10.5 20 L13 19 L10 13 L16 13 Z"
        fill="#fff"
        stroke="#0a0a0c"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function ScreenStudioDemo() {
  const { t } = useI18n();
  const reduced = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [progress, setProgress] = useState(0); // 0..1 within current scene
  const [paused, setPaused] = useState(false);
  const elapsedRef = useRef(0);
  const lastTickRef = useRef<number | null>(null);

  useEffect(() => {
    if (reduced || paused) {
      lastTickRef.current = null;
      return;
    }
    const id = window.setInterval(() => {
      const now = performance.now();
      const prev = lastTickRef.current ?? now;
      const dt = now - prev;
      lastTickRef.current = now;
      elapsedRef.current += dt;
      const frac = Math.min(elapsedRef.current / SCENE_TOTAL_MS, 1);
      setProgress(frac);
      if (elapsedRef.current >= SCENE_TOTAL_MS) {
        elapsedRef.current = 0;
        setProgress(0);
        setIndex((i) => (i + 1) % SCENE_COUNT);
      }
    }, TICK_MS);
    return () => {
      window.clearInterval(id);
      lastTickRef.current = null;
    };
  }, [reduced, paused]);

  const jumpTo = (i: number) => {
    elapsedRef.current = 0;
    setProgress(0);
    setIndex(i % SCENE_COUNT);
  };

  const replay = () => jumpTo(0);

  const scene = SCENES[index];
  const sceneNum = index + 1;
  const from = scene.cursor.from;
  const to = scene.cursor.to;
  const railScale = (index + progress) / SCENE_COUNT;

  const sceneLabels = [
    t('home.demo.scene1', '01 · Twin'),
    t('home.demo.scene2', '02 · Meeting'),
    t('home.demo.scene3', '03 · Actions'),
    t('home.demo.scene4', '04 · Dashboard'),
  ];

  return (
    <section className="relative">
      <div className="max-w-6xl mx-auto px-5 md:px-8">
        <div className="text-center mb-6">
          <div
            className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted)]"
            style={{ fontFamily: "'Geist Mono', ui-monospace, monospace" }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--accent)]" />
            {t('home.demo.label', 'Watch SIMY in 12 seconds')}
          </div>
          <h2
            className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight"
            style={{ fontFamily: "'Geist', sans-serif" }}
          >
            {t('home.demo.title', 'From meeting to shipped PR.')}
          </h2>
          <p className="mt-3 text-[15px] md:text-base text-[color:var(--muted)] max-w-xl mx-auto">
            {t('home.demo.kicker', 'Four scenes, one unbroken take through the real SIMY desktop app.')}
          </p>
        </div>

        <div className="simy-ss-wrap">
          <div className="simy-ss-browser">
            <div className="simy-ss-chrome">
              <div className="simy-ss-dots">
                <span className="simy-ss-dot" style={{ background: '#ff5f57' }} />
                <span className="simy-ss-dot" style={{ background: '#febc2e' }} />
                <span className="simy-ss-dot" style={{ background: '#28c840' }} />
              </div>
              <div className="simy-ss-addr">
                <span className="simy-ss-addr-inner">
                  <span>{'\u{1F512}'}</span>
                  <span>{t('home.demo.addr', 'app.simy.one / home')}</span>
                </span>
              </div>
              <span className="simy-ss-rec">
                <span className="simy-ss-rec-dot" />
                {t('home.demo.rec', 'REC · LIVE')}
              </span>
            </div>

            <div className="simy-ss-viewport" data-simy-stage>
              <div
                key={`slide-${index}`}
                data-simy-scene={sceneNum}
                className="simy-ss-slide"
                style={{ backgroundImage: `url(${scene.img})` }}
              />

              {!reduced && (
                <>
                  <motion.div
                    key={`cursor-${index}`}
                    className="simy-ss-cursor"
                    initial={{ left: `${from[0]}%`, top: `${from[1]}%`, opacity: 0 }}
                    animate={{
                      left: [`${from[0]}%`, `${to[0]}%`, `${to[0]}%`, `${to[0]}%`],
                      top: [`${from[1]}%`, `${to[1]}%`, `${to[1]}%`, `${to[1]}%`],
                      opacity: [0, 1, 1, 0],
                    }}
                    transition={{
                      duration: 3,
                      ease: 'easeInOut',
                      times: [0, 0.45, 0.85, 1],
                    }}
                  >
                    <CursorSVG />
                  </motion.div>
                  <motion.div
                    key={`ripple-${index}`}
                    className="simy-ss-ripple"
                    style={{ left: `${to[0]}%`, top: `${to[1]}%` }}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: [0, 0.2, 2.6], opacity: [0, 0.9, 0] }}
                    transition={{ duration: 1.2, delay: 1.25, ease: 'easeOut' }}
                  />
                </>
              )}
            </div>
          </div>

          <div className="simy-ss-rail">
            <div
              className="simy-ss-rail-fill"
              style={{ transform: `scaleX(${railScale})`, transformOrigin: 'left center' }}
            />
          </div>

          <div className="simy-ss-ticks">
            {sceneLabels.map((label, i) => (
              <button
                key={i}
                className="simy-ss-tick"
                data-active={i === index}
                onClick={() => jumpTo(i)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>

          <div key={`cap-${index}`} className="simy-ss-caption simy-ss-caption-enter">
            <div className="simy-ss-caption-main">
              {t(`home.demo.cap${sceneNum}.main`, '')}
            </div>
            <div className="simy-ss-caption-sub">
              {t(`home.demo.cap${sceneNum}.sub`, '')}
            </div>
          </div>

          <div className="simy-ss-controls">
            <button
              type="button"
              className="simy-ss-btn"
              onClick={() => setPaused((p) => !p)}
              aria-pressed={paused}
            >
              {paused ? t('home.demo.play', 'Play') : t('home.demo.pause', 'Pause')}
            </button>
            <button type="button" className="simy-ss-btn" onClick={replay}>
              {t('home.demo.replay', 'Replay')}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
