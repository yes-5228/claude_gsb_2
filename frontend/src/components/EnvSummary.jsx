import { GradeTag, RegressionTag, ScorePill } from './Tags.jsx';
import { formatDateTime } from '../utils/format.js';

const SUB_LABELS = {
  odor: '异味',
  floor: '地面',
  temperature: '温度',
  humidity: '湿度',
  ventilation: '通风',
  disinfection: '消杀',
};

/** 环境卫生登记值 + 评价结果（含与上一次记录的退步对比）。 */
export default function EnvSummary({ env, prevEnvScore, prevEnvGrade, prevInspectTime, regressed }) {
  if (!env) {
    return (
      <div className="env-summary">
        <div className="section-title">环境卫生量化记录</div>
        <div className="muted">本次巡查未登记环境卫生指标。</div>
      </div>
    );
  }

  const sub = env.subscores || {};

  return (
    <div className="env-summary">
      <div className="card-title">
        <h3>环境卫生量化记录</h3>
        <div className="inline">
          <span className="tag tag-primary">环境卫生分</span>
          <ScorePill score={env.env_score} />
          <GradeTag grade={env.env_grade} />
          {regressed ? (
            <RegressionTag
              regressed
              title={`较上一次记录（${formatDateTime(prevInspectTime)}）明显退步`}
            />
          ) : null}
        </div>
      </div>

      {regressed ? (
        <div className="alert alert-error env-regression-banner">
          环境卫生较上一次记录明显退步
          {prevEnvScore != null ? (
            <>
              ：上次 {Number(prevEnvScore).toFixed(1)} 分（{prevEnvGrade || '-'}，
              {formatDateTime(prevInspectTime)}）→ 本次 {Number(env.env_score).toFixed(1)} 分（
              {env.env_grade}），已在台账中标记。
            </>
          ) : (
            '，已在台账中标记。'
          )}
        </div>
      ) : null}

      <div className="env-metric-grid">
        <div className="env-metric">
          <span className="label">异味等级</span>
          <span className="value">{env.odor_level}</span>
        </div>
        <div className="env-metric">
          <span className="label">地面干湿</span>
          <span className="value">{env.floor_condition}</span>
        </div>
        <div className="env-metric">
          <span className="label">温度</span>
          <span className="value">{Number(env.temperature).toFixed(1)} ℃</span>
        </div>
        <div className="env-metric">
          <span className="label">相对湿度</span>
          <span className="value">{Number(env.humidity).toFixed(0)} %</span>
        </div>
        <div className="env-metric">
          <span className="label">通风状态</span>
          <span className="value">{env.ventilation}</span>
        </div>
        <div className="env-metric">
          <span className="label">消杀频次</span>
          <span className="value">{env.disinfection_count} 次/日</span>
        </div>
      </div>

      <div className="env-subscore">
        {Object.entries(SUB_LABELS).map(([key, label]) => (
          <div className="env-sub-item" key={key}>
            <span className="muted">{label}</span>
            <strong>{sub[key] != null ? Number(sub[key]).toFixed(0) : '-'}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
