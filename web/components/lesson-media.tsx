"use client";

import { useState } from "react";

function objectOf(url: string) {
  return url.split("?", 1)[0];
}

/**
 * Keeps the first signed URL for as long as it points at the same object, so
 * a refresh that re-signs it doesn't restart the video or reload the slides.
 */
function usePinnedUrl(url: string) {
  const [pinned, setPinned] = useState(url);
  if (objectOf(pinned) !== objectOf(url)) {
    setPinned(url);
    return url;
  }
  return pinned;
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
      src={usePinnedUrl(url)}
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
  const src = usePinnedUrl(url);
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
