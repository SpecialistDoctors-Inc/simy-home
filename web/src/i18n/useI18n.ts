import { useCallback, useEffect, useState } from 'react';
import type { Dict } from './types';

const FALLBACK_LANG = 'en';
const dictCache = new Map<string, Dict>();

async function loadDict(lang: string): Promise<Dict> {
  const cached = dictCache.get(lang);
  if (cached) return cached;
  try {
    const res = await fetch(`/lang/${lang}.json`, { cache: 'force-cache' });
    if (!res.ok) throw new Error(`lang ${lang} not found`);
    const dict = (await res.json()) as Dict;
    dictCache.set(lang, dict);
    return dict;
  } catch {
    if (lang !== FALLBACK_LANG) return loadDict(FALLBACK_LANG);
    return {};
  }
}

function detectInitial(): string {
  if (typeof window === 'undefined') return FALLBACK_LANG;
  if (window.simyI18n?.detect) {
    try {
      return window.simyI18n.detect();
    } catch {
      /* fall through */
    }
  }
  try {
    const stored = localStorage.getItem('simy-lang');
    if (stored) return stored;
  } catch {
    /* ignore */
  }
  const nav = (navigator.language || FALLBACK_LANG).toLowerCase();
  if (nav.startsWith('ja')) return 'ja';
  if (nav.startsWith('zh-hans') || nav === 'zh-cn' || nav === 'zh') return 'zh-Hans';
  if (nav.startsWith('zh-hant') || nav === 'zh-tw' || nav === 'zh-hk') return 'zh-Hant';
  if (nav.startsWith('pt')) return 'pt-BR';
  const base = nav.split('-')[0];
  return base || FALLBACK_LANG;
}

export interface UseI18n {
  lang: string;
  dict: Dict;
  t: (key: string, fallback?: string) => string;
  ready: boolean;
}

export function useI18n(): UseI18n {
  const [lang, setLang] = useState<string>(FALLBACK_LANG);
  const [dict, setDict] = useState<Dict>({});
  const [ready, setReady] = useState(false);

  // Initial detection + load
  useEffect(() => {
    let cancelled = false;
    const initial = detectInitial();
    setLang(initial);
    loadDict(initial).then((d) => {
      if (cancelled) return;
      setDict(d);
      setReady(true);
      try {
        document.documentElement.lang = initial;
        document.documentElement.dir = initial === 'ar' ? 'rtl' : 'ltr';
      } catch {
        /* ignore */
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Subscribe to site-wide language changes
  useEffect(() => {
    const onChange = (e: Event) => {
      const code = (e as CustomEvent<string>).detail;
      if (!code || code === lang) return;
      setLang(code);
      loadDict(code).then((d) => {
        setDict(d);
        try {
          document.documentElement.lang = code;
          document.documentElement.dir = code === 'ar' ? 'rtl' : 'ltr';
        } catch {
          /* ignore */
        }
      });
    };
    window.addEventListener('simy-lang-changed', onChange);
    return () => window.removeEventListener('simy-lang-changed', onChange);
  }, [lang]);

  const t = useCallback(
    (key: string, fallback?: string): string => {
      const v = dict[key];
      if (typeof v === 'string' && v.length > 0) return v;
      return fallback ?? key;
    },
    [dict]
  );

  return { lang, dict, t, ready };
}
