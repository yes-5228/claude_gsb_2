import { useState } from 'react';
import { Link } from 'react-router-dom';

import { environmentApi } from '../../api/environment.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { DeltaText, GradeTag, RegressTag, ScorePill, StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDateTime } from '../../utils/format.js';
import { odorLabel } from '../../utils/envScoring.js';
import EnvironmentDetailModal from './EnvironmentDetailModal.jsx';
import EnvironmentFormModal from './EnvironmentFormModal.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  grade: '',
  regressed: '',
  date_from: '',
  date_to: '',
};

const GRADE_OPTIONS = ['优秀', '良好', '合格', '不合格'];

export default function EnvironmentListPage() {
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [active, setActive] = useState(null);

  const list = useListQuery((params) => environmentApi.list(params), DEFAULT_FILTERS, 10);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  const remove = async (row) => {
    if (!window.confirm('确认删除该条环境卫生记录？')) return;
    try {
      await environmentApi.remove(row.id);
      toast.success('删除成功');
      list.reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title="环境卫生记录"
        description="量化登记异味、地面干湿、温湿度、通风与消杀频次，自动评价并与历史记录对比"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
            + 新增环境记录
          </button>
        }
      />
      <div className="content">
        <section className="card">
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="公厕名称 / 记录人 / 备注"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="所属区域">
              <select
                value={list.filters.district}
                onChange={(event) => list.updateFilter('district', event.target.value)}
              >
                <option value="">全部</option>
                {(districts || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="评价等级">
              <select
                value={list.filters.grade}
                onChange={(event) => list.updateFilter('grade', event.target.value)}
              >
                <option value="">全部</option>
                {GRADE_OPTIONS.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="退步情况">
              <select
                value={list.filters.regressed}
                onChange={(event) => list.updateFilter('regressed', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">仅看明显退步</option>
                <option value="false">无退步</option>
              </select>
            </Field>
            <Field label="开始日期">
              <input
                type="date"
                value={list.filters.date_from}
                onChange={(event) => list.updateFilter('date_from', event.target.value)}
              />
            </Field>
            <Field label="结束日期">
              <input
                type="date"
                value={list.filters.date_to}
                onChange={(event) => list.updateFilter('date_to', event.target.value)}
              />
            </Field>
            <button type="button" className="btn" onClick={list.resetFilters}>
              重置
            </button>
          </div>
        </section>

        <section className="card">
          <DataTable
            loading={list.loading}
            error={list.error}
            rows={list.items}
            emptyText="暂无环境卫生记录"
            columns={[
              {
                key: 'record_time',
                title: '记录时间',
                render: (row) => formatDateTime(row.record_time),
              },
              {
                key: 'restroom',
                title: '公厕',
                render: (row) =>
                  row.restroom ? (
                    <Link to={`/restrooms/${row.restroom.id}`}>{row.restroom.name}</Link>
                  ) : (
                    '-'
                  ),
              },
              { key: 'district', title: '区域', render: (row) => row.restroom?.district ?? '-' },
              { key: 'recorder', title: '记录人' },
              { key: 'odor', title: '异味', render: (row) => row.odor_label ?? odorLabel(row.odor_level) },
              {
                key: 'floor_condition',
                title: '地面',
                render: (row) => <StatusTag status={row.floor_condition} />,
              },
              {
                key: 'temp_humidity',
                title: '温湿度',
                render: (row) =>
                  `${row.temperature != null ? `${row.temperature}℃` : '-'} / ${
                    row.humidity != null ? `${row.humidity}%` : '-'
                  }`,
              },
              {
                key: 'ventilation',
                title: '通风',
                render: (row) => <StatusTag status={row.ventilation} />,
              },
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
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="inline">
                    <button type="button" className="btn-link" onClick={() => setActive(row)}>
                      详情
                    </button>
                    <button type="button" className="btn-link danger" onClick={() => remove(row)}>
                      删除
                    </button>
                  </div>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? (
        <EnvironmentFormModal onClose={() => setShowForm(false)} onSaved={list.reload} />
      ) : null}

      {active ? (
        <EnvironmentDetailModal record={active} onClose={() => setActive(null)} />
      ) : null}
    </>
  );
}
