"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


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


def test_environment_records_and_regression(client, restroom):
    dictionaries = client.get("/api/v1/meta/dictionaries").json()
    assert {item["level"] for item in dictionaries["odor_levels"]} == {0, 1, 2, 3}
    assert "积水" in dictionaries["floor_conditions"]
    assert "较差" in dictionaries["ventilation_statuses"]

    # 第一条记录：环境良好，满分
    good = client.post(
        "/api/v1/environment-records",
        json={
            "restroom_id": restroom["id"],
            "recorder": "李巡查",
            "record_time": (datetime.now() - timedelta(hours=5)).isoformat(),
            "odor_level": 0,
            "floor_condition": "干燥",
            "temperature": 25,
            "humidity": 55,
            "ventilation": "良好",
            "disinfection_count": 3,
        },
    ).json()
    assert good["score"] == 100.0
    assert good["grade"] == "优秀"
    assert good["regressed"] is False
    assert good["score_delta"] is None
    assert good["odor_label"] == "无异味"
    assert len(good["breakdown"]) == 6

    # 第二条记录：异味刺鼻、地面积水、通风较差且未消杀 → 明显退步
    bad = client.post(
        "/api/v1/environment-records",
        json={
            "restroom_id": restroom["id"],
            "recorder": "李巡查",
            "odor_level": 3,
            "floor_condition": "积水",
            "temperature": 35,
            "humidity": 95,
            "ventilation": "较差",
            "disinfection_count": 0,
            "remark": "雨天返潮，排风故障",
        },
    ).json()
    assert bad["grade"] == "不合格"
    assert bad["regressed"] is True
    assert bad["prev_score"] == 100.0
    assert bad["score_delta"] < 0
    assert "下降" in bad["regress_reason"]
    assert "异味" in bad["regress_reason"]

    # 台账列表标记退步，并支持按退步筛选
    listed = client.get("/api/v1/restrooms", params={"env_regressed": "true"}).json()
    row = next((item for item in listed["items"] if item["id"] == restroom["id"]), None)
    assert row is not None
    assert row["env_regressed"] is True
    assert row["env_grade"] == "不合格"
    excluded = client.get("/api/v1/restrooms", params={"env_regressed": "false"}).json()
    assert restroom["id"] not in [item["id"] for item in excluded["items"]]

    # 台账详情带环境卫生汇总
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["env_record_count"] == 2
    assert detail["env_regressed"] is True
    assert detail["env_regress_reason"]

    # 同一公厕多次记录按时间对比
    trend = client.get(
        "/api/v1/environment-records/trend", params={"restroom_id": restroom["id"]}
    ).json()
    assert trend["record_count"] == 2
    assert trend["latest_regressed"] is True
    assert [point["score"] for point in trend["points"]] == [100.0, bad["score"]]
    assert trend["points"][1]["score_delta"] == bad["score_delta"]

    # 记录列表按退步与等级筛选
    regressed_only = client.get(
        "/api/v1/environment-records", params={"regressed": "true"}
    ).json()
    assert regressed_only["meta"]["total"] == 1
    assert regressed_only["items"][0]["id"] == bad["id"]
    excellent = client.get(
        "/api/v1/environment-records",
        params={"restroom_id": restroom["id"], "grade": "优秀"},
    ).json()
    assert excellent["meta"]["total"] == 1

    # 更新记录后重算得分与退步标记
    updated = client.patch(
        f"/api/v1/environment-records/{bad['id']}",
        json={"odor_level": 0, "ventilation": "良好", "disinfection_count": 3,
              "floor_condition": "干燥", "temperature": 26, "humidity": 60},
    ).json()
    assert updated["regressed"] is False
    assert updated["score_delta"] == 0.0

    # 异味等级越界被拒绝
    rejected = client.post(
        "/api/v1/environment-records",
        json={"restroom_id": restroom["id"], "recorder": "李巡查", "odor_level": 5},
    )
    assert rejected.status_code == 422

    # 删除后趋势随之变化
    assert client.delete(f"/api/v1/environment-records/{bad['id']}").status_code == 200
    trend_after = client.get(
        "/api/v1/environment-records/trend", params={"restroom_id": restroom["id"]}
    ).json()
    assert trend_after["record_count"] == 1
    assert trend_after["latest_regressed"] is False
