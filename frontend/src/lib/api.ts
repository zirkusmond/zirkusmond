import { queryOptions } from "@tanstack/react-query";
import { createServerOnlyFn } from "@tanstack/react-start";
import {
  getRequestHeader,
  setResponseHeader,
} from "@tanstack/react-start/server";

import type { ReservationDetail } from "#/interfaces/reservation.ts";
import type {
  HomepageResponse,
  ShowDetailResponse,
} from "#/interfaces/show.ts";
import { keysToCamelCase, keysToSnakeCase } from "#/lib/utils.ts";

/**
 * On the server (SSR loaders) we talk to Django directly; in the browser
 * requests go through the /api/$ server route (see routes/api.$.tsx), which
 * proxies to Django and also avoids CORS since Django doesn't send CORS
 * headers.
 */
export const SERVER_API_URL = process.env.API_URL ?? "http://localhost:8000";

export const apiUrl = (path: string) => {
  return typeof window === "undefined"
    ? `${SERVER_API_URL}${path}`
    : `/api${path}`;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    path: string,
  ) {
    super(`API request to ${path} failed with status ${status}`);
  }
}

/**
 * SSR-only: a Node-to-Django fetch has no cookie jar of its own, so without this
 * Django would mint a brand-new session on every server-rendered page load. Forward
 * the visitor's own Cookie header, and relay back whatever Set-Cookie Django sends
 * (e.g. a freshly minted session on a first visit) so the browser ends up sharing
 * that same Django session instead of getting its own separate one on hydration.
 */
const fetchFromDjangoServer = createServerOnlyFn(
  async (path: string, headers: Record<string, string>) => {
    const cookie = getRequestHeader("cookie");
    if (cookie) headers["Cookie"] = cookie;

    const res = await fetch(`${SERVER_API_URL}${path}`, { headers });

    const setCookieValues = res.headers.getSetCookie();
    if (setCookieValues.length > 0) {
      setResponseHeader("set-cookie", setCookieValues);
    }

    return res;
  },
);

export const fetchJson = async <T>(
  path: string,
  opts?: { preload?: boolean },
): Promise<T> => {
  const headers: Record<string, string> = {};
  // Marks TanStack Router's hover/touch-intent preloads so the backend doesn't
  // count a page the visitor never actually looked at as a page view.
  if (opts?.preload) headers["X-Preload"] = "1";

  const res =
    typeof window === "undefined"
      ? await fetchFromDjangoServer(path, headers)
      : await fetch(apiUrl(path), { headers });

  if (!res.ok) {
    throw new ApiError(res.status, path);
  }
  const data = await res.json();
  return keysToCamelCase<T>(data);
};

const getCsrfToken = (): string | null => {
  if (typeof document === "undefined") return null;
  const name = "csrftoken";
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(name + "=")) {
      return trimmed.substring(name.length + 1);
    }
  }
  return null;
};

export const postJson = async <T>(path: string, body: unknown): Promise<T> => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }

  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers,
    body: JSON.stringify(keysToSnakeCase(body)),
    credentials: "include",
  });
  if (!res.ok) {
    throw new ApiError(res.status, path);
  }
  const data = await res.json();
  return keysToCamelCase<T>(data);
};

/**
 * TanStack Query: `queryOptions` bundles a cache key with its fetch function
 * so the same definition can be used by route loaders (queryClient.query) and
 * components (useSuspenseQuery). Sharing one definition guarantees both sides
 * hit the same cache entry.
 */
// `opts.preload` is passed by route loaders when this is a router hover/touch
// "intent" preload rather than a real navigation (see fetchJson) — it never
// affects the query key, so loader and component consumers still share one
// cache entry.
export const homepageQueryOptions = (opts?: { preload?: boolean }) =>
  queryOptions({
    // Cache key: all consumers of ['homepage'] share one cached response.
    queryKey: ["homepage"],
    queryFn: () => fetchJson<HomepageResponse>("/", opts),
  });

export const allShowsQueryOptions = (opts?: { preload?: boolean }) =>
  queryOptions({
    queryKey: ["allShows"],
    queryFn: () => fetchJson<HomepageResponse>("/shows/", opts),
  });

/**
 * TanStack Query: parameterised query — a factory because the cache key must
 * include the showId, giving each show its own cache entry.
 */
export const showQueryOptions = (
  showId: string,
  opts?: { preload?: boolean },
) =>
  queryOptions({
    queryKey: ["show", showId],
    queryFn: async () => {
      const data = await fetchJson<ShowDetailResponse>(
        `/shows/${showId}`,
        opts,
      );
      return data.show;
    },
  });

export const reservationDetailQueryOptions = (reservationId: string) =>
  queryOptions({
    queryKey: ["reservation", reservationId],
    queryFn: () =>
      fetchJson<ReservationDetail>(`/reservation/detail/${reservationId}`),
  });

export interface TeamMember {
  id: number;
  name: string;
  roleDe: string;
  roleEn: string;
  image: string;
  order: number;
}

export interface TeamMembersResponse {
  teamMembers: TeamMember[];
}

export const teamMembersQueryOptions = (opts?: { preload?: boolean }) =>
  queryOptions({
    queryKey: ["teamMembers"],
    queryFn: async () => {
      const data = await fetchJson<TeamMembersResponse>("/team-members/", opts);
      return data.teamMembers;
    },
  });
