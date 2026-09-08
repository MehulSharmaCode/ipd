// frontend/src/components/SchemeReasonPanel.tsx
//
// Renders the deterministic, evidence-based "Why you were selected" reasoning
// the backend now attaches to eligible scheme recommendations
// (match_signals / reason_summary / reason_confidence -- see
// docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sections 5.6-5.7, 9b).
//
// Reuses the exact visual pattern already used inline in Dashboard.tsx for
// scheme.explanation (bg-slate-50 / border / CheckCircle2 rows) so this
// drops in without a visual discontinuity.

import type { ReactNode } from "react";
import { CheckCircle2, ShieldCheck, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useTranslationText } from "@/hooks/useTranslationText";
import type { MatchSignal, ReasonConfidence } from "@/types/scheme";

interface SchemeReasonPanelProps {
  reasonSummary?: string;
  signals?: MatchSignal[];
  confidence?: ReasonConfidence | string;
  sourceUrl?: string | null;
}

const CONFIDENCE_META: Record<
  string,
  { i18nKey: string; badgeClass: string; icon: ReactNode }
> = {
  verified: {
    i18nKey: "dashboard.confidence_verified",
    badgeClass:
      "bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
    icon: <ShieldCheck className="w-3 h-3" />,
  },
  high: {
    i18nKey: "dashboard.confidence_high",
    badgeClass:
      "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900",
    icon: <CheckCircle2 className="w-3 h-3" />,
  },
  medium: {
    i18nKey: "dashboard.confidence_medium",
    badgeClass:
      "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900",
    icon: <Info className="w-3 h-3" />,
  },
  low: {
    i18nKey: "dashboard.confidence_low",
    badgeClass:
      "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700",
    icon: <Info className="w-3 h-3" />,
  },
};

export function SchemeReasonPanel({
  reasonSummary,
  signals,
  confidence,
  sourceUrl,
}: SchemeReasonPanelProps) {
  const { t } = useTranslationText();

  if (!reasonSummary) return null;

  const meta = CONFIDENCE_META[confidence || "low"] || CONFIDENCE_META.low;
  const isLowConfidence = confidence === "low" || !confidence;

  return (
    <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1 mt-2 bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
      <div className="flex items-center justify-between gap-2 mb-1">
        <p className="font-semibold text-emerald-700 dark:text-emerald-500">
          {t("dashboard.why_recommended")}:
        </p>
        <Badge
          variant="outline"
          className={`text-[10px] h-5 shrink-0 gap-1 ${meta.badgeClass}`}
        >
          {meta.icon}
          {t(meta.i18nKey)}
        </Badge>
      </div>

      <p className="flex items-start gap-2 font-medium text-slate-700 dark:text-slate-300">
        <CheckCircle2 className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" />
        {reasonSummary}
      </p>

      {signals && signals.length > 0 && (
        <div className="pl-6 space-y-0.5 pt-1">
          {signals.map((signal, idx) => (
            <p key={idx} className="text-xs text-slate-500 dark:text-slate-500">
              • {signal.text}
            </p>
          ))}
        </div>
      )}

      {isLowConfidence && (
        <p className="text-[11px] text-amber-700 dark:text-amber-500 italic pt-1 border-t border-slate-200 dark:border-slate-800 mt-2">
          {t("dashboard.confidence_low_note")}
          {sourceUrl && (
            <>
              {" "}
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-amber-800 dark:hover:text-amber-400 not-italic"
                onClick={(e) => e.stopPropagation()}
              >
                {t("dashboard.source_myscheme")}
              </a>
            </>
          )}
        </p>
      )}
    </div>
  );
}

export default SchemeReasonPanel;
