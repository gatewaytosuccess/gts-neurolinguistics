import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ApiError, fetchAdminCourse, type AdminCourse } from "@/lib/api";

import { requireAdmin } from "../../_lib/require-admin";
import { CourseDetailsForm } from "../_components/course-details-form";
import { StatusBadge } from "../_components/status-badge";
import { updateCourse } from "../_lib/actions";
import { courseDetailsValues } from "../_lib/course-details";

export const metadata: Metadata = {
  title: "Course · Admin",
};

export default async function AdminCoursePage({
  params,
}: PageProps<"/admin/courses/[id]">) {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  const { id } = await params;

  let course: AdminCourse | null;
  try {
    course = await fetchAdminCourse(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    course = null;
  }

  if (!course) {
    return (
      <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
        The course API is not responding, so this course is unavailable.
      </p>
    );
  }

  return (
    <div>
      <p className="type-label-caps text-accent">Admin area</p>
      <div className="mt-md flex flex-wrap items-center gap-md">
        <h1 className="type-headline-md measure">{course.title}</h1>
        <StatusBadge status={course.status} />
      </div>

      <section aria-labelledby="course-details-heading" className="mt-2xl">
        <h2 id="course-details-heading" className="type-headline-sm">
          Details
        </h2>
        <CourseDetailsForm
          // Remounts per course, so another course's saved state never carries over.
          key={course.id}
          action={updateCourse.bind(null, course.id)}
          initialState={{ values: courseDetailsValues(course), errors: {} }}
          slugLocked={course.status === "published"}
          submitLabel="Save changes"
        />
      </section>
    </div>
  );
}
