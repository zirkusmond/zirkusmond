import { expect } from "@playwright/test";

/** Mailpit (https://mailpit.axllent.org) REST API — see `make e2e-mailpit`. */
export const MAILPIT_URL = process.env.MAILPIT_URL ?? "http://localhost:8025";

interface MailpitAttachment {
  PartID: string;
  FileName: string;
  ContentType: string;
  Size: number;
}

export interface MailpitMessage {
  ID: string;
  Subject: string;
  Text: string;
  To: { Address: string; Name: string }[];
  Attachments: MailpitAttachment[];
}

export const assertMailpitRunning = async () => {
  try {
    const res = await fetch(`${MAILPIT_URL}/api/v1/info`);
    if (!res.ok) throw new Error(`status ${res.status}`);
  } catch (err) {
    throw new Error(
      `Mailpit is not reachable at ${MAILPIT_URL} (${String(err)}). Start it with \`make e2e-mailpit\`.`,
    );
  }
};

/** Polls Mailpit until a message to `address` arrives, then returns it in full. */
export const waitForMessageTo = async (
  address: string,
  timeout = 30_000,
): Promise<MailpitMessage> => {
  let id: string | undefined;
  await expect
    .poll(
      async () => {
        const query = encodeURIComponent(`to:"${address}"`);
        const res = await fetch(`${MAILPIT_URL}/api/v1/search?query=${query}`);
        const body = (await res.json()) as { messages: { ID: string }[] };
        id = body.messages[0]?.ID;
        return body.messages.length;
      },
      { timeout, message: `waiting for an email to ${address}` },
    )
    .toBeGreaterThan(0);

  const res = await fetch(`${MAILPIT_URL}/api/v1/message/${id}`);
  return (await res.json()) as MailpitMessage;
};

export const countMessagesTo = async (address: string): Promise<number> => {
  const query = encodeURIComponent(`to:"${address}"`);
  const res = await fetch(`${MAILPIT_URL}/api/v1/search?query=${query}`);
  const body = (await res.json()) as { messages_count: number };
  return body.messages_count;
};

export const downloadAttachment = async (
  message: MailpitMessage,
  attachment: MailpitAttachment,
): Promise<Buffer> => {
  const res = await fetch(
    `${MAILPIT_URL}/api/v1/message/${message.ID}/part/${attachment.PartID}`,
  );
  return Buffer.from(await res.arrayBuffer());
};
