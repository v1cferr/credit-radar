"use client";

/**
 * Historical series for one indicator.
 *
 * A client component because Recharts needs the DOM. Values arrive as the
 * decimal strings the source published and are parsed to Number only to be
 * plotted: a chart pixel cannot express more precision than a double, and
 * nothing plotted is written back. The tooltip formats from the original
 * string, so the number the reader sees is the number the source published.
 */

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { lineTypeFor, type SeriesPoint } from "@/features/market/series-points";
import { formatDate, formatDecimal } from "@/lib/format";
import { INDICATOR_LABELS } from "@/lib/labels";
import type { Indicator } from "@/lib/api/types";

export function IndicatorHistoryChart({
  indicator,
  points,
}: {
  indicator: Indicator;
  points: SeriesPoint[];
}) {
  const config = {
    value: {
      label: INDICATOR_LABELS[indicator.code].name,
      color: "var(--chart-1)",
    },
  } satisfies ChartConfig;

  const data = points.map((point) => ({
    referenceDate: point.d,
    value: Number(point.v),
    /** The published text, so the tooltip never re-renders a float. */
    published: point.v,
  }));

  return (
    <ChartContainer config={config} className="h-[220px] w-full sm:h-[280px]">
      <LineChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="referenceDate"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={48}
          tickFormatter={(value: string) => formatDate(value).slice(0, 5)}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          width={48}
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => formatDecimal(String(value))}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => formatDate(String(label))}
              formatter={(_value, _name, item) => {
                const published = (item?.payload as { published?: string })
                  ?.published;
                return published ? formatDecimal(published) : null;
              }}
            />
          }
        />
        <Line
          dataKey="value"
          type={lineTypeFor(indicator.kind)}
          stroke="var(--color-value)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ChartContainer>
  );
}
