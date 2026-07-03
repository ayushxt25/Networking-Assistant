import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown } from "lucide-react";

const MENU_GAP = 8;
const VIEWPORT_MARGIN = 12;
const DEFAULT_MENU_MAX_HEIGHT = 288;

const baseButtonClasses =
  "flex w-full items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-left text-sm text-white transition-colors hover:bg-white/[0.08] focus:outline-none focus:border-accent/50";

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export default function CustomSelect({
  value,
  onChange,
  options,
  placeholder = "Select",
  icon: Icon,
  disabled = false,
  className = "",
  buttonClassName = "",
  menuClassName = "",
  align = "left",
}) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState(null);
  const triggerRef = useRef(null);
  const menuRef = useRef(null);

  const selectedOption = useMemo(
    () => options.find((option) => String(option.value) === String(value)),
    [options, value]
  );

  useEffect(() => {
    function handlePointerDown(event) {
      const target = event.target;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  useLayoutEffect(() => {
    if (!open) return undefined;
    let frameId = 0;

    function updatePosition() {
      if (!triggerRef.current) return;

      const rect = triggerRef.current.getBoundingClientRect();
      const menuHeight = menuRef.current?.offsetHeight || DEFAULT_MENU_MAX_HEIGHT;
      const spaceBelow = window.innerHeight - rect.bottom - VIEWPORT_MARGIN;
      const spaceAbove = rect.top - VIEWPORT_MARGIN;
      const openUpward = spaceBelow < Math.min(menuHeight, DEFAULT_MENU_MAX_HEIGHT) && spaceAbove > spaceBelow;
      const maxHeight = Math.max(
        120,
        Math.min(DEFAULT_MENU_MAX_HEIGHT, openUpward ? spaceAbove - MENU_GAP : spaceBelow - MENU_GAP)
      );

      let left =
        align === "right"
          ? rect.right - rect.width
          : rect.left;
      left = clamp(left, VIEWPORT_MARGIN, window.innerWidth - rect.width - VIEWPORT_MARGIN);

      const top = openUpward
        ? Math.max(VIEWPORT_MARGIN, rect.top - Math.min(menuHeight, maxHeight) - MENU_GAP)
        : Math.min(window.innerHeight - VIEWPORT_MARGIN, rect.bottom + MENU_GAP);

      setMenuStyle({
        left,
        top,
        minWidth: rect.width,
        maxWidth: Math.max(rect.width, window.innerWidth - VIEWPORT_MARGIN * 2),
        maxHeight,
        transformOrigin: openUpward ? "bottom center" : "top center",
      });
    }

    updatePosition();
    frameId = window.requestAnimationFrame(updatePosition);

    const handleViewportChange = () => updatePosition();
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    };
  }, [align, open, options.length]);

  function handleWheel(event) {
    const element = menuRef.current;
    if (!element) return;

    const { scrollTop, scrollHeight, clientHeight } = element;
    const deltaY = event.deltaY;
    const canScroll = scrollHeight > clientHeight;
    const atTop = scrollTop <= 0;
    const atBottom = scrollTop + clientHeight >= scrollHeight - 1;

    event.stopPropagation();

    if (!canScroll || (deltaY < 0 && atTop) || (deltaY > 0 && atBottom)) {
      event.preventDefault();
    }
  }

  const menu =
    open && typeof document !== "undefined" && menuStyle
      ? createPortal(
          <AnimatePresence>
            <motion.div
              key="custom-select-menu"
              ref={menuRef}
              role="listbox"
              initial={{ opacity: 0, y: 6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.985 }}
              transition={{ duration: 0.16, ease: "easeOut" }}
              onWheel={handleWheel}
              style={{
                position: "fixed",
                left: menuStyle.left,
                top: menuStyle.top,
                minWidth: menuStyle.minWidth,
                maxWidth: menuStyle.maxWidth,
                maxHeight: menuStyle.maxHeight,
                zIndex: 140,
                overflowY: "auto",
                overscrollBehavior: "contain",
                transformOrigin: menuStyle.transformOrigin,
              }}
              className={`overflow-x-hidden rounded-2xl border border-white/12 bg-[rgba(10,14,24,0.95)] p-1.5 shadow-[0_24px_80px_rgba(2,6,23,0.62)] backdrop-blur-2xl supports-[backdrop-filter]:bg-[rgba(10,14,24,0.82)] ${menuClassName}`}
            >
              {options.map((option) => {
                const isSelected = String(option.value) === String(value);
                return (
                  <button
                    key={String(option.value)}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onChange(option.value);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                      isSelected
                        ? "bg-accent/18 text-white"
                        : "text-white/70 hover:bg-white/[0.06] hover:text-white"
                    }`}
                  >
                    <span className="min-w-0 flex-1 truncate">{option.label}</span>
                    {isSelected ? <Check className="h-4 w-4 text-accent" /> : null}
                  </button>
                );
              })}
            </motion.div>
          </AnimatePresence>,
          document.body
        )
      : null;

  return (
    <>
      <div className={className}>
        <button
          ref={triggerRef}
          type="button"
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          onClick={() => {
            if (!disabled) setOpen((current) => !current);
          }}
          className={`${baseButtonClasses} ${disabled ? "cursor-not-allowed opacity-50" : ""} ${buttonClassName}`}
        >
          {Icon ? <Icon className="h-4 w-4 shrink-0 text-white/35" /> : null}
          <span className="min-w-0 flex-1 truncate text-white/80">{selectedOption?.label || placeholder}</span>
          <ChevronDown className={`h-4 w-4 shrink-0 text-white/35 transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
      </div>
      {menu}
    </>
  );
}
