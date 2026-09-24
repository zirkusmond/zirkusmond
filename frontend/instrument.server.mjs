import * as Sentry from "@sentry/tanstackstart-react";

// Only initialize when a DSN is actually configured (e.g. staging/production).
// In local dev this is unset, and initializing anyway registers atexit/shutdown
// hooks for no benefit.
if (process.env.SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    dataCollection: {
      userInfo: false,
      httpBodies: [],
    },
    enableLogs: true,
    tracesSampleRate: 1.0,
  });
}
