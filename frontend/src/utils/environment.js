// 环境卫生量化评价：与后端 app/services/environment.py 规则保持一致。

export const ENV_WEIGHTS = {
  odor: 30,
  floor: 20,
  temperature: 10,
  humidity: 10,
  ventilation: 15,
  disinfection: 15,
};

export const ODOR_SUBSCORES = {
  无异味: 100,
  轻微异味: 80,
  明显异味: 50,
  强烈刺鼻: 20,
};

export const FLOOR_SUBSCORES = {
  干燥洁净: 100,
  轻微潮湿: 80,
  明显积水湿滑: 50,
  积水污渍: 20,
};

export const VENTILATION_SUBSCORES = {
  通风良好: 100,
  通风一般: 75,
  通风不良: 40,
};

export const TEMPERATURE_IDEAL = [18, 26];
export const HUMIDITY_IDEAL = [40, 70];
const TEMPERATURE_STEP_PENALTY = 5;
const HUMIDITY_STEP_PENALTY = 1.5;

export const DISINFECTION_IDEAL = 3;
const DISINFECTION_STEP = 30;

export const REGRESSION_SCORE_DELTA = 15;

function rangeSubscore(value, [low, high], stepPenalty) {
  const num = Number(value);
  if (Number.isNaN(num)) return 0;
  let deviation = 0;
  if (num < low) deviation = low - num;
  else if (num > high) deviation = num - high;
  return Math.max(0, 100 - deviation * stepPenalty);
}

export function envSubscores(env) {
  if (!env) return null;
  const disinfection = Number(env.disinfection_count || 0);
  return {
    odor: ODOR_SUBSCORES[env.odor_level] ?? 0,
    floor: FLOOR_SUBSCORES[env.floor_condition] ?? 0,
    temperature: rangeSubscore(env.temperature, TEMPERATURE_IDEAL, TEMPERATURE_STEP_PENALTY),
    humidity: rangeSubscore(env.humidity, HUMIDITY_IDEAL, HUMIDITY_STEP_PENALTY),
    ventilation: VENTILATION_SUBSCORES[env.ventilation] ?? 0,
    disinfection:
      disinfection >= DISINFECTION_IDEAL
        ? 100
        : Math.max(0, 100 - (DISINFECTION_IDEAL - disinfection) * DISINFECTION_STEP),
  };
}

/** 保留 1 位小数，四舍六入五成双，与后端 Python round(x, 1) 保持一致。 */
function round1(value) {
  const scaled = value * 10;
  const floor = Math.floor(scaled);
  const fraction = scaled - floor;
  if (fraction > 0.5) return (floor + 1) / 10;
  if (fraction < 0.5) return floor / 10;
  return (floor % 2 === 0 ? floor : floor + 1) / 10;
}

export function calcEnvScore(env) {
  const sub = envSubscores(env);
  if (!sub) return null;
  const totalWeight = Object.values(ENV_WEIGHTS).reduce((sum, w) => sum + w, 0);
  const weighted = Object.entries(ENV_WEIGHTS).reduce(
    (sum, [key, weight]) => sum + sub[key] * weight,
    0,
  );
  return round1(weighted / totalWeight);
}

export function envGradeOf(score) {
  if (score >= 90) return '优秀';
  if (score >= 80) return '良好';
  if (score >= 60) return '合格';
  return '不合格';
}

/** 是否登记了完整的环境指标（用于决定是否提交 env 字段）。 */
export function hasEnv(env) {
  if (!env) return false;
  return ['odor_level', 'floor_condition', 'temperature', 'humidity', 'ventilation', 'disinfection_count']
    .every((key) => env[key] !== '' && env[key] !== null && env[key] !== undefined);
}

/** 同一公厕本次相对上一次是否明显退步。 */
export function envIsRegressed(currentScore, currentGrade, prevScore, prevGrade) {
  if (currentScore == null || prevScore == null) return false;
  if (currentScore <= prevScore - REGRESSION_SCORE_DELTA) return true;
  if (currentGrade === '不合格' && prevGrade && prevGrade !== '不合格') return true;
  return false;
}
