/**
 * What an outline control shows after submitting; neither `error` nor
 * `problems` means it worked. `problems` is set when the course is published.
 */
export type OutlineActionState = { error?: string; problems?: string[] };
