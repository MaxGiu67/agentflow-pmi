import { useEffect, useRef } from 'react'
import grapesjs from 'grapesjs'
import 'grapesjs/dist/css/grapes.min.css'
import newsletterPlugin from 'grapesjs-preset-newsletter'

interface GrapesEditorProps {
  initialHtml?: string
  onHtmlChange?: (html: string) => void
  height?: number
}

export default function GrapesEditor({ initialHtml, onHtmlChange, height = 550 }: GrapesEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null)
  const gjsRef = useRef<any>(null)

  useEffect(() => {
    if (!editorRef.current || gjsRef.current) return

    const editor = grapesjs.init({
      container: editorRef.current,
      height: `${height}px`,
      width: 'auto',
      storageManager: false,
      plugins: [newsletterPlugin],
      pluginsOpts: {
        [newsletterPlugin as any]: {
          modalTitleImport: 'Importa HTML',
          modalBtnImport: 'Importa',
        },
      },
      deviceManager: {
        devices: [
          { name: 'Desktop', width: '' },
          { name: 'Mobile', width: '375px', widthMedia: '480px' },
        ],
      },
      panels: { defaults: [] },
      canvas: {
        styles: [
          'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap',
        ],
      },
    })

    // Custom styles for the editor UI
    const style = document.createElement('style')
    style.textContent = `
      .gjs-one-bg { background-color: #f9fafb !important; }
      .gjs-two-color { color: #374151 !important; }
      .gjs-three-bg { background-color: #863bff !important; }
      .gjs-four-color, .gjs-four-color-h:hover { color: #863bff !important; }
      .gjs-pn-panel { border: none !important; }
      .gjs-cv-canvas { background-color: #f3f4f6 !important; }
      .gjs-frame-wrapper { border-radius: 8px; overflow: hidden; }
      .gjs-block { border-radius: 6px; }
    `
    document.head.appendChild(style)

    // Load initial HTML if provided
    if (initialHtml) {
      editor.setComponents(initialHtml)
    }

    // Track changes
    editor.on('component:update', () => {
      if (onHtmlChange) {
        const html = editor.getHtml()
        const css = editor.getCss()
        const full = css ? `<style>${css}</style>${html}` : html
        onHtmlChange(full)
      }
    })

    gjsRef.current = editor

    return () => {
      if (gjsRef.current) {
        gjsRef.current.destroy()
        gjsRef.current = null
      }
      style.remove()
    }
  }, [])

  // Update content when initialHtml changes externally (e.g. AI generation)
  useEffect(() => {
    if (gjsRef.current && initialHtml) {
      gjsRef.current.setComponents(initialHtml)
    }
  }, [initialHtml])

  return (
    <div
      ref={editorRef}
      className="rounded-xl border border-gray-200 overflow-hidden"
      style={{ height }}
    />
  )
}
