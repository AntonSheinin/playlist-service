import ReactSelect from "react-select";
import type { MultiValue } from "react-select";
import { fieldLabelClass } from "./fieldStyles";

export interface SelectOption {
  value: number;
  label: string;
}

interface MultiSelectProps {
  label?: string;
  options: SelectOption[];
  value: SelectOption[];
  onChange: (selected: MultiValue<SelectOption>) => void;
  placeholder?: string;
  isLoading?: boolean;
  isClearable?: boolean;
}

export function MultiSelect({
  label,
  options,
  value,
  onChange,
  placeholder = "Select...",
  isLoading,
  isClearable = true,
}: MultiSelectProps) {
  return (
    <div>
      {label && (
        <label className={`${fieldLabelClass} mb-1`}>
          {label}
        </label>
      )}
      <ReactSelect
        isMulti
        options={options}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        isLoading={isLoading}
        isClearable={isClearable}
        classNamePrefix="react-select"
        styles={{
          control: (base) => ({
            ...base,
            borderColor: "#cbd5e1",
            borderRadius: 8,
            minHeight: "40px",
            boxShadow: "none",
            "&:hover": { borderColor: "#94a3b8" },
          }),
          valueContainer: (base) => ({ ...base, padding: "2px 8px" }),
          multiValue: (base) => ({
            ...base,
            backgroundColor: "#e0f2fe",
            borderRadius: 6,
          }),
          multiValueLabel: (base) => ({
            ...base,
            color: "#075985",
          }),
          menu: (base) => ({ ...base, zIndex: 60 }),
        }}
      />
    </div>
  );
}
