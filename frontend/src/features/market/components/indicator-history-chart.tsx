"use client";

/**
 * Historical series for one indicator.
 *
 * A client component because Recharts needs the DOM. Values arrive as
 * decimal strings and are parsed to Number here: a chart pixel cannot
 * express more precision than a double, and nothing plotted is written back.
 * The tooltip formats from the original string, so the number the user reads
 * is the one the source published.
 */

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatDate, formatDecimal } from "@/lib/format";
import { INDICATOR_LABELS } from "@/lib/labels";
import type { ObservationSeries } from "@/lib/api/types";

export function IndicatorHistoryChart({ series }: { series: ObservationSeries }) {
  const config = {
    value: {
      label: INDICATOR_LABELS[series.indicator.code].name,
      color: "var(--chart-1)",
    },
  } satisfies ChartConfig;

  const data = series.observations.map((observation) => ({
    referenceDate: observation.reference_date,
    value: Number(observation.value),
    /** Kept so the tooltip can show the published text, not a re-rendered float. */
    published: observation.value,
  }));

  return (
    <ChartContainer config={config} className="h-[280px] w-full">
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
          type="monotone"
          stroke="var(--color-value)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ChartContainer>
  );
}
