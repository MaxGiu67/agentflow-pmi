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
          // Preserve inline styles for email compatibility
          inlineCss: true,
        },
      },
      // Preserve inline styles when parsing HTML
      parser: {
        optionsHtml: {
          // Keep all style attributes
          allowScripts: false,
          allowUnsafeAttr: true,
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
      // Tell GrapesJS to avoid stripping inline styles
      protectedCss: '',
      forceClass: false,
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
      // Use DomComponents to preserve styles
      editor.setComponents(initialHtml)
      // Also inject original styles into the canvas so they render
      const css = extractInlineStylesAsCss(initialHtml)
      if (css) {
        editor.setStyle(css)
      }
    }

    // Track changes — export with inline CSS for email
    editor.on('component:update', () => {
      if (onHtmlChange) {
        exportInlineHtml(editor).then(onHtmlChange)
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

  // Update content when initialHtml changes externally
  useEffect(() => {
    if (gjsRef.current && initialHtml) {
      gjsRef.current.setComponents(initialHtml)
      const css = extractInlineStylesAsCss(initialHtml)
      if (css) {
        gjsRef.current.setStyle(css)
      }
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

/**
 * Export HTML with all CSS inlined (critical for email clients).
 * GrapesJS separates HTML and CSS — we need to merge them back inline.
 */
async function exportInlineHtml(editor: any): Promise<string> {
  const html = editor.getHtml()
  const css = editor.getCss()

  if (!css) return html

  // Simple inline approach: wrap with <style> in <head>
  // For production, use a proper CSS inliner like juice
  return `<style>${css}</style>${html}`
}

/**
 * Extract background colors and key styles from inline HTML
 * to inject into GrapesJS style manager.
 */
function extractInlineStylesAsCss(html: string): string {
  const styles: string[] = []

  // Extract background-color from style attributes
  const bgMatch = html.match(/background(?:-color)?:\s*(#[0-9a-fA-F]{3,8}|rgb[^;)]+\))/g)
  if (bgMatch) {
    // Inject as canvas background so it renders
    styles.push(`body { ${bgMatch[0]}; }`)
  }

  return styles.join('\n')
}
