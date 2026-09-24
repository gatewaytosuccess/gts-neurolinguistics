import type { Metadata } from "next";
import { notFound } from "next/navigation";

import {
  ApiError,
  fetchAdminCourse,
  fetchAdminCurriculum,
  type AdminCourse,
  type CurriculumModule,
} from "@/lib/api";

import { requireAdmin } from "../../_lib/require-admin";
import { CourseDetailsForm } from "../_components/course-details-form";
import { CourseThumbnail } from "../_components/course-thumbnail";
import { CurriculumOutline } from "../_components/curriculum-outline";
import { StatusBadge } from "../_components/status-badge";
import { updateCourse } from "../_lib/actions";
import { courseDetailsValues } from "../_lib/course-details";
import {
  requestThumbnailUpload,
  saveThumbnail,
} from "../_lib/thumbnail-actions";

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

  const [courseResult, curriculumResult] = await Promise.allSettled([
    fetchAdminCourse(id),
    fetchAdminCurriculum(id),
  ]);

  let course: AdminCourse | null = null;
  if (courseResult.status === "fulfilled") {
    course = courseResult.value;
  } else if (
    courseResult.reason instanceof ApiError &&
    courseResult.reason.status === 404
  ) {
    notFound();
  }

  const modules: CurriculumModule[] | null =
    curriculumResult.status === "fulfilled" ? curriculumResult.value : null;

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

      <section aria-labelledby="thumbnail-heading" className="mt-3xl">
        <h2 id="thumbnail-heading" className="type-headline-sm">
          Thumbnail
        </h2>
        <CourseThumbnail
          url={course.thumbnail_url}
          removable={course.status !== "published"}
          requestUpload={requestThumbnailUpload.bind(null, course.id)}
          save={saveThumbnail.bind(null, course.id)}
          remove={saveThumbnail.bind(null, course.id, "")}
        />
      </section>

      <section aria-labelledby="curriculum-heading" className="mt-3xl">
        <h2 id="curriculum-heading" className="type-headline-sm">
          Curriculum
        </h2>
        {modules === null ? (
          <p className="type-body-sm mt-md rounded-sm bg-warning-subtle px-sm py-sm text-warning">
            The course API is not responding, so the curriculum is unavailable.
          </p>
        ) : (
          <CurriculumOutline courseId={course.id} modules={modules} />
        )}
      </section>
    </div>
  );
}
