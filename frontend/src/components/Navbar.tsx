import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Leaf, Sun, Moon } from 'lucide-react';
import { useTheme } from '@/components/theme-provider';
import { useTranslationText } from '@/hooks/useTranslationText';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

export function Navbar() {
    const { theme, setTheme } = useTheme();
    const { t } = useTranslationText();
    const location = useLocation();
    const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('access_token'));

    useEffect(() => {
        const checkAuth = () => setIsLoggedIn(!!localStorage.getItem('access_token'));
        checkAuth(); // Initial check on mount/location change

        // Listen for storage changes (works across tabs)
        window.addEventListener('storage', checkAuth);
        return () => window.removeEventListener('storage', checkAuth);
    }, [location]);

    return (
        <nav className="fixed top-0 w-full z-50 px-4 pt-4 pointer-events-none">
            <motion.div
                initial={{ y: -24, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="max-w-7xl mx-auto flex items-center justify-between px-5 py-3 bg-white/80 dark:bg-[#060a0f]/80 backdrop-blur-md rounded-2xl border border-slate-200 dark:border-slate-800 pointer-events-auto shadow-sm"
            >
                <Link to="/" className="flex items-center gap-2.5 group cursor-pointer">
                    <div className="bg-gradient-to-br from-emerald-500 to-emerald-700 p-1.5 rounded-xl group-hover:scale-110 transition-transform shadow-lg shadow-emerald-500/25">
                        <Leaf className="h-5 w-5 text-white" />
                    </div>
                    <span className="text-lg font-black tracking-[-0.04em] text-emerald-900 dark:text-white">
                        AGRISENSE
                    </span>
                </Link>

                <div className="hidden md:flex gap-7 text-sm font-medium text-slate-600 dark:text-slate-400">
                    <Link to="/#features" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.features') || 'Features'}
                    </Link>
                    <Link to="/#process" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.process') || 'Process'}
                    </Link>
                    <Link to="/#testimonials" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.testimonials') || 'Testimonials'}
                    </Link>
                    <Link to="/community" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors font-bold text-emerald-700 dark:text-emerald-300">
                        Community
                    </Link>
                    <Link to="/#faq" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.faq') || 'FAQ'}
                    </Link>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                        className="h-9 w-9 text-slate-600 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950 rounded-xl"
                    >
                        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                    </Button>
                    <LanguageSwitcher />

                    {isLoggedIn ? (
                        <Link to="/dashboard">
                            <Button className="h-9 px-5 text-sm bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 transition-all hover:scale-105 hover:shadow-emerald-500/40">
                                {t('dashboard.title') || 'Dashboard'}
                            </Button>
                        </Link>
                    ) : (
                        <>
                            <Link to="/auth">
                                <Button variant="ghost" className="h-9 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-emerald-700 dark:hover:text-white hover:bg-emerald-50 dark:hover:bg-white/5 rounded-xl">
                                    {t('nav.login') || 'Login'}
                                </Button>
                            </Link>
                            <Link to="/auth">
                                <Button className="h-9 px-5 text-sm bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 transition-all hover:scale-105 hover:shadow-emerald-500/40">
                                    {t('nav.get_started') || 'Get Started'}
                                </Button>
                            </Link>
                        </>
                    )}
                </div>
            </motion.div>
        </nav>
    );
}
