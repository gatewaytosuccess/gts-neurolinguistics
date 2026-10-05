"use client";

import { useState } from "react";

function objectOf(url: string) {
  return url.split("?", 1)[0];
}

/**
 * Keeps the first signed URL for as long as it points at the same object, so
 * a refresh that re-signs it doesn't restart the video or reload the slides.
 * After `repin()`, the next re-signed URL replaces it.
 */
export function usePinnedUrl(url: string) {
  const [pinned, setPinned] = useState(url);
  const [repinning, setRepinning] = useState(false);
  const repin = () => setRepinning(true);
  if (pinned !== url && (repinning || objectOf(pinned) !== objectOf(url))) {
    setPinned(url);
    setRepinning(false);
    return { url, repin };
  }
  return { url: pinned, repin };
}

export function LessonVideo({
  url,
  className,
}: {
  url: string;
  className: string;
}) {
  return (
    <video
      src={usePinnedUrl(url).url}
      controls
      preload="metadata"
      className={className}
    />
  );
}

export function LessonSlides({
  url,
  title,
  frameClassName,
  linkClassName,
}: {
  url: string;
  title: string;
  frameClassName: string;
  linkClassName: string;
}) {
  const { url: src } = usePinnedUrl(url);
  return (
    <div>
      <iframe src={src} title={title} className={frameClassName} />
      {/* Some browsers, most phones among them, can't show a PDF inline. */}
      <a href={src} target="_blank" rel="noreferrer" className={linkClassName}>
        Download the slides (PDF)
      </a>
    </div>
  );
}
