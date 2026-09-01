"use client";

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type MultiSelectOption = {
  value: string;
  label?: string;
  shortLabel?: string;
};

type MultiSelectProps = {
  options: MultiSelectOption[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
};

export function MultiSelect({
  options,
  value,
  onChange,
  placeholder = "Selecione...",
  loading = false,
  disabled = false,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter((option) => {
    const label = option.label || option.value;
    return label.toLowerCase().includes(search.toLowerCase());
  });

  function toggleOption(optionValue: string) {
    if (value.includes(optionValue)) {
      onChange(value.filter((v) => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  }

  function removeValue(optionValue: string, event: React.MouseEvent) {
    event.stopPropagation();
    onChange(value.filter((v) => v !== optionValue));
  }

  function getChipLabel(optionValue: string) {
    const option = options.find((o) => o.value === optionValue);
    return option?.shortLabel || option?.label || optionValue;
  }

  return (
    <div className="multiSelectContainer" ref={containerRef}>
      <div
        className={`multiSelectTrigger ${isOpen ? "open" : ""} ${disabled ? "disabled" : ""}`}
        onClick={() => {
          if (!disabled) {
            setIsOpen(true);
            inputRef.current?.focus();
          }
        }}
      >
        <div className="multiSelectValues">
          {value.map((v) => (
            <span key={v} className="multiSelectChip">
              {getChipLabel(v)}
              <button type="button" onClick={(e) => removeValue(v, e)} disabled={disabled}>
                <X size={12} />
              </button>
            </span>
          ))}
          <input
            ref={inputRef}
            type="text"
            className="multiSelectInput"
            placeholder={value.length === 0 ? (loading ? "Carregando..." : placeholder) : ""}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onFocus={() => setIsOpen(true)}
            disabled={disabled}
          />
        </div>
      </div>

      {isOpen && !disabled && (
        <div className="multiSelectDropdown">
          {filteredOptions.length === 0 ? (
            <div className="multiSelectEmpty">
              {loading ? "Carregando opções..." : "Nenhuma opção encontrada"}
            </div>
          ) : (
            <div className="multiSelectOptions">
              {filteredOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`multiSelectOption ${value.includes(option.value) ? "selected" : ""}`}
                  onClick={() => toggleOption(option.value)}
                >
                  <span className="multiSelectCheckbox">
                    {value.includes(option.value) && "✓"}
                  </span>
                  {option.label || option.value}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
