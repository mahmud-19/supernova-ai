/**
 * ConfidenceLegend — upgraded with color swatches and gradient bar.
 * Colors match the actual matplotlib jet/plasma heatmap:
 *   High Confidence  → green  (#22c55e)
 *   Moderate         → yellow (#eab308)
 *   High Uncertainty → red    (#ef4444)
 */

interface ConfidenceLegendProps {
  /** Compact one-line mode for tight spaces (default false) */
  compact?: boolean;
}

export function ConfidenceLegend({ compact = false }: ConfidenceLegendProps) {
  const items = [
    { label: 'High Confidence',    color: '#22c55e', cls: 'green'  },
    { label: 'Moderate Confidence',color: '#eab308', cls: 'yellow' },
    { label: 'High Uncertainty',   color: '#ef4444', cls: 'red'    },
  ];

  return (
    <div className={`confidence-legend ${compact ? 'confidence-legend--compact' : ''}`}>
      {/* Gradient colour bar */}
      <div className="legend-gradient-wrap">
        <span className="legend-gradient-label">Low uncertainty</span>
        <div className="legend-gradient-bar" title="Heatmap colour scale" />
        <span className="legend-gradient-label">High uncertainty</span>
      </div>

      {/* Labelled swatches */}
      <div className="legend-swatches">
        {items.map(({ label, color, cls }) => (
          <span key={cls} className="legend-swatch-item">
            <span
              className="legend-swatch"
              style={{ background: color }}
              aria-hidden="true"
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
