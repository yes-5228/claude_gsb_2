"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


def good_env(**overrides) -> dict:
    payload = {
        "odor_level": "无异味",
        "floor_condition": "干燥洁净",
        "temperature": 23.0,
        "humidity": 55.0,
        "ventilation": "通风良好",
        "disinfection_count": 3,
    }
    payload.update(overrides)
    return payload


def bad_env(**overrides) -> dict:
    payload = {
        "odor_level": "强烈刺鼻",
        "floor_condition": "积水污渍",
        "temperature": 38.0,
        "humidity": 92.0,
        "ventilation": "通风不良",
        "disinfection_count": 0,
    }
    payload.update(overrides)
    return payload


def test_health_and_dictionaries(client):
    assert client.get("/health").json()["status"] == "ok"
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "待整改" in payload["issue_status"]
    assert len(payload["inspection_check_items"]) == 8
    assert payload["issue_transitions"]["待整改"] == ["整改中", "已关闭"]


def test_restroom_crud_and_delete_guard(client, restroom):
    assert restroom["code"].startswith("WC-")

    listed = client.get("/api/v1/restrooms", params={"district": "测试区"}).json()
    assert listed["meta"]["total"] >= 1

    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["inspection_count"] == 0
    assert detail["open_issue_count"] == 0

    updated = client.patch(
        f"/api/v1/restrooms/{restroom['id']}", json={"status": "维修中", "manager": "新责任人"}
    ).json()
    assert updated["status"] == "维修中"
    assert updated["manager"] == "新责任人"

    # 存在关联数据时不允许直接删除
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "测试巡查员",
            "shift": "早班",
            "items": full_items(9),
        },
    )
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").status_code == 404


def test_inspection_scoring_and_filter(client, restroom):
    good = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "中班",
            "items": full_items(9),
            "remark": "整体良好",
        },
    ).json()
    assert good["score"] == 90.0
    assert good["grade"] == "优秀"
    assert good["result"] == "正常"

    bad_items = full_items(9)
    bad_items[0]["score"] = 3
    bad_items[0]["remark"] = "地面污渍"
    bad = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "晚班",
            "items": bad_items,
        },
    ).json()
    assert bad["result"] == "发现问题"
    assert bad["score"] < 90

    filtered = client.get(
        "/api/v1/inspections", params={"result": "发现问题", "restroom_id": restroom["id"]}
    ).json()
    assert filtered["meta"]["total"] == 1
    assert filtered["items"][0]["id"] == bad["id"]
    assert filtered["items"][0]["restroom"]["name"] == restroom["name"]

    today = datetime.now().date().isoformat()
    ranged = client.get(
        "/api/v1/inspections", params={"date_from": today, "date_to": today}
    ).json()
    assert ranged["meta"]["total"] == 2

    duplicate = full_items(5) + [{"name": "地面与台阶清洁", "score": 4}]
    rejected = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": duplicate},
    )
    assert rejected.status_code == 400

    empty = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": []},
    )
    assert empty.status_code == 422


def test_issue_lifecycle(client, restroom):
    inspection = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "王巡查",
            "items": full_items(4),
        },
    ).json()

    issue = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "地面污渍未清理",
            "description": "巡查发现地面有明显污渍",
            "category": "保洁不到位",
            "severity": "严重",
            "reporter": "王巡查",
            "assignee": "保洁班组",
            "deadline": (datetime.now() - timedelta(days=1)).isoformat(),
        },
    ).json()
    assert issue["status"] == "待整改"
    assert len(issue["records"]) == 1
    assert issue["records"][0]["action"] == "上报问题"

    # 越级流转被拒绝：待整改 -> 已完成
    invalid = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "已完成", "operator": "值班长"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/issues/{issue['id']}/transitions").json()
    assert {option["status"] for option in options} == {"整改中", "已关闭"}

    processing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "保洁班组张伟", "remark": "已安排清洗"},
    ).json()
    assert processing["status"] == "整改中"
    assert processing["assignee"] == "保洁班组"

    reviewing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "待验收", "operator": "保洁班组张伟", "remark": "整改完成待验收"},
    ).json()
    assert reviewing["status"] == "待验收"

    # 验收驳回回到整改中
    rejected = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "王巡查", "remark": "角落仍有残留"},
    ).json()
    assert rejected["status"] == "整改中"
    assert rejected["records"][-1]["action"] == "验收驳回"

    for target in ("待验收", "已完成", "已关闭"):
        payload = {"to_status": target, "operator": "值班长", "remark": f"流转到{target}"}
        response = client.post(f"/api/v1/issues/{issue['id']}/transitions", json=payload)
        assert response.status_code == 200, response.text
    final = response.json()
    assert final["status"] == "已关闭"
    assert final["closed_at"] is not None
    assert [record["to_status"] for record in final["records"]][-1] == "已关闭"

    closed_record = client.post(
        f"/api/v1/issues/{issue['id']}/records",
        json={"action": "整改进度", "operator": "值班长", "remark": "补充说明"},
    )
    assert closed_record.status_code == 400

    overdue = client.get("/api/v1/issues", params={"overdue": "true"}).json()
    assert overdue["meta"]["total"] == 0

    # 巡查记录可反查关联问题数量
    detail = client.get(f"/api/v1/inspections/{inspection['id']}").json()
    assert detail["issue_count"] == 1


def test_issue_requires_matching_restroom(client, restroom):
    other = client.post(
        "/api/v1/restrooms",
        json={"name": "另一座公厕", "district": "测试区", "address": "测试路 2 号"},
    ).json()
    inspection = client.post(
        "/api/v1/inspections",
        json={"restroom_id": other["id"], "inspector": "周巡查", "items": full_items(9)},
    ).json()
    mismatch = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "关联错误",
        },
    )
    assert mismatch.status_code == 400
    assert "不一致" in mismatch.json()["detail"]


def test_dashboard_stats(client, restroom):
    payload = client.get("/api/v1/stats/dashboard", params={"trend_days": 7}).json()
    overview = payload["overview"]
    assert overview["restroom_total"] >= 1
    assert overview["inspection_total"] >= 1
    assert len(payload["inspection_trend"]) == 7
    assert {item["name"] for item in payload["issue_by_status"]} == {
        "待整改",
        "整改中",
        "待验收",
        "已完成",
        "已关闭",
    }
    assert payload["top_restrooms"]
    assert "rectification_rate" in overview


def test_environmental_recording_and_evaluation(client, restroom):
    dicts = client.get("/api/v1/meta/dictionaries").json()
    assert dicts["odor_levels"][0] == "无异味"
    assert dicts["floor_conditions"]
    assert dicts["ventilation_statuses"]
    assert dicts["env_limits"]["regression_delta"] == 15.0

    created = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "环境巡查员",
            "shift": "早班",
            "items": full_items(9),
            "env": good_env(),
        },
    )
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["env"] is not None
    assert record["env"]["env_score"] == 100.0
    assert record["env"]["env_grade"] == "优秀"
    # 首条记录没有上一次可对比，不标记退步
    assert record["env_regressed"] is False
    assert record["prev_env_score"] is None

    # 非法温湿度被参数校验拦截
    invalid = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "环境巡查员",
            "items": full_items(8),
            "env": good_env(humidity=150),
        },
    )
    assert invalid.status_code == 422


def test_environmental_regression_flag_and_ledger(client, restroom):
    base = datetime.now() - timedelta(days=3)

    def post(env, when):
        return client.post(
            "/api/v1/inspections",
            json={
                "restroom_id": restroom["id"],
                "inspector": "环境巡查员",
                "items": full_items(9 if env == good_env() else 6),
                "env": env,
                "inspect_time": when.isoformat(),
            },
        ).json()

    first = post(good_env(), base)
    second = post(good_env(temperature=24.5), base + timedelta(days=1))
    assert second["prev_env_score"] == 100.0
    assert second["env_regressed"] is False

    # 第三次明显恶化：应标记退步并带上上次评分
    third = post(bad_env(), base + timedelta(days=2))
    assert third["env_regressed"] is True
    assert third["prev_env_grade"] == "优秀"
    assert third["env"]["env_grade"] == "不合格"

    # 列表中的最新记录同样带退步标记
    listed = client.get(
        "/api/v1/inspections", params={"restroom_id": restroom["id"], "order": "desc"}
    ).json()
    latest = listed["items"][0]
    assert latest["id"] == third["id"]
    assert latest["env_regressed"] is True
    assert latest["env_grade"] == "不合格"

    # 可按环境等级筛选
    fail_only = client.get(
        "/api/v1/inspections", params={"restroom_id": restroom["id"], "env_grade": "不合格"}
    ).json()
    assert fail_only["meta"]["total"] == 1

    # 台账列表与详情同步标记退步
    ledger = client.get("/api/v1/restrooms", params={"keyword": restroom["name"]}).json()
    row = next(item for item in ledger["items"] if item["id"] == restroom["id"])
    assert row["env_regressed"] is True
    assert row["latest_env_grade"] == "不合格"

    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["env_regressed"] is True
    assert detail["latest_env_score"] == third["env"]["env_score"]
    assert detail["prev_env_grade"] == "优秀"
    assert detail["env_regression_count"] >= 1

    # 看板统计退步公厕与环境记录数
    overview = client.get("/api/v1/stats/overview").json()
    assert overview["env_record_total"] >= 3
    assert overview["env_regression_restrooms"] >= 1
