import Field from './Field.jsx';

const DEFAULT_LIMITS = {
  temperature_min: -10,
  temperature_max: 50,
  humidity_min: 0,
  humidity_max: 100,
  disinfection_min: 0,
  disinfection_max: 12,
};

/**
 * 环境卫生量化登记表单：异味、地面干湿、温湿度、通风、消杀频次。
 * value/onChange 受控；dictionaries 提供枚举与取值区间。
 */
export default function EnvFields({ value, onChange, dictionaries, limits }) {
  const bounds = { ...DEFAULT_LIMITS, ...(limits || dictionaries?.env_limits || {}) };
  const odorLevels = dictionaries?.odor_levels || ['无异味', '轻微异味', '明显异味', '强烈刺鼻'];
  const floorConditions =
    dictionaries?.floor_conditions || ['干燥洁净', '轻微潮湿', '明显积水湿滑', '积水污渍'];
  const ventilationStatuses = dictionaries?.ventilation_statuses || ['通风良好', '通风一般', '通风不良'];

  const set = (key, fieldValue) => onChange({ ...value, [key]: fieldValue });

  return (
    <div className="env-form">
      <Field label="异味等级">
        <select value={value.odor_level} onChange={(e) => set('odor_level', e.target.value)}>
          <option value="">请选择</option>
          {odorLevels.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </Field>
      <Field label="地面干湿情况">
        <select
          value={value.floor_condition}
          onChange={(e) => set('floor_condition', e.target.value)}
        >
          <option value="">请选择</option>
          {floorConditions.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </Field>
      <Field label="通风状态">
        <select value={value.ventilation} onChange={(e) => set('ventilation', e.target.value)}>
          <option value="">请选择</option>
          {ventilationStatuses.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </Field>
      <Field label="消杀频次（次/日）">
        <input
          type="number"
          min={bounds.disinfection_min}
          max={bounds.disinfection_max}
          step="1"
          value={value.disinfection_count}
          onChange={(e) => set('disinfection_count', e.target.value)}
          placeholder="当日消杀次数"
        />
      </Field>
      <Field label="温度（℃）">
        <input
          type="number"
          min={bounds.temperature_min}
          max={bounds.temperature_max}
          step="0.1"
          value={value.temperature}
          onChange={(e) => set('temperature', e.target.value)}
          placeholder="现场温度"
        />
      </Field>
      <Field label="相对湿度（%）">
        <input
          type="number"
          min={bounds.humidity_min}
          max={bounds.humidity_max}
          step="1"
          value={value.humidity}
          onChange={(e) => set('humidity', e.target.value)}
          placeholder="现场相对湿度"
        />
      </Field>
    </div>
  );
}
