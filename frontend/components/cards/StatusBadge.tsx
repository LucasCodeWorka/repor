type StatusBadgeProps = {
  value: "OK" | "PARCIAL" | "CRITICO" | "ALTO" | "MEDIO" | "BAIXO" | string;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value.toUpperCase();
  const tone =
    normalized === "OK" || normalized === "BAIXO"
      ? "ok"
      : normalized === "PARCIAL" || normalized === "MEDIO"
        ? "warn"
        : "bad";

  return <span className={`statusBadge ${tone}`}>{normalized}</span>;
}
