import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Circle, Image as KonvaImage, Layer, Line, Stage } from 'react-konva';
import { useNavigate, useParams } from 'react-router-dom';
import Konva from 'konva';
import { api } from '../api/client';
import { CaseDetail } from '../api/types';
import { ConfidenceLegend } from '../components/Legend';
import { AppLayout, Breadcrumb } from '../components/Layout';
import { useToast } from '../components/ToastContext';
import { useObjectUrl } from './hooks';
import { Timeline } from '../components/Timeline';

interface EditorState {
  lines: StrokeLine[];
  savedPolygons: number[][][];
}

type Tool = 'brush' | 'eraser' | 'polygon';
type StrokeLine = { tool: 'brush' | 'eraser'; size: number; points: number[] };

const MASK_COLOR = '#20a75a';
const MIN_SCALE = 0.5;
const MAX_SCALE = 8;
const HANDLE_RADIUS = 6;
const CLOSE_DIST = 14;

function useHtmlImage(url?: string) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!url) { setImage(null); return; }
    const img = new window.Image();
    img.onload = () => setImage(img);
    img.src = url;
    return () => setImage(null);
  }, [url]);
  return image;
}

export function Reannotate() {
  const { id } = useParams();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [tool, setTool] = useState<Tool>('brush');
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [brushSize, setBrushSize] = useState(12);
  const [lines, setLines] = useState<StrokeLine[]>([]);
  const [polygon, setPolygon] = useState<number[][]>([]);         // in-progress polygon
  const [savedPolygons, setSavedPolygons] = useState<number[][][]>([]);
  const [drawing, setDrawing] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [scale, setScale] = useState(1);
  const [stagePos, setStagePos] = useState({ x: 0, y: 0 });
  const [panMode, setPanMode] = useState(false);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const stageRef = useRef<Konva.Stage | null>(null);
  const navigate = useNavigate();
  const imageUrl = useObjectUrl(id ? `/cases/${id}/image` : undefined);
  const heatmapUrl = useObjectUrl(id ? `/cases/${id}/heatmap` : undefined);
  const image = useHtmlImage(imageUrl);
  const heatmap = useHtmlImage(heatmapUrl);
  const [reviewerNote, setReviewerNote] = useState('');
  const [canProceed, setCanProceed] = useState(false);
  const { toast } = useToast();

  // Undo/Redo Stacks
  const [history, setHistory] = useState<EditorState[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Filters State
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [invert, setInvert] = useState(false);

  // Selected polygon index for vertex editing (-1 = none)
  const [selectedPolyIdx, setSelectedPolyIdx] = useState<number>(-1);

  // Refs to prevent stale closures in Konva event handlers
  const linesRef = useRef<StrokeLine[]>([]);
  linesRef.current = lines;
  const savedPolygonsRef = useRef<number[][][]>([]);
  savedPolygonsRef.current = savedPolygons;

  useEffect(() => {
    api.get<CaseDetail>(`/cases/${id}`).then((response) => setCaseData(response.data)).catch((err) => setError(err.response?.data?.detail || 'Unable to load annotation view.'));
  }, [id]);

  function pushState(newLines: StrokeLine[], newPolygons: number[][][]) {
    const nextHistory = history.slice(0, historyIndex + 1);
    nextHistory.push({ lines: newLines, savedPolygons: newPolygons });
    setHistory(nextHistory);
    setHistoryIndex(nextHistory.length - 1);
    setLines(newLines);
    setSavedPolygons(newPolygons);
  }

  function undo() {
    if (historyIndex > 0) {
      const idx = historyIndex - 1;
      setHistoryIndex(idx);
      setLines(history[idx].lines);
      setSavedPolygons(history[idx].savedPolygons);
    } else if (historyIndex === 0) {
      setHistoryIndex(-1);
      setLines([]);
      setSavedPolygons([]);
    }
  }

  function redo() {
    if (historyIndex < history.length - 1) {
      const idx = historyIndex + 1;
      setHistoryIndex(idx);
      setLines(history[idx].lines);
      setSavedPolygons(history[idx].savedPolygons);
    }
  }

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const key = event.key.toLowerCase();
      if (event.ctrlKey || event.metaKey) {
        if (key === 'z') { event.preventDefault(); undo(); }
        if (key === 'y') { event.preventDefault(); redo(); }
      } else {
        if (key === 'b') setTool('brush');
        if (key === 'e') setTool('eraser');
        if (key === 'n') setTool('polygon');
        if (key === 'c') setShowHeatmap((value) => !value);
        if (key === 'escape') { setPolygon([]); setSelectedPolyIdx(-1); }
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [historyIndex, history]);

  // Merge AI contours and user-saved polygons; AI contours come first
  const aiContours = useMemo(() => caseData?.current_result?.contour_json || [], [caseData]);
  // All polygons: [ai_contours..., savedPolygons...]
  const allPolygons = useMemo(() => [...aiContours, ...savedPolygons], [aiContours, savedPolygons]);
  const readOnly = Boolean(caseData?.is_finalized);

  const clampScale = (value: number) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, value));

  function pointer(): number[] | null {
    const stage = stageRef.current;
    const pos = stage?.getRelativePointerPosition();
    if (!pos) return null;
    return [Math.max(0, Math.min(512, pos.x)), Math.max(0, Math.min(512, pos.y))];
  }

  function zoomAtPoint(next: number, screenPoint: { x: number; y: number }) {
    const stage = stageRef.current;
    if (!stage) return;
    const newScale = clampScale(next);
    const old = stage.scaleX();
    const worldX = (screenPoint.x - stage.x()) / old;
    const worldY = (screenPoint.y - stage.y()) / old;
    setScale(newScale);
    setStagePos({ x: screenPoint.x - worldX * newScale, y: screenPoint.y - worldY * newScale });
  }

  function handleWheel(event: Konva.KonvaEventObject<WheelEvent>) {
    event.evt.preventDefault();
    const stage = stageRef.current;
    const screenPoint = stage?.getPointerPosition();
    if (!stage || !screenPoint) return;
    const factor = 1.1;
    const next = event.evt.deltaY > 0 ? stage.scaleX() / factor : stage.scaleX() * factor;
    zoomAtPoint(next, screenPoint);
  }

  function resetView() {
    setScale(1);
    setStagePos({ x: 0, y: 0 });
  }

  function mouseDown() {
    if (panMode || readOnly) return;
    const point = pointer();
    if (!point) return;

    if (tool === 'polygon') {
      if (polygon.length > 2) {
        const [x0, y0] = polygon[0];
        if (Math.hypot(point[0] - x0, point[1] - y0) < CLOSE_DIST) {
          // Close polygon → save
          const nextPols = [...savedPolygonsRef.current, polygon];
          setPolygon([]);
          pushState(linesRef.current, nextPols);
          return;
        }
      }
      setPolygon((points) => [...points, point]);
      return;
    }

    setDrawing(true);
    setLines((items) => [...items, { tool, size: brushSize, points: point } as StrokeLine]);
  }

  function mouseMove() {
    const point = pointer();
    if (point) setCursor({ x: point[0], y: point[1] });
    if (panMode || !drawing || tool === 'polygon') return;
    if (!point) return;
    setLines((items) => {
      const next = items.slice();
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, points: [...last.points, ...point] };
      return next;
    });
  }

  function mouseUp() {
    if (drawing) {
      setDrawing(false);
      pushState(linesRef.current, savedPolygonsRef.current);
    }
  }

  /**
   * Handle vertex drag on a saved polygon.
   * polyIdx is absolute index into allPolygons.
   * We only allow editing user-saved polygons (index >= aiContours.length).
   */
  const handleVertexDrag = useCallback((polyIdx: number, vertIdx: number, x: number, y: number) => {
    const savedIdx = polyIdx - aiContours.length;
    if (savedIdx < 0) return; // Can't edit AI contours
    setSavedPolygons(prev => {
      const next = prev.map(p => [...p]);
      next[savedIdx] = next[savedIdx].map((v, i) => i === vertIdx ? [x, y] : v);
      return next;
    });
  }, [aiContours.length]);

  const handleVertexDragEnd = useCallback((polyIdx: number) => {
    // Push to undo/redo history after drag complete
    const savedIdx = polyIdx - aiContours.length;
    if (savedIdx < 0) return;
    pushState(linesRef.current, savedPolygonsRef.current);
  }, [aiContours.length]);

  // Build the saved mask from layer ALPHA
  function renderMask(): string {
    const layer = document.createElement('canvas');
    layer.width = 512;
    layer.height = 512;
    const lctx = layer.getContext('2d');
    if (!lctx) return '';
    lctx.fillStyle = 'white';
    lctx.strokeStyle = 'white';
    lctx.lineCap = 'round';
    lctx.lineJoin = 'round';
    allPolygons.forEach((shape) => {
      if (shape.length < 3) return;
      lctx.globalCompositeOperation = 'source-over';
      lctx.beginPath();
      lctx.moveTo(shape[0][0], shape[0][1]);
      shape.slice(1).forEach(([x, y]) => lctx.lineTo(x, y));
      lctx.closePath();
      lctx.fill();
    });
    lines.forEach((line) => {
      lctx.globalCompositeOperation = line.tool === 'eraser' ? 'destination-out' : 'source-over';
      lctx.lineWidth = line.size;
      lctx.beginPath();
      for (let index = 0; index < line.points.length; index += 2) {
        const x = line.points[index];
        const y = line.points[index + 1];
        if (index === 0) lctx.moveTo(x, y);
        else lctx.lineTo(x, y);
      }
      lctx.stroke();
    });
    const out = document.createElement('canvas');
    out.width = 512;
    out.height = 512;
    const octx = out.getContext('2d');
    if (!octx) return '';
    octx.fillStyle = 'black';
    octx.fillRect(0, 0, 512, 512);
    octx.drawImage(layer, 0, 0);
    return out.toDataURL('image/png');
  }

  async function saveReannotation() {
    if (!caseData) return;
    setBusy(true);
    setError('');
    try {
      const contour_json = allPolygons.length ? allPolygons : caseData.current_result?.contour_json || [];
      await api.post(`/cases/${caseData.id}/annotate`, {
        contour_json,
        mask_png_base64: renderMask(),
        reviewer_note: reviewerNote || undefined,
      });
      setCanProceed(true);
      toast('success', 'Reannotation saved. You may now proceed.');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Unable to save annotation.';
      setError(msg);
      toast('error', msg);
    } finally {
      setBusy(false);
    }
  }

  function proceedToOutcome() {
    if (!caseData) return;
    navigate(`/cases/${caseData.id}/outcome`);
  }

  const BrushIcon = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 3a1 1 0 0 0-1 1v10.5c0 .83-.67 1.5-1.5 1.5S14 15.33 14 14.5V12H4v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1z"/></svg>;
  const EraserIcon = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 20H7L3 16l10-10 7 7-4.5 4.5"/><path d="M6.5 17.5l3-3"/></svg>;
  const PolyIcon = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 22 20 2 20"/></svg>;
  const EyeIcon = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>;

  // Whether a polygon is editable (only user-saved ones, not AI contours)
  const isEditable = (polyIdx: number) => polyIdx >= aiContours.length;

  return (
    <AppLayout title="Reannotate">
      <Breadcrumb items={['Review Dashboard', 'Expert Review', 'Reannotate']} />
      <div className="annotation-shell">
        {/* Left tool panel */}
        <div className="tool-panel">
          <p className="tool-panel-title">Tools</p>
          {[
            { id: 'brush' as Tool,   icon: <BrushIcon />,  label: 'Brush',   key: 'B' },
            { id: 'eraser' as Tool,  icon: <EraserIcon />, label: 'Eraser',  key: 'E' },
            { id: 'polygon' as Tool, icon: <PolyIcon />,   label: 'Polygon', key: 'N' },
          ].map(t => (
            <button
              key={t.id}
              className={`tool-btn ${tool === t.id ? 'active' : ''}`}
              onClick={() => setTool(t.id)}
              title={`${t.label} (${t.key})`}
            >
              {t.icon}
              {t.label}
              <span className="tool-btn-shortcut">{t.key}</span>
            </button>
          ))}
          <button
            className={`tool-btn ${showHeatmap ? 'active' : ''}`}
            onClick={() => setShowHeatmap(v => !v)}
            title="Toggle Confidence Map (C)"
          >
            <EyeIcon /> Heatmap <span className="tool-btn-shortcut">C</span>
          </button>

          <div className="brush-slider-row" style={{ marginTop: 8 }}>
            <div className="brush-slider-label">
              <span>Brush size</span>
              <span>{brushSize} px</span>
            </div>
            <input type="range" className="brush-slider" min={2} max={60} value={brushSize} onChange={e => setBrushSize(Number(e.target.value))} />
            <div style={{ display: 'flex', gap: 6, margin: '6px 0 10px' }}>
              <button type="button" className="btn btn-ghost btn-xs" style={{ flex: 1, padding: '4px', fontSize: '0.75rem', height: 'auto', minHeight: 'auto' }} onClick={() => setBrushSize(4)}>Fine</button>
              <button type="button" className="btn btn-ghost btn-xs" style={{ flex: 1, padding: '4px', fontSize: '0.75rem', height: 'auto', minHeight: 'auto' }} onClick={() => setBrushSize(12)}>Medium</button>
              <button type="button" className="btn btn-ghost btn-xs" style={{ flex: 1, padding: '4px', fontSize: '0.75rem', height: 'auto', minHeight: 'auto' }} onClick={() => setBrushSize(24)}>Thick</button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 4 }}>
              <div style={{ width: Math.max(6, brushSize * 0.5), height: Math.max(6, brushSize * 0.5), borderRadius: '50%', background: tool === 'eraser' ? '#DC2626' : 'var(--primary)', opacity: 0.7 }} />
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 10, marginTop: 4 }}>
            <p className="tool-panel-title" style={{ marginBottom: 6 }}>View</p>
            <div className="zoom-toolbar" style={{ flexDirection: 'column', alignItems: 'stretch', background: 'transparent', border: 'none', padding: 0, gap: 4 }}>
              <div style={{ display: 'flex', gap: 4 }}>
                <button type="button" style={{ flex: 1 }} onClick={() => zoomAtPoint(scale / 1.25, { x: 256, y: 256 })}>−</button>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', minWidth: 44, textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{Math.round(scale * 100)}%</span>
                <button type="button" style={{ flex: 1 }} onClick={() => zoomAtPoint(scale * 1.25, { x: 256, y: 256 })}>+</button>
              </div>
              <button type="button" onClick={resetView} style={{ width: '100%' }}>Reset view</button>
              <button type="button" style={{ width: '100%', background: panMode ? 'var(--primary-light)' : undefined, borderColor: panMode ? 'var(--primary)' : undefined, color: panMode ? 'var(--primary)' : undefined }} onClick={() => setPanMode(v => !v)}>
                {panMode ? '✋ Pan: On' : '✋ Pan'}
              </button>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 10, marginTop: 4 }}>
            <p className="tool-panel-title" style={{ marginBottom: 6 }}>Editor Actions</p>
            <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
              <button type="button" className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={undo} disabled={historyIndex < 0}>↩ Undo</button>
              <button type="button" className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={redo} disabled={historyIndex >= history.length - 1}>↪ Redo</button>
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Initial AI Segmentation</div>
            {caseData?.current_result?.source === 'expert' && (
              <div style={{ fontSize: '0.8125rem', color: 'var(--primary)' }}>Expert Annotation</div>
            )}
            {selectedPolyIdx >= 0 && (
              <div style={{ marginTop: 8, padding: '6px 8px', background: 'var(--primary-faint)', borderRadius: 'var(--r-sm)', fontSize: '0.75rem', color: 'var(--primary)', border: '1px solid var(--primary-light)' }}>
                ✏️ Editing polygon {selectedPolyIdx + 1} — drag handles to reshape
                <br />
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  style={{ marginTop: 4, padding: '2px 6px', fontSize: '0.7rem', height: 'auto', minHeight: 'auto', width: '100%' }}
                  onClick={() => setSelectedPolyIdx(-1)}
                >
                  Deselect (Esc)
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Centre — canvas */}
        <div>
          {error && <div className="inline-error" style={{ marginBottom: 10 }}>{error}</div>}
          {readOnly && <div className="warning" style={{ marginBottom: 10 }}>This case is finalized and is read-only.</div>}
          <div className="canvas-frame">
            <Stage
              width={512} height={512}
              className={panMode ? 'konva-stage pan-cursor' : 'konva-stage draw-cursor'}
              ref={stageRef}
              scaleX={scale} scaleY={scale}
              x={stagePos.x} y={stagePos.y}
              draggable={panMode}
              onWheel={handleWheel}
              onMouseDown={mouseDown} onMouseMove={mouseMove} onMouseUp={mouseUp}
              onMouseLeave={() => setCursor(null)}
              onTouchStart={mouseDown} onTouchMove={mouseMove} onTouchEnd={mouseUp}
              onDragEnd={e => setStagePos({ x: e.target.x(), y: e.target.y() })}
              style={{ filter: `brightness(${brightness}%) contrast(${contrast}%) invert(${invert ? 100 : 0}%)` }}
            >
              {/* Background image + heatmap layer */}
              <Layer listening={false}>
                {image && <KonvaImage image={image} width={512} height={512} />}
                {showHeatmap && heatmap && <KonvaImage image={heatmap} width={512} height={512} opacity={0.38} />}
              </Layer>

              {/* Polygon + brush strokes layer */}
              <Layer>
                {/* Saved polygons — filled contours */}
                {allPolygons.map((shape, polyIdx) => (
                  <Line
                    key={`c-${polyIdx}`}
                    points={shape.flat()}
                    closed
                    stroke={polyIdx === selectedPolyIdx ? '#FFD700' : MASK_COLOR}
                    strokeWidth={polyIdx === selectedPolyIdx ? 4 : 3}
                    fill={polyIdx === selectedPolyIdx ? 'rgba(255,215,0,0.18)' : 'rgba(32,167,90,0.28)'}
                    globalCompositeOperation="source-over"
                    onClick={() => {
                      if (!readOnly && isEditable(polyIdx)) {
                        setSelectedPolyIdx(prev => prev === polyIdx ? -1 : polyIdx);
                      }
                    }}
                    onTap={() => {
                      if (!readOnly && isEditable(polyIdx)) {
                        setSelectedPolyIdx(prev => prev === polyIdx ? -1 : polyIdx);
                      }
                    }}
                    hitStrokeWidth={10}
                  />
                ))}

                {/* In-progress polygon (being drawn) */}
                {polygon.length > 0 && (
                  <Line points={polygon.flat()} stroke="#efc242" strokeWidth={3} closed={false} />
                )}

                {/* In-progress polygon vertex dots */}
                {tool === 'polygon' && polygon.map(([px, py], vi) => (
                  <Circle
                    key={`pv-${vi}`}
                    x={px} y={py}
                    radius={vi === 0 ? HANDLE_RADIUS + 2 : HANDLE_RADIUS - 2}
                    fill={vi === 0 && polygon.length > 2 ? '#efc242' : '#fff'}
                    stroke="#efc242"
                    strokeWidth={2}
                  />
                ))}

                {/* Brush/eraser strokes */}
                {lines.map((line, i) => (
                  <Line key={i} points={line.points} stroke={MASK_COLOR} strokeWidth={line.size} tension={0.4} lineCap="round" lineJoin="round" opacity={line.tool === 'eraser' ? 1 : 0.85} globalCompositeOperation={line.tool === 'eraser' ? 'destination-out' : 'source-over'} />
                ))}
              </Layer>

              {/* Draggable vertex handles for selected polygon */}
              {selectedPolyIdx >= 0 && !readOnly && isEditable(selectedPolyIdx) && (
                <Layer>
                  {allPolygons[selectedPolyIdx]?.map(([vx, vy], vertIdx) => (
                    <Circle
                      key={`vh-${selectedPolyIdx}-${vertIdx}`}
                      x={vx}
                      y={vy}
                      radius={HANDLE_RADIUS / scale}
                      fill="#FFD700"
                      stroke="#fff"
                      strokeWidth={1.5 / scale}
                      draggable
                      onDragMove={e => {
                        handleVertexDrag(selectedPolyIdx, vertIdx, e.target.x(), e.target.y());
                      }}
                      onDragEnd={() => handleVertexDragEnd(selectedPolyIdx)}
                      onMouseEnter={e => { const c = e.target.getStage(); if (c) c.container().style.cursor = 'grab'; }}
                      onMouseLeave={e => { const c = e.target.getStage(); if (c) c.container().style.cursor = ''; }}
                    />
                  ))}
                </Layer>
              )}

              {/* Cursor preview layer */}
              <Layer listening={false}>
                {!panMode && cursor && tool !== 'polygon' && (
                  <Circle x={cursor.x} y={cursor.y} radius={brushSize / 2} stroke={tool === 'eraser' ? '#d34343' : '#ffffff'} strokeWidth={1 / scale} dash={[4 / scale, 4 / scale]} />
                )}
              </Layer>
            </Stage>
          </div>
          <ConfidenceLegend compact />

          {/* Dynamic Image Adjustments panel */}
          <div className="canvas-controls-panel">
            <div className="canvas-controls-title">
              <span>🎛️ Contrast & Exposure Controls</span>
              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={() => { setBrightness(100); setContrast(100); setInvert(false); }}
                style={{ padding: '2px 8px', fontSize: '0.75rem', height: 'auto', minHeight: 'auto' }}
              >
                Reset Filters
              </button>
            </div>
            <div className="canvas-controls-grid">
              <div className="control-slider-group">
                <label>Brightness <span>{brightness}%</span></label>
                <input
                  type="range"
                  min={50}
                  max={200}
                  value={brightness}
                  onChange={e => setBrightness(Number(e.target.value))}
                  className="control-slider"
                />
              </div>
              <div className="control-slider-group">
                <label>Contrast <span>{contrast}%</span></label>
                <input
                  type="range"
                  min={50}
                  max={200}
                  value={contrast}
                  onChange={e => setContrast(Number(e.target.value))}
                  className="control-slider"
                />
              </div>
            </div>
            <div className="control-toggles">
              <label className="control-checkbox-label">
                <input
                  type="checkbox"
                  checked={invert}
                  onChange={e => setInvert(e.target.checked)}
                  style={{ accentColor: 'var(--primary)', cursor: 'pointer' }}
                />
                Invert Scan Colors
              </label>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => { pushState([], []); setPolygon([]); setSelectedPolyIdx(-1); }}>Clear Edits</button>
            <button className="btn btn-primary" disabled={busy || readOnly} onClick={saveReannotation} id="btn-save-reannotation" style={{ flex: 1 }}>
              {busy ? 'Saving…' : 'Save Reannotation'}
            </button>
            <button className="btn btn-secondary" disabled={!canProceed} onClick={proceedToOutcome} id="btn-continue-outcome" style={{ flex: 1 }} title={!canProceed ? 'Save reannotation first' : ''}>
              Continue to Final Outcome
            </button>
          </div>
        </div>

        {/* Right info panel */}
        <div className="info-panel">
          <h3>Confidence Map</h3>
          <p className="text-sm">{showHeatmap ? 'Overlay visible' : 'Overlay hidden'}</p>
          <p className="text-sm">
            <strong>Brush</strong> adds lesion pixels. <strong>Eraser</strong> reveals scan underneath.
            <br />
            <strong>Polygon</strong> closes on first point. Click a saved polygon to <strong>select & drag</strong> its vertices.
          </p>
          <p className="text-sm">Scroll to zoom · Pan mode to drag · Esc to deselect.</p>

          <h3 style={{ marginTop: 8 }}>Reviewer Note</h3>
          <textarea
            id="reviewer-note"
            rows={5}
            placeholder="Optional clinical observations…"
            value={reviewerNote}
            onChange={e => setReviewerNote(e.target.value)}
          />
          <p className="text-xs text-faint" style={{ marginBottom: 16 }}>Saved with <strong>Save Reannotation</strong>.</p>

          {caseData && (
            <div className="card" style={{ padding: 16, border: 'none', background: 'var(--bg)', boxShadow: 'none' }}>
              <Timeline caseId={caseData.id} />
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
