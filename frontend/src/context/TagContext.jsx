import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// Persists the "show topic tags" preference to localStorage (dsa_show_tags).
// When tags are hidden, topic columns render compactly or are suppressed entirely.
const TagContext = createContext();

const STORAGE_KEY = 'dsa_show_tags';

const readPreference = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw !== null) return raw === 'true';
  } catch {
    // localStorage unavailable (private mode / storage blocked) — default to showing tags.
  }
  return true; // default: show tags
};

export const TagProvider = ({ children }) => {
  const [showTags, setShowTags] = useState(readPreference);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(showTags));
    } catch {
      // Non-fatal: preference just won't persist.
    }
  }, [showTags]);

  const toggleShowTags = useCallback(() => {
    setShowTags((prev) => !prev);
  }, []);

  return (
    <TagContext.Provider value={{ showTags, toggleShowTags }}>
      {children}
    </TagContext.Provider>
  );
};

export const useTags = () => useContext(TagContext);
