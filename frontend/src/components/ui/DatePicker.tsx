import DatePickerLib from "react-datepicker";
import { fieldControlClass, fieldLabelClass } from "./fieldStyles";

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
  placeholder = "Select date",
}: DatePickerProps) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className={fieldLabelClass}>
          {label}
        </label>
      )}
      <DatePickerLib
        id={id}
        selected={selected}
        onChange={(date: Date | null) => onChange(date)}
        isClearable={isClearable}
        placeholderText={placeholder}
        dateFormat="yyyy-MM-dd"
        showPopperArrow={false}
        popperPlacement="bottom-start"
        wrapperClassName="w-full"
        calendarClassName="modern-datepicker"
        className={fieldControlClass}
        ariaLabelledBy={id && label ? id : undefined}
      />
    </div>
  );
}
