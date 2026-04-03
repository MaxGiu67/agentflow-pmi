import { useState, useEffect } from 'react'
import { useEmailTemplates, useSendEmail } from '../../api/hooks'
import { X, Send } from 'lucide-react'

interface SendEmailModalProps {
  open: boolean
  onClose: () => void
  toEmail: string
  toName: string
  contactId?: string
  defaultParams?: Record<string, string>
}

export default function SendEmailModal({ open, onClose, toEmail, toName, contactId, defaultParams }: SendEmailModalProps) {
  const { data: templates } = useEmailTemplates()
  const sendEmail = useSendEmail()

  const [templateId, setTemplateId] = useState('')
  const [subject, setSubject] = useState('')
  const [htmlBody, setHtmlBody] = useState('')
  const [params, setParams] = useState<Record<string, string>>(defaultParams || {})

  useEffect(() => {
    if (templateId && templates) {
      const tpl = templates.find((t: any) => t.id === templateId)
      if (tpl) {
        setSubject(tpl.subject)
        setHtmlBody(tpl.html_body)
      }
    }
  }, [templateId, templates])

  if (!open) return null

  const handleSend = async () => {
    await sendEmail.mutateAsync({
      to_email: toEmail,
      to_name: toName,
      subject,
      html_body: htmlBody,
      template_id: templateId || undefined,
      contact_id: contactId || undefined,
      params,
    })
    onClose()
  }

  // Preview with params substituted
  let previewSubject = subject
  let previewBody = htmlBody
  Object.entries(params).forEach(([k, v]) => {
    previewSubject = previewSubject.replaceAll(`{{${k}}}`, v)
    previewBody = previewBody.replaceAll(`{{${k}}}`, v)
  })

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
          <h3 className="font-semibold text-gray-900">Invia email a {toName}</h3>
          <button onClick={onClose}><X className="h-5 w-5 text-gray-400" /></button>
        </div>

        <div className="space-y-3 p-5">
          <div>
            <label className="text-xs font-medium text-gray-500">Template</label>
            <select value={templateId} onChange={(e) => setTemplateId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">— Scrivi da zero —</option>
              {templates?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500">Destinatario</label>
            <p className="text-sm text-gray-700">{toName} &lt;{toEmail}&gt;</p>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500">Oggetto</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500">Corpo</label>
            <textarea value={htmlBody} onChange={(e) => setHtmlBody(e.target.value)} rows={5}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono text-xs" />
          </div>

          {/* Params */}
          <div>
            <label className="text-xs font-medium text-gray-500">Variabili (nome=valore)</label>
            <div className="mt-1 flex flex-wrap gap-2">
              {['nome', 'azienda', 'deal_name', 'commerciale'].map((k) => (
                <input key={k} value={params[k] || ''} onChange={(e) => setParams({ ...params, [k]: e.target.value })}
                  placeholder={k} className="rounded border border-gray-200 px-2 py-1 text-xs w-28" />
              ))}
            </div>
          </div>

          {/* Preview */}
          {previewBody && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs font-medium text-gray-400 mb-1">Preview:</p>
              <p className="text-sm font-medium text-gray-700">{previewSubject}</p>
              <div className="mt-1 text-xs text-gray-600" dangerouslySetInnerHTML={{ __html: previewBody }} />
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-200 px-5 py-3">
          <button onClick={onClose} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          <button onClick={handleSend} disabled={sendEmail.isPending || !subject}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            <Send className="h-4 w-4" /> {sendEmail.isPending ? 'Invio...' : 'Invia'}
          </button>
        </div>
      </div>
    </div>
  )
}
