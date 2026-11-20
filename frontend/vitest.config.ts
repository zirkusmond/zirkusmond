import { defineConfig } from "vitest/config";
import viteReact from "@vitejs/plugin-react";

// Kept separate from vite.config.ts so tests don't load the TanStack Start /
// nitro / Sentry plugins, which break module loading and keep vitest from exiting.
export default defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [viteReact()],
  test: {
    environment: "jsdom",
    // Playwright specs live in e2e/ and run via `pnpm e2e`, not vitest.
    exclude: ["**/node_modules/**", "e2e/**"],
  },
});
