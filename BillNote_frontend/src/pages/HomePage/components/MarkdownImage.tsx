import Zoom from 'react-medium-image-zoom'
import 'react-medium-image-zoom/dist/styles.css'

interface MarkdownImageProps {
  alt?: string
  src: string
}

const MarkdownImage = ({ alt = '', src }: MarkdownImageProps) => {
  return (
    <div className="my-8 flex justify-center">
      <Zoom>
        <img
          src={src}
          alt={alt}
          className="max-w-full cursor-zoom-in rounded-lg object-cover shadow-md transition-all hover:shadow-lg"
          style={{ maxHeight: '500px' }}
        />
      </Zoom>
    </div>
  )
}

export default MarkdownImage
