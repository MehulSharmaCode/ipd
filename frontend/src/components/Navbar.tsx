import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Leaf, Sun, Moon, LogOut, LayoutDashboard, Bell, CheckCheck } from 'lucide-react';
import { useTheme } from '@/components/theme-provider';
import { useTranslationText } from '@/hooks/useTranslationText';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { toast } from 'sonner';
import api from '@/lib/api';

function NotificationBell() {
    const [unreadCount, setUnreadCount] = useState(0);
    const [notifications, setNotifications] = useState<any[]>([]);
    const [isOpen, setIsOpen] = useState(false);

    const fetchNotifications = async () => {
        try {
            const res = await api.get('/farmers/me/notifications');
            if (res.data && res.data.status === 'success') {
                setUnreadCount(res.data.unread_count || 0);
                setNotifications(res.data.notifications || []);
            }
        } catch (e) {
            // Silently fail if not logged in or endpoint unready
        }
    };

    useEffect(() => {
        fetchNotifications();
        const interval = setInterval(fetchNotifications, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleMarkAllRead = async () => {
        try {
            await api.put('/farmers/me/notifications/read-all');
            setUnreadCount(0);
            setNotifications(prev => prev.map(n => ({ ...n, read: true })));
            toast.success("All notifications marked as read");
        } catch (e) {
            toast.error("Failed to mark notifications as read");
        }
    };

    return (
        <div className="relative">
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsOpen(!isOpen)}
                className="h-9 w-9 text-slate-600 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950 rounded-xl relative"
            >
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                    <span className="absolute top-1 right-1 h-4 w-4 bg-rose-500 text-white text-[10px] font-extrabold rounded-full flex items-center justify-center animate-pulse">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </Button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl z-50 p-4">
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-800">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            Notifications ({unreadCount} unread)
                        </span>
                        {unreadCount > 0 && (
                            <button
                                onClick={handleMarkAllRead}
                                className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1 font-medium"
                            >
                                <CheckCheck className="h-3 w-3" /> Mark read
                            </button>
                        )}
                    </div>

                    <div className="max-h-64 overflow-y-auto space-y-2">
                        {notifications.length === 0 ? (
                            <p className="text-xs text-slate-400 text-center py-4">No notifications yet</p>
                        ) : (
                            notifications.map((n) => (
                                <div
                                    key={n._id}
                                    className={`p-2.5 rounded-xl text-xs transition-colors ${
                                        !n.read
                                            ? 'bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200/50 dark:border-emerald-800/50'
                                            : 'bg-slate-50 dark:bg-slate-800/50'
                                    }`}
                                >
                                    <div className="font-bold text-slate-800 dark:text-slate-200 mb-0.5">{n.title}</div>
                                    <div className="text-slate-600 dark:text-slate-400 leading-snug">{n.message}</div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

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
                        <div className="flex items-center gap-2 relative">
                            {/* Notification Bell Badge */}
                            <NotificationBell />

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
