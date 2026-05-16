import dayjs from "dayjs";
import { DatePicker as MuiDatePicker } from "@mui/x-date-pickers/DatePicker";

interface DatePickerProps {
  label?: string;
  selected: Date | null;
  onChange: (date: Date | null) => void;
  isClearable?: boolean;
  id?: string;
  placeholder?: string;
}

export function DatePicker({
  label,
  selected,
  onChange,
  isClearable = true,
  id,
}: DatePickerProps) {
  return (
    <MuiDatePicker
      label={label}
      value={selected ? dayjs(selected) : null}
      onChange={(value) => onChange(value?.toDate() ?? null)}
      format="YYYY-MM-DD"
      slotProps={{
        field: { clearable: isClearable },
        textField: {
          id,
          fullWidth: true,
        },
        popper: { sx: { zIndex: 1500 } },
      }}
    />
  );
}
