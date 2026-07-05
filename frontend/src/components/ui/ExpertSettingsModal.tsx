import { Modal, Button } from "@/components/ui";

interface ExpertSettings {
  hypothesisCount: number;
  agentCycleDepth: number;
  temperature: number;
}

interface ExpertSettingsModalProps {
  open: boolean;
  onClose: () => void;
  settings: ExpertSettings;
  onChange: (s: ExpertSettings) => void;
}

export function ExpertSettingsModal({ open, onClose, settings, onChange }: ExpertSettingsModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Экспертная настройка" size="md">
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-text">Количество гипотез</label>
            <span className="text-sm font-semibold text-accent">{settings.hypothesisCount}</span>
          </div>
          <input
            type="range"
            min={3}
            max={10}
            step={1}
            value={settings.hypothesisCount}
            onChange={(e) => onChange({ ...settings, hypothesisCount: Number(e.target.value) })}
            className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer
              accent-accent [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full"
          />
          <div className="flex justify-between text-[11px] text-text-muted">
            <span>3</span><span>10</span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-text">Глубина цикла Agent-Judge</label>
            <span className="text-sm font-semibold text-accent">{settings.agentCycleDepth}</span>
          </div>
          <input
            type="range"
            min={1}
            max={5}
            step={1}
            value={settings.agentCycleDepth}
            onChange={(e) => onChange({ ...settings, agentCycleDepth: Number(e.target.value) })}
            className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer
              accent-accent [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full"
          />
          <div className="flex justify-between text-[11px] text-text-muted">
            <span>1 (быстро)</span><span>5 (тщательно)</span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-text">Температура (креативность)</label>
            <span className="text-sm font-semibold text-accent">{settings.temperature.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={settings.temperature}
            onChange={(e) => onChange({ ...settings, temperature: Number(e.target.value) })}
            className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer
              accent-accent [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full"
          />
          <div className="flex justify-between text-[11px] text-text-muted">
            <span>0 (точно)</span><span>1 (креативно)</span>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          <Button variant="ghost" onClick={onClose}>Закрыть</Button>
        </div>
      </div>
    </Modal>
  );
}
