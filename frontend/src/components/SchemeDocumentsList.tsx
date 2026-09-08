// frontend/src/components/SchemeDocumentsList.tsx
//
// Renders the required_documents block for a recommended scheme, handling
// all four backend statuses honestly (available / unavailable / fetch_failed
// / not_fetched) -- see docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sections
// 5.1, 9c, 12. The label shown is ALWAYS display_name (the verbatim,
// lightly-cleaned source text) -- doc_type only selects an icon/grouping,
// never displayed as text itself.

import { useState } from "react";
import {
  FileText,
  CreditCard,
  MapPin,
  Sprout,
  GraduationCap,
  ExternalLink,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useTranslationText } from "@/hooks/useTranslationText";
import type { RequiredDocuments, RequiredDocumentItem } from "@/types/scheme";

interface SchemeDocumentsListProps {
  documents?: RequiredDocuments | null;
  sourceUrl?: string | null;
}

const VISIBLE_COUNT = 5;

function docIcon(docType: string) {
  switch (docType) {
    case "AADHAAR":
    case "PAN":
    case "VOTER_ID":
      return <CreditCard className="w-3.5 h-3.5" />;
    case "ADDRESS_PROOF":
    case "DOMICILE_CERTIFICATE":
      return <MapPin className="w-3.5 h-3.5" />;
    case "LAND_RECORD":
      return <Sprout className="w-3.5 h-3.5" />;
    case "EDUCATION_CERTIFICATE":
      return <GraduationCap className="w-3.5 h-3.5" />;
    default:
      return <FileText className="w-3.5 h-3.5" />;
  }
}

function isSafeExternalUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function DocumentRow({ item }: { item: RequiredDocumentItem }) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-slate-400 dark:text-slate-500 mt-0.5 shrink-0">
        {docIcon(item.doc_type)}
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-sm text-slate-700 dark:text-slate-300">
          {item.display_name}
        </span>
        {item.requirement === "conditional" && item.condition_text && (
          <Badge
            variant="outline"
            className="ml-2 text-[10px] h-4 px-1.5 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900"
          >
            {item.condition_text}
          </Badge>
        )}
        {item.links
          .filter(isSafeExternalUrl)
          .map((link, idx) => (
            <a
              key={idx}
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-2 inline-flex items-center gap-0.5 text-[11px] text-emerald-600 dark:text-emerald-400 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="w-3 h-3" /> link
            </a>
          ))}
      </div>
    </div>
  );
}

export function SchemeDocumentsList({
  documents,
  sourceUrl,
}: SchemeDocumentsListProps) {
  const [showAll, setShowAll] = useState(false);
  const { t } = useTranslationText();

  if (!documents || documents.status === "not_fetched") {
    return null;
  }

  if (documents.status === "unavailable") {
    return (
      <div className="mt-3 bg-slate-50/50 dark:bg-slate-900/50 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg p-3 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
        <span>
          {t("dashboard.documents_unavailable")}{" "}
          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-600 dark:text-emerald-400 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {t("dashboard.source_myscheme")} →
            </a>
          )}
        </span>
      </div>
    );
  }

  if (documents.status === "fetch_failed") {
    return (
      <div className="mt-3 bg-slate-50/50 dark:bg-slate-900/50 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg p-3 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
        <span>{t("dashboard.documents_failed")}</span>
      </div>
    );
  }

  const items = documents.items || [];
  if (items.length === 0) return null;

  const visibleItems = showAll ? items : items.slice(0, VISIBLE_COUNT);
  const hiddenCount = items.length - VISIBLE_COUNT;

  return (
    <div className="mt-3 bg-white/50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-800 rounded-lg p-3">
      <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
        {t("dashboard.documents_required", { count: documents.item_count })}
      </p>
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {visibleItems.map((item, idx) => (
          <DocumentRow key={idx} item={item} />
        ))}
      </div>
      {hiddenCount > 0 && (
        <button
          type="button"
          aria-expanded={showAll}
          onClick={(e) => {
            e.stopPropagation();
            setShowAll((v) => !v);
          }}
          className="mt-1 flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
        >
          {showAll ? (
            <>
              {t("dashboard.documents_show_less")} <ChevronUp className="w-3 h-3" />
            </>
          ) : (
            <>
              {t("dashboard.documents_show_all", { count: items.length })}{" "}
              <ChevronDown className="w-3 h-3" />
            </>
          )}
        </button>
      )}
      {sourceUrl && (
        <p className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 dark:text-slate-600">
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline hover:text-slate-600 dark:hover:text-slate-400"
            onClick={(e) => e.stopPropagation()}
          >
            {t("dashboard.source_myscheme")}
          </a>
        </p>
      )}
    </div>
  );
}

export default SchemeDocumentsList;
