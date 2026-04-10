export type Dict = Record<string, string>;

declare global {
  interface Window {
    simyI18n?: {
      setLang: (code: string) => void;
      detect: () => string;
    };
  }
}

export {};
