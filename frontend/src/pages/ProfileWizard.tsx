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
import { Loader2, CheckCircle, Upload, Tractor, User, ShieldCheck, AlertCircle, FileText } from 'lucide-react';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { useTranslationText } from '@/hooks/useTranslationText';
import { Badge } from '@/components/ui/badge';
import { motion, AnimatePresence } from 'framer-motion';

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

interface UploadStatus {
  loading: boolean;
  verified: boolean;
  confidence: number;
  warnings: string[];
}

/**
 * Standardised shape of a single extracted field from the backend.
 * ExtractionResult.fields[name] = { value, source_document, confidence }
 */
interface ExtractedField {
  value: string | number | string[] | null;
  source_document: string;
  confidence: number;
}

/**
 * Agricultural fields extracted from a 7/12 land record by Gemini.
 * Stored separately from the profile so the UI can show an "AI Extracted"
 * indicator on any field that was populated by the AI engine.
 */
interface SatbaraExtraction {
  owner_name?: string;
  survey_number?: string;
  village?: string;
  land_area?: string;
  irrigation?: string;
  soil_type?: string;
  season?: string;
  current_crop?: string;
  ownership_type?: string;
  district?: string;
  taluka?: string;
  gat_number?: string;
  /** Names of every profile field populated by this extraction */
  filledFields: string[];
}

// ─────────────────────────────────────────────────────────────
// Map UI doc-key → backend doc_type key
// Adding a future document type only requires one entry here.
// ─────────────────────────────────────────────────────────────
const DOC_TYPE_MAP: Record<string, string> = {
  aadhar:  'aadhar',
  pan:     'pan',
  satbara: '7_12',
};

// ─────────────────────────────────────────────────────────────
// Centralized ExtractionResult → Profile Mapping
//
// This is the single source of truth for how backend extraction
// fields map to the frontend profile state. No other part of the
// component should parse the raw API response fields directly.
// ─────────────────────────────────────────────────────────────

interface ProfileState {
  full_name: string;
  email: string;
  phone_number: string;
  age: string;
  gender: string;
  category: string;
  state: string;
  district: string;
  taluka: string;
  village: string;
  annual_income: string;
  irrigation_type: string;
  land_size_hectares: string;
  farmer_type: string;
  soil_type: string;
  crop_season: string;
  water_source: string;
  land_ownership: string;
  primary_crops: string;
  is_aadhar_verified: boolean;
  is_pan_verified: boolean;
  is_7_12_verified: boolean;
  aadhar_number: string;
  pan_number: string;
}

function fieldValue(fields: Record<string, ExtractedField>, key: string): string {
  const f = fields[key];
  if (!f || f.value === null || f.value === undefined) return '';
  if (Array.isArray(f.value)) return f.value.join(', ');
  return String(f.value);
}

/**
 * Maps an ExtractionResult.fields object into a partial ProfileState update.
 * Returns { profileUpdates, ocrSuggestions, satbaraExtraction } depending on doc_type.
 */
function mapExtractionToProfile(
  docKey: string,
  backendDocType: string,
  fields: Record<string, ExtractedField>,
  isValid: boolean,
): {
  profileUpdates: Partial<ProfileState>;
  satbaraExtraction: SatbaraExtraction | null;
} {
  const profileUpdates: Partial<ProfileState> = {};
  let satbaraExtraction: SatbaraExtraction | null = null;

  if (backendDocType === 'aadhar') {
    // Aadhaar OCR: read top-level suggestion keys returned by AadhaarProcessor
    const nameVal = fieldValue(fields, 'full_name');
    if (nameVal) profileUpdates.full_name = nameVal;

    const genderVal = fieldValue(fields, 'gender');
    if (genderVal) {
      // Normalize to title case (e.g. MALE -> Male)
      profileUpdates.gender = genderVal.charAt(0).toUpperCase() + genderVal.slice(1).toLowerCase();
    }

    const birthYearVal = fieldValue(fields, 'birth_year');
    const dobVal = fieldValue(fields, 'dob');
    if (birthYearVal) {
      const year = parseInt(birthYearVal.replace(/[^\d]/g, ''), 10);
      if (!isNaN(year) && year > 1900 && year <= new Date().getFullYear()) {
        profileUpdates.age = String(new Date().getFullYear() - year);
      }
    } else if (dobVal) {
      const yearMatch = dobVal.match(/\b(19\d\d|20\d\d)\b/);
      if (yearMatch) {
        const year = parseInt(yearMatch[1], 10);
        if (!isNaN(year) && year <= new Date().getFullYear()) {
          profileUpdates.age = String(new Date().getFullYear() - year);
        }
      }
    }

    const aadhaarNo = fieldValue(fields, 'aadhar_number');
    if (aadhaarNo) {
      profileUpdates.aadhar_number = aadhaarNo;
      profileUpdates.is_aadhar_verified = isValid;
    }
  } else if (backendDocType === 'pan') {
    const nameVal = fieldValue(fields, 'full_name');
    if (nameVal) profileUpdates.full_name = nameVal;

    const panNo = fieldValue(fields, 'pan_number');
    if (panNo) {
      profileUpdates.pan_number = panNo;
      profileUpdates.is_pan_verified = isValid;
    }
  } else if (backendDocType === '7_12') {
    // Gemini Satbara extraction — map all agricultural fields
    const filledFields: string[] = [];

    const landArea = fieldValue(fields, 'land_area');
    if (landArea) {
      // Parse numeric part from strings like "2.5 Hectare" or "2.5"
      const numeric = parseFloat(landArea.replace(/[^\d.]/g, ''));
      if (!isNaN(numeric)) {
        profileUpdates.land_size_hectares = String(numeric);
        filledFields.push('land_size_hectares');
      }
    }

    const irrigation = fieldValue(fields, 'irrigation');
    if (irrigation) {
      profileUpdates.irrigation_type = irrigation;
      filledFields.push('irrigation_type');
    }

    const soilType = fieldValue(fields, 'soil_type');
    if (soilType) {
      profileUpdates.soil_type = soilType;
      filledFields.push('soil_type');
    }

    const season = fieldValue(fields, 'season');
    if (season) {
      profileUpdates.crop_season = season;
      filledFields.push('crop_season');
    }

    const currentCrop = fieldValue(fields, 'current_crop');
    if (currentCrop) {
      profileUpdates.primary_crops = currentCrop;
      filledFields.push('primary_crops');
    }

    const ownershipType = fieldValue(fields, 'ownership_type');
    if (ownershipType) {
      profileUpdates.land_ownership = ownershipType;
      filledFields.push('land_ownership');
    }

    // District/village/taluka from 7/12 only fill the profile if currently empty
    // (enforced by the apply-only-if-blank loop in handleFileUpload).
    const districtVal = fieldValue(fields, 'district');
    const villageVal = fieldValue(fields, 'village');
    const talukaVal = fieldValue(fields, 'taluka');

    satbaraExtraction = {
      owner_name:     fieldValue(fields, 'owner_name') || undefined,
      survey_number:  fieldValue(fields, 'survey_number') || undefined,
      village:        villageVal || undefined,
      land_area:      landArea || undefined,
      irrigation:     irrigation || undefined,
      soil_type:      soilType || undefined,
      season:         season || undefined,
      current_crop:   currentCrop || undefined,
      ownership_type: ownershipType || undefined,
      district:       districtVal || undefined,
      taluka:         talukaVal || undefined,
      gat_number:     fieldValue(fields, 'gat_number') || undefined,
      filledFields,
    };

    if (districtVal) {
      profileUpdates.district = districtVal;
    }
    if (villageVal) {
      profileUpdates.village = villageVal;
      filledFields.push('village');
    }
    if (talukaVal) {
      profileUpdates.taluka = talukaVal;
      filledFields.push('taluka');
    }
  }

  return { profileUpdates, satbaraExtraction };
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
    aadhar:  { loading: false, verified: false, confidence: 0, warnings: [] },
    pan:     { loading: false, verified: false, confidence: 0, warnings: [] },
    satbara: { loading: false, verified: false, confidence: 0, warnings: [] },
  });

  /**
   * Stores agricultural fields extracted from the 7/12.
   * Null means no 7/12 was uploaded; used to control "AI Extracted" badges.
   */
  const [satbaraExtraction, setSatbaraExtraction] = useState<SatbaraExtraction | null>(null);

  /** Tracks which profile fields were populated by the AI (for UI badges). */
  const [aiFilledFields, setAiFilledFields] = useState<Set<string>>(new Set());

  const [profile, setProfile] = useState<ProfileState>({
    full_name: '',
    email: '',
    phone_number: '',
    age: '',
    gender: '',
    category: '',
    state: '',
    district: '',
    taluka: '',
    village: '',
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
    is_7_12_verified: false,
    aadhar_number: '',
    pan_number: '',
  });

  // ── Load existing profile on mount ──────────────────────────
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/farmers/me');
        const d = res.data;
        setProfile((prev) => ({
          ...prev,
          ...d,
          age: d.age?.toString() || '',
          annual_income: d.annual_income?.toString() || '',
          land_size_hectares: d.land_size_hectares?.toString() || '',
          primary_crops: Array.isArray(d.primary_crops) ? d.primary_crops.join(', ') : d.primary_crops || '',
        }));
        setUploadStatus((prev) => ({
          ...prev,
          aadhar: { ...prev.aadhar, verified: d.is_aadhar_verified || false },
          pan:    { ...prev.pan,    verified: d.is_pan_verified    || false },
          satbara:{ ...prev.satbara,verified: d.is_7_12_verified   || false },
        }));
        // If Aadhaar and PAN are already verified, skip to 7/12 upload
        if (d.is_aadhar_verified && d.is_pan_verified) {
          setStep(2);
        }
      } catch {
        // Non-fatal — new user may not have a profile yet
      }
    };
    fetchProfile();
  }, []);

  // ── Unified upload handler ────────────────────────────────────
  /**
   * Single handler for ALL document types: aadhar, pan, satbara (7_12).
   * Behaviour is determined by docKey. Adding a new document type only
   * requires registering it in DOC_TYPE_MAP and handling the response in
   * mapExtractionToProfile().
   */
  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    docKey: 'aadhar' | 'pan' | 'satbara',
  ) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    const backendDocType = DOC_TYPE_MAP[docKey];

    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', backendDocType);

    setUploadStatus((prev) => ({
      ...prev,
      [docKey]: { ...prev[docKey], loading: true, warnings: [] },
    }));

    const loadingMsg =
      docKey === 'satbara'
        ? t('wizard.analyzing_land_record') || 'Analyzing land record. This may take a few seconds.'
        : t('wizard.scanning_document') || 'Scanning document...';
    toast.info(loadingMsg);

    try {
      const res = await api.post('/upload', formData);
      const data = res.data;

      const isValid: boolean = data.validation?.valid === true;
      const warnings: string[] = data.validation?.warnings || [];
      const confidence: number =
        typeof data.fields === 'object' && data.fields !== null
          ? Math.round(
              Object.values(data.fields as Record<string, ExtractedField>)
                .reduce((sum, f) => sum + (f.confidence || 0), 0) /
                Math.max(Object.values(data.fields as Record<string, ExtractedField>).length, 1) *
                100,
            )
          : 0;

      const fields: Record<string, ExtractedField> = data.fields || {};

      // ── Centralized mapping ────────────────────────────────
      const { profileUpdates, satbaraExtraction: extracted } = mapExtractionToProfile(
        docKey,
        backendDocType,
        fields,
        isValid,
      );

      // ── Apply profile updates ──────────────────────────────
      setProfile((prev) => {
        const next = { ...prev };
        for (const [key, value] of Object.entries(profileUpdates)) {
          const k = key as keyof ProfileState;
          // For location fields from 7/12, only fill if currently blank
          if ((k === 'district' || k === 'village' || k === 'taluka') && prev[k]) continue;
          // For name/gender from OCR, only fill if currently blank
          if ((k === 'full_name' || k === 'gender') && prev[k]) continue;
          (next as any)[k] = value;
        }
        return next;
      });

      // ── Handle 7/12 specific state ─────────────────────────
      if (extracted) {
        setSatbaraExtraction(extracted);
        setAiFilledFields(new Set(extracted.filledFields));
      }

      // ── Upload card status ─────────────────────────────────
      setUploadStatus((prev) => ({
        ...prev,
        [docKey]: { loading: false, verified: true, confidence, warnings },
      }));

      // ── Toast ──────────────────────────────────────────────
      if (docKey === 'satbara') {
        const count = extracted?.filledFields.length ?? 0;
        if (isValid) {
          toast.success(
            count > 0
              ? `Land record analyzed. ${count} agricultural fields extracted.`
              : 'Land record uploaded. Review extracted details on the next screen.',
          );
        } else if (warnings.length > 0) {
          toast.warning(`Land record processed with warnings: ${warnings[0]}`);
        } else {
          toast.info('Land record received. Some fields may need manual entry.');
        }
      } else {
        const label = docKey === 'aadhar' ? 'Aadhaar' : 'PAN';
        if (isValid) {
          toast.success(`${label} verified. Fields have been auto-filled.`);
        } else {
          toast.warning(
            warnings.length > 0
              ? `${label} uploaded with warnings: ${warnings[0]}`
              : `${label} uploaded. Some fields may need manual review.`,
          );
          // Still mark as uploaded even if not perfectly valid
          setUploadStatus((prev) => ({
            ...prev,
            [docKey]: { ...prev[docKey], verified: true },
          }));
        }
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Upload failed. Please try again.';
      toast.error(detail);
      setUploadStatus((prev) => ({
        ...prev,
        [docKey]: { ...prev[docKey], loading: false, verified: false },
      }));
    }
  };

  // ── Save personal + agricultural details ────────────────────
  const saveDetails = async () => {
    setProfileSaving(true);
    try {
      // Build payload — strip empty strings so we never overwrite
      // backend-persisted fields with blank values.
      const raw: Record<string, any> = {
        ...profile,
        age: parseInt(profile.age) || null,
        annual_income: parseFloat(profile.annual_income) || 0,
        land_size_hectares: parseFloat(profile.land_size_hectares) || null,
        primary_crops: profile.primary_crops
          .split(',')
          .map((c: string) => c.trim())
          .filter((c: string) => c !== ''),
        profile_wizard_complete: true,
      };

      // Remove keys with empty-string values (keep 0, false, null, arrays)
      const payload: Record<string, any> = {};
      for (const [key, value] of Object.entries(raw)) {
        if (value === '') continue;
        payload[key] = value;
      }

      await api.put('/farmers/me', payload);
      toast.success(t('wizard.toast_success') || 'Profile saved successfully.');
      setStep(step + 1);
    } catch {
      toast.error(t('wizard.toast_fail') || 'Failed to save profile. Please try again.');
    } finally {
      setProfileSaving(false);
    }
  };

  const isKYCComplete = uploadStatus.aadhar.verified && uploadStatus.pan.verified;

  // ─────────────────────────────────────────────────────────────
  // Step configuration
  // Adding a new step only requires adding to these arrays.
  // ─────────────────────────────────────────────────────────────
  const stepLabels = [
    t('wizard.step_verification') || 'Identity Verification',
    t('wizard.step_land_record')  || 'Land Record',
    t('wizard.step_profile')      || 'Profile Review',
    t('common.success')           || 'Complete',
  ];

  const stepIcons = [
    <ShieldCheck className="h-7 w-7" />,
    <FileText    className="h-7 w-7" />,
    <User        className="h-7 w-7" />,
    <CheckCircle className="h-7 w-7" />,
  ];

  const totalSteps = stepLabels.length;
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
    docKey: 'aadhar' | 'pan' | 'satbara';
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
              {status.confidence > 0 ? `${status.confidence}%` : 'Uploaded'}
            </Badge>
          ) : isLoading ? (
            <Loader2 className="animate-spin h-6 w-6 text-emerald-600 shrink-0" />
          ) : null}
        </div>

        {/* Warnings */}
        {isVerified && status.warnings.length > 0 && (
          <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl flex gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{status.warnings[0]}</span>
          </div>
        )}

        {/* Satbara extraction summary */}
        {docKey === 'satbara' && isVerified && satbaraExtraction && !isLoading && (
          <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-xl text-sm space-y-1">
            <p className="font-semibold text-blue-800 dark:text-blue-300 text-xs uppercase tracking-wide mb-2">
              Extracted Information
            </p>
            {satbaraExtraction.owner_name && (
              <div className="flex justify-between text-slate-700 dark:text-slate-300">
                <span className="text-slate-500">Owner</span>
                <span className="font-medium">{satbaraExtraction.owner_name}</span>
              </div>
            )}
            {satbaraExtraction.survey_number && (
              <div className="flex justify-between text-slate-700 dark:text-slate-300">
                <span className="text-slate-500">Survey No.</span>
                <span className="font-medium">{satbaraExtraction.survey_number}</span>
              </div>
            )}
            {satbaraExtraction.village && (
              <div className="flex justify-between text-slate-700 dark:text-slate-300">
                <span className="text-slate-500">Village</span>
                <span className="font-medium">{satbaraExtraction.village}</span>
              </div>
            )}
            {satbaraExtraction.land_area && (
              <div className="flex justify-between text-slate-700 dark:text-slate-300">
                <span className="text-slate-500">Land Area</span>
                <span className="font-medium">{satbaraExtraction.land_area}</span>
              </div>
            )}
            {satbaraExtraction.filledFields.length > 0 && (
              <p className="text-blue-600 dark:text-blue-400 text-xs pt-2 border-t border-blue-200 dark:border-blue-800 mt-2">
                {satbaraExtraction.filledFields.length} agricultural fields extracted.
                Review on the next screen.
              </p>
            )}
          </div>
        )}

        {/* Upload zone (shown when not verified and not loading) */}
        {!isVerified && !isLoading && (
          <div className="relative group mt-2">
            <input
              type="file"
              accept="image/*,application/pdf"
              className="cursor-pointer h-14 opacity-0 absolute inset-0 z-10 w-full"
              onChange={(e) => handleFileUpload(e, docKey)}
            />
            <div className="w-full h-14 border-dashed border-2 border-slate-300 dark:border-slate-600 rounded-xl flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400 group-hover:border-emerald-500 group-hover:text-emerald-600 group-hover:bg-emerald-50 dark:group-hover:bg-emerald-900/10 transition-all font-semibold">
              <Upload className="h-4 w-4" />
              Click or drag file here (JPG, PNG, PDF)
            </div>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="mt-2 space-y-2">
            <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400 font-medium">
              <Loader2 className="animate-spin h-4 w-4 text-emerald-600" />
              {docKey === 'satbara'
                ? 'Analyzing land record. This may take a few seconds.'
                : 'Scanning document...'}
            </div>
            {/* Animated progress bar for Gemini (longer process) */}
            {docKey === 'satbara' && (
              <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full animate-pulse w-2/3" />
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // ─────────────────────────────────────────────────────────────
  // AI Extracted field label helper
  // ─────────────────────────────────────────────────────────────
  const AiExtractedBadge = ({ fieldKey }: { fieldKey: string }) =>
    aiFilledFields.has(fieldKey) ? (
      <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-700 rounded px-1.5 py-0.5">
        AI Extracted
      </span>
    ) : null;

  // ─────────────────────────────────────────────────────────────
  // Main Render
  // ─────────────────────────────────────────────────────────────

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
                {step === totalSteps ? 'Setup Complete' : t('wizard.title') || 'Complete Your Farmer Profile'}
              </CardTitle>
              <CardDescription className="text-emerald-100 mt-1 font-medium">
                {step === 1 && 'Upload your Aadhaar and PAN — identity details will be auto-filled.'}
                {step === 2 && 'Upload your 7/12 land record for automatic agricultural data extraction.'}
                {step === 3 && 'Review your complete profile. AI-extracted fields are labelled below.'}
                {step === 4 && 'Your profile is ready for AI-powered scheme matching.'}
              </CardDescription>
            </div>
            <div className="bg-white/10 backdrop-blur-md p-1 rounded-xl border border-white/20">
              <LanguageSwitcher />
            </div>
          </CardHeader>

          <CardContent className="p-8">
            <AnimatePresence mode="wait">

              {/* ══ STEP 1: IDENTITY VERIFICATION ══════════════════════════════ */}
              {step === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  {/* Info banner */}
                  <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-2xl text-sm">
                    <ShieldCheck className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-blue-800 dark:text-blue-300">AI-Powered Auto-Fill</p>
                      <p className="text-blue-600 dark:text-blue-400 mt-0.5">
                        Upload your documents and our system will automatically extract your name,
                        date of birth, gender, and ID numbers. You can review and edit all fields
                        before saving.
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

                  <DocumentUploadCard
                    docKey="satbara"
                    label="Satbara (7/12) Land Record"
                    description="Maharashtra Land Ownership Extract"
                    icon={<Tractor className="h-5 w-5" />}
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
                      <>Continue to Land Record <CheckCircle className="ml-2 h-5 w-5" /></>
                    ) : (
                      'Upload both documents to continue'
                    )}
                  </Button>
                </motion.div>
              )}

              {/* ══ STEP 2: LAND RECORD UPLOAD (7/12) ═══════════════════════ */}
              {step === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  {/* Info banner */}
                  <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-2xl text-sm">
                    <FileText className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-blue-800 dark:text-blue-300">
                        Intelligent Land Record Analysis
                      </p>
                      <p className="text-blue-600 dark:text-blue-400 mt-0.5">
                        Upload your Maharashtra 7/12 Satbara extract. Our AI engine will extract
                        land area, crops, irrigation type, soil type, and other agricultural details
                        automatically. You can review and edit all extracted fields before saving.
                      </p>
                      <p className="text-blue-500 dark:text-blue-500 mt-1.5 text-xs">
                        This step is optional. You can skip and enter farm details manually.
                      </p>
                    </div>
                  </div>

                  <DocumentUploadCard
                    docKey="satbara"
                    label={t('form.doc_land') || 'Land Record (7/12)'}
                    description="Maharashtra Satbara Extract"
                    icon={<FileText className="h-5 w-5" />}
                  />

                  <div className="flex gap-4 pt-2">
                    <Button
                      variant="outline"
                      className="h-12 px-6 font-bold border-2 rounded-xl"
                      onClick={() => setStep(1)}
                    >
                      {t('wizard.back') || 'Back'}
                    </Button>
                    {/* Skip button — always available */}
                    <Button
                      variant="outline"
                      className="h-12 px-6 font-bold border-2 rounded-xl border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400"
                      onClick={() => setStep(3)}
                      disabled={uploadStatus.satbara.loading}
                    >
                      Skip — Enter manually
                    </Button>
                    {/* Continue button — only prominent once uploaded */}
                    <Button
                      className={`flex-1 h-12 font-bold rounded-xl shadow-lg transition-all ${
                        uploadStatus.satbara.verified
                          ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                      }`}
                      disabled={!uploadStatus.satbara.verified || uploadStatus.satbara.loading}
                      onClick={() => setStep(3)}
                    >
                      Continue to Profile Review
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* ══ STEP 3: UNIFIED PROFILE REVIEW ═══════════════════════════ */}
              {step === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  {/* Pre-fill notice */}
                  {(profile.full_name || profile.gender || profile.age || (satbaraExtraction && satbaraExtraction.filledFields.length > 0)) && (
                    <div className="flex items-start gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800 rounded-xl text-sm text-emerald-700 dark:text-emerald-400">
                      <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
                      <span>
                        Fields have been pre-filled from your uploaded documents.
                        Fields labelled <strong>AI Extracted</strong> came from your land record.
                        Please review and edit if needed before saving.
                      </span>
                    </div>
                  )}

                  {/* ── Personal Details Section ──────────────────────────── */}
                  <div>
                    <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-4 flex items-center gap-2">
                      <User className="h-5 w-5" /> Personal Details
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label className="font-bold">{t('form.phone') || 'Phone Number'}</Label>
                        <Input
                          className="h-12"
                          placeholder="+91 …"
                          value={profile.phone_number}
                          onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold">{t('form.age') || 'Age'}</Label>
                        <Input
                          className="h-12"
                          type="number"
                          value={profile.age}
                          onChange={(e) => setProfile({ ...profile, age: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold">{t('form.income') || 'Annual Income (₹)'}</Label>
                        <Input
                          className="h-12"
                          type="number"
                          placeholder="e.g. 150000"
                          value={profile.annual_income}
                          onChange={(e) => setProfile({ ...profile, annual_income: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold">{t('form.state') || 'State'}</Label>
                        <Input
                          className="h-12"
                          placeholder={t('form.state_placeholder') || 'e.g. Maharashtra'}
                          value={profile.state}
                          onChange={(e) => setProfile({ ...profile, state: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold">{t('form.district') || 'District'}</Label>
                        <Input
                          className="h-12"
                          placeholder={t('form.district_placeholder') || 'e.g. Pune'}
                          value={profile.district}
                          onChange={(e) => setProfile({ ...profile, district: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold">{t('form.gender') || 'Gender'}</Label>
                        <Select
                          value={profile.gender}
                          onValueChange={(v) => setProfile({ ...profile, gender: v })}
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
                  </div>

                  {/* ── Farm Details Section ──────────────────────────────── */}
                  <div>
                    <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-4 flex items-center gap-2">
                      <Tractor className="h-5 w-5" /> Farm Details
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label className="font-bold flex items-center">
                          {t('form.land_size') || 'Land Size (Hectares)'}
                          <AiExtractedBadge fieldKey="land_size_hectares" />
                        </Label>
                        <Input
                          className="h-12"
                          type="number"
                          step="0.1"
                          value={profile.land_size_hectares}
                          onChange={(e) => setProfile({ ...profile, land_size_hectares: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold flex items-center">
                          {t('form.soil_type') || 'Soil Type'}
                          <AiExtractedBadge fieldKey="soil_type" />
                        </Label>
                        <Select
                          value={profile.soil_type}
                          onValueChange={(v) => setProfile({ ...profile, soil_type: v })}
                        >
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
                        <Label className="font-bold flex items-center">
                          {t('form.crop_season') || 'Crop Season'}
                          <AiExtractedBadge fieldKey="crop_season" />
                        </Label>
                        <Select
                          value={profile.crop_season}
                          onValueChange={(v) => setProfile({ ...profile, crop_season: v })}
                        >
                          <SelectTrigger className="h-12"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Kharif">{t('form.season_kharif') || 'Kharif'}</SelectItem>
                            <SelectItem value="Rabi">{t('form.season_rabi') || 'Rabi'}</SelectItem>
                            <SelectItem value="Zaid">{t('form.season_zaid') || 'Zaid'}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold flex items-center">
                          {t('form.water_source') || 'Water Source'}
                          <AiExtractedBadge fieldKey="irrigation_type" />
                        </Label>
                        <Select
                          value={profile.irrigation_type}
                          onValueChange={(v) => setProfile({ ...profile, irrigation_type: v })}
                        >
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

                      <div className="space-y-2">
                        <Label className="font-bold flex items-center">
                          Land Ownership
                          <AiExtractedBadge fieldKey="land_ownership" />
                        </Label>
                        <Select
                          value={profile.land_ownership}
                          onValueChange={(v) => setProfile({ ...profile, land_ownership: v })}
                        >
                          <SelectTrigger className="h-12"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Owned">Owned</SelectItem>
                            <SelectItem value="Leased">Leased</SelectItem>
                            <SelectItem value="Shared">Shared</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label className="font-bold">Farmer Type</Label>
                        <Select
                          value={profile.farmer_type}
                          onValueChange={(v) => setProfile({ ...profile, farmer_type: v })}
                        >
                          <SelectTrigger className="h-12"><SelectValue placeholder={t('common.select')} /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Marginal">Marginal (&lt;1 ha)</SelectItem>
                            <SelectItem value="Small">Small (1–2 ha)</SelectItem>
                            <SelectItem value="Medium">Medium (2–10 ha)</SelectItem>
                            <SelectItem value="Large">Large (&gt;10 ha)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2 mt-6">
                      <Label className="font-bold flex items-center">
                        {t('form.crops') || 'Primary Crops'}
                        <AiExtractedBadge fieldKey="primary_crops" />
                      </Label>
                      <Input
                        className="h-12"
                        placeholder={t('form.crops_placeholder') || 'Wheat, Rice, Sugarcane…'}
                        value={profile.primary_crops}
                        onChange={(e) => setProfile({ ...profile, primary_crops: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="flex gap-4 pt-2">
                    <Button
                      variant="outline"
                      className="h-12 px-6 font-bold border-2 rounded-xl"
                      onClick={() => setStep(2)}
                    >
                      {t('wizard.back') || 'Back'}
                    </Button>
                    <Button
                      className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-600/20"
                      onClick={saveDetails}
                      disabled={profileSaving}
                    >
                      {profileSaving ? (
                        <><Loader2 className="animate-spin mr-2" />Saving profile...</>
                      ) : (
                        t('wizard.save_continue') || 'Save & Finish'
                      )}
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* ══ STEP 4: SUCCESS ════════════════════════════════════════════ */}
              {step === 4 && (
                <motion.div
                  key="step5"
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
                    <h3 className="text-4xl font-black text-slate-900 dark:text-white">Setup Complete</h3>
                    <p className="text-lg text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                      Your verified farmer profile is ready. Our AI is scanning
                      1,200+ government schemes tailored specifically for you.
                    </p>
                  </div>

                  {/* Verification summary */}
                  <div className="max-w-xs mx-auto border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden text-left text-sm">
                    <div className="p-3 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                      <p className="font-semibold text-slate-600 dark:text-slate-300 text-xs uppercase tracking-wider">
                        Verification Summary
                      </p>
                    </div>
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      <div className="flex items-center justify-between px-4 py-3">
                        <span className="text-slate-600 dark:text-slate-400">Aadhaar</span>
                        <span className={`font-semibold text-xs ${uploadStatus.aadhar.verified ? 'text-emerald-600' : 'text-slate-400'}`}>
                          {uploadStatus.aadhar.verified ? 'Verified' : 'Not uploaded'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between px-4 py-3">
                        <span className="text-slate-600 dark:text-slate-400">PAN</span>
                        <span className={`font-semibold text-xs ${uploadStatus.pan.verified ? 'text-emerald-600' : 'text-slate-400'}`}>
                          {uploadStatus.pan.verified ? 'Verified' : 'Not uploaded'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between px-4 py-3">
                        <span className="text-slate-600 dark:text-slate-400">Land Record (7/12)</span>
                        <span className={`font-semibold text-xs ${
                          uploadStatus.satbara.verified
                            ? 'text-emerald-600'
                            : 'text-slate-400'
                        }`}>
                          {uploadStatus.satbara.verified
                            ? `Analyzed${satbaraExtraction ? ` — ${satbaraExtraction.filledFields.length} fields` : ''}`
                            : 'Skipped'}
                        </span>
                      </div>
                    </div>
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