import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { atomDark as codeStyle } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface MarkdownCodeBlockProps {
  codeContent: string
  language: string
}

const MarkdownCodeBlock = ({ codeContent, language }: MarkdownCodeBlockProps) => {
  return (
    <SyntaxHighlighter
      style={codeStyle}
      language={language}
      PreTag="div"
      className="!bg-muted !m-0 !p-0"
      customStyle={{
        margin: 0,
        padding: '1rem',
        background: 'transparent',
        fontSize: '0.9rem',
      }}
    >
      {codeContent}
    </SyntaxHighlighter>
  )
}

export default MarkdownCodeBlock
