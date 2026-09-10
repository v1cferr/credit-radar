"use client";

/**
 * One or more indicator series on a shared axis.
 *
 * A client component because Recharts needs the DOM. Values arrive as the
 * decimal strings the source published and are parsed to Number only to be
 * plotted: a chart pixel cannot express more precision than a double, and
 * nothing plotted is written back. The tooltip formats from the original
 * string, so the number the reader sees is the number the source published.
 *
 * Several series share one implementation because a comparison is the point
 * of most of these charts, and a separate single-series component would
 * drift from it. Which series belong together is decided in
 * `chart-panels.ts`, which owns the constraint that they share a unit and a
 * publication frequency.
 */

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  lineTypeFor,
  mergeSeries,
  type PlottedSeries,
} from "@/features/market/series-points";
import { formatDate, formatDecimal } from "@/lib/format";
import { INDICATOR_LABELS } from "@/lib/labels";

/** Chart tokens, in the order `chart-panels.ts` lists series. */
const STROKES = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function IndicatorChart({ series }: { series: PlottedSeries[] }) {
  const data = mergeSeries(series);

  const config: ChartConfig = Object.fromEntries(
    series.map((entry, index) => [
      entry.code,
      {
        label: INDICATOR_LABELS[entry.code].name,
        color: STROKES[index % STROKES.length],
      },
    ]),
  );

  return (
    <ChartContainer config={config} className="h-[240px] w-full sm:h-[300px]">
      <LineChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="d"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={48}
          tickFormatter={(value: string) => formatDate(value).slice(3)}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          width={52}
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => formatDecimal(String(value))}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => formatDate(String(label))}
              // Formats the published string, so the tooltip never shows a
              // value re-rendered from a float.
              formatter={(value, name) => {
                const label = config[String(name)]?.label;
                return typeof value === "string" ? (
                  <span className="flex w-full justify-between gap-3">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="numeric font-medium">
                      {formatDecimal(value)}
                    </span>
                  </span>
                ) : null;
              }}
            />
          }
        />
        {series.length > 1 ? (
          <ChartLegend content={<ChartLegendContent />} />
        ) : null}
        {series.map((entry, index) => (
          <Line
            key={entry.code}
            dataKey={entry.code}
            type={lineTypeFor(entry.kind)}
            stroke={STROKES[index % STROKES.length]}
            strokeWidth={2}
            dot={false}
            // A date the source published nothing for stays a gap. Joining
            // across it would draw a rate that was never reported.
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
