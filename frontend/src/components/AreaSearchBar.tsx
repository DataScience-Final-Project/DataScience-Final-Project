import React, { useState } from 'react';

export type AreaSearchBarProps = {
  /** Called when the user submits a search (Enter or search button). */
  onSearch: (query: string) => void;
  placeholder?: string;
};

const AreaSearchBar: React.FC<AreaSearchBarProps> = ({
  onSearch,
  placeholder = 'Search city or area…',
}) => {
  const [value, setValue] = useState('');

  const submit = () => {
    onSearch(value.trim());
  };

  return (
    <form
      className="area-search"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <input
        type="search"
        className="area-search__input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        enterKeyHint="search"
        autoComplete="off"
        aria-label={placeholder}
      />
      <button type="submit" className="area-search__btn">
        Search
      </button>
    </form>
  );
};

export default AreaSearchBar;
