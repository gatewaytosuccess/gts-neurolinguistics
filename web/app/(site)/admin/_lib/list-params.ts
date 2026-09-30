/** The first of a repeated search param, or `""` when it is missing. */
export function firstValue(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

/** `1` for anything but an integer above 1. */
export function parsePage(value: string): number {
  const page = Number(value);
  return Number.isInteger(page) && page > 1 ? page : 1;
}
