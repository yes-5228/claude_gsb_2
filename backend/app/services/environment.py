"""环境卫生量化评价。

把巡查时登记的异味等级、地面干湿、温湿度、通风状态与消杀频次折算为
0-100 的环境卫生分并定级；同时提供同一公厕跨时间记录的退步判定。
"""

from app.core.constants import (
    ENV_DISINFECTION_FULL,
    ENV_DISINFECTION_IDEAL,
    ENV_DISINFECTION_STEP,
    ENV_GRADE_EXCELLENT,
    ENV_GRADE_GOOD,
    ENV_GRADE_PASS,
    ENV_HUMIDITY_IDEAL,
    ENV_HUMIDITY_STEP_PENALTY,
    ENV_REGRESSION_SCORE_DELTA,
    ENV_TEMPERATURE_IDEAL,
    ENV_TEMPERATURE_STEP_PENALTY,
    ENV_WEIGHTS,
    FLOOR_SCORES,
    GRADE_EXCELLENT,
    GRADE_FAIL,
    GRADE_GOOD,
    GRADE_PASS,
    ODOR_SCORES,
    VENTILATION_SCORES,
)


def _range_penalty(value: float, ideal: tuple[float, float], step_penalty: float) -> float:
    """落在适宜区间得满分，每偏离区间 1 个单位扣 step_penalty 分。"""
    low, high = ideal
    if value < low:
        deviation = low - value
    elif value > high:
        deviation = value - high
    else:
        return 100.0
    return max(0.0, 100.0 - deviation * step_penalty)


def odor_subscore(odor: str) -> float:
    return ODOR_SCORES.get(odor, 0.0)


def floor_subscore(floor: str) -> float:
    return FLOOR_SCORES.get(floor, 0.0)


def ventilation_subscore(ventilation: str) -> float:
    return VENTILATION_SCORES.get(ventilation, 0.0)


def temperature_subscore(temperature: float) -> float:
    return _range_penalty(temperature, ENV_TEMPERATURE_IDEAL, ENV_TEMPERATURE_STEP_PENALTY)


def humidity_subscore(humidity: float) -> float:
    return _range_penalty(humidity, ENV_HUMIDITY_IDEAL, ENV_HUMIDITY_STEP_PENALTY)


def disinfection_subscore(disinfection_count: int) -> float:
    if disinfection_count >= ENV_DISINFECTION_IDEAL:
        return ENV_DISINFECTION_FULL
    return max(0.0, ENV_DISINFECTION_FULL - (ENV_DISINFECTION_IDEAL - disinfection_count) * ENV_DISINFECTION_STEP)


def env_grade_of(score: float) -> str:
    if score >= ENV_GRADE_EXCELLENT:
        return GRADE_EXCELLENT
    if score >= ENV_GRADE_GOOD:
        return GRADE_GOOD
    if score >= ENV_GRADE_PASS:
        return GRADE_PASS
    return GRADE_FAIL


def evaluate_env(env: dict) -> tuple[float, str, dict[str, float]] | None:
    """根据登记的环境指标计算 (环境卫生分, 等级, 各子项分)。

    env 为空或缺少必要字段时返回 None，表示本次巡查未登记环境信息。
    """
    if not env:
        return None

    odor = env.get("odor_level")
    floor = env.get("floor_condition")
    ventilation = env.get("ventilation")
    temperature = env.get("temperature")
    humidity = env.get("humidity")
    disinfection = env.get("disinfection_count")

    required = (odor, floor, ventilation, temperature, humidity, disinfection)
    if any(value is None for value in required):
        return None

    sub = {
        "odor": odor_subscore(odor),
        "floor": floor_subscore(floor),
        "temperature": temperature_subscore(float(temperature)),
        "humidity": humidity_subscore(float(humidity)),
        "ventilation": ventilation_subscore(ventilation),
        "disinfection": disinfection_subscore(int(disinfection)),
    }
    total_weight = sum(ENV_WEIGHTS.values())
    score = sum(sub[key] * ENV_WEIGHTS[key] for key in ENV_WEIGHTS) / total_weight
    return round(score, 1), env_grade_of(score), {key: round(value, 1) for key, value in sub.items()}


def is_regression(current_score: float | None, current_grade: str | None,
                  previous_score: float | None, previous_grade: str | None) -> bool:
    """同一公厕本次环境记录相对上一次是否明显退步。

    满足任一条件即判定为明显退步：
    1. 环境卫生分下降达到阈值（默认 15 分）；
    2. 由合格及以上跌入「不合格」档。
    仅仅在优秀/良好/合格边界附近小幅波动不算明显退步。
    当前或上次缺少环境记录时不判定。
    """
    if current_score is None or previous_score is None:
        return False
    if current_score <= previous_score - ENV_REGRESSION_SCORE_DELTA:
        return True
    if current_grade == GRADE_FAIL and previous_grade is not None and previous_grade != GRADE_FAIL:
        return True
    return False
