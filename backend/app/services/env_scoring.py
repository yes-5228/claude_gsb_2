"""环境卫生评分与退步判定规则。

评分维度（满分 100）：
- 异味等级 35 分：无异味 35 / 轻微 25 / 明显 12 / 刺鼻 0
- 地面干湿 20 分：干燥 20 / 微湿 12 / 积水 0
- 温度 10 分：舒适区间 16-28℃，每偏离 1℃ 扣 1 分
- 湿度 10 分：舒适区间 40%-70%，每偏离 5% 扣 1 分
- 通风状态 15 分：良好 15 / 一般 9 / 较差 0
- 消杀频次 10 分：当日 ≥3 次 10 / 2 次 8 / 1 次 5 / 0 次 0

温度或湿度缺测时该维度不计入，总分按已记录维度折算百分制。
"""

from app.core.constants import (
    ENV_HUMIDITY_COMFORT,
    ENV_REGRESS_ODOR_JUMP,
    ENV_REGRESS_SCORE_DROP,
    ENV_TEMP_COMFORT,
    ENV_WEIGHT_DISINFECTION,
    ENV_WEIGHT_FLOOR,
    ENV_WEIGHT_HUMIDITY,
    ENV_WEIGHT_ODOR,
    ENV_WEIGHT_TEMPERATURE,
    ENV_WEIGHT_VENTILATION,
    ODOR_LEVELS,
    FloorCondition,
    VentilationStatus,
)
from app.services.scoring import score_to_grade

_ODOR_SCORES = {0: 35.0, 1: 25.0, 2: 12.0, 3: 0.0}
_FLOOR_SCORES = {
    FloorCondition.DRY.value: 20.0,
    FloorCondition.DAMP.value: 12.0,
    FloorCondition.WET.value: 0.0,
}
_VENTILATION_SCORES = {
    VentilationStatus.GOOD.value: 15.0,
    VentilationStatus.FAIR.value: 9.0,
    VentilationStatus.POOR.value: 0.0,
}


def odor_label(level: int) -> str:
    return ODOR_LEVELS.get(level, f"{level} 级")


def _range_score(value: float, comfort: tuple[float, float], full: float, step: float) -> float:
    """舒适区间内满分，每偏离 step 个单位扣 1 分。"""
    low, high = comfort
    deviation = max(low - value, value - high, 0.0)
    return max(0.0, full - deviation / step)


def _disinfection_score(count: int) -> float:
    if count >= 3:
        return 10.0
    if count == 2:
        return 8.0
    if count == 1:
        return 5.0
    return 0.0


def score_breakdown(
    *,
    odor_level: int,
    floor_condition: str,
    temperature: float | None,
    humidity: float | None,
    ventilation: str,
    disinfection_count: int,
) -> list[dict]:
    """返回各维度得分明细，供详情页展示与总分计算。"""
    parts = [
        {
            "key": "odor",
            "label": "异味等级",
            "value": odor_label(odor_level),
            "score": _ODOR_SCORES.get(odor_level, 0.0),
            "max": float(ENV_WEIGHT_ODOR),
        },
        {
            "key": "floor",
            "label": "地面干湿",
            "value": floor_condition,
            "score": _FLOOR_SCORES.get(floor_condition, 0.0),
            "max": float(ENV_WEIGHT_FLOOR),
        },
    ]
    if temperature is not None:
        parts.append(
            {
                "key": "temperature",
                "label": "温度",
                "value": f"{temperature:g}℃",
                "score": _range_score(temperature, ENV_TEMP_COMFORT, ENV_WEIGHT_TEMPERATURE, 1.0),
                "max": float(ENV_WEIGHT_TEMPERATURE),
            }
        )
    if humidity is not None:
        parts.append(
            {
                "key": "humidity",
                "label": "湿度",
                "value": f"{humidity:g}%",
                "score": _range_score(humidity, ENV_HUMIDITY_COMFORT, ENV_WEIGHT_HUMIDITY, 5.0),
                "max": float(ENV_WEIGHT_HUMIDITY),
            }
        )
    parts.append(
        {
            "key": "ventilation",
            "label": "通风状态",
            "value": ventilation,
            "score": _VENTILATION_SCORES.get(ventilation, 0.0),
            "max": float(ENV_WEIGHT_VENTILATION),
        }
    )
    parts.append(
        {
            "key": "disinfection",
            "label": "消杀频次",
            "value": f"当日 {disinfection_count} 次",
            "score": _disinfection_score(disinfection_count),
            "max": float(ENV_WEIGHT_DISINFECTION),
        }
    )
    return parts


def calc_env_score(**kwargs) -> float:
    """按各维度得分折算百分制总分。"""
    parts = score_breakdown(**kwargs)
    full = sum(part["max"] for part in parts)
    if not full:
        return 0.0
    total = sum(part["score"] for part in parts)
    return round(total / full * 100, 1)


def evaluate_env(**kwargs) -> tuple[float, str]:
    """返回 (环境卫生得分, 评价等级)。"""
    score = calc_env_score(**kwargs)
    return score, score_to_grade(score)


def detect_regression(
    *,
    prev_score: float | None,
    prev_odor_level: int | None,
    score: float,
    odor_level: int,
) -> tuple[bool, str | None]:
    """与同一公厕上一条记录对比，判定是否明显退步。"""
    if prev_score is None:
        return False, None
    reasons: list[str] = []
    drop = round(prev_score - score, 1)
    if drop >= ENV_REGRESS_SCORE_DROP:
        reasons.append(f"得分较上次下降 {drop:g} 分")
    if prev_odor_level is not None and odor_level - prev_odor_level >= ENV_REGRESS_ODOR_JUMP:
        reasons.append(f"异味等级由「{odor_label(prev_odor_level)}」升至「{odor_label(odor_level)}」")
    return bool(reasons), "；".join(reasons) if reasons else None
