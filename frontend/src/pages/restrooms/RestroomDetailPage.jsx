import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { environmentApi } from '../../api/environment.js';
import { inspectionApi } from '../../api/inspections.js';
import { issueApi } from '../../api/issues.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import DetailList from '../../components/DetailList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { DeltaText, GradeTag, RegressTag, ScorePill, SeverityTag, StatusTag } from '../../components/Tags.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDateTime } from '../../utils/format.js';
import EnvTrendChart from '../environment/EnvTrendChart.jsx';
import EnvironmentFormModal from '../environment/EnvironmentFormModal.jsx';
import RestroomFormModal from './RestroomFormModal.jsx';

const TABS = [
  { key: 'profile', label: '基础档案' },
  { key: 'inspections', label: '巡查记录' },
  { key: 'environment', label: '环境卫生' },
  { key: 'issues', label: '问题记录' },
];

export default function RestroomDetailPage() {
  const { restroomId } = useParams();
  const [tab, setTab] = useState('profile');
  const [showForm, setShowForm] = useState(false);
  const [showEnvForm, setShowEnvForm] = useState(false);

  const { data: restroom, loading, error, reload } = useAsync(
    () => restroomApi.detail(restroomId),
    [restroomId],
  );
  const inspections = useListQuery(
    (params) => inspectionApi.list({ ...params, restroom_id: restroomId }),
    {},
    5,
  );
  const issues = useListQuery(
    (params) => issueApi.list({ ...params, restroom_id: restroomId }),
    {},
    5,
  );
  const envRecords = useListQuery(
    (params) => environmentApi.list({ ...params, restroom_id: restroomId }),
    {},
    5,
  );
  const envTrend = useAsync(() => environmentApi.trend(restroomId), [restroomId]);

  const reloadEnv = () => {
    envRecords.reload();
    envTrend.reload();
    reload();
  };

  return (
    <>
      <PageHeader
        title={restroom ? `${restroom.name}（${restroom.code}）` : '公厕详情'}
        description={restroom ? `${restroom.district} · ${restroom.address}` : '加载中…'}
        actions={
          <>
            <Link className="btn" to="/restrooms">
              返回列表
            </Link>
            <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
              编辑档案
            </button>
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !restroom ? <div className="loading-block">加载中…</div> : null}

        {restroom ? (
          <>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="label">累计巡查</div>
                <div className="value">
                  {restroom.inspection_count}
                  <span className="unit">次</span>
                </div>
                <div className="foot">
                  最近巡查：{formatDateTime(restroom.latest_inspection_time)}
                </div>
              </div>
              <div className="stat-card is-info">
                <div className="label">巡查均分</div>
                <div className="value">
                  {restroom.avg_score != null ? restroom.avg_score.toFixed(1) : '-'}
                  <span className="unit">分</span>
                </div>
                <div className="foot">
                  最近得分：{restroom.latest_inspection_score ?? '-'}
                </div>
              </div>
              <div className={`stat-card${restroom.open_issue_count ? ' is-danger' : ''}`}>
                <div className="label">未闭环问题</div>
                <div className="value">
                  {restroom.open_issue_count}
                  <span className="unit">条</span>
                </div>
                <div className="foot">累计上报 {restroom.total_issue_count} 条</div>
              </div>
              <div className={`stat-card${restroom.env_regressed ? ' is-danger' : ' is-info'}`}>
                <div className="label">
                  环境卫生 {restroom.env_regressed ? <RegressTag reason={restroom.env_regress_reason} /> : null}
                </div>
                <div className="value">
                  {restroom.env_score != null ? restroom.env_score.toFixed(1) : '-'}
                  <span className="unit">分</span>
                </div>
                <div className="foot">
                  {restroom.env_grade
                    ? `${restroom.env_grade} · 累计 ${restroom.env_record_count} 条 · ${formatDateTime(restroom.env_record_time)}`
                    : '暂无环境卫生记录'}
                </div>
              </div>
            </div>

            <div className="inline">
              {TABS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`btn btn-sm${tab === item.key ? ' btn-primary' : ''}`}
                  onClick={() => setTab(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {tab === 'profile' ? (
              <section className="card">
                <div className="card-title">
                  <h3>基础档案</h3>
                </div>
                <DetailList
                  items={[
                    { label: '公厕编号', value: restroom.code },
                    { label: '公厕名称', value: restroom.name },
                    { label: '所属区域', value: restroom.district },
                    { label: '详细地址', value: restroom.address },
                    { label: '公厕等级', value: restroom.grade },
                    { label: '开放状态', value: <StatusTag status={restroom.status} /> },
                    { label: '开放时间', value: restroom.open_hours },
                    { label: '保洁责任人', value: restroom.manager },
                    { label: '联系电话', value: restroom.manager_phone },
                    { label: '蹲位数量', value: `${restroom.stall_count} 个` },
                    { label: '洗手盆数量', value: `${restroom.basin_count} 个` },
                    { label: '无障碍设施', value: restroom.has_accessible ? '已配置' : '未配置' },
                    { label: '备注', value: restroom.remark || '无' },
                    { label: '建档时间', value: formatDateTime(restroom.created_at) },
                  ]}
                />
              </section>
            ) : null}

            {tab === 'inspections' ? (
              <section className="card">
                <div className="card-title">
                  <h3>巡查记录</h3>
                  <Link className="hint" to="/inspections">
                    前往巡查模块 →
                  </Link>
                </div>
                <DataTable
                  loading={inspections.loading}
                  error={inspections.error}
                  rows={inspections.items}
                  emptyText="该公厕暂无巡查记录"
                  columns={[
                    { key: 'inspect_time', title: '巡查时间', render: (row) => formatDateTime(row.inspect_time) },
                    { key: 'inspector', title: '巡查人' },
                    { key: 'shift', title: '班次' },
                    { key: 'score', title: '得分', render: (row) => <ScorePill score={row.score} /> },
                    { key: 'result', title: '结论', render: (row) => <StatusTag status={row.result} /> },
                    { key: 'remark', title: '备注', wrap: true, render: (row) => row.remark || '-' },
                  ]}
                />
                <Pagination meta={inspections.meta} onPageChange={inspections.setPage} />
              </section>
            ) : null}

            {tab === 'environment' ? (
              <>
                <section className="card">
                  <div className="card-title">
                    <h3>环境卫生趋势</h3>
                    <div className="inline">
                      {envTrend.data?.avg_score != null ? (
                        <span className="hint">历史均分 {envTrend.data.avg_score}</span>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => setShowEnvForm(true)}
                      >
                        + 新增环境记录
                      </button>
                    </div>
                  </div>
                  {envTrend.loading ? (
                    <div className="loading-block">数据加载中…</div>
                  ) : envTrend.error ? (
                    <div className="alert alert-error">{envTrend.error.message}</div>
                  ) : (
                    <EnvTrendChart points={envTrend.data?.points || []} />
                  )}
                </section>
                <section className="card">
                  <div className="card-title">
                    <h3>环境卫生记录</h3>
                    <Link className="hint" to="/environment">
                      前往环境卫生模块 →
                    </Link>
                  </div>
                  <DataTable
                    loading={envRecords.loading}
                    error={envRecords.error}
                    rows={envRecords.items}
                    emptyText="该公厕暂无环境卫生记录"
                    columns={[
                      { key: 'record_time', title: '记录时间', render: (row) => formatDateTime(row.record_time) },
                      { key: 'recorder', title: '记录人' },
                      { key: 'odor_label', title: '异味' },
                      { key: 'floor_condition', title: '地面', render: (row) => <StatusTag status={row.floor_condition} /> },
                      { key: 'ventilation', title: '通风', render: (row) => <StatusTag status={row.ventilation} /> },
                      { key: 'disinfection_count', title: '消杀', render: (row) => `${row.disinfection_count} 次` },
                      { key: 'score', title: '得分', render: (row) => <ScorePill score={row.score} /> },
                      { key: 'grade', title: '评价', render: (row) => <GradeTag grade={row.grade} /> },
                      {
                        key: 'compare',
                        title: '较上次',
                        render: (row) => (
                          <div className="inline">
                            <DeltaText delta={row.score_delta} />
                            {row.regressed ? <RegressTag reason={row.regress_reason} /> : null}
                          </div>
                        ),
                      },
                      { key: 'remark', title: '备注', wrap: true, render: (row) => row.remark || '-' },
                    ]}
                  />
                  <Pagination meta={envRecords.meta} onPageChange={envRecords.setPage} />
                </section>
              </>
            ) : null}

            {tab === 'issues' ? (
              <section className="card">
                <div className="card-title">
                  <h3>问题记录</h3>
                  <Link className="hint" to="/issues">
                    前往整改模块 →
                  </Link>
                </div>
                <DataTable
                  loading={issues.loading}
                  error={issues.error}
                  rows={issues.items}
                  emptyText="该公厕暂无问题上报"
                  columns={[
                    { key: 'code', title: '编号' },
                    {
                      key: 'title',
                      title: '问题',
                      wrap: true,
                      render: (row) => <Link to={`/issues/${row.id}`}>{row.title}</Link>,
                    },
                    { key: 'category', title: '分类' },
                    { key: 'severity', title: '程度', render: (row) => <SeverityTag severity={row.severity} /> },
                    { key: 'status', title: '状态', render: (row) => <StatusTag status={row.status} /> },
                    { key: 'report_time', title: '上报时间', render: (row) => formatDateTime(row.report_time) },
                  ]}
                />
                <Pagination meta={issues.meta} onPageChange={issues.setPage} />
              </section>
            ) : null}
          </>
        ) : null}
      </div>

      {showForm && restroom ? (
        <RestroomFormModal
          restroom={restroom}
          onClose={() => setShowForm(false)}
          onSaved={reload}
        />
      ) : null}

      {showEnvForm ? (
        <EnvironmentFormModal
          defaultRestroomId={restroomId}
          onClose={() => setShowEnvForm(false)}
          onSaved={reloadEnv}
        />
      ) : null}
    </>
  );
}
