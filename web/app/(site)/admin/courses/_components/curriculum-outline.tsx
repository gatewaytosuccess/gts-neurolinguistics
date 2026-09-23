import Link from "next/link";

import { AutoSubmitSelect } from "@/components/auto-submit-select";
import type { CurriculumLesson, CurriculumModule } from "@/lib/api";

import {
  addLesson,
  addModule,
  deleteLesson,
  deleteModule,
  moveLesson,
  moveLessonToModule,
  moveModule,
  renameModule,
} from "../_lib/curriculum-actions";
import type { OutlineActionState } from "../_lib/curriculum";
import { OutlineForm } from "./outline-form";

const fieldClassName =
  "type-body-md min-w-0 rounded-sm border border-border-strong bg-paper-raised px-sm py-xs text-accent-strong placeholder:text-meta-text";

const controlClassName =
  "type-label-md rounded-sm border border-border-strong bg-paper-raised px-sm py-xs text-primary hover:bg-primary-pale disabled:cursor-not-allowed disabled:text-meta-text disabled:hover:bg-paper-raised";

const dangerClassName =
  "type-label-md rounded-sm border border-error bg-paper-raised px-sm py-xs text-error hover:bg-error-subtle";

function twoDigits(n: number) {
  return String(n).padStart(2, "0");
}

function learners(count: number) {
  return count === 1 ? "1 learner has" : `${count} learners have`;
}

function lessonDeleteWarning({
  learners_with_progress: count,
}: CurriculumLesson) {
  return count === 0
    ? "No learners have progress on this lesson."
    : `${learners(count)} progress on this lesson. Deleting it deletes that progress too.`;
}

function moduleDeleteWarning({
  lessons,
  learners_with_progress: count,
}: CurriculumModule) {
  if (lessons.length === 0) return "This module has no lessons.";
  const deletes =
    lessons.length === 1
      ? "Deleting it deletes its lesson too."
      : `Deleting it deletes its ${lessons.length} lessons too.`;
  const progress =
    count === 0
      ? "No learners have progress on them."
      : `${learners(count)} progress on them, which is deleted as well.`;
  return `${deletes} ${progress}`;
}

export function CurriculumOutline({
  courseId,
  modules,
}: {
  courseId: string;
  modules: CurriculumModule[];
}) {
  return (
    <>
      {modules.length === 0 ? (
        <p className="type-body-md mt-md text-meta-text">
          No modules yet. Add the first one below.
        </p>
      ) : (
        <ol className="mt-lg border-t border-border-strong">
          {modules.map((module, index) => (
            <ModuleItem
              key={module.id}
              courseId={courseId}
              module={module}
              number={index + 1}
              count={modules.length}
              otherModules={modules.filter(({ id }) => id !== module.id)}
            />
          ))}
        </ol>
      )}

      <OutlineForm
        action={addModule.bind(null, courseId)}
        className="measure mt-lg flex flex-wrap items-end gap-sm"
      >
        <div className="flex min-w-0 flex-1 flex-col">
          <label htmlFor="new-module-title" className="type-label-md">
            New module
          </label>
          <input
            id="new-module-title"
            name="title"
            type="text"
            required
            maxLength={255}
            placeholder="Module title"
            className={`${fieldClassName} mt-xs`}
          />
        </div>
        <button type="submit" className="button-secondary">
          Add module
        </button>
      </OutlineForm>
    </>
  );
}

function ModuleItem({
  courseId,
  module,
  number,
  count,
  otherModules,
}: {
  courseId: string;
  module: CurriculumModule;
  number: number;
  count: number;
  otherModules: CurriculumModule[];
}) {
  const titleId = `module-${module.id}-title`;

  return (
    <li className="border-b border-border-strong py-lg">
      <div className="flex flex-wrap items-end gap-sm">
        <OutlineForm
          action={renameModule.bind(null, module.id)}
          className="flex min-w-0 flex-1 flex-wrap items-end gap-sm"
        >
          <div className="flex min-w-[200px] flex-1 flex-col">
            <label htmlFor={titleId} className="type-label-caps text-accent">
              Module {twoDigits(number)}
            </label>
            <input
              id={titleId}
              name="title"
              type="text"
              required
              maxLength={255}
              defaultValue={module.title}
              className={`${fieldClassName} type-label-lg mt-xs`}
            />
          </div>
          <button type="submit" className={controlClassName}>
            Rename
          </button>
        </OutlineForm>

        <OutlineForm
          action={moveModule.bind(null, module.id)}
          className="flex flex-wrap gap-xs"
        >
          <MoveButtons
            position={module.position}
            count={count}
            noun="module"
            title={module.title}
          />
        </OutlineForm>

        <DeleteControl
          noun="module"
          title={module.title}
          warning={moduleDeleteWarning(module)}
          action={deleteModule.bind(null, module.id)}
        />
      </div>

      {module.lessons.length > 0 && (
        <ol className="mt-md">
          {module.lessons.map((lesson) => (
            <LessonItem
              key={lesson.id}
              courseId={courseId}
              lesson={lesson}
              moduleNumber={number}
              count={module.lessons.length}
              otherModules={otherModules}
            />
          ))}
        </ol>
      )}

      <OutlineForm
        action={addLesson.bind(null, module.id)}
        className="mt-md flex flex-wrap items-center gap-sm"
      >
        <label htmlFor={`module-${module.id}-new-lesson`} className="sr-only">
          New lesson in {module.title}
        </label>
        <input
          id={`module-${module.id}-new-lesson`}
          name="title"
          type="text"
          required
          maxLength={255}
          placeholder="Lesson title"
          className={`${fieldClassName} flex-1 sm:max-w-[320px]`}
        />
        <button type="submit" className={controlClassName}>
          Add lesson
        </button>
      </OutlineForm>
    </li>
  );
}

function LessonItem({
  courseId,
  lesson,
  moduleNumber,
  count,
  otherModules,
}: {
  courseId: string;
  lesson: CurriculumLesson;
  moduleNumber: number;
  count: number;
  otherModules: CurriculumModule[];
}) {
  const moveSelectId = `lesson-${lesson.id}-module`;

  return (
    <li className="flex flex-wrap items-center gap-x-md gap-y-sm border-t border-rule py-sm">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-sm">
        <span className="type-data-md text-meta-text">
          {moduleNumber}.{lesson.position}
        </span>
        <Link
          href={`/admin/courses/${courseId}/lessons/${lesson.id}`}
          className="type-label-lg text-accent-strong hover:text-primary hover:underline"
        >
          {lesson.title}
        </Link>
        {lesson.is_empty && <Chip>Empty</Chip>}
        {lesson.is_preview && <Chip>Preview</Chip>}
      </div>

      <div className="flex flex-wrap items-center gap-sm">
        <OutlineForm
          action={moveLesson.bind(null, lesson.id)}
          className="flex flex-wrap gap-xs"
        >
          <MoveButtons
            position={lesson.position}
            count={count}
            noun="lesson"
            title={lesson.title}
          />
        </OutlineForm>

        {otherModules.length > 0 && (
          <OutlineForm
            action={moveLessonToModule.bind(null, lesson.id)}
            className="flex flex-wrap items-center gap-xs"
          >
            <label htmlFor={moveSelectId} className="sr-only">
              Move {lesson.title} to module
            </label>
            <AutoSubmitSelect
              id={moveSelectId}
              name="module_id"
              defaultValue=""
              className={`${fieldClassName} type-label-md max-w-[200px]`}
            >
              <option value="" disabled>
                Move to module…
              </option>
              {otherModules.map((module) => (
                <option key={module.id} value={module.id}>
                  {twoDigits(module.position)} · {module.title}
                </option>
              ))}
            </AutoSubmitSelect>
            <button type="submit" className={controlClassName}>
              Move
            </button>
          </OutlineForm>
        )}

        <DeleteControl
          noun="lesson"
          title={lesson.title}
          warning={lessonDeleteWarning(lesson)}
          action={deleteLesson.bind(null, lesson.id)}
        />
      </div>
    </li>
  );
}

// Both buttons submit `position`; the one clicked decides which value is sent.
function MoveButtons({
  position,
  count,
  noun,
  title,
}: {
  position: number;
  count: number;
  noun: string;
  title: string;
}) {
  return (
    <>
      <button
        type="submit"
        name="position"
        value={position - 1}
        disabled={position <= 1}
        aria-label={`Move ${noun} ${title} up`}
        className={controlClassName}
      >
        ↑
      </button>
      <button
        type="submit"
        name="position"
        value={position + 1}
        disabled={position >= count}
        aria-label={`Move ${noun} ${title} down`}
        className={controlClassName}
      >
        ↓
      </button>
    </>
  );
}

// A <details> disclosure, so confirming needs no JavaScript. Open, it takes a line of its own.
function DeleteControl({
  noun,
  title,
  warning,
  action,
}: {
  noun: string;
  title: string;
  warning: string;
  action: () => Promise<OutlineActionState>;
}) {
  return (
    <details className="group open:basis-full">
      <summary
        aria-label={`Delete ${noun} ${title}`}
        className={`${dangerClassName} cursor-pointer list-none group-open:bg-error-subtle [&::-webkit-details-marker]:hidden`}
      >
        Delete
      </summary>
      <div className="mt-sm rounded-sm border border-error bg-paper-raised p-sm">
        <p className="type-body-sm measure">
          Delete the {noun} &ldquo;{title}&rdquo;? {warning}
        </p>
        <OutlineForm action={action} className="mt-sm flex flex-wrap gap-sm">
          <button type="submit" className={dangerClassName}>
            Delete {noun}
          </button>
        </OutlineForm>
      </div>
    </details>
  );
}

function Chip({ children }: { children: string }) {
  return (
    <span className="type-label-caps rounded-full bg-tertiary-pale px-sm py-xs text-tertiary-strong">
      {children}
    </span>
  );
}
