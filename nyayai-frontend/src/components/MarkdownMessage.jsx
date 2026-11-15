import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
export default function MarkdownMessage({ content }) {
  return (
    <div className="chat-prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{
          p:({children})=><p>{children}</p>,
          strong:({children})=><strong className="font-semibold text-stone-900">{children}</strong>,
          ul:({children})=><ul>{children}</ul>,
          ol:({children})=><ol>{children}</ol>,
          li:({children})=><li>{children}</li>,
          a:({href,children})=><a href={href} target="_blank" rel="noreferrer" className="text-forest-700 underline decoration-forest-300 hover:decoration-forest-600">{children}</a>,
          code:({children})=><code>{children}</code>,
          blockquote:({children})=><blockquote>{children}</blockquote>,
        }}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
