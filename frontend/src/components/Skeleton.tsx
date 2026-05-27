interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
}

export function Skeleton({ width = '100%', height = '16px', borderRadius = '6px', className = '' }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius }}
      aria-hidden="true"
    />
  );
}

export function SkeletonRow({ cols }: { cols: number }) {
  return (
    <div className="skeleton-table-row">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} height="14px" width={i === 0 ? '80px' : i === 1 ? '140px' : '70px'} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="skeleton-table" aria-label="Loading..." aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} cols={cols} />
      ))}
    </div>
  );
}
