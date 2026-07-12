import { useTranslation } from 'react-i18next';

/**
 * A wrapper hook for `useTranslation` that encourages developers 
 * to pass valid translation keys rather than using hardcoded text.
 */
export function useTranslationText(namespace?: string) {
    const { t, i18n, ready } = useTranslation(namespace);

    // You can extend this to add strict typings or logging for missing keys
    return { t, i18n, ready };
}
