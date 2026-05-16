import { Autocomplete, TextField } from "@mui/material";

export interface SelectOption {
  value: number;
  label: string;
}

interface MultiSelectProps {
  label?: string;
  options: SelectOption[];
  value: SelectOption[];
  onChange: (selected: SelectOption[]) => void;
  onInputChange?: (value: string) => void;
  placeholder?: string;
  isLoading?: boolean;
  isClearable?: boolean;
  noOptionsMessage?: (inputValue: string) => string;
  className?: string;
}

export function MultiSelect({
  label,
  options,
  value,
  onChange,
  onInputChange,
  placeholder = "Select...",
  isLoading,
  isClearable = true,
  noOptionsMessage,
  className,
}: MultiSelectProps) {
  const compact = !label;

  return (
    <Autocomplete
      className={className}
      multiple
      size="small"
      options={options}
      value={value}
      loading={isLoading}
      limitTags={compact ? 1 : -1}
      disableClearable={!isClearable}
      filterOptions={onInputChange ? (items) => items : undefined}
      isOptionEqualToValue={(option, selected) => option.value === selected.value}
      getOptionLabel={(option) => option.label}
      noOptionsText={noOptionsMessage ? noOptionsMessage("") : "No options"}
      onChange={(_, selected) => onChange(selected)}
      onInputChange={(_, inputValue, reason) => {
        if (reason === "input") onInputChange?.(inputValue);
      }}
      slotProps={{ popper: { sx: { zIndex: 1500 } } }}
      sx={{
        minWidth: compact ? 160 : undefined,
        "& .MuiInputBase-root": {
          minHeight: compact ? 32 : undefined,
          py: compact ? 0 : undefined,
          fontSize: compact ? 12 : undefined,
        },
        "& .MuiChip-root": {
          height: compact ? 20 : undefined,
          fontSize: compact ? 11 : undefined,
        },
      }}
      renderInput={(params) => (
        <TextField {...params} label={label} placeholder={placeholder} fullWidth />
      )}
    />
  );
}
