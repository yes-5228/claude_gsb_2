import { useEffect, useMemo, useState } from 'react';

import { environmentApi } from '../../api/environment.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { GradeTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import {
  FLOOR_CONDITIONS,
  ODOR_LEVELS,
  VENTILATION_STATUSES,
  calcEnvScore,
  envGradeOf,
} from '../../utils/envScoring.js';
import { toDateTimeInput } from '../../utils/format.js';

export default function EnvironmentFormModal({ defaultRestroomId, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [options, setOptions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    restroom_id: defaultRestroomId ? Number(defaultRestroomId) : '',
    recorder: '',
    record_time: toDateTimeInput(),
    odor_level: 0,
    floor_condition: '干燥',
    temperature: '',
    humidity: '',
    ventilation: '良好',
    disinfection_count: 2,
    remark: '',
  });

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setOptions)
      .catch((err) => setError(err.message));
  }, []);

  const odorOptions = dictionaries?.odor_levels ?? ODOR_LEVELS;
  const floorOptions = dictionaries?.floor_conditions ?? FLOOR_CONDITIONS;
  const ventilationOptions = dictionaries?.ventilation_statuses ?? VENTILATION_STATUSES;

  const score = useMemo(
    () =>
      calcEnvScore({
        odorLevel: Number(form.odor_level),
        floorCondition: form.floor_condition,
        temperature: form.temperature,
        humidity: form.humidity,
        ventilation: form.ventilation,
        disinfectionCount: form.disinfection_count,
      }),
    [form],
  );
  const grade = envGradeOf(score);

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!form.restroom_id) {
      setError('请选择公厕');
      return;
    }
    if (!form.recorder.trim()) {
      setError('请填写记录人');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await environmentApi.create({
        restroom_id: Number(form.restroom_id),
        recorder: form.recorder.trim(),
        record_time: form.record_time ? new Date(form.record_time).toISOString() : null,
        odor_level: Number(form.odor_level),
        floor_condition: form.floor_condition,
        temperature: form.temperature === '' ? null : Number(form.temperature),
        humidity: form.humidity === '' ? null : Number(form.humidity),
        ventilation: form.ventilation,
        disinfection_count: Number(form.disinfection_count) || 0,
        remark: form.remark || null,
      });
      toast.success('环境卫生记录已提交');
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="新增环境卫生记录"
      onClose={onClose}
      width={760}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="environment-form" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中…' : '提交记录'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="environment-form" onSubmit={submit} className="form-grid">
        <Field label="公厕 *">
          <select
            value={form.restroom_id}
            onChange={(event) => update('restroom_id', event.target.value)}
          >
            <option value="">请选择公厕</option>
            {options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.code} {option.name}（{option.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="记录人 *">
          <input
            value={form.recorder}
            onChange={(event) => update('recorder', event.target.value)}
            placeholder="请输入记录人姓名"
          />
        </Field>
        <Field label="记录时间">
          <input
            type="datetime-local"
            value={form.record_time}
            onChange={(event) => update('record_time', event.target.value)}
          />
        </Field>
        <Field label="当日消杀次数">
          <input
            type="number"
            min="0"
            max="20"
            step="1"
            value={form.disinfection_count}
            onChange={(event) => update('disinfection_count', event.target.value)}
          />
        </Field>
        <Field label="温度（℃，可留空）">
          <input
            type="number"
            step="0.1"
            value={form.temperature}
            placeholder="如 28.5"
            onChange={(event) => update('temperature', event.target.value)}
          />
        </Field>
        <Field label="湿度（%，可留空）">
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            value={form.humidity}
            placeholder="如 65"
            onChange={(event) => update('humidity', event.target.value)}
          />
        </Field>
        <Field label="地面干湿情况">
          <select
            value={form.floor_condition}
            onChange={(event) => update('floor_condition', event.target.value)}
          >
            {floorOptions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="通风状态">
          <select
            value={form.ventilation}
            onChange={(event) => update('ventilation', event.target.value)}
          >
            {ventilationOptions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
      </form>

      <div className="card-title">
        <div className="inline">
          <h3>异味等级</h3>
          <span className="tag tag-primary">当前得分 {score.toFixed(1)}</span>
          <GradeTag grade={grade} />
        </div>
        <span className="hint">评分规则：异味 35 / 地面 20 / 温湿度 20 / 通风 15 / 消杀 10</span>
      </div>
      <div className="odor-picker">
        {odorOptions.map((item) => (
          <button
            key={item.level}
            type="button"
            className={`odor-option odor-${item.level}${
              Number(form.odor_level) === item.level ? ' active' : ''
            }`}
            onClick={() => update('odor_level', item.level)}
          >
            <strong>{item.level}</strong>
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      <Field label="备注" full>
        <textarea
          rows="2"
          value={form.remark}
          onChange={(event) => update('remark', event.target.value)}
          placeholder="环境异常情况说明（可选）"
        />
      </Field>
    </Modal>
  );
}
