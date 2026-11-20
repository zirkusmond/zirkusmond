import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** IDs/credentials written by `manage.py seed_e2e` when the Django web server starts. */
export interface E2EState {
  showId: number;
  showTitle: string;
  eventId: number;
  eventTimeAndDate: string;
  ticketPrice: number;
  staffUsername: string;
  staffPassword: string;
}

const STATE_FILE = fileURLToPath(new URL("../.state.json", import.meta.url));

export const loadState = (): E2EState => {
  const raw = readFileSync(STATE_FILE, "utf8").trim();
  // seed_e2e prints a single JSON line; ignore anything else on stdout.
  const line = raw
    .split("\n")
    .reverse()
    .find((l) => l.trim().startsWith("{"));
  if (!line) throw new Error(`No seed output found in ${STATE_FILE}`);
  return JSON.parse(line) as E2EState;
};
