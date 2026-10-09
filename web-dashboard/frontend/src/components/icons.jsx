/* Inline SVG icon set — avoids a new icon dependency. */
export function Icon({ d, size = 18, ...rest }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      <path d={d} />
    </svg>
  );
}

export const paths = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  flame: "M12 2c1 4-4 5.5-4 10a4 4 0 0 0 8 0c0-1.5-.5-2.5-1-3.5-1.5 1-2 2-2 3.5A2.5 2.5 0 0 1 8 12C8 7 12 6 12 2Z",
  pin: "M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M9 13h6M9 17h6",
  gear: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.9 2.9l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.9-2.9l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.9-2.9l.1.1a1.7 1.7 0 0 0 1.9.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h0a1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.9 2.9l-.1.1a1.7 1.7 0 0 0-.3 1.9v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z",
  bell: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3",
  truck: "M1 8h13v9H1zM14 11h4l4 4v2h-8zM5.5 20a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6ZM17.5 20a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6Z",
  check: "M20 6 9 17l-5-5",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM12 6v6l4 2",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7ZM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  refresh: "M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6",
  x: "M18 6 6 18M6 6l12 12",
  chevron: "m6 9 6 6 6-6",
  chevronR: "m9 18 6-6-6-6",
  layers: "m12 2 10 5.7L12 13.3 2 7.7ZM2 12.3 12 18l10-5.7M2 16.7 12 22.3l10-5.6",
  leaf: "M11 20A7 7 0 0 1 4 13c0-4 3-8 8-10 5-2 8-1 8-1s-1 8-4 12c-2 3-4 5-5 6ZM5 21c4-6 8-9 12-11",
  alert: "M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z",
  box: "M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16ZM3.3 7 12 12l8.7-5M12 22V12",
  bottle: "M10 2h4v3l2 3v11a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V8l2-3ZM8 12h8",
  glass: "M6 2h12l-2 8a4 4 0 0 1-8 0ZM12 14v7M8 21h8",
  plug: "M9 7V3M15 7V3M7 7h10v4a5 5 0 0 1-10 0ZM12 16v5",
  metal: "M4 20 10 4M14 4l6 16M12 8v8M8 12h8",
  spark: "M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1",
  users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  chart: "M3 3v16a2 2 0 0 0 2 2h16M7 13l3 3 7-7",
  plus: "M12 5v14M5 12h14",
  arrowUR: "M7 17 17 7M8 7h9v9",
  send: "m22 2-7 20-4-9-9-4ZM22 2 11 13",
  route: "M6 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM18 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM6 16h7a4 4 0 0 0 0-8H9",
  calendar: "M8 2v4M16 2v4M3 8h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
};

/* Waste-class → icon / chip color mapping, tuned to the civic palette. */
export function wasteMeta(name) {
  const n = String(name || "Unknown").toLowerCase();
  if (n.includes("plastic") || n.includes("bottle") || n.includes("poly"))
    return { icon: paths.bottle, bg: "#EAF1F8", tx: "#2B5F8A", bd: "#C3D6E8", dot: "#2F7FD1" };
  if (n.includes("paper") || n.includes("cardboard") || n.includes("wood"))
    return { icon: paths.box, bg: "#FAF1DE", tx: "#8A5F14", bd: "#EBD3A0", dot: "#C08A2D" };
  if (n.includes("glass"))
    return { icon: paths.glass, bg: "#E6F4F1", tx: "#1F6E66", bd: "#BFE0D8", dot: "#3AA8A0" };
  if (n.includes("metal") || n.includes("tin") || n.includes("aluminium") || n.includes("aluminum") || n.includes("steel"))
    return { icon: paths.metal, bg: "#ECEFF1", tx: "#4A5A66", bd: "#CBD3D8", dot: "#6B7B8A" };
  if (n.includes("organic") || n.includes("food") || n.includes("wet") || n.includes("leaf") || n.includes("garden"))
    return { icon: paths.leaf, bg: "#E9F2E4", tx: "#2E6B34", bd: "#C2DDB8", dot: "#3E9B4F" };
  if (n.includes("e-waste") || n.includes("electronic") || n.includes("battery") || n.includes("ewaste"))
    return { icon: paths.plug, bg: "#EFECFA", tx: "#4B3A86", bd: "#CFC4EC", dot: "#6F5CC4" };
  if (n.includes("hazard") || n.includes("chemical") || n.includes("toxic") || n.includes("medical"))
    return { icon: paths.alert, bg: "#FBE9E4", tx: "#A03E2E", bd: "#F2C4B8", dot: "#E66B59" };
  return { icon: paths.spark, bg: "#EFF0EA", tx: "#45564F", bd: "#D5D9CF", dot: "#819087" };
}
