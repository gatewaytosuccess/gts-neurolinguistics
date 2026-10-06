import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Markdown } from "@/components/markdown";
import {
  ApiError,
  fetchCourse,
  fetchCourseReviews,
  fetchCurrentUser,
  fetchMyReview,
  fetchViewerOutline,
  type CourseDetail,
  type CourseReview,
  type Paginated,
  type ViewerOutline,
} from "@/lib/api";
import { markdownExcerpt } from "@/lib/markdown-excerpt";

import { InstructorCredentials } from "../../_components/landing/instructor-credentials";
import { landing } from "../../_content/landing";
import { Curriculum } from "./_components/curriculum";
import { MyReviewPanel } from "./_components/my-review";
import {
  PurchasePanel,
  type EnrollmentState,
} from "./_components/purchase-panel";
import { Reviews } from "./_components/reviews";
import { deleteReview, saveReview } from "./_lib/review-actions";

/**
 * `null` if the API is unreachable or errors. Throws Next's not-found error on
 * a 404, so it must be awaited in the render path.
 */
async function loadCourse(slug: string): Promise<CourseDetail | null> {
  try {
    return await fetchCourse(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return null;
  }
}

/**
 * `null` if the API is unreachable or errors, including a 404 for the course
 * itself, which `loadCourse` handles. A page past the last falls back to page 1.
 */
async function loadReviews(
  slug: string,
  page: number,
): Promise<{ page: number; reviews: Paginated<CourseReview> } | null> {
  try {
    return { page, reviews: await fetchCourseReviews(slug, page) };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404 && page > 1) {
      return loadReviews(slug, 1);
    }
    return null;
  }
}

// Signed out, the public course data already says which lessons are previews.
async function fetchSignedInOutline(
  slug: string,
): Promise<ViewerOutline | null> {
  const { userId } = await auth();
  return userId ? fetchViewerOutline(slug) : null;
}

function parsePage(value: string | string[] | undefined): number {
  const page = Number(Array.isArray(value) ? value[0] : value);
  return Number.isInteger(page) && page > 1 ? page : 1;
}

export async function generateMetadata({
  params,
}: PageProps<"/courses/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const course = await loadCourse(slug);
  if (course === null) return { title: "Courses" };

  const description = markdownExcerpt(course.description, 160) || undefined;
  return {
    title: course.title,
    description,
    openGraph: {
      title: course.title,
      description,
      images: course.thumbnail_url ? [course.thumbnail_url] : undefined,
    },
  };
}

export default async function CoursePage({
  params,
  searchParams,
}: PageProps<"/courses/[slug]">) {
  const { slug } = await params;
  const reviewsPage = parsePage((await searchParams).reviews);
  const [course, reviews, [outlineResult, currentUser, myReview]] =
    await Promise.all([
      loadCourse(slug),
      loadReviews(slug, reviewsPage),
      Promise.allSettled([
        fetchSignedInOutline(slug),
        fetchCurrentUser(),
        fetchMyReview(slug),
      ]),
    ]);

  if (course === null) {
    return (
      <div className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl">
        <AllCoursesLink />
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so this course is unavailable.
        </p>
      </div>
    );
  }

  // A failed call (suspended account, API error) reads as not enrolled and not an admin.
  const outline =
    outlineResult.status === "fulfilled" ? outlineResult.value : null;
  const enrolled = outline?.access === "enrolled";
  const enrollment: EnrollmentState = enrolled
    ? "enrolled"
    : outline?.revoked_at
      ? "revoked"
      : "none";
  const isAdmin =
    currentUser.status === "fulfilled" && currentUser.value?.role === "admin";

  return (
    <>
      {/* Under md the panel sits between the header and the body, in source order. */}
      <div className="mx-auto grid max-w-[1200px] gap-xl px-md py-2xl sm:px-margin md:grid-cols-12 md:gap-x-gutter lg:py-3xl">
        <header className="min-w-0 md:col-span-7">
          <AllCoursesLink />
          <p className="type-label-caps mt-xl text-accent">Course</p>
          <h1 className="type-headline-sm mt-sm break-words lg:type-headline-md">
            {course.title}
          </h1>
          <CourseRating
            average={course.rating_average}
            count={course.rating_count}
          />
        </header>

        <PurchasePanel
          course={course}
          enrollment={enrollment}
          isAdmin={isAdmin}
          className="min-w-0 md:sticky md:top-lg md:col-span-5 md:col-start-8 md:row-span-2 md:row-start-1 md:self-start lg:col-span-4 lg:col-start-9"
        />

        <div className="flex min-w-0 flex-col gap-2xl md:col-span-7">
          {course.description && (
            <section aria-labelledby="about-heading">
              <h2 id="about-heading" className="type-headline-sm">
                About this course
              </h2>
              <div className="mt-md break-words">
                <Markdown>{course.description}</Markdown>
              </div>
            </section>
          )}
          {course.modules.length > 0 && (
            <Curriculum
              slug={course.slug}
              modules={course.modules}
              outline={outline}
            />
          )}
        </div>
      </div>

      <InstructorCredentials instructor={landing.instructor} />

      <Reviews
        slug={course.slug}
        ratingAverage={course.rating_average}
        ratingCount={course.rating_count}
        reviews={reviews?.reviews ?? null}
        page={reviews?.page ?? 1}
        ownReview={
          enrolled &&
          (myReview.status === "fulfilled" ? (
            <MyReviewPanel
              key={myReview.value?.updated_at ?? "none"}
              review={myReview.value}
              save={saveReview.bind(null, course.slug)}
              remove={deleteReview.bind(null, course.slug)}
            />
          ) : (
            <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
              Your review couldn&rsquo;t be loaded right now.
            </p>
          ))
        }
      />
    </>
  );
}

function AllCoursesLink() {
  return (
    <Link href="/courses" className="type-label-md text-primary underline">
      &larr; All courses
    </Link>
  );
}

function CourseRating({
  average,
  count,
}: {
  average: number | null;
  count: number;
}) {
  if (average === null || count === 0) {
    return <p className="type-caption mt-md text-meta-text">No ratings yet</p>;
  }

  return (
    <p className="type-data-md mt-md text-meta-text">
      <span aria-hidden className="text-tertiary-strong">
        ★{" "}
      </span>
      <span className="sr-only">Rated </span>
      {average.toFixed(1)}
      <span className="type-caption">
        {" "}
        from {count.toLocaleString("en-US")}{" "}
        {count === 1 ? "rating" : "ratings"}
      </span>
    </p>
  );
}
