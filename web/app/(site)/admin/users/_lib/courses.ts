import { fetchAdminCourses, type AdminCourseSummary } from "@/lib/api";

/** Every course, drafts included, by title. Throws if any page fails. */
export async function fetchEveryAdminCourse(): Promise<AdminCourseSummary[]> {
  const first = await fetchAdminCourses({ sort: "title" });
  const pageSize = first.results.length;
  const pageCount = pageSize ? Math.ceil(first.count / pageSize) : 1;

  const rest = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) =>
      fetchAdminCourses({ sort: "title", page: index + 2 }),
    ),
  );
  return [first, ...rest].flatMap((page) => page.results);
}
