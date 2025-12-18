/**
 * DataTable - Basic table component for structured data display
 * Part of the trading cockpit primitive component library
 */

interface Column {
  key: string;
  header: string;
  align?: 'left' | 'right' | 'center';
  render?: (value: any, row: any) => React.ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  className?: string;
  emptyMessage?: string;
}

export function DataTable({ columns, data, className = '', emptyMessage = 'No data available' }: DataTableProps) {
  if (data.length === 0) {
    return (
      <div className={`rounded-lg border border-[var(--stroke-0)] bg-[var(--bg-1)] ${className}`}>
        <div className="p-8 text-center text-[var(--text-2)]">
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border border-[var(--stroke-0)] bg-[var(--bg-1)] overflow-hidden ${className}`}>
      <table className="w-full">
        <thead>
          <tr className="border-b border-[var(--stroke-0)] bg-[var(--bg-2)]">
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-4 py-3 text-left text-[0.6875rem] uppercase tracking-wide text-[var(--text-2)] font-medium ${
                  column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'
                }`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className="border-b border-[var(--stroke-1)] last:border-0 hover:bg-[var(--bg-2)] transition-colors"
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-4 py-3 text-[0.875rem] text-[var(--text-0)] ${
                    column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'
                  }`}
                >
                  {column.render ? column.render(row[column.key], row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
