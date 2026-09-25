/** What the publish, unpublish and delete controls show after submitting. */
export type CourseStatusState = {
  error?: string;
  problems?: string[];
  /** A delete was refused: someone has enrolled in, bought or reviewed the course. */
  hasHistory?: boolean;
};
