import DetailList from '../../components/DetailList.jsx';
import Modal from '../../components/Modal.jsx';
import { DeltaText, GradeTag, RegressTag, ScorePill, StatusTag } from '../../components/Tags.jsx';
import { formatDateTime } from '../../utils/format.js';
import { odorLabel } from '../../utils/envScoring.js';

export default function EnvironmentDetailModal({ record, onClose }) {
  if (!record) return null;

  return (
    <Modal
      title={`环境卫生详情 - ${record.restroom?.name ?? ''}`}
      onClose={onClose}
      width={760}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          关闭
        </button>
      }
    >
      {record.regressed ? (
        <div className="alert alert-error">
          较上次记录明显退步：{record.regress_reason || '多项指标恶化'}，已在台账中标记。
        </div>
      ) : null}
      <DetailList
        items={[
          { label: '记录时间', value: formatDateTime(record.record_time) },
          { label: '记录人', value: record.recorder },
          { label: '异味等级', value: `${record.odor_level} 级（${record.odor_label ?? odorLabel(record.odor_level)}）` },
          { label: '地面干湿', value: <StatusTag status={record.floor_condition} /> },
          {
            label: '温度',
            value: record.temperature != null ? `${record.temperature}℃` : '未测量',
          },
          {
            label: '湿度',
            value: record.humidity != null ? `${record.humidity}%` : '未测量',
          },
          { label: '通风状态', value: <StatusTag status={record.ventilation} /> },
          { label: '当日消杀', value: `${record.disinfection_count} 次` },
          { label: '环境卫生得分', value: <ScorePill score={record.score} /> },
          { label: '评价等级', value: <GradeTag grade={record.grade} /> },
          {
            label: '与上次对比',
            value: (
              <div className="inline">
                <DeltaText delta={record.score_delta} />
                {record.prev_score != null ? (
                  <span className="muted">（上次 {Number(record.prev_score).toFixed(1)} 分）</span>
                ) : null}
                {record.regressed ? <RegressTag reason={record.regress_reason} /> : null}
              </div>
            ),
          },
          { label: '备注', value: record.remark || '无' },
        ]}
      />

      <div className="section-title">评分明细</div>
      <div className="check-grid">
        {(record.breakdown || []).map((part) => (
          <div className={`check-item${part.score < part.max * 0.6 ? ' is-low' : ''}`} key={part.key}>
            <div className="name">{part.label}</div>
            <div className="score-line">
              <strong>
                {Number(part.score).toFixed(0)}
                <span className="muted"> / {part.max}</span>
              </strong>
              <span className="muted">{part.value}</span>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
