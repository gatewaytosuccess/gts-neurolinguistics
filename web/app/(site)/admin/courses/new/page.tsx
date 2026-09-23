import type { Metadata } from "next";

import { requireAdmin } from "../../_lib/require-admin";
import { CourseDetailsForm } from "../_components/course-details-form";
import { createCourse } from "../_lib/actions";
import { EMPTY_COURSE_DETAILS } from "../_lib/course-details";

export const metadata: Metadata = {
  title: "New course · Admin",
};

export default async function NewCoursePage() {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  return (
    <div>
      <p className="type-label-caps text-accent">Admin area</p>
      <h1 className="type-headline-md measure mt-md">New course</h1>
      <p className="type-body-md measure mt-sm">
        The course starts as a draft, out of the catalog until it&rsquo;s
        published.
      </p>

      <CourseDetailsForm
        action={createCourse}
        initialState={EMPTY_COURSE_DETAILS}
        submitLabel="Create course"
      />
    </div>
  );
}
