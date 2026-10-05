"use client";

import { useRouter } from "next/navigation";
import { useEffect, useEffectEvent, useRef } from "react";

import { usePinnedUrl } from "@/components/lesson-media";
import type { ViewerLessonProgress } from "@/lib/api";

import { setLessonCompleted } from "../_lib/progress-actions";
import { isLessonCompleted, useOutline } from "./outline-context";

const SAVE_EVERY_MS = 15_000;
// A saved position this close to the end restarts the video instead.
const END_SLACK_SECONDS = 5;

/**
 * The lesson viewer's `<video>`: resumes and saves the learner's position,
 * completes the lesson when it ends, and re-signs an expired URL. Must be
 * keyed by lesson, since it only reads `progress` on mount.
 */
export function ViewerVideo({
  url,
  className,
  lessonId,
  progress,
}: {
  url: string;
  className: string;
  lessonId: string;
  /** `null` unless the caller is enrolled, which saves nothing. */
  progress: ViewerLessonProgress | null;
}) {
  const router = useRouter();
  const outline = useOutline();
  const { url: src, repin } = usePinnedUrl(url);
  const videoRef = useRef<HTMLVideoElement>(null);

  const resumeAt = useRef(
    progress && progress.status !== "completed"
      ? progress.last_position_seconds
      : 0,
  );
  const recoverAt = useRef<{ seconds: number; play: boolean } | null>(null);
  // Until the start position is applied, currentTime would overwrite the saved one.
  const started = useRef(false);
  // One refresh per successful load, so a URL that never works can't loop.
  const recoverable = useRef(true);
  const lastSaved = useRef({
    seconds: progress?.last_position_seconds ?? 0,
    at: 0,
  });

  function save(video: HTMLVideoElement) {
    if (!progress || !started.current) return;
    const seconds = Math.floor(video.currentTime);
    lastSaved.current.at = Date.now();
    if (seconds === lastSaved.current.seconds) return;
    lastSaved.current.seconds = seconds;
    navigator.sendBeacon(
      "/learn/api/progress",
      JSON.stringify({ lessonId, position_seconds: seconds }),
    );
  }

  function start(video: HTMLVideoElement) {
    recoverable.current = true;
    const recovery = recoverAt.current;
    if (recovery) {
      recoverAt.current = null;
      video.currentTime = recovery.seconds;
      if (recovery.play) video.play().catch(() => {});
    } else if (!started.current) {
      // NaN for an unknown duration, which also starts from 0.
      if (resumeAt.current < video.duration - END_SLACK_SECONDS) {
        video.currentTime = resumeAt.current;
      }
    }
    started.current = true;
  }

  function recover(video: HTMLVideoElement) {
    if (!recoverable.current) return;
    recoverable.current = false;
    if (started.current) {
      recoverAt.current = { seconds: video.currentTime, play: !video.paused };
      started.current = false;
    }
    repin();
    router.refresh();
  }

  function complete() {
    if (!progress || isLessonCompleted(outline, lessonId)) return;
    // Errors are dropped: Mark complete is still there to retry.
    void setLessonCompleted(lessonId, true);
  }

  const onMount = useEffectEvent((video: HTMLVideoElement) => {
    // Hydration can come after the element has already loaded or failed.
    if (video.error) recover(video);
    else if (video.readyState >= HTMLMediaElement.HAVE_METADATA) start(video);
  });
  const onLeave = useEffectEvent(save);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    onMount(video);
    const leave = () => onLeave(video);
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("pagehide", leave);
      leave();
    };
  }, []);

  return (
    <video
      ref={videoRef}
      src={src}
      controls
      preload="metadata"
      className={className}
      onLoadedMetadata={(event) => start(event.currentTarget)}
      onTimeUpdate={(event) => {
        if (Date.now() - lastSaved.current.at >= SAVE_EVERY_MS) {
          save(event.currentTarget);
        }
      }}
      onPause={(event) => save(event.currentTarget)}
      onEnded={complete}
      onError={(event) => recover(event.currentTarget)}
    />
  );
}
