export const CREDIT_PER_YUAN = 100;
export const VIDEO_CREDIT_UNIT = 10;

export function yuanToVideoCredits(yuanCost: number): number {
  const rawCredits = Math.ceil(Math.max(0, yuanCost) * CREDIT_PER_YUAN);
  return Math.ceil(rawCredits / VIDEO_CREDIT_UNIT) * VIDEO_CREDIT_UNIT;
}

export function formatVideoCreditEstimate(
  yuanPerSecond: number,
  durationSeconds: number,
  count: number,
): string {
  const yuanCost = Math.max(1, durationSeconds) * Math.max(1, count) * Math.max(0, yuanPerSecond);
  const credits = yuanToVideoCredits(yuanCost);
  return `约 ${credits} 积分`;
}
