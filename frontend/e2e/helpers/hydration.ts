import type { Page } from "@playwright/test";

/**
 * Waits until React has hydrated the SSR'd page. Interacting before that either
 * does nothing (custom dropdowns) or triggers full-page navigations instead of
 * client-side ones, which then land on another not-yet-hydrated page.
 */
export const waitForHydration = async (page: Page) => {
  await page.waitForFunction(() => {
    const body = document.body as unknown as Record<string, unknown> | null;
    return (
      !!body && Object.keys(body).some((k) => k.startsWith("__reactFiber$"))
    );
  });
};
