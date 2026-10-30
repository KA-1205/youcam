"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { loadShortlist, saveShortlist, toggleSaved } from "./shortlist";

type ShortlistValue = {
  savedIds: string[];
  isSaved: (refId: string) => boolean;
  toggleSave: (refId: string) => void;
};

const ShortlistContext = createContext<ShortlistValue | null>(null);

export function ShortlistProvider({ children }: { children: React.ReactNode }) {
  const [savedIds, setSavedIds] = useState<string[]>([]);

  useEffect(() => {
    setSavedIds(loadShortlist(window.sessionStorage));
  }, []);

  const toggleSave = useCallback((refId: string) => {
    setSavedIds((prev) => {
      const next = toggleSaved(prev, refId);
      saveShortlist(window.sessionStorage, next);
      return next;
    });
  }, []);

  const value = useMemo<ShortlistValue>(
    () => ({
      savedIds,
      isSaved: (refId: string) => savedIds.includes(refId),
      toggleSave,
    }),
    [savedIds, toggleSave],
  );

  return <ShortlistContext.Provider value={value}>{children}</ShortlistContext.Provider>;
}

export function useShortlist(): ShortlistValue {
  const ctx = useContext(ShortlistContext);
  if (!ctx) throw new Error("useShortlist must be used inside ShortlistProvider");
  return ctx;
}
