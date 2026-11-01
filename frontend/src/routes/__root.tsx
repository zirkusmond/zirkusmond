import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
} from "@tanstack/react-router";
import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { TanStackDevtools } from "@tanstack/react-devtools";
import type { QueryClient } from "@tanstack/react-query";

import "#/i18n";
import { useTranslation } from "react-i18next";
import Navbar from "#/components/zirkusmond/general/Navbar";
import NotFound from "#/components/zirkusmond/general/NotFound";
import ErrorPage from "#/components/zirkusmond/general/ErrorPage";
import CookieConsentBanner from "#/components/zirkusmond/general/CookieConsentBanner";

import appCss from "../styles.css?url";
import Footer from "#/components/zirkusmond/general/Footer";

// Types the router context created in router.tsx, so every route loader gets
// a typed `context.queryClient` for prefetching TanStack Query data.
interface RouterContext {
  queryClient: QueryClient;
}

const RootDocument = ({ children }: { children: React.ReactNode }) => {
  const { i18n } = useTranslation();

  return (
    <html lang={i18n.language} translate="no" suppressHydrationWarning>
      <head>
        <HeadContent />
      </head>
      <body className="font-sans antialiased wrap-anywhere selection:bg-[rgba(79,184,178,0.24)] flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1">{children}</main>
        <TanStackDevtools
          config={{
            position: "bottom-right",
          }}
          plugins={[
            {
              name: "Tanstack Router",
              render: <TanStackRouterDevtoolsPanel />,
            },
          ]}
        />
        <Footer />
        <CookieConsentBanner />
        <Scripts />
      </body>
    </html>
  );
};

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      {
        charSet: "utf-8",
      },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1",
      },
      {
        name: "google",
        content: "notranslate",
      },
      {
        title: "Zirkus Mond",
      },
      {
        name: "description",
        content:
          "Zirkus Mond – Dein Zirkus in Berlin! Entdecke unser Programm: Live Shows, Events, Community und zeitgenössische Zirkuskunst im Herzen Berlins.",
      },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      {
        rel: "icon",
        href: "/images/logos/logo.webp",
      },
    ],
  }),
  shellComponent: RootDocument,
  notFoundComponent: () => <NotFound />,
  errorComponent: (props) => (
    <RootDocument>
      <ErrorPage {...props} />
    </RootDocument>
  ),
});
