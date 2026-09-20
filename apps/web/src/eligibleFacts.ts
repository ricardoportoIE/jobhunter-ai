import type { Fact } from "./types";

/** Preselect only currently valid facts already permitted for matching. */
export function eligibleMatchingFacts(facts: Fact[], now = Date.now()) {
  return facts.filter(
    (fact) =>
      fact.status === "verified" &&
      fact.allowed_uses.includes("matching") &&
      fact.sensitivity !== "sensitive" &&
      (!fact.valid_from || Date.parse(fact.valid_from) <= now) &&
      (!fact.valid_until || Date.parse(fact.valid_until) > now),
  );
}
