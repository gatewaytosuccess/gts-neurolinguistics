import type { PresignedUpload } from "@/lib/api";

/** A Server Action's answer to a request to upload a file. */
export type UploadTicket = { upload: PresignedUpload } | { error: string };

/** A Server Action's answer to saving or removing an uploaded file's key. */
export type UploadResult = { error?: string };
