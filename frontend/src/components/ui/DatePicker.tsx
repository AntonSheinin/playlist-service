interface DatePickerProps {
  label?: string;
  selected: Date | null;
  onChange: (date: Date | null) => void;
  isClearable?: boolean;
}

function toInputValue(date: Date | null): string {
  if (!date) return "";
  return date.toISOString().split("T")[0];
}

export function DatePicker({
  label,
  selected,
  onChange,
  isClearable = true,
}: DatePickerProps) {
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    if (!val) {
      onChange(null);
      return;
    }
    // Parse YYYY-MM-DD in local timezone
    const [y, m, d] = val.split("-").map(Number);
    onChange(new Date(y, m - 1, d));
  }

  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          type="date"
          value={toInputValue(selected)}
          onChange={handleChange}
          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
        {isClearable && selected && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="absolute right-8 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
