import ReactSelect from "react-select";
import type { MultiValue } from "react-select";

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
        <label className="block text-sm font-medium text-gray-700 mb-1">
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
            borderColor: "#d1d5db",
            "&:hover": { borderColor: "#9ca3af" },
            boxShadow: "none",
            minHeight: "38px",
          }),
          multiValue: (base) => ({
            ...base,
            backgroundColor: "#dbeafe",
          }),
          multiValueLabel: (base) => ({
            ...base,
            color: "#1e40af",
          }),
        }}
      />
    </div>
  );
}
