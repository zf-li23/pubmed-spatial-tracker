import { FilterState, FilterOptions } from '../types';

interface FilterPanelProps {
  options: FilterOptions;
  filters: FilterState;
  onToggle: (key: keyof FilterState, value: string) => void;
  onClearAll: () => void;
}

function CheckboxGroup({
  label,
  values,
  selected,
  onToggle,
  groupKey,
}: {
  label: string;
  values: string[];
  selected: Set<string>;
  onToggle: (key: keyof FilterState, value: string) => void;
  groupKey: keyof FilterState;
}) {
  if (values.length === 0) return null;
  return (
    <div className="filter-group">
      <div className="filter-group-label">{label} ({values.length})</div>
      <div className="filter-group-options">
        {values.map(v => (
          <label key={v} className={`filter-chip ${selected.has(v) ? 'active' : ''}`}>
            <input
              type="checkbox"
              checked={selected.has(v)}
              onChange={() => onToggle(groupKey, v)}
              style={{ display: 'none' }}
            />
            {v}
          </label>
        ))}
      </div>
    </div>
  );
}

export default function FilterPanel({ options, filters, onToggle, onClearAll }: FilterPanelProps) {
  const hasAnyFilter =
    filters.years.size > 0 ||
    filters.categories.size > 0 ||
    filters.tags.size > 0 ||
    filters.technologies.size > 0 ||
    filters.biologicalTopics.size > 0 ||
    filters.journals.size > 0;

  return (
    <aside className="filter-panel">
      <div className="filter-header">
        <h3>Filters</h3>
        {hasAnyFilter && (
          <button className="filter-clear-btn" onClick={onClearAll}>
            Clear All
          </button>
        )}
      </div>

      <CheckboxGroup label="Year" values={options.years} selected={filters.years} onToggle={onToggle} groupKey="years" />
      <CheckboxGroup label="Category" values={options.categories} selected={filters.categories} onToggle={onToggle} groupKey="categories" />
      <CheckboxGroup label="Tags" values={options.tags} selected={filters.tags} onToggle={onToggle} groupKey="tags" />
      <CheckboxGroup label="Technology" values={options.technologies} selected={filters.technologies} onToggle={onToggle} groupKey="technologies" />
      <CheckboxGroup label="Biological Topic" values={options.biologicalTopics} selected={filters.biologicalTopics} onToggle={onToggle} groupKey="biologicalTopics" />

      {/* 期刊：可搜索下拉 */}
      <div className="filter-group">
        <div className="filter-group-label">Journal ({options.journals.length})</div>
        <JournalSelector
          journals={options.journals}
          selected={filters.journals}
          onToggle={v => onToggle('journals', v)}
        />
      </div>
    </aside>
  );
}

/** 期刊搜索选择器 */
import { useState, useMemo } from 'react';

function JournalSelector({
  journals,
  selected,
  onToggle,
}: {
  journals: string[];
  selected: Set<string>;
  onToggle: (v: string) => void;
}) {
  const [query, setQuery] = useState('');
  const filtered = useMemo(
    () => journals.filter(j => j.toLowerCase().includes(query.toLowerCase())),
    [journals, query],
  );

  return (
    <div className="journal-selector">
      <input
        type="text"
        placeholder="Search journal..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        className="journal-search-input"
      />
      <div className="journal-list">
        {filtered.slice(0, 100).map(j => (
          <label key={j} className={`filter-chip ${selected.has(j) ? 'active' : ''}`}>
            <input
              type="checkbox"
              checked={selected.has(j)}
              onChange={() => onToggle(j)}
              style={{ display: 'none' }}
            />
            {j}
          </label>
        ))}
        {filtered.length > 100 && (
          <span className="journal-more">...and {filtered.length - 100} more</span>
        )}
      </div>
    </div>
  );
}
