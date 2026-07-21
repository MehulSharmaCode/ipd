import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, useInView, AnimatePresence, cubicBezier } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Leaf, ShieldCheck, Zap, Search, ArrowRight, CheckCircle2,
  Globe, Sprout, BarChart3, FileText, Star,
  ChevronDown, Twitter, Linkedin, Github, Bell,
  Database, ClipboardList, TrendingUp, Users, Award, Lock,
  Sun, Moon
} from 'lucide-react';

import DarkVeil from '@/components/DarkVeil';
import { useTheme } from '@/components/theme-provider';
import { useTranslationText } from '@/hooks/useTranslationText';
import CropShowcase from '@/components/CropShowcase';
import api from '@/lib/api';

// ─── DATA & ACCENTS ────────────────────────────────────────────────────────────

const accentMap = {
  emerald: { bg: "bg-emerald-500/10 dark:bg-emerald-500/15", text: "text-emerald-600 dark:text-emerald-400", border: "group-hover:border-emerald-500/40" },
  blue: { bg: "bg-blue-500/10 dark:bg-blue-500/15", text: "text-blue-600 dark:text-blue-400", border: "group-hover:border-blue-500/40" },
  amber: { bg: "bg-amber-500/10 dark:bg-amber-500/15", text: "text-amber-600 dark:text-amber-400", border: "group-hover:border-amber-500/40" },
  violet: { bg: "bg-violet-500/10 dark:bg-violet-500/15", text: "text-violet-600 dark:text-violet-400", border: "group-hover:border-violet-500/40" },
  teal: { bg: "bg-teal-500/10 dark:bg-teal-500/15", text: "text-teal-600 dark:text-teal-400", border: "group-hover:border-teal-500/40" },
  rose: { bg: "bg-rose-500/10 dark:bg-rose-500/15", text: "text-rose-600 dark:text-rose-400", border: "group-hover:border-rose-500/40" },
};

// ─── ANIMATIONS ────────────────────────────────────────────────────────────────

const easeCustom = cubicBezier(0.22, 1, 0.36, 1);

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: easeCustom } },
};

const stagger = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.12 } },
};

// ─── COUNTER ───────────────────────────────────────────────────────────────────

function AnimatedCounter({ target, suffix = "", prefix = "" }: { target: number; suffix?: string; prefix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const duration = 1800;
    const step = (timestamp: number) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(ease * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [inView, target]);

  return (
    <span ref={ref}>
      {prefix}{count.toLocaleString('en-IN')}{suffix}
    </span>
  );
}

// ─── FAQ ITEM ──────────────────────────────────────────────────────────────────

function FAQItem({ q, a }: { q: string; a: string; key?: any }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div
      variants={fadeUp}
      className={`border-b border-slate-200 dark:border-slate-800 transition-colors ${open ? "" : "hover:border-emerald-300 dark:hover:border-emerald-700"}`}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-5 text-left gap-4 group"
      >
        <span className="text-base font-semibold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
          {q}
        </span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25 }}>
          <ChevronDown className="h-5 w-5 text-slate-400 shrink-0" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <p className="pb-5 text-slate-500 dark:text-slate-400 leading-relaxed text-sm">{a}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── MAIN COMPONENT ────────────────────────────────────────────────────────────

export default function LandingPage() {
  const { theme, setTheme } = useTheme();
  const { t } = useTranslationText();
  const navigate = useNavigate();

  const features = [
    { title: t('hero.features_list.0.title'), description: t('hero.features_list.0.desc'), icon: <Zap className="h-5 w-5" />, accent: "emerald" },
    { title: t('hero.features_list.1.title'), description: t('hero.features_list.1.desc'), icon: <Lock className="h-5 w-5" />, accent: "blue" },
    { title: t('hero.features_list.2.title'), description: t('hero.features_list.2.desc'), icon: <BarChart3 className="h-5 w-5" />, accent: "amber" },
    { title: t('hero.features_list.3.title'), description: t('hero.features_list.3.desc'), icon: <ClipboardList className="h-5 w-5" />, accent: "violet" },
    { title: t('hero.features_list.4.title'), description: t('hero.features_list.4.desc'), icon: <Database className="h-5 w-5" />, accent: "teal" },
    { title: t('hero.features_list.5.title'), description: t('hero.features_list.5.desc'), icon: <Search className="h-5 w-5" />, accent: "rose" },
  ];

  const stats = [
    { value: 10000, suffix: "+", label: t('stats.0.label'), icon: <Users className="h-5 w-5" /> },
    { value: 1200, suffix: "+", label: t('stats.1.label'), icon: <Database className="h-5 w-5" /> },
    { value: 50, prefix: "₹", suffix: t('stats.2.suffix'), label: t('stats.2.label'), icon: <TrendingUp className="h-5 w-5" /> },
    { value: 95, suffix: "%", label: t('stats.3.label'), icon: <Award className="h-5 w-5" /> },
  ];

  const [testimonials, setTestimonials] = useState<any[]>([]);

  useEffect(() => {
    const fetchTopStories = async () => {
      try {
        const response = await api.get('/stories/top?limit=3');
        // If the database is empty, provide some fallback mock data
        if (response.data.length === 0) {
          setTestimonials([
            { farmer_name: t('testimonials.list.0.name'), location_state: t('testimonials.list.0.state'), crop_type: t('testimonials.list.0.role'), content: t('testimonials.list.0.quote'), avatar: "RP", color: "from-emerald-500 to-teal-600" },
            { farmer_name: t('testimonials.list.1.name'), location_state: t('testimonials.list.1.state'), crop_type: t('testimonials.list.1.role'), content: t('testimonials.list.1.quote'), avatar: "KD", color: "from-blue-500 to-indigo-600" },
            { farmer_name: t('testimonials.list.2.name'), location_state: t('testimonials.list.2.state'), crop_type: t('testimonials.list.2.role'), content: t('testimonials.list.2.quote'), avatar: "GS", color: "from-amber-500 to-orange-600" }
          ]);
        } else {
          setTestimonials(response.data.map((story: any, index: number) => {
            const colors = [
              "from-emerald-500 to-teal-600",
              "from-blue-500 to-indigo-600",
              "from-amber-500 to-orange-600"
            ];
            return {
              ...story,
              avatar: story.farmer_name.substring(0, 2).toUpperCase(),
              color: colors[index % colors.length]
            }
          }));
        }
      } catch (error) {
        console.error("Error fetching top stories:", error);
      }
    };
    fetchTopStories();
  }, [t]);

  const faqs = [
    { q: t('faq.list.0.q'), a: t('faq.list.0.a') },
    { q: t('faq.list.1.q'), a: t('faq.list.1.a') },
    { q: t('faq.list.2.q'), a: t('faq.list.2.a') },
    { q: t('faq.list.3.q'), a: t('faq.list.3.a') },
    { q: t('faq.list.4.q'), a: t('faq.list.4.a') },
    { q: t('faq.list.5.q'), a: t('faq.list.5.a') },
  ];

  const steps = [
    { num: "01", title: t('process.steps.0.title'), desc: t('process.steps.0.desc'), icon: <FileText className="h-5 w-5" /> },
    { num: "02", title: t('process.steps.1.title'), desc: t('process.steps.1.desc'), icon: <Search className="h-5 w-5" /> },
    { num: "03", title: t('process.steps.2.title'), desc: t('process.steps.2.desc'), icon: <ShieldCheck className="h-5 w-5" /> },
    { num: "04", title: t('process.steps.3.title'), desc: t('process.steps.3.desc'), icon: <CheckCircle2 className="h-5 w-5" /> },
  ];

  const benefits = [
    { title: t('benefits.list.0.title'), desc: t('benefits.list.0.desc'), icon: <Bell className="h-6 w-6" /> },
    { title: t('benefits.list.1.title'), desc: t('benefits.list.1.desc'), icon: <FileText className="h-6 w-6" /> },
    { title: t('benefits.list.2.title'), desc: t('benefits.list.2.desc'), icon: <Globe className="h-6 w-6" /> },
    { title: t('benefits.list.3.title'), desc: t('benefits.list.3.desc'), icon: <TrendingUp className="h-6 w-6" /> },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#060a0f] font-sans text-slate-900 dark:text-slate-50 overflow-x-hidden transition-colors duration-300">
      {/* ── HERO ── */}
      <section className="relative w-full min-h-screen flex items-center justify-center px-6 pt-28 pb-20 overflow-hidden">

        {theme === "dark" && (
          <div className="absolute inset-0 z-0">
            <div className="absolute inset-0 opacity-90 bg-[#060a0f]">
              <DarkVeil
                hueShift={0}
                noiseIntensity={0}
                scanlineIntensity={0.05}
                speed={1.5}
                scanlineFrequency={5}
                warpAmount={0}
              />
            </div>
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#060a0f]/30 to-[#060a0f]" />
            {/* Glow orbs */}
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-emerald-600/10 blur-[120px] rounded-full pointer-events-none" />
          </div>
        )}

        {theme === "light" && (
          <div className="absolute inset-0 z-0 bg-white">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(16,185,129,0.12),transparent)]" />
            <div className="absolute inset-0 bg-gradient-to-b from-white via-emerald-50/40 to-slate-50" />
          </div>
        )}

        {/* Grid texture */}
        <div className="absolute inset-0 z-0 opacity-[0.025] dark:opacity-[0.04]"
          style={{ backgroundImage: "linear-gradient(#10b981 1px,transparent 1px),linear-gradient(90deg,#10b981 1px,transparent 1px)", backgroundSize: "60px 60px" }} />

        <motion.div
          variants={stagger}
          initial="hidden"
          animate="visible"
          className="max-w-5xl mx-auto text-center relative z-10"
        >
          <motion.div variants={fadeUp} className="mb-7">
            <Badge className="px-4 py-1.5 rounded-full bg-emerald-500/10 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-300/40 dark:border-emerald-500/30 text-xs font-semibold backdrop-blur-md">
              <Sprout className="h-3.5 w-3.5 mr-1.5 inline-block" />
              {t('hero.badge')}
            </Badge>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="text-5xl md:text-7xl lg:text-[5.5rem] font-black tracking-[-0.04em] text-slate-900 dark:text-white mb-7 leading-[1.05]"
          >
            {t('hero.title_part1')}{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-300 italic">
              {t('hero.title_highlight')}
            </span>
            <br />
            {t('hero.title_part2')}
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="text-lg md:text-xl text-slate-600 dark:text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed font-normal"
          >
            {t('hero.subtitle')}
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-col sm:flex-row justify-center items-center gap-4 mb-14">
            <Link to={localStorage.getItem('access_token') ? "/dashboard" : "/auth"}>
              <Button className="h-13 px-8 py-4 text-base bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl group transition-all shadow-xl shadow-emerald-500/20 hover:shadow-emerald-500/35 hover:scale-105">
                {t('common.get_started')}
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
            <Button variant="outline" className="h-13 px-8 py-4 text-base font-semibold border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-400 dark:hover:border-emerald-600 rounded-xl bg-transparent">
              {t('hero.watch_demo')}
            </Button>
          </motion.div>

          {/* Trust indicators */}
          <motion.div variants={fadeUp} className="flex flex-wrap justify-center items-center gap-x-8 gap-y-3 text-sm text-slate-500 dark:text-slate-500">
            {[
              { icon: <ShieldCheck className="h-4 w-4 text-emerald-500" />, text: t('hero.trust_1') },
              { icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />, text: t('hero.trust_2') },
              { icon: <Users className="h-4 w-4 text-emerald-500" />, text: t('hero.trust_3') },
            ].map((item, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {item.icon}
                {item.text}
              </span>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* ── STATS ── */}
      <section className="py-16 px-6 bg-white dark:bg-slate-950 border-y border-slate-100 dark:border-slate-800/60">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="grid grid-cols-2 md:grid-cols-4 gap-8"
          >
            {stats.map((s, i) => (
              <motion.div key={i} variants={fadeUp} className="text-center">
                <div className="flex justify-center mb-3">
                  <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl text-emerald-600 dark:text-emerald-400">
                    {s.icon}
                  </div>
                </div>
                <div className="text-3xl md:text-4xl font-black tracking-tight text-slate-900 dark:text-white mb-1">
                  <AnimatedCounter target={s.value} suffix={s.suffix} prefix={s.prefix} />
                </div>
                <div className="text-sm text-slate-500 dark:text-slate-500 font-medium">{s.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── CROPS SHOWCASE ── */}
      <CropShowcase />

      {/* ── FEATURES ── */}
      <section id="features" className="py-28 px-6 bg-slate-50 dark:bg-[#060a0f]">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="text-center mb-16"
          >
            <motion.div variants={fadeUp}>
              <Badge className="mb-4 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 text-xs font-semibold rounded-full">
                {t('hero.features_badge')}
              </Badge>
            </motion.div>
            <motion.h2 variants={fadeUp} className="text-4xl md:text-5xl font-black tracking-[-0.03em] text-slate-900 dark:text-white mb-4">
              {t('hero.features_title')}
            </motion.h2>
            <motion.p variants={fadeUp} className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
              {t('hero.features_subtitle')}
            </motion.p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5"
          >
            {features.map((f, idx) => {
              const accent = accentMap[f.accent as keyof typeof accentMap];
              return (
                <motion.div key={idx} variants={fadeUp}>
                  <Card className={`group h-full border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-none hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/40 hover:-translate-y-1.5 transition-all duration-400 rounded-2xl overflow-hidden ${accent.border}`}>
                    <CardHeader className="pb-3">
                      <div className={`${accent.bg} w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${accent.text} group-hover:scale-110 transition-transform duration-400`}>
                        {f.icon}
                      </div>
                      <CardTitle className={`text-lg font-bold tracking-tight text-slate-900 dark:text-white`}>{f.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <CardDescription className="text-slate-500 dark:text-slate-400 leading-relaxed text-sm">
                        {f.description}
                      </CardDescription>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="process" className="py-28 px-6 bg-white dark:bg-slate-950">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="text-center mb-16"
          >
            <motion.div variants={fadeUp}>
              <Badge className="mb-4 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 text-xs font-semibold rounded-full">
                {t('process.badge')}
              </Badge>
            </motion.div>
            <motion.h2 variants={fadeUp} className="text-4xl md:text-5xl font-black tracking-[-0.03em] text-slate-900 dark:text-white mb-4" dangerouslySetInnerHTML={{ __html: t('process.title') }} />
          </motion.div>

          <div className="relative">
            {/* Connector line */}
            <div className="absolute top-10 left-[calc(12.5%+20px)] right-[calc(12.5%+20px)] hidden lg:block h-px bg-gradient-to-r from-transparent via-emerald-300/60 dark:via-emerald-700/40 to-transparent" />

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={stagger}
              className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8"
            >
              {steps.map((step, i) => (
                <motion.div key={i} variants={fadeUp} className="relative">
                  <div className="flex flex-col items-center text-center">
                    <div className="relative mb-5">
                      <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/30 dark:to-emerald-800/20 border border-emerald-200/60 dark:border-emerald-700/30 flex items-center justify-center shadow-sm">
                        <span className="text-emerald-600 dark:text-emerald-400">{step.icon}</span>
                      </div>
                      <div className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-emerald-600 flex items-center justify-center">
                        <span className="text-white text-[10px] font-black">{i + 1}</span>
                      </div>
                    </div>
                    <h4 className="font-bold text-slate-900 dark:text-white mb-2 text-base">{step.title}</h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{step.desc}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── BENEFITS ── */}
      <section className="py-28 px-6 bg-slate-50 dark:bg-[#060a0f]">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, ease: easeCustom }}
            >
              <Badge className="mb-5 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 text-xs font-semibold rounded-full">
                {t('benefits.badge')}
              </Badge>
              <h2 className="text-4xl md:text-5xl font-black tracking-[-0.03em] text-slate-900 dark:text-white mb-6 leading-tight">
                {t('benefits.title')}
              </h2>
              <p className="text-slate-500 dark:text-slate-400 leading-relaxed mb-8">
                {t('benefits.subtitle')}
              </p>
              <Link to="/auth">
                <Button className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 py-3 rounded-xl shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all">
                  {t('benefits.start_free')} <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </motion.div>

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={stagger}
              className="grid sm:grid-cols-2 gap-4"
            >
              {benefits.map((b, i) => (
                <motion.div key={i} variants={fadeUp}>
                  <div className="p-5 bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors group">
                    <div className="p-2.5 bg-emerald-50 dark:bg-emerald-900/30 rounded-xl text-emerald-600 dark:text-emerald-400 w-fit mb-4 group-hover:scale-110 transition-transform">
                      {b.icon}
                    </div>
                    <h4 className="font-bold text-slate-900 dark:text-white mb-1.5 text-sm">{b.title}</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{b.desc}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section id="testimonials" className="py-28 px-6 bg-white dark:bg-slate-950">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="text-center mb-16"
          >
            <motion.div variants={fadeUp}>
              <Badge className="mb-4 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 text-xs font-semibold rounded-full">
                {t('testimonials.badge')}
              </Badge>
            </motion.div>
            <motion.h2 variants={fadeUp} className="text-4xl md:text-5xl font-black tracking-[-0.03em] text-slate-900 dark:text-white mb-4">
              {t('testimonials.title')}
            </motion.h2>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="grid md:grid-cols-3 gap-6"
          >
            {testimonials.map((t, i) => (
              <motion.div key={i} variants={fadeUp}>
                <div className="h-full p-7 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl hover:shadow-xl hover:shadow-slate-100/80 dark:hover:shadow-black/30 hover:-translate-y-1 transition-all duration-400 flex flex-col">
                  <div className="flex mb-4 gap-0.5">
                    {[...Array(5)].map((_, s) => (
                      <Star key={s} className="h-4 w-4 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-sm mb-6 flex-1 line-clamp-4">
                    "{t.content}"
                  </p>
                  <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                    <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${t.color} flex items-center justify-center text-white text-xs font-black shrink-0`}>
                      {t.avatar}
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 dark:text-white text-sm">{t.farmer_name}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-500">{t.crop_type} · {t.location_state}</div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
          <motion.div variants={fadeUp} className="mt-12 text-center">
            <Link to="/community">
              <Button variant="outline" className="border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20">
                Explore Community Hub <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="py-28 px-6 bg-slate-50 dark:bg-[#060a0f]">
        <div className="max-w-2xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="text-center mb-14"
          >
            <motion.div variants={fadeUp}>
              <Badge className="mb-4 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 text-xs font-semibold rounded-full">
                {t('faq.badge')}
              </Badge>
            </motion.div>
            <motion.h2 variants={fadeUp} className="text-4xl font-black tracking-[-0.03em] text-slate-900 dark:text-white">
              {t('faq.title')}
            </motion.h2>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="divide-y divide-slate-200 dark:divide-slate-800"
          >
            {faqs.map((faq, i) => (
              <FAQItem key={i} q={faq.q} a={faq.a} />
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section className="py-28 px-6 bg-white dark:bg-slate-950">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: easeCustom }}
            className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-emerald-950 via-emerald-900 to-teal-900 p-12 md:p-20 text-center shadow-2xl"
          >
            {/* Decorative glows */}
            <div className="absolute -top-20 -right-20 w-72 h-72 bg-emerald-400/10 blur-3xl rounded-full pointer-events-none" />
            <div className="absolute -bottom-20 -left-20 w-72 h-72 bg-teal-400/10 blur-3xl rounded-full pointer-events-none" />

            <div className="relative z-10">
              <Badge className="mb-6 px-3 py-1 bg-emerald-500/20 text-emerald-300 border-emerald-500/30 text-xs font-semibold rounded-full">
                {t('cta.badge')}
              </Badge>
              <h2 className="text-4xl md:text-5xl font-black tracking-[-0.03em] text-white mb-5 leading-tight" dangerouslySetInnerHTML={{ __html: t('cta.title') }} />
              <p className="text-emerald-200/70 mb-10 max-w-lg mx-auto leading-relaxed">
                {t('cta.subtitle')}
              </p>
              <Link to="/auth">
                <Button className="h-14 px-10 text-base bg-white hover:bg-emerald-50 text-emerald-900 font-bold rounded-2xl shadow-xl hover:scale-105 transition-all group">
                  {t('cta.button')}
                  <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="py-16 px-6 border-t border-slate-200 dark:border-slate-800/60 bg-white dark:bg-[#060a0f]">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-5 gap-12 mb-12">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-5">
                <div className="bg-gradient-to-br from-emerald-500 to-emerald-700 p-1.5 rounded-xl shadow-lg shadow-emerald-500/20">
                  <Leaf className="h-5 w-5 text-white" />
                </div>
                <span className="font-black text-lg tracking-[-0.04em] text-emerald-900 dark:text-white">
                  AGRISENSE
                </span>
              </div>
              <p className="text-slate-500 dark:text-slate-500 text-sm leading-relaxed max-w-xs">
                {t('footer.desc')}
              </p>
              <div className="flex gap-3 mt-6">
                {[Twitter, Linkedin, Github].map((Icon, i) => (
                  <a key={i} href="#" className="h-9 w-9 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-center text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors">
                    <Icon className="h-4 w-4" />
                  </a>
                ))}
              </div>
            </div>

            {[
              { title: t('footer.col1_title'), links: [t('footer.col1_l1'), t('footer.col1_l2'), t('footer.col1_l3'), t('footer.col1_l4')] },
              { title: t('footer.col2_title'), links: [t('footer.col2_l1'), t('footer.col2_l2'), t('footer.col2_l3'), t('footer.col2_l4')] },
              { title: t('footer.col3_title'), links: [t('footer.col3_l1'), t('footer.col3_l2'), t('footer.col3_l3'), t('footer.col3_l4')] },
            ].map((col, i) => (
              <div key={i}>
                <h5 className="font-bold text-slate-900 dark:text-white text-sm mb-4">{col.title}</h5>
                <ul className="space-y-3">
                  {col.links.map((link, j) => (
                    <li key={j}>
                      <a href="#" className="text-sm text-slate-500 dark:text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="pt-8 border-t border-slate-100 dark:border-slate-800/60 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-xs text-slate-400 dark:text-slate-600">
              {t('footer.rights')}
            </p>
            <div className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-600">
              <Globe className="h-3.5 w-3.5" />
              {t('footer.available_in')}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}