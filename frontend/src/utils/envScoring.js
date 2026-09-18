/**
 * 环境卫生评分规则（与后端 app/services/env_scoring.py 保持一致），
 * 用于登记表单的实时得分预览。
 */

export const ODOR_LEVELS = [
  { level: 0, label: '无异味' },
  { level: 1, label: '轻微异味' },
  { level: 2, label: '明显异味' },
  { level: 3, label: '刺鼻异味' },
];

export const FLOOR_CONDITIONS = ['干燥', '微湿', '积水'];
export const VENTILATION_STATUSES = ['良好', '一般', '较差'];

const ODOR_SCORES = { 0: 35, 1: 25, 2: 12, 3: 0 };
const FLOOR_SCORES = { 干燥: 20, 微湿: 12, 积水: 0 };
const VENTILATION_SCORES = { 良好: 15, 一般: 9, 较差: 0 };

const TEMP_COMFORT = [16, 28];
const HUMIDITY_COMFORT = [40, 70];

export function odorLabel(level) {
  return ODOR_LEVELS.find((item) => item.level === Number(level))?.label ?? `${level} 级`;
}

function rangeScore(value, [low, high], full, step) {
  const deviation = Math.max(low - value, value - high, 0);
  return Math.max(0, full - deviation / step);
}

function disinfectionScore(count) {
  if (count >= 3) return 10;
  if (count === 2) return 8;
  if (count === 1) return 5;
  return 0;
}

/** 计算环境卫生百分制得分；温湿度缺测时该维度不计入。 */
export function calcEnvScore({
  odorLevel,
  floorCondition,
  temperature,
  humidity,
  ventilation,
  disinfectionCount,
}) {
  let total = (ODOR_SCORES[odorLevel] ?? 0) + (FLOOR_SCORES[floorCondition] ?? 0);
  let full = 35 + 20;
  if (temperature !== null && temperature !== undefined && temperature !== '') {
    total += rangeScore(Number(temperature), TEMP_COMFORT, 10, 1);
    full += 10;
  }
  if (humidity !== null && humidity !== undefined && humidity !== '') {
    total += rangeScore(Number(humidity), HUMIDITY_COMFORT, 10, 5);
    full += 10;
  }
  total += (VENTILATION_SCORES[ventilation] ?? 0) + disinfectionScore(Number(disinfectionCount) || 0);
  full += 15 + 10;
  return Math.round((total / full) * 1000) / 10;
}

export function envGradeOf(score) {
  if (score >= 90) return '优秀';
  if (score >= 80) return '良好';
  if (score >= 70) return '合格';
  return '不合格';
}
