// frontend/src/components/SchemeTimelineBadge.tsx
//
// Renders the application deadline / timeline state for a recommended scheme.
// See docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sections 5.2, 5.7 (Phase 3),
// 9d. `timeline_state` is computed at READ TIME by the backend (never
// persisted), so it can never go stale here either.

import { useState, type ComponentType } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useTranslationText } from "@/hooks/useTranslationText";
import type { ApplicationTimeline, TimelineState } from "@/types/scheme";

interface SchemeTimelineBadgeProps {
  timelineState?: TimelineState | null;
  timeline?: ApplicationTimeline | null;
}

const STATE_META: Record<
  string,
  { badgeClass: string; icon: ComponentType<{ className?: string }> }
> = {
  open: {
    badgeClass:
      "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900",
    icon: CheckCircle2,
  },
  closing_soon: {
    badgeClass:
      "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900",
    icon: AlertTriangle,
  },
  expired: {
    badgeClass:
      "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-900",
    icon: XCircle,
  },
  open_ended: {
    badgeClass:
      "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700",
    icon: Info,
  },
  unknown: {
    badgeClass:
      "bg-slate-50 dark:bg-slate-900 text-slate-400 dark:text-slate-500 border-slate-200 dark:border-slate-800",
    icon: Info,
  },
  unknown_with_mention: {
    badgeClass:
      "bg-amber-50/60 dark:bg-amber-950/20 text-amber-700 dark:text-amber-500 border-amber-100 dark:border-amber-900/50",
    icon: Info,
  },
};

function isSafeExternalUrl(url: string | null | undefined): url is string {
  return !!url && (url.startsWith("http://") || url.startsWith("https://"));
}

export function SchemeTimelineBadge({
  timelineState,
  timeline,
}: SchemeTimelineBadgeProps) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslationText();

  if (!timelineState) return null;

  const meta = STATE_META[timelineState.state] || STATE_META.unknown;
  const Icon = meta.icon;
  const hasMentions =
    timelineState.state === "unknown_with_mention" &&
    timeline?.text_mentions &&
    timeline.text_mentions.length > 0;
  const applicationModes = timeline?.application_modes || [];

  return (
    <div className="flex flex-wrap items-center gap-2 mt-2">
      <button
        type="button"
        disabled={!hasMentions}
        aria-expanded={hasMentions ? expanded : undefined}
        onClick={(e) => {
          e.stopPropagation();
          if (hasMentions) setExpanded((v) => !v);
        }}
        className={hasMentions ? "cursor-pointer" : "cursor-default"}
      >
        <Badge
          variant="outline"
          className={`text-[11px] h-6 gap-1 px-2 ${meta.badgeClass}`}
        >
          <Icon className="w-3.5 h-3.5" />
          {timelineState.label}
          {hasMentions &&
            (expanded ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            ))}
        </Badge>
      </button>

      {applicationModes.map((mode, idx) =>
        isSafeExternalUrl(mode.url) ? (
          <a
            key={idx}
            href={mode.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            <Badge
              variant="outline"
              className="text-[10px] h-5 bg-white dark:bg-slate-900 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-800"
            >
              {mode.mode}
            </Badge>
          </a>
        ) : (
          <Badge
            key={idx}
            variant="outline"
            className="text-[10px] h-5 bg-white dark:bg-slate-900 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-800"
          >
            {mode.mode}
          </Badge>
        )
      )}

      {hasMentions && expanded && (
        <blockquote className="w-full mt-1 text-xs italic text-slate-500 dark:text-slate-400 border-l-2 border-amber-300 dark:border-amber-800 pl-2">
          "{timeline!.text_mentions[0].excerpt}"
          <footer className="text-[10px] not-italic text-slate-400 dark:text-slate-600 mt-0.5">
            {t("dashboard.quoted_from_official_page")}
          </footer>
        </blockquote>
      )}
    </div>
  );
}

export default SchemeTimelineBadge;
