/**
 * React 19 document metadata — sets <title> and <meta> per page.
 * React 19 hoists these to <head> automatically.
 */

interface PageMetaProps {
  title: string
  description?: string
}

export default function PageMeta({ title, description }: PageMetaProps) {
  return (
    <>
      <title>{title} — AgentFlow PMI</title>
      {description && <meta name="description" content={description} />}
    </>
  )
}
