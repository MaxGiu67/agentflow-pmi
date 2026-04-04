import { useEffect, useRef } from 'react'
import GjsEditor from '@grapesjs/react'
import type { Editor } from 'grapesjs'
import 'grapesjs/dist/css/grapes.min.css'
import mjmlPlugin from 'grapesjs-mjml'

interface GrapesEditorProps {
  initialHtml?: string
  onHtmlChange?: (html: string) => void
  height?: number
}

export default function GrapesEditor({ initialHtml, onHtmlChange, height = 550 }: GrapesEditorProps) {
  const editorRef = useRef<Editor | null>(null)
  const initialHtmlRef = useRef(initialHtml)

  // Keep ref in sync for onEditor callback
  useEffect(() => {
    initialHtmlRef.current = initialHtml
    if (editorRef.current && initialHtml) {
      // Reload MJML content when AI regenerates
      const mjmlContent = htmlToMjml(initialHtml)
      editorRef.current.setComponents(mjmlContent)
    }
  }, [initialHtml])

  const onEditor = (editor: Editor) => {
    editorRef.current = editor

    // Load initial content
    if (initialHtmlRef.current) {
      const mjmlContent = htmlToMjml(initialHtmlRef.current)
      editor.setComponents(mjmlContent)
    }

    // Track changes — export as compiled HTML (inline CSS)
    editor.on('component:update', () => {
      if (onHtmlChange) {
        try {
          // MJML plugin compiles to HTML with inline styles
          const html = editor.getHtml()
          const css = editor.getCss()
          const full = css ? `<style>${css}</style>${html}` : html
          onHtmlChange(full)
        } catch {
          // Fallback
          onHtmlChange(editor.getHtml())
        }
      }
    })
  }

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden" style={{ height }}>
      <GjsEditor
        grapesjs="https://unpkg.com/grapesjs"
        grapesjsCss="https://unpkg.com/grapesjs/dist/css/grapes.min.css"
        onEditor={onEditor}
        options={{
          height: `${height}px`,
          storageManager: false,
          plugins: [mjmlPlugin],
          pluginsOpts: {
            [mjmlPlugin as unknown as string]: {
              // Export with inline CSS
              overwriteExport: true,
              // MJML fonts
              fonts: {
                'DM Sans': 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap',
              },
            },
          },
          deviceManager: {
            devices: [
              { name: 'Desktop', width: '' },
              { name: 'Mobile', width: '375px', widthMedia: '480px' },
            ],
          },
          canvas: {
            styles: [
              'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap',
            ],
          },
        }}
      />
      <style>{`
        .gjs-one-bg { background-color: #f9fafb !important; }
        .gjs-two-color { color: #374151 !important; }
        .gjs-three-bg { background-color: #863bff !important; }
        .gjs-four-color, .gjs-four-color-h:hover { color: #863bff !important; }
      `}</style>
    </div>
  )
}

/**
 * Convert plain HTML to basic MJML structure for the editor.
 * This wraps HTML content in MJML tags so the MJML plugin can parse it.
 */
function htmlToMjml(html: string): string {
  // If already MJML, return as-is
  if (html.includes('<mjml>') || html.includes('<mj-')) {
    return html
  }

  // Wrap HTML in MJML structure
  return `
    <mjml>
      <mj-head>
        <mj-attributes>
          <mj-all font-family="-apple-system, BlinkMacSystemFont, 'DM Sans', sans-serif" />
          <mj-text font-size="16px" color="#555555" line-height="1.6" />
          <mj-button background-color="#863bff" border-radius="10px" font-size="16px" font-weight="600" />
        </mj-attributes>
      </mj-head>
      <mj-body background-color="#f9fafb">
        <mj-section>
          <mj-column>
            <mj-text>
              ${html}
            </mj-text>
          </mj-column>
        </mj-section>
      </mj-body>
    </mjml>
  `
}
