/**
 * The image a link to this dashboard previews as.
 *
 * Deliberately static: the same bytes for every request, generated from
 * nothing but the strings in this file. A link preview is fetched by
 * whatever chat app or crawler the link passes through, so an Open Graph
 * image that read a score, a balance or a collection date would hand that
 * figure to every intermediary along the way. This one cannot, because it
 * has no access to any.
 *
 * The mark echoes the app icon: concentric rings and a sweep line.
 */

import { ImageResponse } from "next/og";

export const alt = "CreditRadar";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const INK = "#0f172a";
const ACCENT = "#38bdf8";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "96px",
          backgroundColor: INK,
          color: "#f8fafc",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "28px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "112px",
              height: "112px",
              borderRadius: "26px",
              border: `2px solid ${ACCENT}`,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "68px",
                height: "68px",
                borderRadius: "34px",
                border: `3px solid ${ACCENT}`,
                opacity: 0.55,
              }}
            >
              <div
                style={{
                  width: "18px",
                  height: "18px",
                  borderRadius: "9px",
                  backgroundColor: ACCENT,
                }}
              />
            </div>
          </div>
          <div style={{ fontSize: "88px", fontWeight: 700, letterSpacing: "-2px" }}>
            CreditRadar
          </div>
        </div>

        <div style={{ marginTop: "48px", fontSize: "40px", color: "#cbd5e1" }}>
          Inteligência de crédito pessoal para o mercado brasileiro
        </div>

        <div style={{ marginTop: "20px", fontSize: "28px", color: "#64748b" }}>
          Observa, normaliza e explica. Nunca age em seu nome.
        </div>
      </div>
    ),
    size,
  );
}
