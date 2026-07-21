import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  LayoutDashboard,
  UserCircle,
  FileCheck,
  Tractor,
  User,
  CreditCard,
  GraduationCap,
  UploadCloud,
  FileText,
  Sprout,
  ArrowRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronRight,
  Loader2,
  Save,
  MapPin,
  LogOut,
  TrendingUp,
  Globe,
  Mic
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslationText } from '@/hooks/useTranslationText';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { useVoiceInput } from '@/hooks/useVoiceInput';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<'home' | 'profile'>('home');
  const [schemeTab, setSchemeTab] = useState<'eligible' | 'ineligible' | 'monitored' | 'risk_alerts'>('eligible');
  const [farmer, setFarmer] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [monitoredSchemes, setMonitoredSchemes] = useState<any[]>([]);
  const [selectedScheme, setSelectedScheme] = useState<any>(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const schemesRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslationText();

  // Voice Input (apurv-auth)
  const { isSupported: voiceSupported, listen } = useVoiceInput();
  const [listeningField, setListeningField] = useState<string | null>(null);
  const voiceLang = 'en-IN';

  const startVoice = (fieldKey: string) => {
    listen(
      fieldKey,
      voiceLang,
      (val) => setFormData(prev => ({ ...prev, [fieldKey]: val })),
      (err) => toast.error(err),
      (active) => setListeningField(active ? fieldKey : null)
    );
  };

  const [uploadType, setUploadType] = useState('Aadhar');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);

  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone_number: '',
    age: '',
    gender: '',
    category: '',
    highest_qualification: '',
    is_differently_abled: 'false',
    state: '',
    district: '',
    pincode: '',
    aadhar_number: '',
    pan_number: '',
    annual_income: '',
    bank_account_linked: 'false',
    land_size_hectares: '',
    farmer_type: '',
    irrigation_type: '',
    soil_type: '',
    crop_season: '',
    water_source: '',
    land_ownership: '',
    primary_crops: '',
  });

  const fetchProfile = async () => {
    try {
      const res = await api.get('/farmers/me');
      setFarmer(res.data);

      const d = res.data;
      setFormData({
        full_name: d.full_name || '',
        email: d.email || '',
        phone_number: d.phone_number || '',
        age: d.age?.toString() || '',
        gender: d.gender || '',
        category: d.category || '',
        highest_qualification: d.highest_qualification || '',
        is_differently_abled: d.is_differently_abled ? 'true' : 'false',
        state: d.state || '',
        district: d.district || '',
        pincode: d.pincode || '',
        aadhar_number: d.aadhar_number || '',
        pan_number: d.pan_number || '',
        annual_income: d.annual_income?.toString() || '',
        bank_account_linked: d.bank_account_linked ? 'true' : 'false',
        land_size_hectares: d.land_size_hectares?.toString() || '',
        farmer_type: d.farmer_type || '',
        irrigation_type: d.irrigation_type || '',
        soil_type: d.soil_type || '',
        crop_season: d.crop_season || '',
        water_source: d.water_source || '',
        land_ownership: d.land_ownership || '',
        primary_crops: d.primary_crops?.join(', ') || '',
      });
    } catch (err) {
      toast.error(t('auth.toast_fail'));
    }
  };

  const fetchMonitoredSchemes = async () => {
    try {
      const res = await api.get('/monitoring/system-status');
      // system-status returns an object with details. we want the recent_updates array.
      if (res.data && res.data.recent_updates) {
        setMonitoredSchemes(res.data.recent_updates);
      } else {
        setMonitoredSchemes([]);
      }
    } catch (err) {
      console.error("Failed to fetch monitored schemes", err);
    }
  };

  useEffect(() => {
    fetchProfile();
    fetchMonitoredSchemes();
  }, [navigate]);

  // After registration: auto-scroll to schemes section
  useEffect(() => {
    if (searchParams.get('from') === 'setup') {
      // Wait for data to load before scrolling
      const timer = setTimeout(() => {
        if (schemesRef.current) {
          schemesRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        toast.success('🎉 Welcome! Your personalized scheme matches are ready below.', {
          duration: 5000,
        });
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [searchParams]);

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...formData,
        age: parseInt(formData.age) || null,
        annual_income: parseFloat(formData.annual_income) || null,
        land_size_hectares: parseFloat(formData.land_size_hectares) || null,
        is_differently_abled: formData.is_differently_abled === 'true',
        bank_account_linked: formData.bank_account_linked === 'true',
        primary_crops: formData.primary_crops.split(',').map((c: string) => c.trim()).filter((c: string) => c !== ""),
      };

      await api.put('/farmers/me', payload);
      toast.success(t('dashboard.toast_profile_updated'));
      fetchProfile();
      setActiveTab('home');
    } catch (err) {
      toast.error(t('dashboard.toast_profile_failed'));
    } finally {
      setSaving(false);
    }
  };

  const handleDocumentUpload = async () => {
    if (!selectedFile) {
      toast.error(t('dashboard.toast_upload_failed'));
      return;
    }

    setUploadingDoc(true);
    try {
      const docData = new FormData();
      docData.append('file', selectedFile);

      if (uploadType === 'Policy_Document') {
        // Special case for Admin Policy testing
        toast.loading("Ingesting policy document via AI Engine...");
        const res = await api.post('/monitoring/test/policy-ingest', docData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        toast.dismiss();
        toast.success(`Policy ingested: ${Object.keys(res.data.extracted_rules || {}).length} rules extracted`);
      } else {
        // Normalize doc_type to lowercase — backend validates against 'aadhar', 'pan'
        docData.append('doc_type', uploadType.toLowerCase());
        const res = await api.post('/upload', docData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        // API returns: { status, documentType, confidence, fields, validation, profileSuggestions }
        const data = res.data;
        const isValid: boolean = data.validation?.valid === true;
        const fields = data.fields || {};

        if (isValid) {
          // Show extracted ID number in the success message
          const extractedId = fields.aadhaarNumber || fields.panNumber || '';
          toast.success(
            extractedId
              ? `✅ ${uploadType} verified! ID: ${extractedId}`
              : t('dashboard.toast_upload_success', { type: uploadType }) || `${uploadType} uploaded successfully`
          );
        } else {
          const warnings = data.validation?.warnings || [];
          if (warnings.length > 0) {
            toast.warning(`Document uploaded with warnings: ${warnings[0]}`);
          } else {
            toast.success(t('dashboard.toast_upload_success', { type: uploadType }) || `${uploadType} uploaded successfully`);
          }
        }

        setSelectedFile(null);
        const fileInput = document.getElementById('document-upload') as HTMLInputElement;
        if (fileInput) fileInput.value = '';

        fetchProfile();
      }
    } catch (err: any) {
      toast.dismiss();
      console.error(err);
      const errMsg = err.response?.data?.detail || "Upload failed. Please try again.";
      toast.error(errMsg);
    } finally {
      setUploadingDoc(false);
    }
  };



    if (!farmer) return (
      <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-950 font-bold text-emerald-600 dark:text-emerald-500">
        <Loader2 className="animate-spin h-8 w-8 mr-3" /> {t('common.loading')}
      </div>
    );

    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-300 flex flex-col md:flex-row overflow-hidden pt-20">

        <aside className="w-full md:w-64 bg-emerald-950 dark:bg-slate-900 text-white p-6 flex flex-col border-r border-emerald-900 dark:border-slate-800 transition-colors duration-300 z-20">
          <div className="flex items-center gap-2 mb-10">
            <LayoutDashboard className="text-emerald-400" />
            <span className="font-black text-xl tracking-tighter">AGRISENSE</span>
          </div>
          <nav className="space-y-2 flex-1">
            <Button
              variant="ghost"
              className={`w-full justify-start transition-all ${activeTab === 'home' ? 'bg-emerald-900 dark:bg-emerald-600/20 text-white dark:text-emerald-400' : 'text-emerald-100 dark:text-slate-400 hover:bg-emerald-900 dark:hover:bg-slate-800'}`}
              onClick={() => setActiveTab('home')}
            >
              <LayoutDashboard className="mr-2 h-4 w-4" /> {t('dashboard.nav_home')}
            </Button>
            <Button
              variant="ghost"
              className={`w-full justify-start transition-all ${activeTab === 'profile' ? 'bg-emerald-900 dark:bg-emerald-600/20 text-white dark:text-emerald-400' : 'text-emerald-100 dark:text-slate-400 hover:bg-emerald-900 dark:hover:bg-slate-800'}`}
              onClick={() => setActiveTab('profile')}
            >
              <UserCircle className="mr-2 h-4 w-4" /> {t('dashboard.nav_profile')}
            </Button>
          </nav>
          <Button
            variant="outline"
            className="mt-4 border-emerald-800 dark:border-slate-700 bg-transparent text-emerald-400 dark:text-slate-300 hover:bg-emerald-900 dark:hover:bg-slate-800 hover:text-emerald-300 dark:hover:text-white transition-all"
            onClick={() => {
              localStorage.removeItem('access_token');
              toast.success('You have been logged out successfully.');
              navigate('/');
            }}
          >
            <LogOut className="mr-2 h-4 w-4" /> {t('common.logout')}
          </Button>
        </aside>

        <main className="flex-1 p-4 md:p-8 overflow-y-auto relative">
          <div className="absolute top-[-10%] right-[-5%] w-96 h-96 bg-emerald-500/10 dark:bg-emerald-500/5 rounded-full blur-[100px] pointer-events-none" />
          <div className="absolute bottom-[-10%] left-[-5%] w-96 h-96 bg-teal-500/10 dark:bg-teal-500/5 rounded-full blur-[100px] pointer-events-none" />

          <div className="max-w-5xl mx-auto relative z-10">
            <AnimatePresence mode="wait">
              {activeTab === 'home' && (
                <motion.div
                  key="home"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.4 }}
                >
                  <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
                    <div>
                      <h1 className="text-3xl font-black text-slate-900 dark:text-white leading-tight tracking-tight">{t('dashboard.welcome', { name: farmer.full_name })}</h1>
                      <p className="text-slate-500 dark:text-slate-400 font-medium italic">{t('dashboard.welcome_sub')}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      {farmer.land_size_hectares ? (
                        <Badge className="bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 px-4 py-1">{t('dashboard.verified_profile')}</Badge>
                      ) : (
                        <Button size="sm" variant="destructive" onClick={() => navigate('/profile-setup')} className="animate-pulse shadow-lg shadow-red-500/20">
                          <AlertCircle className="mr-2 h-4 w-4" /> {t('dashboard.complete_setup')}
                        </Button>
                      )}
                    </div>
                  </header>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                    <Card className="border border-slate-100 dark:border-slate-800 shadow-md bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm transition-all hover:shadow-lg">
                      <CardContent className="pt-6">
                        <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">{t('dashboard.total_land')}</p>
                        <div className="text-3xl font-black mt-1 text-slate-900 dark:text-white">{farmer.land_size_hectares || 0} Ha</div>
                        <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold mt-2 flex items-center">
                          <MapPin className="h-3 w-3 mr-1" /> {farmer.district || t('dashboard.location_not_set')}
                        </p>
                      </CardContent>
                    </Card>

                    <Card className="border border-slate-100 dark:border-slate-800 shadow-md bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm transition-all hover:shadow-lg">
                      <CardContent className="pt-6">
                        <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">{t('dashboard.verification')}</p>
                        <div className="text-3xl font-black mt-1 text-emerald-600 dark:text-emerald-400">
                          {farmer.aadhar_number ? t('common.verified') : t('common.pending')}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">{t('dashboard.update_to_verify')}</p>
                      </CardContent>
                    </Card>

                    <Card className="border-none shadow-lg bg-emerald-600 dark:bg-emerald-700 text-white shadow-emerald-600/20 transition-all hover:scale-[1.02]">
                      <CardContent className="pt-6">
                        <p className="text-xs font-bold text-emerald-200 uppercase tracking-widest">{t('dashboard.ai_score')}</p>
                        <div className="text-4xl font-black mt-1">
                          {farmer.recommended_schemes && farmer.recommended_schemes.length > 0
                            ? `${Math.round(farmer.recommended_schemes[0].success_probability * 100)}%`
                            : '0%'}
                        </div>
                        <div className="flex items-center text-xs mt-2 text-emerald-100">
                          <TrendingUp className="h-3 w-3 mr-1" /> {t('dashboard.new_matches', { count: farmer.recommended_schemes?.length || 0 })}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                      <div ref={schemesRef} className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">

                        <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <FileCheck className="text-emerald-600 dark:text-emerald-500" /> {t('dashboard.schemes_title')}
                        </h3>
                        <div className="flex gap-2 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-800">
                          <button
                            onClick={() => setSchemeTab('eligible')}
                            className={`px-4 py-1.5 text-sm font-bold rounded-lg transition-all ${schemeTab === 'eligible' ? 'bg-white dark:bg-slate-800 text-emerald-600 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                          >
                            Eligible Matches
                          </button>
                          <button
                            onClick={() => setSchemeTab('ineligible')}
                            className={`px-4 py-1.5 text-sm font-bold rounded-lg transition-all ${schemeTab === 'ineligible' ? 'bg-white dark:bg-slate-800 text-rose-600 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                          >
                            Explore Other Schemes
                          </button>
                          <button
                            onClick={() => setSchemeTab('monitored')}
                            className={`px-4 py-1.5 text-sm font-bold rounded-lg transition-all ${schemeTab === 'monitored' ? 'bg-white dark:bg-slate-800 text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                          >
                            Latest Portal Updates
                          </button>
                          <button
                            onClick={() => setSchemeTab('risk_alerts')}
                            className={`px-4 py-1.5 text-sm font-bold rounded-lg transition-all ${schemeTab === 'risk_alerts' ? 'bg-white dark:bg-slate-800 text-amber-600 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                          >
                            Risk Alerts
                          </button>
                        </div>
                      </div>

                      <div className="space-y-4">
                        {schemeTab === 'eligible' && (
                          farmer.recommended_bundles && farmer.recommended_bundles.length > 0 ? (
                            farmer.recommended_bundles.map((bundle: any, i: number) => (
                              <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.1 }}
                                key={`bundle-${bundle.bundle_id}`}
                                className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm p-6 rounded-3xl border-2 border-emerald-100 dark:border-emerald-900/50 shadow-md flex flex-col gap-4 overflow-hidden relative"
                              >
                                {i === 0 && <div className="absolute top-0 right-0 bg-emerald-500 text-white text-[10px] font-bold px-3 py-1 rounded-bl-xl uppercase tracking-wider">Top Recommended Bundle</div>}

                                <div className="flex items-center justify-between border-b border-emerald-50 dark:border-slate-800 pb-4">
                                  <div>
                                    <h4 className="font-black text-emerald-900 dark:text-emerald-400 text-xl flex items-center gap-2">Package {i + 1}</h4>
                                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-emerald-500" /> {bundle.graph_explanation}</p>
                                  </div>
                                  <div className="text-right shrink-0 ml-4">
                                    <div className="text-[10px] uppercase text-slate-400 font-bold tracking-widest leading-none mb-1">Total Benefit</div>
                                    <Badge className="bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-400 border-none text-sm px-3 py-1 font-black">
                                      {bundle.total_benefit}
                                    </Badge>
                                  </div>
                                </div>

                                <div className="flex flex-col gap-4 mt-4">
                                  {bundle.schemes.map((scheme: any, idx: number) => (
                                    <div key={`s-${idx}`} className="bg-white/50 dark:bg-slate-900/50 p-5 rounded-2xl border border-emerald-100 dark:border-emerald-900/50 shadow-sm flex flex-col md:flex-row md:items-start justify-between group hover:border-emerald-500 transition-all gap-4">
                                      <div className="flex items-start gap-4 flex-1">
                                        <div className="bg-emerald-50 dark:bg-emerald-950/50 p-3 rounded-xl text-emerald-600 dark:text-emerald-400 font-bold group-hover:bg-emerald-600 group-hover:text-white transition-colors shrink-0">
                                          {scheme.scheme_id.toString().slice(0, 3).toUpperCase()}
                                        </div>
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2 mb-2">
                                            <h4 className="font-bold text-slate-900 dark:text-white text-lg">{scheme.scheme_name}</h4>
                                            <Badge variant="outline" className="text-[10px] h-5 bg-emerald-50/50 text-emerald-600 border-emerald-200">
                                              {Math.round((scheme.success_probability || 0) * 100)}% Match
                                            </Badge>
                                          </div>
                                          <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1 mt-2 bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                                            <p className="font-semibold text-emerald-700 dark:text-emerald-500 mb-1">Why you were selected:</p>
                                            {Array.isArray(scheme.explanation) ? scheme.explanation.map((reason: string, rIdx: number) => (
                                              <p key={rIdx} className="flex items-start gap-2"><CheckCircle2 className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" /> {reason}</p>
                                            )) : <p className="flex items-start gap-2"><CheckCircle2 className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" /> {scheme.explanation}</p>}
                                          </div>

                                          {scheme.predicted_financial_value > 0 && (
                                            <div className="mt-3">
                                              <div className="bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/50 p-3 flex justify-between items-center rounded-t-xl">
                                                <div className="flex items-center gap-2">
                                                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                                                  <span className="text-xs font-bold text-slate-600 dark:text-slate-400">Predicted Impact:</span>
                                                  <span className="text-sm font-black text-emerald-700 dark:text-emerald-400">
                                                    ₹{scheme.predicted_financial_value.toLocaleString()}
                                                  </span>
                                                </div>
                                                <Badge variant="secondary" className="text-[10px] bg-white border-slate-200 text-emerald-700">
                                                  {scheme.benefit_type}
                                                </Badge>
                                              </div>
                                              <div className="bg-slate-50 dark:bg-slate-900 text-[10px] text-slate-500 mt-0 italic px-3 py-2 border border-t-0 border-emerald-100 dark:border-emerald-900/50 rounded-b-xl leading-tight">
                                                ★ {scheme.prediction_explanation}
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                      <Button variant="ghost" className="rounded-full text-slate-600 dark:text-slate-300 md:group-hover:bg-emerald-600 md:group-hover:text-white transition-all self-end md:self-center shrink-0">
                                        {t('dashboard.apply')} <ChevronRight className="ml-1 h-4 w-4" />
                                      </Button>
                                    </div>
                                  ))}
                                </div>
                              </motion.div>
                            ))
                          ) : farmer.recommended_schemes && farmer.recommended_schemes.length > 0 ? (
                            // Fallback: show individual schemes if bundles is empty
                            farmer.recommended_schemes.map((scheme: any, i: number) => (
                              <motion.div
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.1 }}
                                key={scheme.scheme_id}
                                className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm p-5 rounded-2xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between group hover:border-emerald-500 dark:hover:border-emerald-500 transition-all cursor-pointer hover:shadow-md"
                              >
                                <div className="flex items-center gap-4">
                                  <div className="bg-emerald-50 dark:bg-emerald-950/50 p-3 rounded-xl text-emerald-600 dark:text-emerald-400 font-bold group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                                    {scheme.scheme_id.toString().slice(0, 3).toUpperCase()}
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      <h4 className="font-bold text-slate-900 dark:text-white">{scheme.scheme_name}</h4>
                                      <Badge variant="outline" className="text-[10px] h-5 bg-emerald-50/50 text-emerald-600 border-emerald-200">
                                        {Math.round(scheme.success_probability * 100)}% Match
                                      </Badge>
                                    </div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">{scheme.explanation}</p>
                                    {scheme.predicted_financial_value > 0 && (
                                      <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 font-semibold">₹{scheme.predicted_financial_value?.toLocaleString()} — {scheme.benefit_type}</p>
                                    )}
                                  </div>
                                </div>
                                <Button variant="ghost" className="rounded-full text-slate-600 dark:text-slate-300 group-hover:bg-emerald-600 group-hover:text-white transition-all">
                                  {t('dashboard.apply')} <ChevronRight className="ml-1 h-4 w-4" />
                                </Button>
                              </motion.div>
                            ))
                          ) : (
                            <div className="text-center py-10 bg-slate-100/50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800">
                              <p className="text-slate-500 dark:text-slate-400 italic">No recommended schemes found. Complete your profile for better matches.</p>
                            </div>
                          )
                        )}

                        {schemeTab === 'ineligible' && (
                          farmer.ineligible_schemes && farmer.ineligible_schemes.length > 0 ? (
                            farmer.ineligible_schemes.map((scheme: any, i: number) => (
                              <motion.div
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.1 }}
                                key={`inelig-${scheme.scheme_id}`}
                                className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-start justify-between opacity-80 hover:opacity-100 transition-all gap-4"
                              >
                                <div className="flex items-start gap-4 flex-1">
                                  <div className="bg-slate-100 dark:bg-slate-800 p-3 rounded-xl text-slate-500 dark:text-slate-400 font-bold shrink-0">
                                    {scheme.scheme_id.toString().slice(0, 3).toUpperCase()}
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-2">
                                      <h4 className="font-bold text-slate-700 dark:text-slate-300 text-lg">{scheme.scheme_name}</h4>
                                      <Badge variant="outline" className="text-[10px] h-5 bg-rose-50 dark:bg-rose-950/30 text-rose-600 border-rose-200 dark:border-rose-900 font-medium">
                                        Not Eligible
                                      </Badge>
                                    </div>
                                    <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1 mt-2 bg-rose-50/50 dark:bg-rose-950/10 p-3 rounded-lg border border-rose-100 dark:border-rose-900/30">
                                      <p className="font-semibold text-rose-700 dark:text-rose-400 mb-1">Missing Requirements:</p>
                                      {Array.isArray(scheme.explanation) ? scheme.explanation.map((reason: string, idx: number) => (
                                        <p key={idx} className="flex items-start gap-2"><XCircle className="w-4 h-4 mt-0.5 text-rose-500 shrink-0" /> {reason}</p>
                                      )) : <p>{scheme.explanation}</p>}
                                    </div>
                                  </div>
                                </div>
                              </motion.div>
                            ))
                          ) : (
                            <div className="text-center py-10 bg-slate-100/50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800">
                              <p className="text-slate-500 dark:text-slate-400 italic">No ineligible schemes found. You qualify for everything we have!</p>
                            </div>
                          )
                        )}

                        {schemeTab === 'monitored' && (
                          <div className="space-y-4">
                            <div className="flex justify-between items-center bg-blue-50/50 dark:bg-blue-900/10 p-4 rounded-xl border border-blue-100 dark:border-blue-900/30">
                              <p className="text-sm text-blue-800 dark:text-blue-300 font-medium flex items-center gap-2">
                                <Info className="h-4 w-4" /> Proactive monitoring is active on government portals.
                              </p>
                              <Button
                                variant="outline"
                                size="sm"
                                className="border-blue-200 text-blue-700 hover:bg-blue-100"
                                onClick={async () => {
                                  toast.loading("Checking portals in background...");
                                  try {
                                    await api.post('/monitoring/refresh-schemes');
                                    await fetchMonitoredSchemes();
                                    toast.dismiss();
                                    toast.success("Refresh complete. Portals checked.");
                                  } catch (err) {
                                    toast.dismiss();
                                    toast.error("Failed to check portals");
                                  }
                                }}
                              >
                                Refresh Now
                              </Button>
                            </div>

                            {monitoredSchemes.length > 0 ? (
                              monitoredSchemes.map((scheme: any, i: number) => (
                                <motion.div
                                  initial={{ opacity: 0, x: 20 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: i * 0.1 }}
                                  key={`monitored-${scheme.id}`}
                                  className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm p-5 rounded-2xl border border-blue-100 dark:border-blue-900/30 shadow-sm flex flex-col md:flex-row md:items-start justify-between opacity-90 hover:opacity-100 transition-all gap-4"
                                >
                                  <div className="flex items-start gap-4 flex-1">
                                    <div className="bg-blue-50 dark:bg-blue-900/30 p-3 rounded-xl text-blue-600 dark:text-blue-400 font-bold shrink-0">
                                      <Globe className="h-5 w-5" />
                                    </div>
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-2">
                                        <h4 className="font-bold text-slate-800 dark:text-slate-200 text-lg">{scheme.title}</h4>
                                        <Badge variant="outline" className={`text-[10px] h-5 font-medium ${scheme.status === 'New' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-blue-50 text-blue-600 border-blue-200'}`}>
                                          {scheme.status}
                                        </Badge>
                                      </div>
                                      <div className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                        Source: <span className="font-medium text-slate-700 dark:text-slate-300">{scheme.source}</span>
                                      </div>
                                    </div>
                                  </div>
                                  <Button
                                    variant="ghost"
                                    className="rounded-full text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-all self-end md:self-center shrink-0"
                                    onClick={() => setSelectedScheme(scheme)}
                                  >
                                    View Details <ChevronRight className="ml-1 h-4 w-4" />
                                  </Button>
                                </motion.div>
                              ))
                            ) : (
                              <div className="text-center py-10 bg-slate-100/50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800">
                                <p className="text-slate-500 dark:text-slate-400 italic">No new scheme updates found.</p>
                              </div>
                            )}
                          </div>
                        )}

                        {schemeTab === 'risk_alerts' && (
                          <div className="space-y-4">
                            {farmer.predictive_alerts && farmer.predictive_alerts.length > 0 ? (
                              farmer.predictive_alerts.map((alert: any, idx: number) => {
                                const isHigh = alert.severity === 'high' || alert.severity === 'critical';
                                const isMedium = alert.severity === 'medium';

                                const bgClass = isHigh ? 'bg-rose-50 dark:bg-rose-950/30' :
                                  isMedium ? 'bg-amber-50 dark:bg-amber-950/30' :
                                    'bg-blue-50 dark:bg-blue-950/30';
                                const borderClass = isHigh ? 'border-rose-200 dark:border-rose-900/50' :
                                  isMedium ? 'border-amber-200 dark:border-amber-900/50' :
                                    'border-blue-200 dark:border-blue-900/50';
                                const textClass = isHigh ? 'text-rose-700 dark:text-rose-400' :
                                  isMedium ? 'text-amber-700 dark:text-amber-400' :
                                    'text-blue-700 dark:text-blue-400';
                                const Icon = isHigh ? AlertCircle : isMedium ? AlertTriangle : Info;

                                return (
                                  <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                    key={`alert-tab-${idx}`}
                                    className={`p-5 rounded-2xl border ${bgClass} ${borderClass} flex flex-col md:flex-row gap-4 items-start shadow-sm`}
                                  >
                                    <div className={`p-3 rounded-xl bg-white/50 dark:bg-slate-900/50 shrink-0 ${textClass}`}>
                                      <Icon className="h-6 w-6" />
                                    </div>
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-2">
                                        <h4 className={`font-bold text-lg ${textClass}`}>{alert.alert_type.replace('_', ' ').toUpperCase()}</h4>
                                        <Badge variant="outline" className={`text-[10px] h-5 uppercase border-current ${textClass}`}>
                                          {alert.severity}
                                        </Badge>
                                      </div>
                                      <p className="text-slate-600 dark:text-slate-300 text-sm mb-3 leading-relaxed">
                                        {alert.message}
                                      </p>
                                      {alert.recommended_action && (
                                        <div className="bg-white/60 dark:bg-slate-900/60 p-3 rounded-lg border border-white/20 dark:border-slate-800/50 flex items-start gap-2">
                                          <CheckCircle2 className="h-4 w-4 mt-0.5 text-emerald-500 shrink-0" />
                                          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                                            Action Recommended: <span className="font-normal text-slate-600 dark:text-slate-400">{alert.recommended_action}</span>
                                          </span>
                                        </div>
                                      )}
                                    </div>
                                  </motion.div>
                                )
                              })
                            ) : (
                              <div className="text-center py-10 bg-slate-100/50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800">
                                <p className="text-slate-500 dark:text-slate-400 italic">No active risk alerts for your farm at the moment.</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                </motion.div>
              )}


              {activeTab === 'profile' && (
                <motion.div
                  key="profile"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.4 }}
                  className="space-y-6 pb-12"
                >
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 gap-4">
                    <div>
                      <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">{t('dashboard.profile_title')}</h1>
                      <p className="text-slate-500 dark:text-slate-400">{t('dashboard.profile_desc')}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <LanguageSwitcher />
                      <Button onClick={handleProfileUpdate} className="bg-emerald-600 hover:bg-emerald-500 text-white w-full md:w-auto shadow-lg shadow-emerald-600/20" disabled={saving}>
                        {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        {t('dashboard.save_all')}
                      </Button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                    <Card className="border border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2 text-slate-900 dark:text-white"><User className="h-5 w-5 text-emerald-600 dark:text-emerald-500" /> {t('dashboard.personal_contact')}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300">{t('auth.name')}</Label>
                          <Input value={formData.full_name} disabled className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-500" />
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300">{t('auth.email')}</Label>
                          <Input value={formData.email} disabled className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-500" />
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                            {t('form.phone')}
                                                        {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('phone_number')} className={`p-1 rounded-full transition-colors ${listeningField === 'phone_number' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                          </Label>
                          <Input value={formData.phone_number} onChange={e => setFormData({ ...formData, phone_number: e.target.value })} placeholder="+91..." className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                              {t('form.age')}
                                                            {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('age')} className={`p-1 rounded-full transition-colors ${listeningField === 'age' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                            </Label>
                            <Input type="number" value={formData.age} onChange={e => setFormData({ ...formData, age: e.target.value })} className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                          </div>
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.gender')}</Label>
                            <Select value={formData.gender} onValueChange={v => setFormData({ ...formData, gender: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Male">{t('form.male')}</SelectItem>
                                <SelectItem value="Female">{t('form.female')}</SelectItem>
                                <SelectItem value="Other">{t('form.other')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.category')}</Label>
                            <Select value={formData.category} onValueChange={v => setFormData({ ...formData, category: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('form.category')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="General">{t('form.general')}</SelectItem>
                                <SelectItem value="OBC">{t('form.obc')}</SelectItem>
                                <SelectItem value="SC">{t('form.sc')}</SelectItem>
                                <SelectItem value="ST">{t('form.st')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.diff_abled')}</Label>
                            <Select value={formData.is_differently_abled} onValueChange={v => setFormData({ ...formData, is_differently_abled: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="true">{t('form.yes')}</SelectItem>
                                <SelectItem value="false">{t('form.no')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="border border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2 text-slate-900 dark:text-white"><MapPin className="h-5 w-5 text-emerald-600 dark:text-emerald-500" /> {t('dashboard.location_edu')}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                            {t('form.state')}
                                                        {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('state')} className={`p-1 rounded-full transition-colors ${listeningField === 'state' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                          </Label>
                          <Input value={formData.state} onChange={e => setFormData({ ...formData, state: e.target.value })} placeholder={t('form.state_placeholder')} className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                            {t('form.district')}
                                                        {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('district')} className={`p-1 rounded-full transition-colors ${listeningField === 'district' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                          </Label>
                          <Input value={formData.district} onChange={e => setFormData({ ...formData, district: e.target.value })} placeholder={t('form.district_placeholder')} className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                            {t('form.pincode')}
                                                        {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('pincode')} className={`p-1 rounded-full transition-colors ${listeningField === 'pincode' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                          </Label>
                          <Input value={formData.pincode} onChange={e => setFormData({ ...formData, pincode: e.target.value })} className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                        </div>
                        <div className="grid gap-2">
                          <Label className="flex items-center gap-2 text-slate-700 dark:text-slate-300"><GraduationCap className="h-4 w-4" /> {t('form.qualification')}</Label>
                          <Select value={formData.highest_qualification} onValueChange={v => setFormData({ ...formData, highest_qualification: v })}>
                            <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="None">{t('form.edu_none')}</SelectItem>
                              <SelectItem value="Primary">{t('form.edu_primary')}</SelectItem>
                              <SelectItem value="Secondary">{t('form.edu_secondary')}</SelectItem>
                              <SelectItem value="Higher Secondary">{t('form.edu_higher')}</SelectItem>
                              <SelectItem value="Graduate">{t('form.edu_grad')}</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="border border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2 text-slate-900 dark:text-white"><CreditCard className="h-5 w-5 text-emerald-600 dark:text-emerald-500" /> {t('dashboard.identity_fin')}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid gap-2">
                          <Label className="flex items-center justify-between text-slate-700 dark:text-slate-300">
                            <div className="flex items-center gap-2">
                              {t('form.aadhar')}
                              {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('aadhar_number')} className={`p-1 rounded-full transition-colors ${listeningField === 'aadhar_number' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                            </div>
                            {farmer.is_aadhar_verified ? (
                              <Badge variant="outline" className="text-[10px] h-5 bg-emerald-50 text-emerald-600 border-emerald-200">
                                {t('dashboard.verified')}
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[10px] h-5 bg-amber-50 text-amber-600 border-amber-200">
                                {t('dashboard.unverified')}
                              </Badge>
                            )}
                          </Label>
                          <Input
                            value={formData.aadhar_number}
                            onChange={e => {
                              const val = e.target.value.replace(/\D/g, '').slice(0, 12);
                              setFormData({ ...formData, aadhar_number: val });
                            }}
                            placeholder="0000 0000 0000"
                            className={`bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white ${formData.aadhar_number?.length > 0 && formData.aadhar_number.length !== 12 ? 'border-amber-500 focus-visible:ring-amber-500' : ''}`}
                          />
                        </div>
                        <div className="grid gap-2 mt-4">
                          <Label className="flex items-center justify-between text-slate-700 dark:text-slate-300">
                            <div className="flex items-center gap-2">
                              {t('form.pan')}
                              {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('pan_number')} className={`p-1 rounded-full transition-colors ${listeningField === 'pan_number' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                            </div>
                            {farmer.is_pan_verified ? (
                              <Badge variant="outline" className="text-[10px] h-5 bg-emerald-50 text-emerald-600 border-emerald-200">
                                {t('dashboard.verified')}
                              </Badge>
                            ) : formData.pan_number?.length === 10 && /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(formData.pan_number) ? (
                              <Badge variant="outline" className="text-[10px] h-5 bg-amber-50 text-amber-600 border-amber-200">
                                {t('dashboard.unverified')}
                              </Badge>
                            ) : null}
                          </Label>
                          <Input
                            value={formData.pan_number}
                            onChange={e => {
                              const val = e.target.value.toUpperCase().slice(0, 10);
                              setFormData({ ...formData, pan_number: val });
                            }}
                            placeholder="ABCDE1234F"
                            className={`uppercase bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white ${formData.pan_number?.length > 0 && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(formData.pan_number) ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                          />
                          {formData.pan_number?.length > 0 && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(formData.pan_number) && (
                            <p className="text-[10px] text-red-500 mt-[-4px]">Invalid PAN format</p>
                          )}
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                            {t('form.income')}
                                                        {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('annual_income')} className={`p-1 rounded-full transition-colors ${listeningField === 'annual_income' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                          </Label>
                          <Input type="number" value={formData.annual_income} onChange={e => setFormData({ ...formData, annual_income: e.target.value })} placeholder="e.g. 150000" className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300">{t('form.bank_linked')}</Label>
                          <Select value={formData.bank_account_linked} onValueChange={v => setFormData({ ...formData, bank_account_linked: v })}>
                            <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="true">{t('form.yes')}</SelectItem>
                              <SelectItem value="false">{t('form.no')}</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="border border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2 text-slate-900 dark:text-white"><Tractor className="h-5 w-5 text-emerald-600 dark:text-emerald-500" /> {t('dashboard.agri_details')}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                              {t('form.land_size')}
                                                            {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('land_size_hectares')} className={`p-1 rounded-full transition-colors ${listeningField === 'land_size_hectares' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                            </Label>
                            <Input type="number" step="0.01" value={formData.land_size_hectares} onChange={e => setFormData({ ...formData, land_size_hectares: e.target.value })} className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white" />
                          </div>
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.farmer_type')}</Label>
                            <Select value={formData.farmer_type} onValueChange={v => setFormData({ ...formData, farmer_type: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Marginal">{t('form.type_marginal')}</SelectItem>
                                <SelectItem value="Small">{t('form.type_small')}</SelectItem>
                                <SelectItem value="Semi-Medium">{t('form.type_semimedium')}</SelectItem>
                                <SelectItem value="Medium">{t('form.type_medium')}</SelectItem>
                                <SelectItem value="Large">{t('form.type_large')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.irrigation')}</Label>
                            <Select value={formData.irrigation_type} onValueChange={v => setFormData({ ...formData, irrigation_type: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Rainfed">{t('form.irr_rainfed')}</SelectItem>
                                <SelectItem value="Canal">{t('form.irr_canal')}</SelectItem>
                                <SelectItem value="Borewell">{t('form.irr_borewell')}</SelectItem>
                                <SelectItem value="Drip">{t('form.irr_drip')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.soil_type')}</Label>
                            <Select value={formData.soil_type} onValueChange={v => setFormData({ ...formData, soil_type: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Alluvial">{t('form.soil_alluvial')}</SelectItem>
                                <SelectItem value="Black">{t('form.soil_black')}</SelectItem>
                                <SelectItem value="Red">{t('form.soil_red')}</SelectItem>
                                <SelectItem value="Laterite">{t('form.soil_laterite')}</SelectItem>
                                <SelectItem value="Desert">{t('form.soil_desert')}</SelectItem>
                                <SelectItem value="Mountain">{t('form.soil_mountain')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.crop_season')}</Label>
                            <Select value={formData.crop_season} onValueChange={v => setFormData({ ...formData, crop_season: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Kharif">{t('form.season_kharif')}</SelectItem>
                                <SelectItem value="Rabi">{t('form.season_rabi')}</SelectItem>
                                <SelectItem value="Zaid">{t('form.season_zaid')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="grid gap-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.water_source')}</Label>
                            <Select value={formData.water_source} onValueChange={v => setFormData({ ...formData, water_source: v })}>
                              <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Well">{t('form.water_well')}</SelectItem>
                                <SelectItem value="Canal">{t('form.water_canal')}</SelectItem>
                                <SelectItem value="Rain">{t('form.water_rain')}</SelectItem>
                                <SelectItem value="River">{t('form.water_river')}</SelectItem>
                                <SelectItem value="Borewell">{t('form.water_borewell')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300">{t('form.land_ownership')}</Label>
                          <Select value={formData.land_ownership} onValueChange={v => setFormData({ ...formData, land_ownership: v })}>
                            <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 focus-visible:ring-emerald-500 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Owned">{t('form.own_owned')}</SelectItem>
                              <SelectItem value="Leased">{t('form.own_leased')}</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="grid gap-2">
                          <Label className="text-slate-700 dark:text-slate-300 flex items-center justify-between">
                            {t('form.crops')}
                                                        {voiceSupported !== undefined && <button type="button" onClick={() => startVoice('primary_crops')} className={`p-1 rounded-full transition-colors ${listeningField === 'primary_crops' ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-emerald-600'}`} title="Voice input"><Mic className="h-3.5 w-3.5" /></button>}
                          </Label>
                          <textarea
                            className="flex min-h-[80px] w-full rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-white focus-visible:ring-2 focus-visible:ring-emerald-500 outline-none"
                            placeholder={t('form.crops_placeholder') || "Wheat, Rice... "}
                            value={formData.primary_crops}
                            onChange={e => setFormData({ ...formData, primary_crops: e.target.value })}
                          />
                        </div>

                        {/* ML Crop Recommender UI */}
                        <div className="col-span-1 md:col-span-2 mt-4 bg-emerald-50/50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 p-4 rounded-xl flex flex-col md:flex-row items-center justify-between gap-4">
                          <div className="flex-1">
                            <h4 className="font-bold text-emerald-800 dark:text-emerald-400 flex items-center gap-2">
                              <Sprout className="h-4 w-4" /> AI Crop Recommender
                            </h4>
                            <p className="text-sm text-emerald-600 dark:text-emerald-500 mt-1">
                              Not sure what to plant next? Get an AI-driven suggestion based on your soil and local climate data.
                            </p>
                          </div>
                          <Button 
                            variant="secondary"
                            onClick={async (e) => {
                              e.preventDefault();
                              toast.loading("Analyzing soil & weather data...");
                              try {
                                const res = await api.post('/farmers/recommend-crop', formData);
                                toast.dismiss();
                                if (res.data && res.data.recommended_crop) {
                                  toast.success(`Recommended Crop: ${res.data.recommended_crop.toUpperCase()}`, { duration: 5000 });
                                  // Optionally auto-fill the field
                                  if (!formData.primary_crops.toLowerCase().includes(res.data.recommended_crop.toLowerCase())) {
                                    setFormData(prev => ({
                                      ...prev,
                                      primary_crops: prev.primary_crops ? `${prev.primary_crops}, ${res.data.recommended_crop}` : res.data.recommended_crop
                                    }));
                                  }
                                }
                              } catch (err) {
                                toast.dismiss();
                                toast.error("Failed to fetch recommendation");
                              }
                            }}
                            className="bg-emerald-100 hover:bg-emerald-200 text-emerald-800 dark:bg-emerald-800 dark:hover:bg-emerald-700 dark:text-emerald-100 font-bold shrink-0 shadow-sm"
                          >
                            <TrendingUp className="mr-2 h-4 w-4" /> Get Suggestion
                          </Button>
                        </div>


                      </CardContent>
                    </Card>

                    <Card className="shadow-sm md:col-span-2 border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm border-t-4 border-t-emerald-500 dark:border-t-emerald-500">
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2 text-slate-900 dark:text-white">
                          <UploadCloud className="h-5 w-5 text-emerald-600 dark:text-emerald-500" />
                          {t('dashboard.doc_center')}
                        </CardTitle>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                          {t('dashboard.doc_desc')}
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="flex flex-col md:flex-row gap-4 items-end bg-slate-50 dark:bg-slate-950/50 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
                          <div className="flex-1 w-full space-y-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.doc_type')}</Label>
                            <Select value={uploadType} onValueChange={setUploadType}>
                              <SelectTrigger className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Aadhar">{t('form.doc_aadhar')}</SelectItem>
                                <SelectItem value="PAN">{t('form.doc_pan')}</SelectItem>
                                <SelectItem value="Land_Record">{t('form.doc_land')}</SelectItem>
                                <SelectItem value="Bank_Passbook">{t('form.doc_bank')}</SelectItem>
                                <SelectItem value="Policy_Document" className="text-violet-600 font-bold dark:text-violet-400">Policy Document (Admin Test)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex-1 w-full space-y-2">
                            <Label className="text-slate-700 dark:text-slate-300">{t('form.select_file')}</Label>
                            <Input
                              id="document-upload"
                              type="file"
                              className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white cursor-pointer file:text-emerald-600 dark:file:text-emerald-400"
                              accept="image/*,.pdf"
                              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                            />
                          </div>
                          <Button
                            onClick={handleDocumentUpload}
                            disabled={!selectedFile || uploadingDoc}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white w-full md:w-auto shadow-md"
                          >
                            {uploadingDoc ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UploadCloud className="h-4 w-4 mr-2" />}
                            {t('form.upload_btn')}
                          </Button>
                        </div>

                        <div>
                          <Label className="mb-3 block text-slate-700 dark:text-slate-300 font-bold">{t('form.verified_docs')}</Label>
                          {farmer?.documents_uploaded?.length > 0 ? (
                            <div className="flex flex-wrap gap-3">
                              {farmer.documents_uploaded.map((docString: string, idx: number) => {
                                const docName = typeof docString === 'string' ? docString.split(':')[0] : 'Document';
                                return (
                                  <Badge key={idx} variant="outline" className="px-4 py-2 flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/50 text-emerald-800 dark:text-emerald-400 text-sm">
                                    <FileText className="h-4 w-4" />
                                    {docName.replace('_', ' ')}
                                  </Badge>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="text-sm text-slate-400 dark:text-slate-500 italic bg-white dark:bg-slate-900 border border-dashed border-slate-200 dark:border-slate-800 p-4 rounded-lg text-center">
                              {t('form.no_docs')}
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>

                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Scheme Details Dialog Moved Outside AnimatePresence to Prevent Multiple Children Warning */}
            <Dialog open={!!selectedScheme} onOpenChange={(open: boolean) => !open && setSelectedScheme(null)}>
              <DialogContent className="sm:max-w-[600px] bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800">
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold flex items-center gap-2 text-slate-900 dark:text-white">
                    <Globe className="h-5 w-5 text-blue-500" />
                    {selectedScheme?.title}
                  </DialogTitle>
                  <DialogDescription className="text-slate-500 dark:text-slate-400 flex items-center gap-2 pt-2">
                    <Badge variant="secondary" className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 pointer-events-none">
                      {selectedScheme?.status}
                    </Badge>
                    <span>Source: {selectedScheme?.source}</span>
                    <span className="text-xs">{selectedScheme?.date_found}</span>
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4 space-y-4">
                  <div>
                    <h4 className="font-semibold text-slate-900 dark:text-white mb-2">Description</h4>
                    <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
                      {selectedScheme?.description || "No description provided."}
                    </p>
                  </div>
                  {selectedScheme?.insights && selectedScheme.insights.length > 0 && (
                    <div className="bg-blue-50/50 dark:bg-blue-900/10 p-4 rounded-xl border border-blue-100 dark:border-blue-900/30">
                      <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-2 flex items-center gap-2">
                        <Info className="h-4 w-4" /> Key Insights
                      </h4>
                      <ul className="list-disc pl-5 text-sm text-blue-800 dark:text-blue-400 space-y-1">
                        {selectedScheme.insights.map((insight: string, idx: number) => (
                          <li key={idx}>{insight}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {selectedScheme?.url && selectedScheme.url !== "#" && (
                    <Button
                      className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white"
                      onClick={() => {
                        const url = selectedScheme.url.startsWith('http') ? selectedScheme.url : `https://${selectedScheme.url}`;
                        window.open(url, '_blank', 'noopener,noreferrer');
                      }}
                    >
                      Visit Official Portal <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  )}
                </div>
              </DialogContent>
            </Dialog>

          </div>
        </main >
      </div >
    );
  }