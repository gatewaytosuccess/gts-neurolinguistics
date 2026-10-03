"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { ViewerOutline } from "@/lib/api";

import { CurriculumNav } from "./curriculum-nav";
import { ViewerHeader } from "./viewer-header";

// Tailwind's `lg`, where the sidebar stops being a drawer.
const DESKTOP_QUERY = "(min-width: 64rem)";

export function ViewerShell({
  slug,
  outline,
  admin,
  signedIn,
  children,
}: {
  slug: string;
  /** `null` when the API couldn't say: no sidebar. */
  outline: ViewerOutline | null;
  admin: boolean;
  signedIn: boolean;
  children: ReactNode;
}) {
  const { lessonId } = useParams<{ lessonId?: string }>();
  const drawerRef = useRef<HTMLDialogElement>(null);

  const currentModuleId = outline?.modules.find((module) =>
    module.lessons.some((lesson) => lesson.id === lessonId),
  )?.id;

  // Opening a lesson expands its module and leaves the others as they were.
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(
    () => new Set(currentModuleId ? [currentModuleId] : []),
  );
  const [expandedFor, setExpandedFor] = useState(currentModuleId);
  if (currentModuleId !== expandedFor) {
    setExpandedFor(currentModuleId);
    if (currentModuleId && !expanded.has(currentModuleId)) {
      setExpanded(new Set(expanded).add(currentModuleId));
    }
  }

  function toggle(moduleId: string) {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (!next.delete(moduleId)) next.add(moduleId);
      return next;
    });
  }

  // A modal left open while the window widens would keep the page inert.
  useEffect(() => {
    const desktop = window.matchMedia(DESKTOP_QUERY);
    const closeOnDesktop = () => {
      if (desktop.matches) drawerRef.current?.close();
    };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);

  const closeDrawer = () => drawerRef.current?.close();

  return (
    <>
      <ViewerHeader
        slug={slug}
        courseTitle={outline?.course.title}
        editHref={
          admin && outline && lessonId
            ? `/admin/courses/${outline.course.id}/lessons/${lessonId}`
            : undefined
        }
        viewingAsAdmin={outline?.access === "admin"}
        signedIn={signedIn}
        onOpenCurriculum={
          outline ? () => drawerRef.current?.showModal() : undefined
        }
      />

      <div className="flex flex-1">
        {outline && (
          <aside className="hidden w-[300px] shrink-0 border-r border-dark-rule lg:block">
            <div className="sticky top-0 max-h-dvh overflow-y-auto px-sm py-lg">
              <CurriculumNav
                slug={slug}
                modules={outline.modules}
                currentLessonId={lessonId}
                expanded={expanded}
                onToggle={toggle}
              />
            </div>
          </aside>
        )}
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>

      {outline && (
        <dialog
          ref={drawerRef}
          aria-labelledby="curriculum-drawer-heading"
          // Clicks on the panel land on its inner wrapper; only the backdrop hits the dialog.
          onClick={(event) => {
            if (event.target === event.currentTarget) closeDrawer();
          }}
          className="page-dark m-0 h-dvh max-h-none border-r border-dark-rule w-[min(320px,calc(100%-var(--spacing-2xl)))] max-w-none p-0 transition-[translate] duration-200 ease-out backdrop:bg-dark-bg/70 starting:open:-translate-x-full"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center gap-md border-b border-dark-rule px-md py-sm">
              <h2
                id="curriculum-drawer-heading"
                className="type-label-lg min-w-0 flex-1 truncate"
              >
                {outline.course.title}
              </h2>
              <button
                type="button"
                onClick={closeDrawer}
                aria-label="Close the curriculum"
                className="type-label-lg -mx-sm px-sm py-xs text-dark-primary hover:text-dark-primary-strong"
              >
                &times;
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-sm py-md">
              <CurriculumNav
                slug={slug}
                modules={outline.modules}
                currentLessonId={lessonId}
                expanded={expanded}
                onToggle={toggle}
                onNavigate={closeDrawer}
              />
            </div>
          </div>
        </dialog>
      )}
    </>
  );
}
