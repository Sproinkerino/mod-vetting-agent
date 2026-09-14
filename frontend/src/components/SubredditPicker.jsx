import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { fetchPopularSubreddits, suggestSubreddits } from '../lib/api';
import { MAX_SUBREDDITS, normalizeSubredditName, sameSubreddit } from '../lib/subreddits';

const VALID_NAME = /^[A-Za-z0-9_]{2,21}$/;

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
  const [remoteOptions, setRemoteOptions] = useState([]);
  const [popular, setPopular] = useState([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [status, setStatus] = useState(options ? 'ready' : 'loading');

  useEffect(() => {
    if (options) return undefined;
    let current = true;
    fetchPopularSubreddits()
      .then((items) => {
        if (!current) return;
        setPopular(items);
        setStatus('ready');
      })
      .catch(() => {
        if (!current) return;
        setPopular([]);
        setStatus('error');
      });
    return () => { current = false; };
  }, [options]);

  useEffect(() => {
    const normalized = normalizeSubredditName(query);
    if (!normalized || options) return undefined;
    let current = true;
    const timer = window.setTimeout(() => {
      suggestSubreddits(normalized)
        .then((items) => {
          if (!current) return;
          setRemoteOptions(items);
          setStatus('ready');
        })
        .catch(() => {
          if (!current) return;
          setRemoteOptions([]);
          setStatus('error');
        });
    }, 200);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [query, options]);

  const suggestions = useMemo(() => {
    const normalized = normalizeSubredditName(query);
    const source = normalized ? (options || remoteOptions).filter((item) => item.name.toLowerCase().includes(normalized.toLowerCase())) : (options || popular);
    const available = source.filter((item) => !value.some((selected) => sameSubreddit(selected, item.name)));
    if (normalized && VALID_NAME.test(normalized) && !available.some((item) => sameSubreddit(item.name, normalized))) {
      return [{ name: normalized, custom: true }, ...available].slice(0, 10);
    }
    return available.slice(0, 10);
  }, [options, popular, query, remoteOptions, value]);

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
  const effectiveStatus = !normalizeSubredditName(query) || options ? 'ready' : status;
  const statusText = limitReached
    ? `Maximum ${MAX_SUBREDDITS} communities selected.`
    : effectiveStatus === 'loading'
      ? 'Loading subreddit suggestions.'
      : effectiveStatus === 'error'
        ? 'Live suggestions are unavailable. You can still enter a subreddit name.'
        : `${suggestions.length} suggestion${suggestions.length === 1 ? '' : 's'} available.`;

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
        onChange={(event) => { setQuery(event.target.value); setActiveIndex(0); setStatus(options ? 'ready' : 'loading'); setOpen(true); }}
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
            id={listId + '-' + index}
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
        {effectiveStatus === 'loading' && <li className="subreddit-option-message">Searching Reddit...</li>}
        {effectiveStatus !== 'loading' && suggestions.length === 0 && <li className="subreddit-option-message">No communities found.</li>}
      </ul>}
    </div>
    {value.length > 0 && <div className="selected-subreddits" aria-label="Selected communities">
      {value.map((name) => <span key={name}>r/{name}<button type="button" aria-label={`Remove r/${name}`} onClick={() => remove(name)} disabled={disabled}>x</button></span>)}
    </div>}
    {showPopular && value.length === 0 && popular.length > 0 && <div className="popular-subreddits" aria-label="Popular communities">
      <span>Popular</span>
      {popular.slice(0, 6).map((item) => <button type="button" key={item.name} onClick={() => select(item.name)} disabled={disabled}>r/{item.name}</button>)}
    </div>}
    <small className="subreddit-help">{help}</small>
    <span id={statusId} className="visually-hidden" role="status" aria-live="polite">{statusText}</span>
  </div>;
}