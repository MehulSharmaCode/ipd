import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { toast } from 'sonner';
import { Loader2, CheckCircle, Upload, Tractor, User, ShieldCheck, Sparkles, AlertCircle } from 'lucide-react';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { useTranslationText } from '@/hooks/useTranslationText';
import { Badge } from '@/components/ui/badge';
import { motion, AnimatePresence } from 'framer-motion';

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────
interface OcrSuggestions {
  full_name_ocr_suggestion?: string;
  gender?: string;
  age?: number;
  dob?: string;
  aadhar_number?: string;
  pan_number?: string;
}

interface UploadStatus {
  loading: boolean;
  verified: boolean;
  confidence: number;
  warnings: string[];
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────
export default function ProfileWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [profileSaving, setProfileSaving] = useState(false);
  const { t } = useTranslationText();

  const [uploadStatus, setUploadStatus] = useState<Record<string, UploadStatus>>({
    aadhar: { loading: false, verified: false, confidence: 0, warnings: [] },
    pan:    { loading: false, verified: false, confidence: 0, warnings: [] },
  });

  const [profile, setProfile] = useState({
    full_name: '',
    email: '',
    phone_number: '',
    age: '',
    gender: '',
    category: '',
    state: '',
    district: '',
    annual_income: '',
    irrigation_type: '',
    land_size_hectares: '',
    farmer_type: '',
    soil_type: '',
    crop_season: '',
    water_source: '',
    land_ownership: '',
    primary_crops: '',
    is_aadhar_verified: false,
    is_pan_verified: false,
    aadhar_number: '',
    pan_number: '',
  });

  // ── Load existing profile on mount ──────────────────────────
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/farmers/me');
        const d = res.data;
        setProfile((prev: any) => ({
          ...prev,
          ...d,
          age: d.age?.toString() || '',
          annual_income: d.annual_income?.toString() || '',
          land_size_hectares: d.land_size_hectares?.toString() || '',
          primary_crops: d.primary_crops?.join(', ') || '',
        }));
        setUploadStatus(prev => ({
          ...prev,
          aadhar: { ...prev.aadhar, verified: d.is_aadhar_verified || false },
          pan:    { ...prev.pan,    verified: d.is_pan_verified    || false },
        }));
        // If both documents are already verified, skip to Step 2
        if (d.is_aadhar_verified && d.is_pan_verified) {
          setStep(2);
        }
      } catch {
        // Non-fatal — new user may not have a profile yet
      }
    };
    fetchProfile();
  }, []);

  // ── OCR-powered document upload ──────────────────────────────
  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    docType: 'aadhar' | 'pan',
  ) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];

    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);

    setUploadStatus(prev => ({
      ...prev,
      [docType]: { ...prev[docType], loading: true, warnings: [] },
    }));
    toast.info('🔍 Scanning document with OCR…');

    try {
      const res = await api.post('/upload', formData);
      const data = res.data;

      const isValid: boolean = data.validation?.valid === true;
      const warnings: string[] = data.validation?.warnings || [];
      const confidence: number = data.confidence || 0;
      const suggestions: OcrSuggestions = data.profileSuggestions || {};
      const fields = data.fields || {};

      // ── Auto-fill profile fields from OCR suggestions ──────
      setProfile(prev => {
        const updates: any = { ...prev };

        // Prefer OCR name only if user hasn't filled it
        if (suggestions.full_name_ocr_suggestion && !prev.full_name) {
          updates.full_name = suggestions.full_name_ocr_suggestion;
        }
        if (suggestions.gender && !prev.gender) {
          updates.gender = suggestions.gender;
        }
        if (suggestions.age && !prev.age) {
          updates.age = String(suggestions.age);
        }
        if (docType === 'aadhar' && fields.aadhaarNumber) {
          updates.aadhar_number = fields.aadhaarNumber;
          updates.is_aadhar_verified = isValid;
        }
        if (docType === 'pan' && fields.panNumber) {
          updates.pan_number = fields.panNumber;
          updates.is_pan_verified = isValid;
        }

        return updates;
      });

      // ── Update upload card status ──────────────────────────
      setUploadStatus(prev => ({
        ...prev,
        [docType]: { loading: false, verified: true, confidence, warnings },
      }));

      if (isValid) {
        toast.success(`✅ ${docType === 'aadhar' ? 'Aadhaar' : 'PAN'} verified! Fields auto-filled.`);
      } else {
        toast.warning(
          warnings.length > 0
            ? `⚠️ Uploaded — ${warnings[0]}`
            : '⚠️ Document uploaded. Some fields may need manual review.',
        );
        // Still mark as "uploaded" even if not perfectly verified
        setUploadStatus(prev => ({
          ...prev,
          [docType]: { ...prev[docType], verified: true },
        }));
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Upload failed. Please try again.';
      toast.error(`❌ ${detail}`);
      setUploadStatus(prev => ({
        ...prev,
        [docType]: { ...prev[docType], loading: false, verified: false },
      }));
    }
  };

  // ── Save personal + agricultural details ────────────────────
  const saveDetails = async () => {
    setProfileSaving(true);
    try {
      const payload = {
        ...profile,
        age: parseInt(profile.age) || null,
        annual_income: parseFloat(profile.annual_income) || 0,
        land_size_hectares: parseFloat(profile.land_size_hectares) || null,
        primary_crops: profile.primary_crops
          .split(',')
          .map((c: string) => c.trim())
          .filter((c: string) => c !== ''),
        profile_wizard_complete: true,   // ← marks wizard as done
      };
      await api.put('/farmers/me', payload);
      toast.success(t('wizard.toast_success'));
      setStep(step + 1);
    } catch {
      toast.error(t('wizard.toast_fail'));
    } finally {
      setProfileSaving(false);
    }
  };

  const isKYCComplete = uploadStatus.aadhar.verified && uploadStatus.pan.verified;
  const totalSteps = 4;
  const progressPct = ((step - 1) / (totalSteps - 1)) * 100;

  // ─────────────────────────────────────────────────────────────
  // Render helpers
  // ─────────────────────────────────────────────────────────────

  const DocumentUploadCard = ({
    docKey,
    label,
    description,
    icon,
  }: {
    docKey: 'aadhar' | 'pan';
    label: string;
    description: string;
    icon: React.ReactNode;
  }) => {
    const status = uploadStatus[docKey];
    const isVerified = status.verified;
    const isLoading = status.loading;

    return (
      <div
        className={`p-6 border-2 rounded-2xl transition-all duration-300 ${
          isVerified
            ? 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-500'
            : 'bg-slate-50 dark:bg-slate-800/30 border-slate-200 dark:border-slate-800'
        }`}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={`p-3 rounded-xl ${
                isVerified
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-500'
              }`}
            >
              {icon}
            </div>
            <div>
              <h4 className="font-bold text-slate-900 dark:text-white text-lg">{label}</h4>
              <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
            </div>
          </div>
          {isVerified && !isLoading ? (
            <Badge className="bg-emerald-500 text-white h-8 px-3 text-xs rounded-lg flex gap-1 items-center shrink-0">
              <CheckCircle className="h-3.5 w-3.5" />
              {status.confidence > 0 ? `${Math.round(status.confidence)}%` : 'Uploaded'}
            </Badge>
          ) : isLoading ? (
            <Loader2 className="animate-spin h-6 w-6 text-emerald-600 shrink-0" />
          ) : null}
        </div>

        {/* OCR warnings */}
        {isVerified && status.warnings.length > 0 && (
          <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl flex gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{status.warnings[0]}</span>
          </div>
        )}

        {/* Upload zone */}
        {!isVerified && !isLoading && (
          <div className="relative group mt-2">
            <input
              type="file"
              accept="image/*,application/pdf"
              className="cursor-pointer h-14 opacity-0 absolute inset-0 z-10 w-full"
              onChange={e => handleFileUpload(e, docKey)}
            />
            <div className="w-full h-14 border-dashed border-2 border-slate-300 dark:border-slate-600 rounded-xl flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400 group-hover:border-emerald-500 group-hover:text-emerald-600 group-hover:bg-emerald-50 dark:group-hover:bg-emerald-900/10 transition-all font-semibold">
              <Upload className="h-4 w-4" />
              Click or drag file here (JPG, PNG, PDF)
            </div>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="mt-2 flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400 font-medium">
            <Loader2 className="animate-spin h-4 w-4 text-emerald-600" />
            Running OCR analysis…
          </div>
        )}
      </div>
    );
  };

  // ─────────────────────────────────────────────────────────────
  // Main Render
  // ─────────────────────────────────────────────────────────────
  const stepLabels = [
    t('wizard.step_verification') || 'Identity',
    t('wizard.step_personal') || 'Personal Details',
    t('wizard.step_farm') || 'Farm Details',
    t('common.success') || 'Complete',
  ];

  const stepIcons = [
    <ShieldCheck className="h-7 w-7" />,
    <User className="h-7 w-7" />,
    <Tractor className="h-7 w-7" />,
    <CheckCircle className="h-7 w-7" />,
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 py-12 px-4 transition-colors duration-300">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* ── Progress Header ── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">
              Step {step} of {totalSteps}
            </span>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {stepLabels[step - 1]}
            </span>
          </div>
          <Progress
            value={progressPct}
            className="h-2.5 bg-emerald-100 dark:bg-emerald-900/30 rounded-full"
          />
          {/* Step indicators */}
          <div className="flex gap-2">
            {stepLabels.map((label, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    idx + 1 < step
                      ? 'bg-emerald-500 text-white'
                      : idx + 1 === step
                      ? 'bg-emerald-600 text-white ring-4 ring-emerald-300/40'
                      : 'bg-slate-200 dark:bg-slate-700 text-slate-400'
                  }`}
                >
                  {idx + 1 < step ? <CheckCircle className="h-4 w-4" /> : idx + 1}
                </div>
                <span className="text-[10px] text-slate-400 hidden sm:block truncate">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Main Card ── */}
        <Card className="shadow-2xl border-none bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl overflow-hidden">
          <CardHeader className="bg-emerald-600 dark:bg-emerald-700 text-white p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-emerald-500/20">
            <div>
              <CardTitle className="text-2xl font-black flex items-center gap-3">
                {stepIcons[step - 1]}
                {step === 4 ? 'Setup Complete!' : t('wizard.title')}
              </CardTitle>
              <CardDescription className="text-emerald-100 mt-1 font-medium">
                {step === 1 && 'Upload your Aadhaar & PAN — we\'ll auto-fill your details'}
                {step === 2 && t('wizard.subtitle')}
                {step === 3 && 'Tell us about your farm'}
                {step === 4 && 'Your profile is ready for AI scheme matching'}
              </CardDescription>
            </div>
            <div className="bg-white/10 backdrop-blur-md p-1 rounded-xl border border-white/20">
              <LanguageSwitcher />
            </div>
          </CardHeader>

          <CardContent className="p-8">
            <AnimatePresence mode="wait">

              {/* ══ STEP 1: IDENTITY VERIFICATION (OCR UPLOAD) ══════════════════ */}
              {step === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  {/* OCR info banner */}
                  <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-2xl text-sm">
                    <Sparkles className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-blue-800 dark:text-blue-300">AI-Powered Auto-Fill</p>
                      <p className="text-blue-600 dark:text-blue-400 mt-0.5">
                        Upload your documents and our OCR engine will automatically
                        extract your name, DOB, gender, and ID numbers — saving you time.
                        You can review and edit everything before saving.
                      </p>
                    </div>
                  </div>

                  <DocumentUploadCard
                    docKey="aadhar"
                    label={t('form.doc_aadhar') || 'Aadhaar Card'}
                    description="12-digit UIDAI Government ID"
                    icon={<ShieldCheck className="h-5 w-5" />}
                  />

                  <DocumentUploadCard
                    docKey="pan"
                    label={t('form.doc_pan') || 'PAN Card'}
                    description="Income Tax Department ID"
                    icon={<Upload className="h-5 w-5" />}
                  />

                  <Button
                    className={`w-full h-14 text-lg font-bold rounded-xl transition-all shadow-lg ${
                      isKYCComplete
                        ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 hover:scale-[1.01]'
                        : 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                    }`}
                    disabled={!isKYCComplete}
                    onClick={() => setStep(2)}
                  >
                    {isKYCComplete ? (
                      <>Continue to Personal Details <CheckCircle className="ml-2 h-5 w-5" /></>
                    ) : (
                      'Upload both documents to continue'
                    )}
                  </Button>
                </motion.div>
              )}

              {/* ══ STEP 2: PERSONAL DETAILS (OCR PRE-FILLED) ════════════════ */}
              {step === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  {/* OCR pre-fill notice */}
                  {(profile.full_name || profile.gender || profile.age) && (
                    <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800 rounded-xl text-sm text-emerald-700 dark:text-emerald-400">
                      <Sparkles className="h-4 w-4 shrink-0" />
                      <span>Fields pre-filled from your documents. Please review and edit if needed.</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.phone') || 'Phone Number'}</Label>
                      <Input
                        className="h-12"
                        placeholder="+91 …"
                        value={profile.phone_number}
                        onChange={e => setProfile({ ...profile, phone_number: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.age') || 'Age'}</Label>
                      <Input
                        className="h-12"
                        type="number"
                        value={profile.age}
                        onChange={e => setProfile({ ...profile, age: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.income') || 'Annual Income (₹)'}</Label>
                      <Input
                        className="h-12"
                        type="number"
                        placeholder="e.g. 150000"
                        value={profile.annual_income}
                        onChange={e => setProfile({ ...profile, annual_income: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.state') || 'State'}</Label>
                      <Input
                        className="h-12"
                        placeholder={t('form.state_placeholder') || 'e.g. Maharashtra'}
                        value={profile.state}
                        onChange={e => setProfile({ ...profile, state: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.district') || 'District'}</Label>
                      <Input
                        className="h-12"
                        placeholder={t('form.district_placeholder') || 'e.g. Pune'}
                        value={profile.district}
                        onChange={e => setProfile({ ...profile, district: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.gender') || 'Gender'}</Label>
                      <Select
                        value={profile.gender}
                        onValueChange={v => setProfile({ ...profile, gender: v })}
                      >
                        <SelectTrigger className="h-12">
                          <SelectValue placeholder={t('common.select') || 'Select'} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Male">{t('form.male') || 'Male'}</SelectItem>
                          <SelectItem value="Female">{t('form.female') || 'Female'}</SelectItem>
                          <SelectItem value="Other">{t('form.other') || 'Other'}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex gap-4 pt-2">
                    <Button variant="outline" className="h-12 px-6 font-bold border-2 rounded-xl" onClick={() => setStep(1)}>
                      {t('wizard.back') || 'Back'}
                    </Button>
                    <Button
                      className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-600/20"
                      onClick={() => setStep(3)}
                    >
                      Next: Farm Details
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* ══ STEP 3: AGRICULTURAL DATA ════════════════════════════════ */}
              {step === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.land_size') || 'Land Size (Hectares)'}</Label>
                      <Input
                        className="h-12"
                        type="number"
                        step="0.1"
                        value={profile.land_size_hectares}
                        onChange={e => setProfile({ ...profile, land_size_hectares: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.soil_type') || 'Soil Type'}</Label>
                      <Select value={profile.soil_type} onValueChange={v => setProfile({ ...profile, soil_type: v })}>
                        <SelectTrigger className="h-12"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Alluvial">{t('form.soil_alluvial') || 'Alluvial'}</SelectItem>
                          <SelectItem value="Black">{t('form.soil_black') || 'Black'}</SelectItem>
                          <SelectItem value="Red">{t('form.soil_red') || 'Red'}</SelectItem>
                          <SelectItem value="Laterite">{t('form.soil_laterite') || 'Laterite'}</SelectItem>
                          <SelectItem value="Desert">{t('form.soil_desert') || 'Desert'}</SelectItem>
                          <SelectItem value="Mountain">{t('form.soil_mountain') || 'Mountain'}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.crop_season') || 'Crop Season'}</Label>
                      <Select value={profile.crop_season} onValueChange={v => setProfile({ ...profile, crop_season: v })}>
                        <SelectTrigger className="h-12"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Kharif">{t('form.season_kharif') || 'Kharif'}</SelectItem>
                          <SelectItem value="Rabi">{t('form.season_rabi') || 'Rabi'}</SelectItem>
                          <SelectItem value="Zaid">{t('form.season_zaid') || 'Zaid'}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="font-bold">{t('form.water_source') || 'Water Source'}</Label>
                      <Select value={profile.water_source} onValueChange={v => setProfile({ ...profile, water_source: v })}>
                        <SelectTrigger className="h-12"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Well">{t('form.water_well') || 'Well'}</SelectItem>
                          <SelectItem value="Canal">{t('form.water_canal') || 'Canal'}</SelectItem>
                          <SelectItem value="Rain">{t('form.water_rain') || 'Rainwater'}</SelectItem>
                          <SelectItem value="River">{t('form.water_river') || 'River'}</SelectItem>
                          <SelectItem value="Borewell">{t('form.water_borewell') || 'Borewell'}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="font-bold">{t('form.crops') || 'Primary Crops'}</Label>
                    <Input
                      className="h-12"
                      placeholder={t('form.crops_placeholder') || 'Wheat, Rice, Sugarcane…'}
                      value={profile.primary_crops}
                      onChange={e => setProfile({ ...profile, primary_crops: e.target.value })}
                    />
                  </div>

                  <div className="flex gap-4 pt-2">
                    <Button variant="outline" className="h-12 px-6 font-bold border-2 rounded-xl" onClick={() => setStep(2)}>
                      {t('wizard.back') || 'Back'}
                    </Button>
                    <Button
                      className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-600/20"
                      onClick={saveDetails}
                      disabled={profileSaving}
                    >
                      {profileSaving ? <Loader2 className="animate-spin" /> : t('wizard.save_continue') || 'Save & Finish'}
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* ══ STEP 4: SUCCESS ═══════════════════════════════════════════ */}
              {step === 4 && (
                <motion.div
                  key="step4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4 }}
                  className="space-y-8 text-center py-4"
                >
                  <div className="relative">
                    <div className="absolute inset-0 bg-emerald-400/20 rounded-full blur-3xl scale-150" />
                    <CheckCircle className="h-28 w-28 text-emerald-500 mx-auto relative drop-shadow-xl" />
                  </div>
                  <div className="space-y-3">
                    <h3 className="text-4xl font-black text-slate-900 dark:text-white">Setup Complete!</h3>
                    <p className="text-lg text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                      Your verified farmer profile is ready. Our AI is scanning
                      1,200+ government schemes tailored specifically for you.
                    </p>
                  </div>
                  <Button
                    className="w-full h-14 bg-emerald-600 hover:bg-emerald-500 text-white text-xl font-bold rounded-2xl shadow-xl shadow-emerald-600/30 hover:scale-[1.02] transition-all"
                    onClick={() => navigate('/dashboard?from=setup')}
                  >
                    View My Scheme Matches
                    <CheckCircle className="ml-3 h-6 w-6" />
                  </Button>
                </motion.div>
              )}

            </AnimatePresence>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}