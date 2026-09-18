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


class FloorCondition(StrEnum):
    DRY = "干燥"
    DAMP = "微湿"
    WET = "积水"


class VentilationStatus(StrEnum):
    GOOD = "良好"
    FAIR = "一般"
    POOR = "较差"


# 异味等级：数值越大异味越重，便于量化对比
ODOR_LEVELS: dict[int, str] = {
    0: "无异味",
    1: "轻微异味",
    2: "明显异味",
    3: "刺鼻异味",
}
ODOR_LEVEL_MIN = min(ODOR_LEVELS)
ODOR_LEVEL_MAX = max(ODOR_LEVELS)


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

# 环境卫生评分权重（满分 100）：异味 35、地面 20、温度 10、湿度 10、通风 15、消杀 10
ENV_WEIGHT_ODOR = 35
ENV_WEIGHT_FLOOR = 20
ENV_WEIGHT_TEMPERATURE = 10
ENV_WEIGHT_HUMIDITY = 10
ENV_WEIGHT_VENTILATION = 15
ENV_WEIGHT_DISINFECTION = 10

# 温度舒适区间（℃）与湿度舒适区间（%），超出区间按偏离程度扣分
ENV_TEMP_COMFORT = (16.0, 28.0)
ENV_HUMIDITY_COMFORT = (40.0, 70.0)

# 明显退步判定：得分较上一次下降超过该分值，或异味等级一次上升超过该级数
ENV_REGRESS_SCORE_DROP = 15.0
ENV_REGRESS_ODOR_JUMP = 2
