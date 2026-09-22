import { t, dateLocale } from "./i18n";
import type { DiscoveryItem } from "./discoveryTypes";
import type { Profile } from "./types";
export function sourceError(code: string | null): string {
  if (code === "GMAIL_API_DISABLED")
    return t(
      "Enable the Gmail API in the Google Cloud project used by this OAuth client, then enable the source again.",
    );
  if (code === "SOURCE_ACCESS_DENIED")
    return t("Access was refused. The source has been paused.");
  if (code === "SOURCE_RATE_LIMIT")
    return t(
      "The provider asked us to wait. The next check has been rescheduled.",
    );
  if (code === "GMAIL_LABEL_MISSING")
    return t(
      "The Gmail label is missing. Choose a custom label and enable the source again.",
    );
  if (code === "GMAIL_RECONNECT" || code === "GMAIL_NOT_CONFIGURED")
    return t("Reconnect Gmail before checking this source.");
  return t(
    "The source could not be checked. Existing opportunities were preserved.",
  );
}

export function discoveryDate(value: string | null) {
  return value
    ? new Date(value).toLocaleString(dateLocale())
    : t("Not yet checked");
}

export function preferenceHints(
  item: DiscoveryItem,
  profile: Profile,
): string[] {
  if (item.item_type !== "vacancy") return [];
  const title = item.title.toLocaleLowerCase("en-GB");
  const location = (item.location ?? "").toLocaleLowerCase("en-GB");
  return [
    ...profile.target_roles.filter(
      (role) => role.trim() && title.includes(role.toLocaleLowerCase("en-GB")),
    ),
    ...profile.locations.filter(
      (place) =>
        place.trim() && location.includes(place.toLocaleLowerCase("en-GB")),
    ),
  ];
}
