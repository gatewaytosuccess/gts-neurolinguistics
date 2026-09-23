"use client";

import type { ComponentProps } from "react";

// Without JavaScript the form's submit button does the same job.
export function AutoSubmitSelect(
  props: Omit<ComponentProps<"select">, "onChange">,
) {
  return (
    <select
      {...props}
      onChange={(event) => event.currentTarget.form?.requestSubmit()}
    />
  );
}
