// Runs against the Firestore emulator from docker-compose (FIRESTORE_EMULATOR_HOST, default localhost:8080).
import { readFileSync } from "node:fs";
import { afterAll, beforeAll, beforeEach, describe, test } from "vitest";
import { assertFails, assertSucceeds, initializeTestEnvironment } from "@firebase/rules-unit-testing";
import { collection, doc, getDoc, getDocs, query, setDoc, where } from "firebase/firestore";

const [host, port] = (process.env.FIRESTORE_EMULATOR_HOST ?? "localhost:8080").split(":");
let env;

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: "demo-launchpad",
    firestore: {
      host,
      port: Number(port),
      rules: readFileSync(new URL("../firestore.rules", import.meta.url), "utf8"),
    },
  });
});

afterAll(() => env.cleanup());

beforeEach(async () => {
  await env.clearFirestore();
  // Seed as the server would (Admin SDK path: rules disabled).
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, "campaigns/c-a"), { org_id: "org-a", status: "draft", created_at: 1 });
    await setDoc(doc(db, "campaigns/c-a/runs/r1/steps/s1"), { node: "merger", status: "done" });
    await setDoc(doc(db, "campaigns/c-b"), { org_id: "org-b", status: "draft", created_at: 2 });
    await setDoc(doc(db, "orgs/org-a/members/alice"), { role: "marketer" });
    await setDoc(doc(db, "guardrail_events/g1"), { campaign_id: "c-a", at: 1 });
  });
});

const alice = () => env.authenticatedContext("alice", { org_id: "org-a", role: "marketer" }).firestore();
const bob = () => env.authenticatedContext("bob", { org_id: "org-b", role: "marketer" }).firestore();
const anon = () => env.unauthenticatedContext().firestore();

describe("campaigns", () => {
  test("member reads own org's campaign", () => assertSucceeds(getDoc(doc(alice(), "campaigns/c-a"))));
  test("user from another org cannot read it", () => assertFails(getDoc(doc(bob(), "campaigns/c-a"))));
  test("signed-out user cannot read it", () => assertFails(getDoc(doc(anon(), "campaigns/c-a"))));

  test("member reads nested timeline steps", () =>
    assertSucceeds(getDoc(doc(alice(), "campaigns/c-a/runs/r1/steps/s1"))));
  test("other org cannot read nested steps", () =>
    assertFails(getDoc(doc(bob(), "campaigns/c-a/runs/r1/steps/s1"))));

  test("list filtered by own org succeeds", () =>
    assertSucceeds(getDocs(query(collection(alice(), "campaigns"), where("org_id", "==", "org-a")))));
  test("unfiltered list is rejected", () => assertFails(getDocs(collection(alice(), "campaigns"))));

  test("browser cannot create a campaign", () =>
    assertFails(setDoc(doc(alice(), "campaigns/new"), { org_id: "org-a" })));
  test("browser cannot write a step", () =>
    assertFails(setDoc(doc(alice(), "campaigns/c-a/runs/r1/steps/s2"), { status: "done" })));
});

describe("members", () => {
  test("user reads own membership", () => assertSucceeds(getDoc(doc(alice(), "orgs/org-a/members/alice"))));
  test("user cannot read another org's members", () =>
    assertFails(getDoc(doc(bob(), "orgs/org-a/members/alice"))));
  test("user cannot change their role", () =>
    assertFails(setDoc(doc(alice(), "orgs/org-a/members/alice"), { role: "brand_admin" })));
});

describe("guardrail_events", () => {
  test("closed to signed-in users", () => assertFails(getDoc(doc(alice(), "guardrail_events/g1"))));
});

describe("everything else", () => {
  test("unknown collections are denied", () => assertFails(getDoc(doc(alice(), "anything/x"))));
});
