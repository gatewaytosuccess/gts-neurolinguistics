import Link from "next/link";

import type {
  AdminCourseSummary,
  AdminEnrollment,
  EnrollmentStatus,
} from "@/lib/api";

import { StatusBadge as CourseStatusBadge } from "../../courses/_components/status-badge";
import { SOURCE_LABELS } from "../_lib/enrollment";
import {
  grantEnrollment,
  restoreEnrollment,
  revokeEnrollment,
} from "../_lib/enrollment-actions";
import { formatDate } from "../_lib/format";
import {
  GrantForm,
  RestoreButton,
  RevokeDialog,
  type GrantableCourse,
} from "./enrollment-controls";

export function Enrollments({
  userId,
  name,
  enrollments,
  courses,
}: {
  userId: string;
  name: string;
  enrollments: AdminEnrollment[];
  courses: AdminCourseSummary[];
}) {
  const enrolledIds = new Set(enrollments.map((row) => row.course.id));
  const grantable: GrantableCourse[] = courses
    .filter((course) => !enrolledIds.has(course.id))
    .map(({ id, title, status }) => ({ id, title, status }));

  return (
    <>
      {enrollments.length === 0 ? (
        <p className="type-body-md mt-md">No enrollments.</p>
      ) : (
        <EnrollmentTable name={name} enrollments={enrollments} />
      )}
      {courses.length === 0 ? (
        <p className="type-body-sm mt-lg text-meta-text">
          There are no courses to grant yet.
        </p>
      ) : grantable.length === 0 ? (
        <p className="type-body-sm mt-lg text-meta-text">
          Every course is already enrolled or revoked.
        </p>
      ) : (
        <GrantForm
          courses={grantable}
          grant={grantEnrollment.bind(null, userId)}
        />
      )}
    </>
  );
}

function EnrollmentTable({
  name,
  enrollments,
}: {
  name: string;
  enrollments: AdminEnrollment[];
}) {
  const headerClassName = "type-label-md px-sm py-sm text-accent";

  return (
    <div className="mt-md overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <thead>
          <tr className="border-b border-border-strong">
            <th scope="col" className={headerClassName}>
              Course
            </th>
            <th scope="col" className={headerClassName}>
              Source
            </th>
            <th scope="col" className={headerClassName}>
              Status
            </th>
            <th scope="col" className={headerClassName}>
              Enrolled
            </th>
            <th scope="col" className={`${headerClassName} text-right`}>
              Progress
            </th>
            <th scope="col" className={headerClassName}>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {enrollments.map((enrollment) => (
            <tr key={enrollment.id} className="border-b border-rule align-top">
              <td className="px-sm py-sm">
                <div className="flex flex-wrap items-center gap-x-sm gap-y-xs">
                  <Link
                    href={`/admin/courses/${enrollment.course.id}`}
                    className="type-label-lg break-words text-accent-strong hover:text-primary hover:underline"
                  >
                    {enrollment.course.title}
                  </Link>
                  {enrollment.course.status === "draft" && (
                    <CourseStatusBadge status="draft" />
                  )}
                </div>
              </td>
              <td className="type-body-sm px-sm py-sm">
                {SOURCE_LABELS[enrollment.source]}
              </td>
              <td className="px-sm py-sm">
                <EnrollmentStatusBadge status={enrollment.status} />
              </td>
              <td className="type-data-md whitespace-nowrap px-sm py-sm text-meta-text">
                {enrollment.revoked_at ? (
                  <>
                    Revoked{" "}
                    <time dateTime={enrollment.revoked_at}>
                      {formatDate(enrollment.revoked_at)}
                    </time>
                  </>
                ) : (
                  <time dateTime={enrollment.enrolled_at}>
                    {formatDate(enrollment.enrolled_at)}
                  </time>
                )}
              </td>
              <td className="px-sm py-sm text-right">
                <Progress enrollment={enrollment} />
              </td>
              <td className="px-sm py-sm text-right">
                {enrollment.status === "active" ? (
                  <RevokeDialog
                    name={name}
                    courseTitle={enrollment.course.title}
                    isPurchase={enrollment.source === "purchase"}
                    revoke={revokeEnrollment.bind(null, enrollment.id)}
                  />
                ) : (
                  <RestoreButton
                    restore={restoreEnrollment.bind(null, enrollment.id)}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Progress({ enrollment }: { enrollment: AdminEnrollment }) {
  const { completed_lesson_count: completed, lesson_count: total } = enrollment;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  return (
    <>
      <span className="type-data-md block">{percent}%</span>
      <span className="type-caption block whitespace-nowrap text-meta-text">
        {completed} of {total} {total === 1 ? "lesson" : "lessons"}
      </span>
    </>
  );
}

function EnrollmentStatusBadge({ status }: { status: EnrollmentStatus }) {
  return (
    <span
      className={`type-label-caps inline-block whitespace-nowrap rounded-full px-sm py-xs ${
        status === "active"
          ? "bg-success-subtle text-success"
          : "bg-warning-subtle text-warning"
      }`}
    >
      {status === "active" ? "Active" : "Revoked"}
    </span>
  );
}
