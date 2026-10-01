/** What the suspend and reinstate dialogs show after submitting. */
export type SuspensionState = {
  /** The reason as typed, so a refused submission keeps it. */
  reason?: string;
  reasonErrors?: string[];
  error?: string;
};

export const BLANK_REASON_ERROR = "Give a reason for suspending this user.";
