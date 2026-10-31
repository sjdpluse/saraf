// Preserve the ORIGINAL FastAPI -> React error contract after the switch to
// signed Supabase Edge transport. The UI must continue to receive status/code,
// particularly IDENTITY_VERIFICATION_REQUIRED and expired quote conditions.
export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/** Convert only the external adapter error shape, never claim a payment succeeded. */
export function asOriginalApiError(error) {
  if (error instanceof ApiError) return error;
  const status = Number(error?.status);
  const code = typeof error?.code === 'string' ? error.code : 'SERVICE_UNAVAILABLE';
  const message = typeof error?.message === 'string' && error.message.trim()
    ? error.message : 'اتصال با خدمات صراف برقرار نشد.';
  return new ApiError(message, Number.isInteger(status) && status >= 400 && status < 600
    ? status : 503, code);
}
