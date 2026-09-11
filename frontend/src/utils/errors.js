// Extract a human-readable message from a DRF / axios error response.
export const extractError = (err) => {
  const data = err?.response?.data;
  if (!data) return err?.message || 'Something went wrong. Please try again.';
  if (typeof data === 'string') return data;
  // DRF views return { error, message, detail, ... }
  if (data.error) return data.error;
  if (data.message) return data.message;
  if (data.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
  // Field-level errors, e.g. { username: ['This field is required.'] }
  for (const key of Object.keys(data)) {
    const v = data[key];
    if (Array.isArray(v)) return `${key}: ${v[0]}`;
    if (typeof v === 'string') return `${key}: ${v}`;
  }
  return 'Something went wrong. Please try again.';
};

// Extract an optional error code (e.g. 'email_not_verified') for branching UI.
export const extractErrorCode = (err) => err?.response?.data?.code || null;