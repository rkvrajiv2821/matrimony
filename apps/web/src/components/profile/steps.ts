export const STEPS = [
  "basic",
  "community",
  "education",
  "career",
  "family",
  "lifestyle",
  "photos",
  "preferences",
] as const;

export type Step = (typeof STEPS)[number];

export const REQUIRED_STEPS: ReadonlySet<Step> = new Set([
  "basic",
  "community",
  "education",
  "career",
  "photos",
]);

export function isStep(s: string): s is Step {
  return (STEPS as readonly string[]).includes(s);
}

/** Which completion flags mark a wizard step as done. */
export const STEP_COMPLETION: Record<Step, string[]> = {
  basic: ["basic", "location"],
  community: ["community"],
  education: ["education"],
  career: ["career"],
  family: ["family"],
  lifestyle: ["lifestyle"],
  photos: ["photo"],
  preferences: ["preferences"],
};

export const HEIGHTS_CM = Array.from({ length: 220 - 120 + 1 }, (_, i) => 120 + i);

export function heightLabel(cm: number): string {
  const inches = Math.round(cm / 2.54);
  return `${cm} cm (${Math.floor(inches / 12)}′${inches % 12}″)`;
}
