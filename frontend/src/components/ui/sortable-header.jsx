import { ChevronDown, ChevronUp } from 'lucide-react';

export default function SortableHeader({ label, column, sortConfig, onSort }) {
  const isActive = sortConfig.key === column;
  const isAscending = isActive && sortConfig.direction === 'asc';

  return (
    <th>
      <button
        type="button"
        className={`table-sort-button ${isActive ? 'active' : ''}`}
        onClick={() => onSort(column)}
      >
        <span>{label}</span>
        <span className="table-sort-icons" aria-hidden="true">
          <ChevronUp size={12} className={isAscending ? 'active' : ''} />
          <ChevronDown size={12} className={isActive && !isAscending ? 'active' : ''} />
        </span>
      </button>
    </th>
  );
}
