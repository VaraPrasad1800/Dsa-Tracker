import React from 'react';
import { Toaster, toast } from 'react-hot-toast';

export { toast };

/**
 * Global toaster — render this once at the app root.
 */
export function AppToaster() {
  return (
    <Toaster
      position="bottom-right"
      gutter={10}
      toastOptions={{
        duration: 3000,
        style: {
          background: 'rgba(13, 13, 20, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '12px',
          color: '#f1f5f9',
          fontSize: '13px',
          fontWeight: '500',
          padding: '12px 16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)',
          maxWidth: '360px',
        },
        success: {
          iconTheme: { primary: '#10b981', secondary: '#0a0a0f' },
          style: {
            background: 'rgba(13, 13, 20, 0.95)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
          },
        },
        error: {
          iconTheme: { primary: '#f43f5e', secondary: '#0a0a0f' },
          style: {
            background: 'rgba(13, 13, 20, 0.95)',
            border: '1px solid rgba(244, 63, 94, 0.25)',
          },
        },
        loading: {
          iconTheme: { primary: '#6366f1', secondary: '#0a0a0f' },
        },
      }}
    />
  );
}
