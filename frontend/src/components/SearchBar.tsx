interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
}

export default function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="search-bar">
      <span className="search-icon">🔍</span>
      <input
        type="text"
        placeholder="Search by PMID, Title, or DOI..."
        value={value}
        onChange={e => onChange(e.target.value)}
        className="search-input"
      />
      {value && (
        <button className="search-clear" onClick={() => onChange('')} title="Clear">
          ✕
        </button>
      )}
    </div>
  );
}
