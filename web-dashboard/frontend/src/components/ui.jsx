/* Shared civic UI primitives. Presentation only — no data fetching. */

export function Card({ className = "", children, ...rest }) {
  return (
    <section className={`inv-card ${className}`} {...rest}>
      {children}
    </section>
  );
}

export function CardHeader({ eyebrow, title, subtitle, right, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 px-5 pb-4 pt-5">
      <div className="min-w-0">
        {eyebrow && <p className="metalabel mb-1">{eyebrow}</p>}
        {title && <h2 className="font-display text-[19px] font-semibold tracking-tight text-ink">{title}</h2>}
        {subtitle && <p className="mt-0.5 text-[13px] text-ink-mute">{subtitle}</p>}
      </div>
      {(right || action) && <div className="flex shrink-0 items-center gap-2">{right || action}</div>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && <p className="metalabel mb-1.5">{eyebrow}</p>}
        <h1 className="font-display text-balance text-[30px] font-semibold leading-[1.05] tracking-tight text-ink md:text-[34px]">
          {title}
        </h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-mute">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Tabs({ options, value, onChange, ariaLabel }) {
  return (
    <div role="tablist" aria-label={ariaLabel || "Filter"} className="flex flex-wrap gap-1 rounded-lg border border-line bg-white p-1">
      {options.map((opt) => {
        const active = value === opt.id;
        return (
          <button
            key={opt.id}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.id)}
            className={`rounded-md px-3.5 py-1.5 text-[13px] font-semibold transition-all ${
              active ? "bg-forest text-white shadow-sm" : "text-ink-mute hover:bg-[#F4F2E9] hover:text-ink"
            }`}
          >
            {opt.label}
            {opt.count != null && (
              <span className={`tnum ml-1.5 rounded px-1.5 py-0.5 font-mono text-[11px] ${active ? "bg-white/20" : "bg-[#EFECE1] text-ink-mute"}`}>
                {opt.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* Keep old export name working for any lingering imports */
export const SegmentedControl = Tabs;

export function LoadingState({ label = "Loading…" }) {
  return (
    <div className="inv-card px-6 py-10">
      <div className="mx-auto flex max-w-xs items-center justify-center gap-3.5">
        <span className="brand-pulse flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-forest text-[15px] font-bold text-civic-lime">
          ◈
        </span>
        <div className="text-left">
          <p className="text-sm font-semibold text-ink">{label}</p>
          <div className="mt-1.5 h-1 w-40 overflow-hidden rounded-full bg-[#EDEAE0]">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-forest" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-xl border border-[#F2C4B8] bg-[#FDF0EC] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-civic-coral/15 text-civic-coral">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
            </svg>
          </span>
          <div>
            <p className="font-display text-[16px] font-semibold text-ink">Feed unreachable</p>
            <p className="mt-0.5 text-sm text-ink-soft">{message}</p>
          </div>
        </div>
        {onRetry && (
          <button onClick={onRetry} className="inv-btn-primary">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint, icon, action }) {
  return (
    <div className="inv-card flex flex-col items-center px-6 py-12 text-center">
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-forest text-civic-lime">
        {icon || (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 20A7 7 0 0 1 4 13c0-4 3-8 8-10 5-2 8-1 8-1s-1 8-4 12c-2 3-4 5-5 6ZM5 21c4-6 8-9 12-11" />
          </svg>
        )}
      </span>
      <p className="font-display text-[18px] font-semibold text-ink">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-[13px] leading-relaxed text-ink-mute">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/* Tiny inline sparkline — pure SVG, data-driven, no chart lib */
export function Sparkline({ values = [], width = 120, height = 36, stroke = "#123D32" }) {
  if (!values.length) return <div style={{ width, height }} />;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const pts = values
    .map((v, i) => `${(i * step).toFixed(1)},${(height - 4 - ((v - min) / span) * (height - 8)).toFixed(1)}`)
    .join(" ");
  const id = `sg-${stroke.replace("#", "")}-${values.length}-${Math.round(values.reduce((a, b) => a + b, 0))}`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${height} ${pts} ${width},${height}`} fill={`url(#${id})`} />
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* Smooth area chart — pure SVG, real data */
export function AreaChart({ values = [], labels = [], height = 180, stroke = "#123D32" }) {
  const w = 600;
  const h = height;
  const pad = 8;
  if (!values.length) return <div style={{ height: h }} className="flex items-center justify-center text-sm text-ink-mute">No data yet</div>;
  const max = Math.max(...values, 1);
  const step = values.length > 1 ? (w - pad * 2) / (values.length - 1) : 0;
  const y = (v) => h - 26 - (v / max) * (h - 52);
  const x = (i) => pad + i * step;
  let d = `M ${x(0).toFixed(1)},${y(values[0]).toFixed(1)}`;
  for (let i = 1; i < values.length; i++) {
    const x0 = x(i - 1);
    const x1 = x(i);
    const xc = (x0 + x1) / 2;
    d += ` C ${xc.toFixed(1)},${y(values[i - 1]).toFixed(1)} ${xc.toFixed(1)},${y(values[i]).toFixed(1)} ${x1.toFixed(1)},${y(values[i]).toFixed(1)}`;
  }
  const area = `${d} L ${x(values.length - 1).toFixed(1)},${h - 22} L ${x(0).toFixed(1)},${h - 22} Z`;
  const gid = `ag-${values.length}-${Math.round(values.reduce((a, b) => a + b, 0))}`;
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: h }} role="img" aria-label="7-day report volume">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={pad} x2={w - pad} y1={22 + f * (h - 48)} y2={22 + f * (h - 48)} stroke="#E2E7DE" strokeDasharray="3 4" />
        ))}
        <path d={area} fill={`url(#${gid})`} />
        <path d={d} fill="none" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
        {values.map((v, i) => (
          <g key={i}>
            <circle cx={x(i)} cy={y(v)} r={i === values.length - 1 ? 4.5 : 3} fill="#fff" stroke={stroke} strokeWidth="2.5" />
            {i === values.length - 1 && (
              <text x={x(i)} y={y(v) - 12} textAnchor="middle" fontSize="12" fontWeight="700" fill="#123D32">{v}</text>
            )}
          </g>
        ))}
      </svg>
      {labels.length > 0 && (
        <div className="mt-1 flex justify-between px-1">
          {labels.map((l, i) => (
            <span key={i} className="text-[10px] font-semibold uppercase tracking-wide text-ink-mute">{l}</span>
          ))}
        </div>
      )}
    </div>
  );
}

/* Donut for class distribution — pure SVG */
export function Donut({ segments = [], size = 150, thickness = 20 }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EDEAE0" strokeWidth={thickness} />
        {segments.map((s, i) => {
          const frac = s.value / total;
          const el = (
            <circle
              key={i}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={thickness}
              strokeDasharray={`${(frac * c).toFixed(1)} ${c.toFixed(1)}`}
              strokeDashoffset={(-offset * c).toFixed(1)}
              strokeLinecap="butt"
            />
          );
          offset += frac;
          return el;
        })}
      </svg>
      <div className="absolute text-center">
        <p className="tnum font-display text-[26px] font-semibold text-ink">{total}</p>
        <p className="metalabel mt-0.5">reports</p>
      </div>
    </div>
  );
}
