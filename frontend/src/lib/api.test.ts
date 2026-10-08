import {
  api,
  clearUserToken,
  getUserToken,
  normalizeApiError,
  restoreRememberedToken,
  setUserToken,
} from "./api.ts";

function equal(actual: unknown, expected: unknown) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(JSON.stringify({ actual, expected }));
  }
}

function setupHost() {
  const store = { token: "", cleared: 0 };
  const host = {
    load_remembered_token: () => Promise.resolve(store.token),
    save_remembered_token: (token: string) => {
      store.token = token;
      return Promise.resolve(true);
    },
    clear_remembered_token: () => {
      store.token = "";
      store.cleared++;
      return Promise.resolve();
    },
  };
  const window = Object.assign(new EventTarget(), {
    pywebview: { api: host },
    __SESSION_TOKEN__: "synthetic-loopback",
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: window,
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: { cookie: "" },
  });
  return { host, store };
}

Deno.test("empty error fields and hidden validation fields always produce a visible explanation", () => {
  equal(
    normalizeApiError({ message: "Sign-in failed", fields: {} }).fields.general,
    ["Sign-in failed"],
  );
  equal(
    normalizeApiError({ fields: { auth: ["Invalid credentials"] } }).fields
      .general,
    ["Invalid credentials"],
  );
  equal(
    normalizeApiError({ fields: { schedule: ["Choose a future slot"] } })
      .message,
    "Choose a future slot",
  );
});

Deno.test("network failures keep sign-in error fields renderable", () => {
  const error = normalizeApiError(new TypeError("Failed to fetch"));
  equal(error.fields.general, ["Failed to fetch"]);
  equal(error.message, "Failed to fetch");
});

Deno.test("logout waits for native cleanup before a token can be restored", async () => {
  const { host } = setupHost();
  await setUserToken("synthetic-staff-session", true);
  let release!: () => void;
  let finished = false;
  host.clear_remembered_token = () =>
    new Promise<void>((resolve) => {
      release = resolve;
    });
  const clearing = clearUserToken().then(() => {
    finished = true;
  });
  await Promise.resolve();
  equal(getUserToken(), "");
  equal(finished, false);
  release();
  await clearing;
  equal(finished, true);
});

Deno.test("credential rotation updates remembered storage and a session-only login clears it", async () => {
  const { store } = setupHost();
  await setUserToken("synthetic-original", true);
  globalThis.fetch = () =>
    Promise.resolve(
      new Response(
        JSON.stringify({ user: { id: 1 }, token: "synthetic-rotated" }),
        { status: 200 },
      ),
    );
  await api.auth.updateProfile({ username: "synthetic-renamed" });
  equal(store.token, "synthetic-rotated");
  equal(getUserToken(), "synthetic-rotated");
  await setUserToken("synthetic-temporary", false);
  equal(store.token, "");
  equal(getUserToken(), "synthetic-temporary");
  equal(await restoreRememberedToken(), "");
});

Deno.test("remembered restore waits for a late native bridge", async () => {
  const { host, store } = setupHost();
  store.token = "synthetic-late-session";
  const win = window as unknown as EventTarget & {
    pywebview?: { api: typeof host };
    __DESKTOP_HOST__: boolean;
  };
  delete win.pywebview;
  win.__DESKTOP_HOST__ = true;
  const restored = restoreRememberedToken();
  win.pywebview = { api: host };
  win.dispatchEvent(new Event("pywebviewready"));
  equal(await restored, "synthetic-late-session");
});

Deno.test("a revoked current session clears authentication and notifies the app", async () => {
  setupHost();
  await setUserToken("synthetic-expired", false);
  let notifications = 0;
  window.addEventListener("staff-session-expired", () => {
    notifications++;
  });
  globalThis.fetch = () =>
    Promise.resolve(
      new Response(
        JSON.stringify({
          error: {
            code: "UNAUTHENTICATED",
            message: "Sign in again",
            fields: {},
          },
        }),
        { status: 401 },
      ),
    );
  try {
    await api.listPatients();
  } catch { /* Expected unauthenticated response. */ }
  equal(getUserToken(), "");
  equal(notifications, 1);
});

Deno.test("a late response from the previous account cannot log out the new account", async () => {
  setupHost();
  await setUserToken("synthetic-previous", false);
  let respond!: (response: Response) => void;
  globalThis.fetch = () =>
    new Promise<Response>((resolve) => {
      respond = resolve;
    });
  const previousRequest = api.listPatients().catch(() => undefined);
  await setUserToken("synthetic-current", false);
  respond(new Response("{}", { status: 401 }));
  await previousRequest;
  equal(getUserToken(), "synthetic-current");
});
