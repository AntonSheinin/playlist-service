interface EmptyStateProps {
  message?: string;
  colSpan?: number;
}

export function EmptyState({ message = "No data found", colSpan }: EmptyStateProps) {
  if (colSpan) {
    return (
      <tr>
        <td colSpan={colSpan} className="px-4 py-8 text-center text-gray-500">
          {message}
        </td>
      </tr>
    );
  }

  return (
    <div className="px-4 py-8 text-center text-gray-500">{message}</div>
  );
}
