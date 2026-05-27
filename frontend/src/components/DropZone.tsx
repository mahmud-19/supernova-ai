import { DragEvent, useRef, useState } from 'react';

interface DropZoneProps {
  onFile: (file: File) => void;
  uploading?: boolean;
  previewUrl?: string;
}

export function DropZone({ onFile, uploading = false, previewUrl }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function accept(file?: File) {
    if (file) onFile(file);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    accept(event.dataTransfer.files[0]);
  }

  if (previewUrl) {
    return (
      <div className="drop-zone-preview">
        <img src={previewUrl} alt="Selected image preview" />
        <div className="drop-zone-preview-bar">
          <div className={`upload-progress ${uploading ? 'upload-progress-indeterminate' : ''}`}>
            <div className="upload-progress-fill" style={{ width: uploading ? '40%' : '0%' }} />
          </div>
        </div>
        {!uploading && (
          <button
            type="button"
            style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(15,23,42,0.7)', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer' }}
            onClick={() => inputRef.current?.click()}
          >
            Change image
          </button>
        )}
        <input ref={inputRef} type="file" accept="image/png,image/jpeg" onChange={(e) => accept(e.target.files?.[0])} hidden />
      </div>
    );
  }

  return (
    <div
      className={`drop-zone ${dragging ? 'dragging' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      aria-label="Upload image file"
    >
      <input ref={inputRef} type="file" accept="image/png,image/jpeg" onChange={(e) => accept(e.target.files?.[0])} hidden />
      <div className="drop-zone-icon">📁</div>
      <strong>Click or drag & drop an image</strong>
      <span>PNG or JPEG only · max 20 MB</span>
    </div>
  );
}
