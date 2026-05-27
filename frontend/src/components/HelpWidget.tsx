import { useState } from 'react';

export function HelpWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        className="help-float-btn"
        onClick={() => setOpen(p => !p)}
        title="Open Onboarding Handbook"
        aria-label="Clinical Guide & Help"
      >
        ?
      </button>

      <div className={`help-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
        <div className="help-drawer-header">
          <h3 style={{ margin: 0 }}>Clinical Handbook</h3>
          <button className="help-drawer-close" onClick={() => setOpen(false)} aria-label="Close guide">×</button>
        </div>

        <div className="help-drawer-body">
          <div className="help-section">
            <h4>💡 UI Dark Mode</h4>
            <p>
              Ultrasound scanning rooms are typically kept dim to prevent glare. Use the Sun/Moon toggle at the top right of the navigation bar to switch to our high-contrast, low-strain Dark Mode.
            </p>
          </div>

          <div className="help-section">
            <h4>🎛️ Image Adjustments</h4>
            <p>
              Under the ultrasound viewport, use the <strong>Contrast Controls</strong> panel to tune exposure, brightness, and contrast. Invert color is highly recommended for identifying faint boundaries on dense scans.
            </p>
          </div>

          <div className="help-section">
            <h4>🎨 Colormap Interpretation</h4>
            <p>
              The AI overlay depicts pixel-wise standard deviation (prediction uncertainty) across the deep learning model ensemble:
            </p>
            <ul>
              <li><strong>Blue/Green</strong>: Low variance. High AI consensus and boundary confidence.</li>
              <li><strong>Yellow/Orange</strong>: Moderate variance. AI suggests checking this zone.</li>
              <li><strong>Red</strong>: High variance. High uncertainty; review note is advised.</li>
            </ul>
          </div>

          <div className="help-section">
            <h4>✍️ Reannotation Editor & Shortcuts</h4>
            <p>
              When adjusting boundary contours on the re-annotation canvas, use the following interactive tool presets:
            </p>
            <ul>
              <li><strong>Brush (B)</strong>: Paint positive lesion pixels.</li>
              <li><strong>Eraser (E)</strong>: Erase boundary pixels to reveal raw ultrasound.</li>
              <li><strong>Polygon (N)</strong>: Place sequential anchors. Click the initial point to close the polygon.</li>
              <li><strong>Heatmap (C)</strong>: Toggle uncertainty map overlay.</li>
              <li><strong>Zoom & Pan</strong>: Enable <strong>Pan mode</strong> to drag, or scroll to zoom.</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
