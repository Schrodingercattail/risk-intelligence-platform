/**
 * Table Component
 *
 * Reusable table with consistent styling.
 */

interface TableProps {
  columns: Array<{
    key: string;
    header: string;
    className?: string;
  }>;
  data: Array<Record<string, any>>;
  onRowClick?: (row: Record<string, any>) => void;
  emptyMessage?: string;
}

export default function Table({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No data available',
}: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider ${
                  column.className || ''
                }`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-slate-200">
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-6 py-4 text-center text-sm text-slate-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, index) => (
              <tr
                key={index}
                className={onRowClick ? 'cursor-pointer hover:bg-slate-50' : ''}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`px-6 py-4 whitespace-nowrap text-sm text-slate-900 ${
                      column.className || ''
                    }`}
                  >
                    {row[column.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
