import type { AdminCourse } from "@/lib/api";

/** What the details form shows; `price` is in dollars, as typed. */
export type CourseDetailsValues = {
  title: string;
  slug: string;
  description: string;
  price: string;
};

export type CourseDetailsState = {
  values: CourseDetailsValues;
  errors: Partial<Record<keyof CourseDetailsValues | "form", string[]>>;
  saved?: boolean;
};

export const EMPTY_COURSE_DETAILS: CourseDetailsState = {
  values: { title: "", slug: "", description: "", price: "" },
  errors: {},
};

export function courseDetailsValues(course: AdminCourse): CourseDetailsValues {
  return {
    title: course.title,
    slug: course.slug,
    description: course.description,
    price: (course.price_cents / 100).toFixed(2),
  };
}
