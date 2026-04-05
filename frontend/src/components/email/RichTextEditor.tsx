import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Image from '@tiptap/extension-image'
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  List, ListOrdered, Link as LinkIcon, Image as ImageIcon,
  AlignLeft, AlignCenter, AlignRight, Heading1, Heading2,
  Undo, Redo, Code,
} from 'lucide-react'
import { useEffect } from 'react'

interface RichTextEditorProps {
  value: string
  onChange: (html: string) => void
  placeholder?: string
}

export default function RichTextEditor({ value, onChange }: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Link.configure({ openOnClick: false }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Image.configure({ inline: true }),
    ],
    content: value || '',
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[200px] px-4 py-3',
      },
    },
  })

  // Sync external value changes
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || '')
    }
  }, [value])

  if (!editor) return null

  const addLink = () => {
    const url = prompt('URL del link:')
    if (url) editor.chain().focus().setLink({ href: url }).run()
  }

  const addImage = () => {
    const url = prompt('URL immagine:')
    if (url) editor.chain().focus().setImage({ src: url }).run()
  }

  const insertVariable = (variable: string) => {
    editor.chain().focus().insertContent(`{{${variable}}}`).run()
  }

  return (
    <div className="rounded-lg border border-gray-300 bg-white overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-0.5 border-b border-gray-200 bg-gray-50 px-2 py-1.5">
        <ToolBtn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Grassetto">
          <Bold className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Corsivo">
          <Italic className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleUnderline().run()} active={editor.isActive('underline')} title="Sottolineato">
          <UnderlineIcon className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="Barrato">
          <Strikethrough className="h-3.5 w-3.5" />
        </ToolBtn>

        <div className="mx-1 h-5 w-px bg-gray-300" />

        <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="Titolo 1">
          <Heading1 className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="Titolo 2">
          <Heading2 className="h-3.5 w-3.5" />
        </ToolBtn>

        <div className="mx-1 h-5 w-px bg-gray-300" />

        <ToolBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Elenco puntato">
          <List className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Elenco numerato">
          <ListOrdered className="h-3.5 w-3.5" />
        </ToolBtn>

        <div className="mx-1 h-5 w-px bg-gray-300" />

        <ToolBtn onClick={() => editor.chain().focus().setTextAlign('left').run()} active={editor.isActive({ textAlign: 'left' })} title="Allinea a sinistra">
          <AlignLeft className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().setTextAlign('center').run()} active={editor.isActive({ textAlign: 'center' })} title="Centra">
          <AlignCenter className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().setTextAlign('right').run()} active={editor.isActive({ textAlign: 'right' })} title="Allinea a destra">
          <AlignRight className="h-3.5 w-3.5" />
        </ToolBtn>

        <div className="mx-1 h-5 w-px bg-gray-300" />

        <ToolBtn onClick={addLink} active={editor.isActive('link')} title="Inserisci link">
          <LinkIcon className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={addImage} title="Inserisci immagine">
          <ImageIcon className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleCodeBlock().run()} active={editor.isActive('codeBlock')} title="Blocco codice">
          <Code className="h-3.5 w-3.5" />
        </ToolBtn>

        <div className="mx-1 h-5 w-px bg-gray-300" />

        <ToolBtn onClick={() => editor.chain().focus().undo().run()} title="Annulla">
          <Undo className="h-3.5 w-3.5" />
        </ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().redo().run()} title="Ripeti">
          <Redo className="h-3.5 w-3.5" />
        </ToolBtn>
      </div>

      {/* Variable quick-insert bar */}
      <div className="flex flex-wrap items-center gap-1 border-b border-gray-100 bg-gray-50/50 px-3 py-1.5">
        <span className="text-[9px] font-semibold uppercase text-gray-400 mr-1">Variabili:</span>
        {['nome', 'azienda', 'deal_name', 'deal_value', 'email'].map((v) => (
          <button key={v} onClick={() => insertVariable(v)}
            className="rounded bg-purple-50 px-1.5 py-0.5 text-[10px] font-mono text-purple-600 border border-purple-200 hover:bg-purple-100">
            {`{{${v}}}`}
          </button>
        ))}
      </div>

      {/* Editor */}
      <EditorContent editor={editor} />
    </div>
  )
}

function ToolBtn({ onClick, active, title, children }: { onClick: () => void; active?: boolean; title: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`rounded p-1.5 transition-colors ${active ? 'bg-purple-100 text-purple-700' : 'text-gray-500 hover:bg-gray-200 hover:text-gray-700'}`}
    >
      {children}
    </button>
  )
}
