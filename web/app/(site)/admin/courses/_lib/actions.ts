"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";

import {
  ApiError,
  createAdminCourse,
  updateAdminCourse,
  type AdminCourse,
  type FieldErrors,
} from "@/lib/api";

import { courseDetailsValues, type CourseDetailsState } from "./course-details";

const PRICE_FORMAT_ERROR = "Enter a price in dollars, such as 129 or 129.99.";

/** `null` unless it's whole dollars or dollars and cents; commas and a `$` are allowed. */
function parsePriceCents(price: string): number | null {
  const match = /^\$?(\d+)(?:\.(\d{1,2}))?$/.exec(price.replaceAll(",", ""));
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}

function readForm(formData: FormData, previous: CourseDetailsState) {
  const field = (name: string) => String(formData.get(name) ?? "").trim();
  // A published course's form has no slug field, so its slug is left out of the payload.
  const sendsSlug = formData.has("slug");
  const values = {
    title: field("title"),
    description: field("description"),
    price: field("price"),
    slug: sendsSlug ? field("slug") : previous.values.slug,
  };
  return { values, sendsSlug, priceCents: parsePriceCents(values.price) };
}

function formErrors(error: unknown): CourseDetailsState["errors"] {
  if (!(error instanceof ApiError)) {
    return {
      form: ["The course API is not responding, so nothing was saved."],
    };
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    const { title, slug, description, price_cents, non_field_errors } =
      error.body as FieldErrors;
    return {
      title,
      slug,
      description,
      price: price_cents,
      form: non_field_errors,
    };
  }
  if (error.status === 401 || error.status === 403) {
    return { form: ["You no longer have access to the admin area."] };
  }
  if (error.status === 404) {
    return { form: ["This course no longer exists."] };
  }
  return { form: ["The course API couldn't save this course. Try again."] };
}

export async function createCourse(
  previous: CourseDetailsState,
  formData: FormData,
): Promise<CourseDetailsState> {
  const { values, priceCents } = readForm(formData, previous);
  if (priceCents === null) {
    return { values, errors: { price: [PRICE_FORMAT_ERROR] } };
  }

  let course: AdminCourse;
  try {
    course = await createAdminCourse({
      title: values.title,
      description: values.description,
      price_cents: priceCents,
      slug: values.slug,
    });
  } catch (error) {
    return { values, errors: formErrors(error) };
  }

  redirect(`/admin/courses/${course.id}`);
}

export async function updateCourse(
  id: string,
  previous: CourseDetailsState,
  formData: FormData,
): Promise<CourseDetailsState> {
  const { values, sendsSlug, priceCents } = readForm(formData, previous);
  if (priceCents === null) {
    return { values, errors: { price: [PRICE_FORMAT_ERROR] } };
  }

  let course: AdminCourse;
  try {
    course = await updateAdminCourse(id, {
      title: values.title,
      description: values.description,
      price_cents: priceCents,
      ...(sendsSlug ? { slug: values.slug } : {}),
    });
  } catch (error) {
    return { values, errors: formErrors(error) };
  }

  // Re-renders the heading and status badge above the form.
  refresh();
  return { values: courseDetailsValues(course), errors: {}, saved: true };
}
