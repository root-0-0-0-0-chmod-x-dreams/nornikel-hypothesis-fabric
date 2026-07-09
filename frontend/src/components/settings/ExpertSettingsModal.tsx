import { useState, useEffect } from "react";
import { Modal, Button } from "@/components/ui";
import type { GenerationSettings } from "@/types";

interface ExpertSettingsModalProps {
  open: boolean;
  onClose: () => void;
  settings: GenerationSettings;
  onSave: (settings: GenerationSettings) => void;
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  leftLabel,
  rightLabel,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  leftLabel: string;
  rightLabel: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text">{label}</span>
        <span className="text-sm font-semibold text-accent">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-accent"
      />
      <div className="flex justify-between text-[11px] text-text-muted">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  );
}

export function ExpertSettingsModal({ open, onClose, settings, onSave }: ExpertSettingsModalProps) {
  const [draft, setDraft] = useState(settings);

  useEffect(() => {
    if (open) setDraft(settings);
  }, [open, settings]);

  const handleSave = () => {
    onSave(draft);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Экспертная настройка" size="md">
      <div className="flex flex-col gap-6">
        <SliderField
          label="Количество гипотез"
          value={draft.maxHypotheses}
          min={3}
          max={10}
          step={1}
          leftLabel="3"
          rightLabel="10"
          onChange={(v) => setDraft((s) => ({ ...s, maxHypotheses: v }))}
        />
        <SliderField
          label="Глубина цикла Agent-Judge"
          value={draft.agentCycleDepth}
          min={1}
          max={5}
          step={1}
          leftLabel="1 (быстро)"
          rightLabel="5 (тщательно)"
          onChange={(v) => setDraft((s) => ({ ...s, agentCycleDepth: v }))}
        />
        <SliderField
          label="Температура (креативность)"
          value={draft.temperature}
          min={0}
          max={1}
          step={0.1}
          leftLabel="0 (точно)"
          rightLabel="1 (креативно)"
          onChange={(v) => setDraft((s) => ({ ...s, temperature: v }))}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Закрыть</Button>
          <Button variant="primary" onClick={handleSave}>Сохранить</Button>
        </div>
      </div>
    </Modal>
  );
}
