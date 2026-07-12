import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import resourcesToBackend from 'i18next-resources-to-backend';

i18n
    .use(LanguageDetector)
    // Use resourcesToBackend to lazy load translation files
    .use(
        resourcesToBackend((language: string) =>
            import(`./locales/${language}.json`)
        )
    )
    .use(initReactI18next)
    .init({
        fallbackLng: 'en',
        // have a common namespace used around the full app
        ns: ['translation'],
        defaultNS: 'translation',

        // debug: true, // Optional: uncomment if needed for debugging

        interpolation: {
            escapeValue: false, // React already safeguards from xss
        },
        detection: {
            // Configure language detection to check localStorage first
            order: ['localStorage', 'navigator'],
            caches: ['localStorage'],
        }
    });

// Update the html lang attribute whenever language changes
i18n.on('languageChanged', (lng) => {
    document.documentElement.lang = lng;
});

export default i18n;
