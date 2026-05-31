/**
 * Deterministic mock presentation data for patient discovery (until ratings API exists).
 */
export function mockRatingFromId(id: string | number | undefined | null): number {
  if (id == null) return 4.6;
  const s = String(id);
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) | 0;
  const t = (Math.abs(h) % 80) / 10;
  return Math.round((4.0 + t) * 10) / 10;
}

export function mockReviewCountFromId(id: string | number | undefined | null): number {
  if (id == null) return 86;
  const s = String(id);
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 17 + s.charCodeAt(i)) | 0;
  return 30 + (Math.abs(h) % 400);
}

export function initialsFromName(name: string): string {
  const p = name.trim().split(/\s+/).filter(Boolean);
  if (p.length === 0) return '?';
  if (p.length === 1) return p[0]!.slice(0, 2).toUpperCase();
  return `${p[0]![0]!}${p[p.length - 1]![0]!}`.toUpperCase();
}
