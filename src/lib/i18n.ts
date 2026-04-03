import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from '../locales/en.json'
import ja from '../locales/ja.json'
import zh from '../locales/zh.json'
import ko from '../locales/ko.json'
import es from '../locales/es.json'
import fr from '../locales/fr.json'
import de from '../locales/de.json'
import it from '../locales/it.json'
import pt from '../locales/pt.json'
import ru from '../locales/ru.json'
import ar from '../locales/ar.json'
import hi from '../locales/hi.json'
import tr from '../locales/tr.json'
import pl from '../locales/pl.json'
import nl from '../locales/nl.json'
import sv from '../locales/sv.json'
import da from '../locales/da.json'
import no from '../locales/no.json'
import fi from '../locales/fi.json'
import cs from '../locales/cs.json'
import hu from '../locales/hu.json'
import th from '../locales/th.json'

const resources = {
  en: { translation: en },
  ja: { translation: ja },
  zh: { translation: zh },
  ko: { translation: ko },
  es: { translation: es },
  fr: { translation: fr },
  de: { translation: de },
  it: { translation: it },
  pt: { translation: pt },
  ru: { translation: ru },
  ar: { translation: ar },
  hi: { translation: hi },
  tr: { translation: tr },
  pl: { translation: pl },
  nl: { translation: nl },
  sv: { translation: sv },
  da: { translation: da },
  no: { translation: no },
  fi: { translation: fi },
  cs: { translation: cs },
  hu: { translation: hu },
  th: { translation: th },
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en', // Set default language explicitly
    fallbackLng: 'en',
    debug: false,
    interpolation: {
      escapeValue: false,
    },
  })

export default i18n