import React, {
  useState, useEffect, useRef, useCallback, useLayoutEffect,
} from 'react'
import { Stage, Layer, Image as KImage, Rect, Text, Transformer, Group } from 'react-konva'
import { SAMPLE_DATA, NICHE_LABELS } from './sampleData.js'

// ── Constants ──────────────────────────────────────────────────────────────────
const CANVAS_W = 1173
const CANVAS_H = 1341

// ── Utilities ──────────────────────────────────────────────────────────────────
function getSample(niche, fieldName) {
  const samples = SAMPLE_DATA[niche] || {}
  return samples[fieldName] ?? `[${fieldName}]`
}

// ── Field Box (one draggable/resizable region) ─────────────────────────────────
function FieldBox({ name, field, isSelected, niche, onSelect, onChange, rectRef, hideOverlays }) {
  const sample = getSample(niche, name)
  const [isDragging, setIsDragging] = useState(false)

  // Keep an internal ref so we can imperatively sync Konva node state.
  // react-konva sometimes doesn't re-apply controlled props after a drag/transform
  // has caused the node's internal state to diverge — imperative sync fixes that.
  const nodeRef = useRef(null)

  useEffect(() => {
    const node = nodeRef.current
    if (!node) return
    node.x(field.x)
    node.y(field.y)
    node.width(field.max_width)
    node.height(field.max_height)
    node.scaleX(1)   // reset any residual transform scale
    node.scaleY(1)
    node.getLayer()?.batchDraw()
  }, [field.x, field.y, field.max_width, field.max_height])

  return (
    <Group
      ref={(el) => {
        nodeRef.current = el
        if (typeof rectRef === 'function') rectRef(el)
      }}
      draggable
      onClick={(e) => {
        e.cancelBubble = true
        onSelect(name)
      }}
      onTap={(e) => {
        e.cancelBubble = true
        onSelect(name)
      }}
      onDragStart={(e) => {
        setIsDragging(true)
      }}
      onDragEnd={(e) => {
        setIsDragging(false)
        onChange(name, {
          x: Math.round(e.currentTarget.x()),
          y: Math.round(e.currentTarget.y()),
        })
      }}
      onTransformEnd={(e) => {
        const node = e.currentTarget
        const newW = Math.round(node.width() * node.scaleX())
        const newH = Math.round(node.height() * node.scaleY())
        node.scaleX(1)
        node.scaleY(1)
        onChange(name, {
          x: Math.round(node.x()),
          y: Math.round(node.y()),
          max_width: newW,
          max_height: newH,
        })
      }}
    >
      {/* 1. Invisible Stable Hit Area */}
      <Rect
        x={0}
        y={0}
        width={field.max_width}
        height={field.max_height}
        fill="rgba(0,0,0,0)"
      />
      {/* 2. Visual Overlay (hidden during drag/preview) */}
      <Rect
        name="visual-overlay"
        x={0}
        y={0}
        width={field.max_width}
        height={field.max_height}
        fill={isSelected ? 'rgba(99,102,241,0.12)' : 'rgba(99,102,241,0.04)'}
        stroke={isSelected ? '#6366f1' : 'rgba(99,102,241,0.5)'}
        strokeWidth={isSelected ? 2 : 1}
        visible={!hideOverlays && !isDragging}
        listening={false}
      />
      {/* 3. Text Content */}
      <Text
        x={0}
        y={0}
        width={Math.max(field.max_width, 10)}
        height={Math.max(field.max_height, 10)}
        text={sample}
        fontSize={field.preferred_font_size}
        fontFamily="Inter, Arial, sans-serif"
        align={field.alignment || 'left'}
        verticalAlign="top"
        fill="#000000"
        wrap="word"
        ellipsis
        listening={false}
      />
    </Group>
  )
}

// ── Main App ───────────────────────────────────────────────────────────────────
export default function App() {
  const [niches, setNiches] = useState({})
  const [selectedNiche, setSelectedNiche] = useState('career_resources')
  const [layout, setLayout] = useState({})        // canonical coords always
  const layoutRef = useRef(layout)
  layoutRef.current = layout

  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const historyIndexRef = useRef(-1)

  const [selectedField, setSelectedField] = useState(null)
  const [templateImg, setTemplateImg] = useState(null)
  const [displayScale, setDisplayScale] = useState(0.5)
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const [rendering, setRendering] = useState(false)
  const [renderResult, setRenderResult] = useState(null) // base64 png
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [spacePressed, setSpacePressed] = useState(false)

  const isHydratingRef = useRef(false)
  const abortControllerRef = useRef(null)

  const canvasContainerRef = useRef(null)
  const trRef = useRef(null)
  const fieldRefs = useRef({})   // { fieldName → Konva Rect node }
  const stageRef = useRef(null)

  const handleNicheChange = (id) => {
    if (hasUnsavedChanges) {
      if (!window.confirm("You have unsaved changes. Discard?")) return
    }
    setSelectedNiche(id)
    setHasUnsavedChanges(false)
  }

  // ── Load niche list on mount ─────────────────────────────────────────────────
  useEffect(() => {
    fetch('/niches')
      .then(r => r.json())
      .then(setNiches)
      .catch(() => setStatus('Error: backend not reachable'))
  }, [])

  // ── Load layout when niche changes ───────────────────────────────────────────
  useEffect(() => {
    setSelectedField(null)
    setRenderResult(null)
    fieldRefs.current = {}
    isHydratingRef.current = true
    fetch(`/layout/${selectedNiche}`)
      .then(r => r.json())
      .then(data => {
        setLayout(data)
        setHistory([data])
        setHistoryIndex(0)
        historyIndexRef.current = 0
        setHasUnsavedChanges(false)
        setStatus(`Loaded: ${NICHE_LABELS[selectedNiche] || selectedNiche}`)
        
        setTimeout(() => { isHydratingRef.current = false }, 100)
      })
      .catch(() => setStatus('Error loading layout'))
  }, [selectedNiche])

  // ── Load template image when niche changes ───────────────────────────────────
  useEffect(() => {
    const niche = niches[selectedNiche]
    if (!niche) return
    setTemplateImg(null)
    const img = new window.Image()
    img.onload = () => setTemplateImg(img)
    img.onerror = () => setStatus('Error loading template image')
    img.src = `/templates/${encodeURIComponent(niche.template)}`
  }, [selectedNiche, niches])

  // ── Auto-fit canvas to container ─────────────────────────────────────────────
  useLayoutEffect(() => {
    const el = canvasContainerRef.current
    if (!el) return
    const measure = () => {
      const { width, height } = el.getBoundingClientRect()
      const scaleW = (width - 24) / CANVAS_W
      const scaleH = (height - 24) / CANVAS_H
      setDisplayScale(Math.min(scaleW, scaleH, 1.0))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // ── Sync Transformer to selectedField ────────────────────────────────────────
  useEffect(() => {
    if (!trRef.current) return
    const node = selectedField ? fieldRefs.current[selectedField] : null
    trRef.current.nodes(node ? [node] : [])
    trRef.current.getLayer()?.batchDraw()
  }, [selectedField, layout])

  // ── Update a field's properties (canonical coords) ───────────────────────────
  const updateField = useCallback((name, changes) => {
    setLayout(prev => {
      const newLayout = {
        ...prev,
        [name]: { ...prev[name], ...changes },
      }
      
      setHistory(hPrev => {
        const h = hPrev.slice(0, historyIndexRef.current + 1)
        h.push(newLayout)
        if (h.length > 50) h.shift()
        historyIndexRef.current = h.length - 1
        setHistoryIndex(historyIndexRef.current)
        return h
      })

      return newLayout
    })
    setHasUnsavedChanges(true)
  }, [])

  // ── Undo / Redo Handlers ─────────────────────────────────────────────────────
  const handleUndo = useCallback(() => {
    setHistoryIndex(prev => {
      if (prev > 0) {
        const next = prev - 1
        setLayout(history[next])
        historyIndexRef.current = next
        setHasUnsavedChanges(true)
        return next
      }
      return prev
    })
  }, [history])

  const handleRedo = useCallback(() => {
    setHistoryIndex(prev => {
      if (prev < history.length - 1) {
        const next = prev + 1
        setLayout(history[next])
        historyIndexRef.current = next
        setHasUnsavedChanges(true)
        return next
      }
      return prev
    })
  }, [history])

  // ── Keyboard Controls ────────────────────────────────────────────────────────
  useEffect(() => {
    const keydownHandler = (e) => {
      const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.isContentEditable
      
      // Undo/Redo shortcuts
      if ((e.ctrlKey || e.metaKey) && !isInput) {
        if (e.key === 'z') {
          e.preventDefault()
          if (e.shiftKey) {
            handleRedo()
          } else {
            handleUndo()
          }
          return
        }
        if (e.key === 'y') {
          e.preventDefault()
          handleRedo()
          return
        }
      }

      // Escape to deselect
      if (e.key === 'Escape' && !isInput) {
        setSelectedField(null)
        return
      }
      
      // Spacebar for clean preview
      if (e.code === 'Space' && !isInput) {
        if (!spacePressed) setSpacePressed(true)
        e.preventDefault() // prevent scrolling
        return
      }

      // Arrow keys to move
      if (selectedField && !isInput) {
        const step = e.shiftKey ? 10 : 1
        const moves = {
          ArrowLeft:  { x: -step },
          ArrowRight: { x: +step },
          ArrowUp:    { y: -step },
          ArrowDown:  { y: +step },
        }
        if (moves[e.key]) {
          e.preventDefault()
          setLayout(prev => {
            const f = prev[selectedField]
            if (!f) return prev
            const delta = moves[e.key]
            const updated = {
              ...f,
              x: Math.round(f.x + (delta.x ?? 0)),
              y: Math.round(f.y + (delta.y ?? 0)),
            }
            const newLayout = { ...prev, [selectedField]: updated }

            setHistory(hPrev => {
              const h = hPrev.slice(0, historyIndexRef.current + 1)
              h.push(newLayout)
              if (h.length > 50) h.shift()
              historyIndexRef.current = h.length - 1
              setHistoryIndex(historyIndexRef.current)
              return h
            })

            const node = fieldRefs.current[selectedField]
            if (node) {
              node.x(updated.x)
              node.y(updated.y)
              node.getLayer()?.batchDraw()
            }
            return newLayout
          })
          setHasUnsavedChanges(true)
        }
      }
    }
    
    const keyupHandler = (e) => {
      if (e.code === 'Space') {
        setSpacePressed(false)
      }
    }
    
    const blurHandler = () => {
      // Release space lock if window loses focus
      setSpacePressed(false)
    }

    window.addEventListener('keydown', keydownHandler)
    window.addEventListener('keyup', keyupHandler)
    window.addEventListener('blur', blurHandler)
    return () => {
      window.removeEventListener('keydown', keydownHandler)
      window.removeEventListener('keyup', keyupHandler)
      window.removeEventListener('blur', blurHandler)
    }
  }, [selectedField, spacePressed])

  // ── Deselect on stage click (not on a field) ─────────────────────────────────
  const handleStageClick = (e) => {
    if (e.target === e.target.getStage() || e.target.attrs.name === 'template-bg') {
      setSelectedField(null)
    }
  }

  // ── Save layout ───────────────────────────────────────────────────────────────
  const handleSave = async (currentLayout = layoutRef.current) => {
    setSaving(true)
    setStatus('Saving…')
    try {
      const resp = await fetch(`/layout/${selectedNiche}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ regions: currentLayout }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        setStatus(`Save failed: ${err.detail}`)
      } else {
        setStatus('✓ Saved successfully')
        setHasUnsavedChanges(false)
      }
    } catch {
      setStatus('Save error: network failure')
    } finally {
      setSaving(false)
    }
  }

  // ── Render current slide ──────────────────────────────────────────────────────
  const handleRender = async (currentLayout = layoutRef.current) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    setRendering(true)
    setStatus('Rendering with Pillow…')
    const sampleData = SAMPLE_DATA[selectedNiche] || {}
    try {
      const resp = await fetch(`/render/${selectedNiche}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sample_data: sampleData, layout: currentLayout }),
        signal: abortController.signal
      })
      if (!resp.ok) {
        const err = await resp.json()
        setStatus(`Render failed: ${err.detail}`)
      } else {
        const data = await resp.json()
        setRenderResult(data.image)
        setStatus('✓ Pillow render complete')
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setStatus('Render error: network failure')
      }
    } finally {
      if (abortControllerRef.current === abortController) {
        setRendering(false)
      }
    }
  }

  // ── Debounced Autosave ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!hasUnsavedChanges || isHydratingRef.current) return
    
    const timer = setTimeout(() => {
      handleSave()
    }, 600)
    
    return () => clearTimeout(timer)
  }, [layout, hasUnsavedChanges])

  // ── Debounced Auto-Render ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!hasUnsavedChanges || isHydratingRef.current) return

    const timer = setTimeout(() => {
      handleRender()
    }, 1000)
    
    return () => clearTimeout(timer)
  }, [layout, hasUnsavedChanges])

  // ── Right-panel numeric input handler ─────────────────────────────────────────
  const handlePropChange = (key, raw) => {
    const val = parseInt(raw, 10)
    if (!isNaN(val) && selectedField) {
      updateField(selectedField, { [key]: val })
    }
  }

  const sel = selectedField ? layout[selectedField] : null

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="editor">
      {/* ── Top toolbar ── */}
      <div className="toolbar">
        <span className="toolbar-title">🎯 Calibration Editor</span>
        <span className="status-msg">{status}</span>
        <div className="toolbar-actions">
          <button
            className="btn btn-secondary"
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            title="Undo (Ctrl+Z)"
          >
            ↩ Undo
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1 || history.length === 0}
            title="Redo (Ctrl+Y)"
          >
            ↪ Redo
          </button>
          <button
            className="btn btn-primary"
            onClick={() => handleSave()}
            disabled={saving || Object.keys(layout).length === 0}
          >
            {saving ? 'Saving…' : '💾 Save Layout'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => handleRender()}
            disabled={rendering || Object.keys(layout).length === 0}
          >
            {rendering ? 'Rendering…' : '🖼 Render Slide'}
          </button>
        </div>
      </div>

      <div className="main">
        {/* ── Left sidebar ── */}
        <div className="left-panel">
          <div className="panel-section">
            <div className="panel-label">NICHE</div>
            {Object.entries(NICHE_LABELS).map(([id, label]) => (
              <div
                key={id}
                className={`niche-item ${selectedNiche === id ? 'active' : ''}`}
                onClick={() => setSelectedNiche(id)}
              >
                {label}
              </div>
            ))}
          </div>

          <div className="panel-section">
            <div className="panel-label">FIELDS</div>
            {Object.keys(layout).map(name => (
              <div
                key={name}
                className={`field-item ${selectedField === name ? 'active' : ''}`}
                onClick={() => setSelectedField(name)}
              >
                {name}
              </div>
            ))}
          </div>
        </div>

        {/* ── Canvas area ── */}
        <div className="canvas-area" ref={canvasContainerRef} style={{ position: 'relative' }}>
          {/* Konva canvas */}
          <Stage
            ref={stageRef}
            width={CANVAS_W * displayScale}
            height={CANVAS_H * displayScale}
            scaleX={displayScale}
            scaleY={displayScale}
            onClick={handleStageClick}
            onTap={handleStageClick}
            style={{ display: 'block', margin: '12px auto', cursor: 'default' }}
          >
            <Layer>
              {/* Template background — locked, non-interactive */}
              {templateImg && (
                <KImage
                  name="template-bg"
                  image={templateImg}
                  x={0}
                  y={0}
                  width={CANVAS_W}
                  height={CANVAS_H}
                  listening={false}
                />
              )}

              {Object.entries(layout).map(([name, field]) => (
                <FieldBox
                  key={name}
                  name={name}
                  field={field}
                  isSelected={selectedField === name}
                  niche={selectedNiche}
                  onSelect={setSelectedField}
                  onChange={updateField}
                  rectRef={el => { fieldRefs.current[name] = el }}
                  hideOverlays={spacePressed}
                />
              ))}

              {/* Single Transformer for selected field */}
              <Transformer
                ref={trRef}
                visible={!spacePressed && selectedField !== null}
                rotateEnabled={false}
                flipEnabled={false}
                enabledAnchors={[
                  'top-left', 'top-center', 'top-right',
                  'middle-left', 'middle-right',
                  'bottom-left', 'bottom-center', 'bottom-right',
                ]}
                boundBoxFunc={(oldBox, newBox) =>
                  newBox.width < 10 || newBox.height < 10 ? oldBox : newBox
                }
              />
            </Layer>
          </Stage>

          {/* Pillow Live Render PIP */}
          {renderResult && (
            <div style={{
              position: 'absolute',
              bottom: 24,
              right: 24,
              width: 320,
              backgroundColor: '#1f2937',
              border: '1px solid #374151',
              borderRadius: 8,
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
              overflow: 'hidden',
              zIndex: 50
            }}>
              <div style={{
                backgroundColor: '#374151',
                padding: '6px 12px',
                fontSize: 12,
                fontWeight: 600,
                color: '#e5e7eb',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>Live Backend Render</span>
                <button 
                  onClick={() => setRenderResult(null)}
                  style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 14 }}
                >✕</button>
              </div>
              <img
                src={`data:image/png;base64,${renderResult}`}
                alt="Live Pillow render"
                style={{
                  width: '100%',
                  display: 'block',
                  backgroundColor: '#000'
                }}
              />
            </div>
          )}
        </div>

        {/* ── Right properties panel ── */}
        <div className="right-panel">
          {sel ? (
            <>
              <div className="panel-section">
                <div className="panel-label">FIELD</div>
                <div className="field-name-display">{selectedField}</div>
              </div>

              <div className="panel-section">
                <div className="panel-label">POSITION</div>
                <PropRow label="X" value={sel.x} onChange={v => handlePropChange('x', v)} />
                <PropRow label="Y" value={sel.y} onChange={v => handlePropChange('y', v)} />
              </div>

              <div className="panel-section">
                <div className="panel-label">SIZE</div>
                <PropRow label="Width" value={sel.max_width} onChange={v => handlePropChange('max_width', v)} />
                <PropRow label="Height" value={sel.max_height} onChange={v => handlePropChange('max_height', v)} />
              </div>

              <div className="panel-section">
                <div className="panel-label">FONT</div>
                <PropRow label="Size" value={sel.preferred_font_size} onChange={v => handlePropChange('preferred_font_size', v)} />
                <PropRow label="Min Size" value={sel.minimum_font_size} onChange={v => handlePropChange('minimum_font_size', v)} />
                <PropRow label="Max Lines" value={sel.max_lines} onChange={v => handlePropChange('max_lines', v)} />
              </div>

              <div className="panel-section">
                <div className="panel-label">ALIGNMENT</div>
                <select
                  className="prop-select"
                  value={sel.alignment || 'left'}
                  onChange={e => updateField(selectedField, { alignment: e.target.value })}
                >
                  <option value="left">Left</option>
                  <option value="center">Center</option>
                  <option value="right">Right</option>
                </select>
              </div>

              <div className="panel-section coords-hint">
                <div className="panel-label">COORDINATES</div>
                <div className="hint-text">
                  All values are canonical 1173×1341 pixels.
                  <br />
                  Arrow = 1px · Shift+Arrow = 10px
                </div>
              </div>
            </>
          ) : (
            <div className="no-selection">
              Click a field on the canvas or in the field list to select it.
            </div>
          )}

          <div className="right-panel-actions">
            {hasUnsavedChanges && (
              <div style={{ color: '#fbbf24', fontSize: 11, marginBottom: 8, textAlign: 'center' }}>
                ⚠️ Unsaved changes
              </div>
            )}
            <button
              className={`btn btn-primary btn-full ${hasUnsavedChanges ? 'unsaved' : ''}`}
              onClick={() => handleSave()}
              disabled={saving || Object.keys(layout).length === 0}
            >
              {saving ? 'Saving…' : (hasUnsavedChanges ? '💾 Save Layout *' : '💾 Save Layout')}
            </button>
            <button
              className="btn btn-secondary btn-full"
              onClick={() => handleRender()}
              disabled={rendering || Object.keys(layout).length === 0}
            >
              {rendering ? 'Rendering…' : '🖼 Render Slide'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Reusable numeric property row ──────────────────────────────────────────────
function PropRow({ label, value, onChange }) {
  const [local, setLocal] = useState(String(value))

  // Sync when external value changes (e.g. drag)
  useEffect(() => { setLocal(String(value)) }, [value])

  return (
    <div className="prop-row">
      <label className="prop-label">{label}</label>
      <input
        className="prop-input"
        type="number"
        value={local}
        onChange={e => setLocal(e.target.value)}
        onBlur={() => onChange(local)}
        onKeyDown={e => { if (e.key === 'Enter') onChange(local) }}
      />
    </div>
  )
}
