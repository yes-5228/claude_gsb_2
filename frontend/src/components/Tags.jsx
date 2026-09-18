import { isOverdue, scoreTone, severityTone, statusTone } from '../utils/format.js';

export function StatusTag({ status }) {
  return <span className={`tag ${statusTone(status)}`}>{status}</span>;
}

export function SeverityTag({ severity }) {
  return <span className={`tag ${severityTone(severity)}`}>{severity}</span>;
}

export function ScorePill({ score }) {
  return <span className={`score-pill ${scoreTone(score)}`}>{Number(score).toFixed(1)}</span>;
}

export function OverdueTag({ deadline, status }) {
  if (!isOverdue(deadline, status)) return null;
  return <span className="tag tag-danger">已超期</span>;
}

export function GradeTag({ grade }) {
  const tone =
    grade === '优秀'
      ? 'tag-success'
      : grade === '良好'
        ? 'tag-primary'
        : grade === '合格'
          ? 'tag-warning'
          : 'tag-danger';
  return <span className={`tag ${tone}`}>{grade || '未评级'}</span>;
}

/** 与上一条记录的得分差：正绿负红，无历史记录时显示首次记录。 */
export function DeltaText({ delta }) {
  if (delta === null || delta === undefined) return <span className="muted">首次记录</span>;
  if (Number(delta) === 0) return <span className="muted">持平</span>;
  const up = delta > 0;
  return (
    <span style={{ color: up ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
      {up ? '↑' : '↓'} {Math.abs(Number(delta)).toFixed(1)}
    </span>
  );
}

/** 环境卫生明显退步标记。 */
export function RegressTag({ reason }) {
  return (
    <span className="tag tag-danger" title={reason || '较上次记录明显退步'}>
      退步
    </span>
  );
}
