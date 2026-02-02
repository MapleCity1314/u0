import { useId } from "react";

type Point = { date: string; nav: number };

type Props = {
  data: Point[];
  stroke?: string;
};

function buildPath(values: number[], width: number, height: number) {
  if (values.length === 0) {
    return "";
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = width / Math.max(values.length - 1, 1);
  return values
    .map((value, index) => {
      const x = index * step;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export default function MiniSparkline({ data, stroke = "#10b981" }: Props) {
  const gradientId = useId();
  const values = data.map((item) => item.nav);
  const width = 160;
  const height = 44;
  const linePath = buildPath(values, width, height);
  if (!linePath) {
    return <svg width={width} height={height} className="overflow-visible" />;
  }
  const fillPath = `${linePath} L${width},${height} L0,${height} Z`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.2" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fillPath} fill={`url(#${gradientId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
