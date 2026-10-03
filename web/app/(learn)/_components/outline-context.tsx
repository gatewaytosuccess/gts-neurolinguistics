"use client";

import { createContext, useContext } from "react";

import type { ViewerOutline } from "@/lib/api";

export const OutlineContext = createContext<ViewerOutline | null>(null);

/** The layout's outline of the course; `null` when the API couldn't say. */
export function useOutline(): ViewerOutline | null {
  return useContext(OutlineContext);
}
