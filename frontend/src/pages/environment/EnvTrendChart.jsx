import { formatShortDate } from '../../utils/format.js';
import { scoreTone } from '../../utils/format.js';

/** 同一公厕环境卫生得分时间序列：柱高为得分，红框表示明显退步。 */
export default function EnvTrendChart({ points }) {
  if (!points?.length) return <div className="empty-block">暂无环境卫生记录</div>;

  return (
    <>
      <div className="env-trend">
        {points.map((point) => (
          <div
            className="env-trend-col"
            key={point.id}
            title={`${point.record_time} 得分 ${point.score}（${point.grade}）${
              point.regressed ? '，明显退步' : ''
            }`}
          >
            <span className="env-trend-score">{Number(point.score).toFixed(0)}</span>
            <div
              className={`env-trend-bar ${scoreTone(point.score)}${point.regressed ? ' regressed' : ''}`}
              style={{ height: `${Math.max(point.score * 1.2, 2)}px` }}
            />
            <span className="trend-label">{formatShortDate(point.record_time)}</span>
          </div>
        ))}
      </div>
      <div className="legend">
        <span>柱高为环境卫生得分（满分 100）</span>
        <span className="issues">红框为明显退步记录</span>
      </div>
    </>
  );
}
