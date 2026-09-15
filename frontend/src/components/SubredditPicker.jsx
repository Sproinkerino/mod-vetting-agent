import { useId, useMemo, useRef, useState } from 'react';
import { MAX_SUBREDDITS, normalizeSubredditName, sameSubreddit } from '../lib/subreddits';
import { findSubreddits, POPULAR_SUBREDDITS } from '../lib/subredditCatalog';

const VALID_NAME = /^[A-Za-z0-9_]{2,21}$/;

function rankOptions(items, query, limit = 10) {
  const needle = query.toLocaleLowerCase();
  return items
    .filter((item) => item.name.toLocaleLowerCase().includes(needle))
    .sort((left, right) => {
      const leftName = left.name.toLocaleLowerCase();
      const rightName = right.name.toLocaleLowerCase();
      const prefixDifference = Number(!leftName.startsWith(needle)) - Number(!rightName.startsWith(needle));
      return prefixDifference || (right.count || 0) - (left.count || 0) || left.name.localeCompare(right.name);
    })
    .slice(0, limit);
}

export default function SubredditPicker({
  value = [],
  onChange,
  options,
  disabled = false,
  label = 'Focus on communities',
  help = 'Optional. Leave empty to search all Reddit activity.',
  variant = 'full',
  showPopular = false,
}) {
  const reactId = useId();
  const inputId = `subreddit-input-${reactId}`;
  const listId = `subreddit-list-${reactId}`;
  const statusId = `subreddit-status-${reactId}`;
  const rootRef = useRef(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const suggestions = useMemo(() => {
    const normalized = normalizeSubredditName(query);
    const source = options
      ? (normalized ? rankOptions(options, normalized) : options.slice(0, 10))
      : findSubreddits(normalized, 10);
    const available = source.filter((item) => !value.some((selected) => sameSubreddit(selected, item.name)));
    if (normalized && VALID_NAME.test(normalized) && !available.some((item) => sameSubreddit(item.name, normalized))) {
      return [{ name: normalized, custom: true }, ...available].slice(0, 10);
    }
    return available.slice(0, 10);
  }, [options, query, value]);

  function select(name) {
    if (value.length >= MAX_SUBREDDITS || value.some((selected) => sameSubreddit(selected, name))) return;
    onChange([...value, name]);
    setQuery('');
    setOpen(false);
  }

  function remove(name) {
    onChange(value.filter((selected) => !sameSubreddit(selected, name)));
  }

  function handleKeyDown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => Math.min(current + 1, Math.max(0, suggestions.length - 1)));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((current) => Math.max(0, current - 1));
    } else if (event.key === 'Enter' && open && suggestions[activeIndex]) {
      event.preventDefault();
      select(suggestions[activeIndex].name);
    } else if (event.key === 'Escape') {
      setOpen(false);
    } else if (event.key === 'Backspace' && !query && value.length) {
      remove(value[value.length - 1]);
    }
  }

  const limitReached = value.length >= MAX_SUBREDDITS;
  const visibleSuggestions = open && !limitReached;
  const statusText = limitReached
    ? `Maximum ${MAX_SUBREDDITS} communities selected.`
    : `${suggestions.length} suggestion${suggestions.length === 1 ? '' : 's'} available from the bundled directory.`;

  return <div className={`subreddit-picker subreddit-picker-${variant}`} ref={rootRef}>
    <div className="subreddit-picker-heading">
      <label htmlFor={inputId}>{label}</label>
      {value.length > 0 && <button type="button" className="scope-clear" onClick={() => onChange([])} disabled={disabled}>All Reddit</button>}
    </div>
    <div className="subreddit-combobox">
      <span aria-hidden="true">r/</span>
      <input
        id={inputId}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={visibleSuggestions}
        aria-controls={listId}
        aria-activedescendant={visibleSuggestions && suggestions[activeIndex] ? `${listId}-${activeIndex}` : undefined}
        aria-describedby={statusId}
        value={query}
        onChange={(event) => { setQuery(event.target.value); setActiveIndex(0); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={(event) => {
          if (!rootRef.current?.contains(event.relatedTarget)) setOpen(false);
        }}
        onKeyDown={handleKeyDown}
        placeholder={limitReached ? 'Selection limit reached' : 'Type a community'}
        disabled={disabled || limitReached}
        autoComplete="off"
      />
      <span className="scope-count">{value.length}/{MAX_SUBREDDITS}</span>
      {visibleSuggestions && <ul id={listId} role="listbox" className="subreddit-options">
        {suggestions.map((item, index) => <li role="none" key={item.name}>
          <button
            id={`${listId}-${index}`}
            role="option"
            aria-selected={index === activeIndex}
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => select(item.name)}
          >
            <span><strong>r/{item.name}</strong>{item.title && <small>{item.title}</small>}</span>
            {item.count != null && <b>{item.count}</b>}
            {item.custom && <em>Use name</em>}
          </button>
        </li>)}
        {suggestions.length === 0 && <li className="subreddit-option-message">No matching community. You can still enter its exact name.</li>}
      </ul>}
    </div>
    {value.length > 0 && <div className="selected-subreddits" aria-label="Selected communities">
      {value.map((name) => <span key={name}>r/{name}<button type="button" aria-label={`Remove r/${name}`} onClick={() => remove(name)} disabled={disabled}>x</button></span>)}
    </div>}
    {showPopular && value.length === 0 && <div className="popular-subreddits" aria-label="Popular communities">
      <span>Popular</span>
      {POPULAR_SUBREDDITS.slice(0, 6).map((item) => <button type="button" key={item.name} onClick={() => select(item.name)} disabled={disabled}>r/{item.name}</button>)}
    </div>}
    <small className="subreddit-help">{help}</small>
    <span id={statusId} className="visually-hidden" role="status" aria-live="polite">{statusText}</span>
  </div>;
}