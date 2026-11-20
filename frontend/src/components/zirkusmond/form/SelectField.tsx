import { useState, useRef, useEffect } from "react";
import { ChevronDownIcon, CheckIcon } from "lucide-react";
import { Field, FieldError, FieldLabel } from "#/components/ui/field.tsx";

export interface SelectFieldProps {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  error?: string;
}

export default function SelectField({
  id,
  label,
  placeholder,
  value,
  onChange,
  options,
  error,
}: SelectFieldProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <Field orientation="responsive">
      <FieldLabel htmlFor={id} className="text-base sm:text-lg md:text-xl">
        {label}
      </FieldLabel>
      <div ref={containerRef} className="relative bg-white/10">
        <button
          id={id}
          type="button"
          aria-invalid={!!error}
          onClick={() => setIsOpen(!isOpen)}
          className="flex h-10 sm:h-11 w-full items-center justify-between border-2 border-primary bg-transparent px-2 sm:px-3 text-base sm:text-lg text-white hover:bg-transparent aria-invalid:border-destructive"
        >
          <span className={"text-white"}>
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          <ChevronDownIcon className="size-4 text-primary" />
        </button>
        {isOpen && (
          <div className="absolute z-50 w-full max-h-[400px] overflow-y-auto border-2 border-t-0 border-primary bg-[url(/images/general/bg_pattern.webp)] bg-repeat [scrollbar-width:thin] [scrollbar-color:white_transparent] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:bg-white [&::-webkit-scrollbar-track]:bg-transparent">
            {options.map((option) => {
              const isSelected = option.value === value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  className={`flex w-full items-center bg-black/10 justify-between px-2 sm:px-3 py-2 text-left text-base sm:text-lg hover:bg-black/10 hover:text-primary ${
                    isSelected ? "text-primary" : "text-white"
                  }`}
                >
                  <span>{option.label}</span>
                  {isSelected && (
                    <CheckIcon
                      className="size-4 stroke-primary"
                      strokeWidth={3}
                    />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
      {error && <FieldError>{error}</FieldError>}
    </Field>
  );
}
