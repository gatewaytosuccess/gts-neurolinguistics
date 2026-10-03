"use client";

import { useEffect } from "react";

import { recordOpened } from "../_lib/progress-actions";

// An effect, not the lesson GET: prefetching a sidebar link must not count as opening it.
export function RecordOpened({ lessonId }: { lessonId: string }) {
  useEffect(() => {
    void recordOpened(lessonId);
  }, [lessonId]);

  return null;
}
