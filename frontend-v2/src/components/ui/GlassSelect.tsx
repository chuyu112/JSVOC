"use client";

interface GlassSelectProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  options: (string | number)[];
  renderLabel?: (value: string | number) => string;
}

export default function GlassSelect({
  label,
  value,
  onChange,
  options,
  renderLabel,
}: GlassSelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[12px] font-[540] text-[#9ca3af]">{label}</label>
      <select
        className="input-glass w-full appearance-none cursor-pointer"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {renderLabel ? renderLabel(option) : option}
          </option>
        ))}
      </select>
    </div>
  );
}
