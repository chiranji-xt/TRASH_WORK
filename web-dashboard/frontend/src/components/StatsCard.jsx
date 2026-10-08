export default function StatsCard({ title, value, subtitle }) {
  return (
    <div className="glass-card p-4 md:p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-gray-500">
          {title}
        </p>
        <span className="h-6 w-6 rounded-full bg-black/5 flex items-center justify-center text-xs">
          ⬤
        </span>
      </div>
      <p className="text-2xl md:text-3xl font-semibold leading-none">{value}</p>
      {subtitle && (
        <p className="text-xs text-gray-500 mt-2">{subtitle}</p>
      )}
    </div>
  );
}
