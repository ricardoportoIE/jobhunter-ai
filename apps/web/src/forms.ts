export const value = (form: FormData, name: string) =>
  String(form.get(name) ?? "").trim();
export const optional = (form: FormData, name: string) =>
  value(form, name) || null;
export const lines = (form: FormData, name: string) =>
  value(form, name)
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
