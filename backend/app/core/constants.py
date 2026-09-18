"""业务枚举与规则常量。"""

from enum import StrEnum


class RestroomStatus(StrEnum):
    NORMAL = "正常开放"
    MAINTENANCE = "维修中"
    CLOSED = "暂停使用"


class RestroomGrade(StrEnum):
    FIRST = "一类"
    SECOND = "二类"
    THIRD = "三类"


class Shift(StrEnum):
    MORNING = "早班"
    MIDDLE = "中班"
    NIGHT = "晚班"


class InspectionResult(StrEnum):
    NORMAL = "正常"
    ABNORMAL = "发现问题"


class OdorLevel(StrEnum):
    NONE = "无异味"
    MILD = "轻微异味"
    OBVIOUS = "明显异味"
    STRONG = "强烈刺鼻"


class FloorCondition(StrEnum):
    DRY = "干燥洁净"
    DAMP = "轻微潮湿"
    WET = "明显积水湿滑"
    DIRTY = "积水污渍"


class VentilationStatus(StrEnum):
    GOOD = "通风良好"
    NORMAL = "通风一般"
    POOR = "通风不良"


class IssueCategory(StrEnum):
    CLEANING = "保洁不到位"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    SAFETY = "安全隐患"
    OTHER = "其他"


class IssueSeverity(StrEnum):
    NORMAL = "一般"
    SERIOUS = "严重"
    URGENT = "紧急"


class IssueStatus(StrEnum):
    PENDING = "待整改"
    PROCESSING = "整改中"
    REVIEWING = "待验收"
    DONE = "已完成"
    CLOSED = "已关闭"


# 整改流转规则：当前状态 -> 允许流转到的状态
ISSUE_TRANSITIONS: dict[str, list[str]] = {
    IssueStatus.PENDING: [IssueStatus.PROCESSING, IssueStatus.CLOSED],
    IssueStatus.PROCESSING: [IssueStatus.REVIEWING, IssueStatus.CLOSED],
    IssueStatus.REVIEWING: [IssueStatus.DONE, IssueStatus.PROCESSING],
    IssueStatus.DONE: [IssueStatus.CLOSED],
    IssueStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成整改流水
TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (IssueStatus.PENDING, IssueStatus.PROCESSING): "开始整改",
    (IssueStatus.PENDING, IssueStatus.CLOSED): "作废关闭",
    (IssueStatus.PROCESSING, IssueStatus.REVIEWING): "提交验收",
    (IssueStatus.PROCESSING, IssueStatus.CLOSED): "终止关闭",
    (IssueStatus.REVIEWING, IssueStatus.DONE): "验收通过",
    (IssueStatus.REVIEWING, IssueStatus.PROCESSING): "验收驳回",
    (IssueStatus.DONE, IssueStatus.CLOSED): "归档关闭",
}

# 巡查检查项，每项 0-10 分
INSPECTION_CHECK_ITEMS: list[str] = [
    "地面与台阶清洁",
    "便池蹲位清洁",
    "洗手台与镜面",
    "通风除臭",
    "耗材补充",
    "垃圾清运",
    "工具与标识摆放",
    "墙面门窗卫生",
]

INSPECTION_ITEM_MAX_SCORE = 10

GRADE_EXCELLENT = "优秀"
GRADE_GOOD = "良好"
GRADE_PASS = "合格"
GRADE_FAIL = "不合格"

# 仍处于整改闭环中的状态，用于统计未整改问题
OPEN_ISSUE_STATUSES: list[str] = [
    IssueStatus.PENDING,
    IssueStatus.PROCESSING,
    IssueStatus.REVIEWING,
]

# 单检查项低于该分数视为不合格项
INSPECTION_ITEM_PROBLEM_THRESHOLD = 6

# ---------------------------------------------------------------------------
# 环境卫生量化记录（异味、地面、温湿度、通风、消杀频次）
# ---------------------------------------------------------------------------

# 温湿度、消杀频次的合理取值区间，用于接口校验
ENV_TEMPERATURE_MIN = -10.0
ENV_TEMPERATURE_MAX = 50.0
ENV_HUMIDITY_MIN = 0.0
ENV_HUMIDITY_MAX = 100.0
ENV_DISINFECTION_MIN = 0
ENV_DISINFECTION_MAX = 12

# 适宜温湿度区间：落在区间内得满分，越偏离扣分越重
ENV_TEMPERATURE_IDEAL = (18.0, 26.0)
ENV_HUMIDITY_IDEAL = (40.0, 70.0)
# 每偏离适宜区间 1℃ / 1 个百分点所扣的分数
ENV_TEMPERATURE_STEP_PENALTY = 5.0
ENV_HUMIDITY_STEP_PENALTY = 1.5

# 各异味等级对应的卫生子分（异味越重得分越低）
ODOR_SCORES: dict[str, float] = {
    OdorLevel.NONE: 100.0,
    OdorLevel.MILD: 80.0,
    OdorLevel.OBVIOUS: 50.0,
    OdorLevel.STRONG: 20.0,
}

# 地面干湿情况对应的卫生子分
FLOOR_SCORES: dict[str, float] = {
    FloorCondition.DRY: 100.0,
    FloorCondition.DAMP: 80.0,
    FloorCondition.WET: 50.0,
    FloorCondition.DIRTY: 20.0,
}

# 通风状态对应的卫生子分
VENTILATION_SCORES: dict[str, float] = {
    VentilationStatus.GOOD: 100.0,
    VentilationStatus.NORMAL: 75.0,
    VentilationStatus.POOR: 40.0,
}

# 消杀频次（次/日）与子分：达到建议频次即满分，不足按比例给分
ENV_DISINFECTION_IDEAL = 3
ENV_DISINFECTION_FULL = 100.0
ENV_DISINFECTION_STEP = 30.0  # 每少 1 次扣 30 分

# 环境卫生评价各指标权重（合计 100）
ENV_WEIGHTS: dict[str, float] = {
    "odor": 30.0,
    "floor": 20.0,
    "temperature": 10.0,
    "humidity": 10.0,
    "ventilation": 15.0,
    "disinfection": 15.0,
}

# 环境卫生评价等级沿用优秀/良好/合格/不合格
ENV_GRADE_EXCELLENT = 90.0
ENV_GRADE_GOOD = 80.0
ENV_GRADE_PASS = 60.0

# 等级排序，用于判定是否跨档退步
ENV_GRADE_ORDER = [GRADE_FAIL, GRADE_PASS, GRADE_GOOD, GRADE_EXCELLENT]

# 较上一次同公厕记录，环境卫生分下降达到该差值即判定为明显退步
ENV_REGRESSION_SCORE_DELTA = 15.0
