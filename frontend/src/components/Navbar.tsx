import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Leaf, Sun, Moon, LogOut, LayoutDashboard } from 'lucide-react';
import { useTheme } from '@/components/theme-provider';
import { useTranslationText } from '@/hooks/useTranslationText';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { toast } from 'sonner';

export function Navbar() {
    const { theme, setTheme } = useTheme();
    const { t } = useTranslationText();
    const location = useLocation();
    const navigate = useNavigate();
    const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('access_token'));

    useEffect(() => {
        const checkAuth = () => setIsLoggedIn(!!localStorage.getItem('access_token'));
        checkAuth(); // Initial check on mount/location change

        // Listen for storage changes (across tabs and local auth events)
        window.addEventListener('storage', checkAuth);
        window.addEventListener('auth-change', checkAuth);
        return () => {
            window.removeEventListener('storage', checkAuth);
            window.removeEventListener('auth-change', checkAuth);
        };
    }, [location]);

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        setIsLoggedIn(false);
        window.dispatchEvent(new Event('auth-change'));
        toast.success(t('common.logout') || 'Logged out successfully');
        navigate('/');
    };

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
                    <a href="/#features" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.features') || 'Features'}
                    </a>
                    <a href="/#process" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.process') || 'Process'}
                    </a>
                    <a href="/#testimonials" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.testimonials') || 'Testimonials'}
                    </a>
                    <Link to="/community" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors font-bold text-emerald-700 dark:text-emerald-300">
                        Community
                    </Link>
                    <a href="/#faq" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {t('nav.faq') || 'FAQ'}
                    </a>
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
                        <div className="flex items-center gap-2">
                            <Link to="/dashboard">
                                <Button className="h-9 px-4 text-sm bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 transition-all hover:scale-105 flex items-center gap-1.5">
                                    <LayoutDashboard className="h-4 w-4" />
                                    {t('dashboard.title') || 'Dashboard'}
                                </Button>
                            </Link>
                            <Button
                                variant="ghost"
                                onClick={handleLogout}
                                className="h-9 px-3 text-sm font-semibold text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl flex items-center gap-1.5"
                            >
                                <LogOut className="h-4 w-4" />
                                {t('common.logout') || 'Sign Out'}
                            </Button>
                        </div>
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
